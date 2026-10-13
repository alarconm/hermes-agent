# Website braces override

The exact `braces` alias in `package.json` is limited to Docusaurus build and
development tooling. Its patterns come from repository configuration and source
files, not from untrusted runtime requests. Do not reuse this override in a
runtime path that accepts user-controlled glob patterns.

Upstream `braces@3.0.3` is still affected by GHSA-vfj7-8cjw-p6xm. The
`@eriche/braces@3.0.3-patch.1` fork closes the advisory's deeply nested curly
brace vector, but **does not provide complete CWE-674 protection**. Deep
parentheses followed by the `expand` to `stringify` call chain can still exhaust
the stack, and `maxDepth: NaN` bypasses its parse limit. Expanded output can
also consume excessive memory. The npm audit result is clean because of the
alias; it is not proof that untrusted patterns are safe.

The fork is published by a different maintainer. Keep the version exact and
the lockfile integrity entry intact. Do not automatically update this alias:
review any future publisher/version or upstream replacement independently,
including the published bytes and actual consumers. The current lockfile pins
the reviewed tarball with SHA512
`lpLhAVYSl5rFB2DpvrEGjRS4KqCCjeIwwDi6mU5gbsWHPjUNp5B8ZGrVdy5IWBTQyBf8iP3GwQHLx1am6+UUGg==`.

Independent review and post-install consumer checks are recorded in the
remediation evidence for this change. Both `chokidar` and `micromatch` must
resolve to the reviewed fork, with no nested original `braces@3.0.3`.
