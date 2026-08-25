"""Regression coverage for detached delegated-agent SessionDB ownership."""

from __future__ import annotations

import threading

from hermes_state import SessionDB
from run_agent import AIAgent
from tools.delegate_tool import _open_owned_child_session_db


def _make_session(db: SessionDB, session_id: str) -> None:
    db.create_session(session_id=session_id, source="subagent", model="test")


def _owned_agent(db: SessionDB, session_id: str) -> AIAgent:
    """Build the minimum AIAgent shape needed to exercise close ownership."""
    agent = object.__new__(AIAgent)
    agent._session_db = db
    agent._owns_session_db = True
    agent._session_db_closed = False
    agent._end_session_on_close = True
    agent.session_id = session_id
    agent._active_children = []
    agent._active_children_lock = threading.Lock()
    agent._session_messages = []
    agent.client = None
    return agent


def test_detached_child_connection_survives_parent_close(tmp_path):
    """Reproduce the cron/background ordering without sharing a connection.

    The old delegate path passed ``parent_db`` directly to the child. Cron then
    called ``parent_db.close()`` as soon as its foreground turn returned, and
    the still-running child hit ``self._conn.execute`` with ``_conn is None``.
    """
    db_path = tmp_path / "state.db"
    parent_db = SessionDB(db_path=db_path)
    parent_agent = type("Parent", (), {"_session_db": parent_db})()
    child_db = _open_owned_child_session_db(parent_agent)
    assert child_db is not None
    assert child_db is not parent_db
    _make_session(child_db, "child")

    parent_db.close()

    child_db.append_message("child", "assistant", "still running")
    assert child_db.get_messages("child")[-1]["content"] == "still running"
    child_db.close()


def test_owned_agent_close_closes_only_its_independent_handle(tmp_path):
    db_path = tmp_path / "state.db"
    parent_db = SessionDB(db_path=db_path)
    child_db = SessionDB(db_path=db_path)
    _make_session(parent_db, "parent")
    _make_session(child_db, "child")
    child = _owned_agent(child_db, "child")

    child.close()

    assert child._session_db is None
    assert child._session_db_closed is True
    assert child._get_session_db_for_recall() is None
    parent_db.append_message("parent", "assistant", "parent remains open")
    assert parent_db.get_messages("parent")[-1]["content"] == "parent remains open"
    parent_db.close()


def test_concurrent_detached_children_finish_after_parent_close(tmp_path):
    """Bounded stress harness for the gateway cron + background fan-out race."""
    db_path = tmp_path / "state.db"
    parent_db = SessionDB(db_path=db_path)
    child_dbs = [SessionDB(db_path=db_path) for _ in range(3)]
    for idx, db in enumerate(child_dbs):
        _make_session(db, f"child-{idx}")

    parent_db.close()
    errors = []

    def writer(idx: int, db: SessionDB) -> None:
        try:
            for seq in range(40):
                db.append_message(
                    f"child-{idx}", "tool", f"progress-{seq}", tool_name="stress"
                )
        except Exception as exc:  # pragma: no cover - assertion reports detail
            errors.append(exc)

    threads = [
        threading.Thread(target=writer, args=(idx, db))
        for idx, db in enumerate(child_dbs)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    for idx, db in enumerate(child_dbs):
        assert len(db.get_messages(f"child-{idx}")) == 40
        db.close()
