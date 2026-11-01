# Execution policy repair reconciliation — 2026-11-01

This commit reconciles the retained execution allowlist and shell approval repair
into `tjksecurity/jarvis` on the non-production branch
`codex/eva-execution-policy-reconciliation-2026-11-01`. Canonical main was verified
at `92f7ca10bf73f2f0fe065b3577c7a6e97ff7e357`, with tree
`2ab1f2645decdd171cb9f32ca085f78371a162bd`. No other branches or open PRs were
present at ownership inspection. This task is the sole reconciliation writer.

## Reconciled behavior

Agent construction snapshots its advertised custom tool names. Local dispatch
requires that explicit allow set and rejects unknown or excluded names before
invoking a handler. Provider-side tools are excluded from local permissions.
Every arbitrary shell call checks the existing operator callback and runs only
after boolean True approval. Missing, failing or refusing callbacks fail closed.
The legacy confirm input cannot bypass authorization. CLI prompt and server
deny/one-shot/session modes remain in use.

The six source/documentation changes and one new regression test file retain the
exact bytes previously reviewed and tested. The original patch is preserved as
`execution-approval-boundary.patch` beside this record, SHA-256
`b1f0e2d5789f94b030989d9f9d5540c945942d33bc514d867ce26fb506e5fe2d`.

## Checks on the reconciled copy

- Existing stdlib unittest suite: **28 tests passed**, 0 failures, 0 errors.
  Command equivalent: `python -m unittest discover -s tests -v`.
  Current output is in `execution-policy-offline-results.txt`.
- All **19 Python source/test files** parse successfully with ast.parse.
- `node --check web/app.js` and `node --check web/sw.js` passed using existing Node.
- The PWA manifest parses as valid JSON.
- `git diff --check` passed for the repaired source. The staged whitespace check
  passes for source and authored documentation, excluding the two exact-byte
  historical artifacts: literal patch context contains required space-only lines,
  and the historical test result uses CRLF. Their original hashes are preserved.
- All **33 upstream source blobs** and **7 retained changed-file hashes** matched
  before reconciliation. No unrelated source changes were present or replaced.

These tests mock provider construction/calls, registry handlers, subprocesses,
memory, configuration and platform probes. No live tool, provider, private data,
HTTP listener, shell command, credential generation or paid call was exercised.

## Preserved historical evidence

`historical-execution-policy-work-log.md` and
`historical-offline-test-results.txt` retain their exact earlier bytes. Their
statements about having made no commits or pushes describe the earlier bounded
local repair, before the November 1 reconciliation request. The raw original
baseline-failure trace remains local because it contains personal filesystem
paths; it reproduced two bypasses with mocked handlers/subprocesses.

## Acceptance limits and follow-up

The environment still lacks prompt_toolkit and FastAPI/Starlette, so full CLI and
ASGI integration acceptance remains blocked. The Anthropic SDK is also absent;
provider boundaries must remain mocked during offline verification. Existing
httpx, pydantic and Rich do not replace the missing frameworks. No dependency
installation or expanded access was performed; prior dependency approval remains
unanswered. Memory/voice tools, direct server mutations and provider-side tools
remain outside this bounded exclusion policy; this is not a global sandbox.

The repository's existing CI workflow checks Markdown links only. CI must be
inspected on the exact resulting branch SHA; its outcome does not establish the
28 local guard tests or product runtime acceptance. The final local/remote SHA
and observed CI state are recorded in the task's reconciliation receipt after
the branch is created. Main is not merged or deployed.

Direct Git transport had a DNS failure. Existing authorized GitHub connection
operations are used for backup; local Git data is materialized only after exact
blob/tree/commit identity verification, with the canonical base as a shallow
boundary. No credentials, network settings, force updates or services changed.
Library attachment retries remain stopped and are independent of Git backup.
