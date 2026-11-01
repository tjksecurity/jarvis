# EVA execution-time approval boundary repair

Source: tjksecurity/jarvis main, commit 92f7ca10bf73f2f0fe065b3577c7a6e97ff7e357.
Connected branch and recursive tree confirmed on 2026-10-31. Allowed task workspace
was empty before acquisition; no local owner/checkout or unrelated changes present.
Parent reports no existing owner in available project notes and child listing.
No AGENTS.md found in workspace/ancestor instruction locations, or AGENTS.md and
.agents/skills entries in the complete source tree (tree truncated=false).

Scope: bounded local source repair and offline regression tests. No deployment,
model/provider use, live listeners, package installation, credentials, or live tools.

Acceptance checklist:
- [x] Confirm exact source identity and isolated task workspace.
- [x] Acquire source copy and verify every source blob against connected tree.
- [x] Trace filtered schemas through execution and shell approval semantics.
- [x] Enforce explicit allowed tool set at execution; deny unknown/excluded names.
- [x] Preserve CLI/server interfaces and human confirmation intent.
- [x] Test allowed/excluded/unknown tool calls with side effects mocked.
- [x] Test shell confirmation acceptance, refusal, and unavailable approval.
- [x] Preserve reviewable patch and record exact commands/results/limitations.

Environment: system Python 3.13.2 (32 bit); pytest, anthropic, and FastAPI absent.
rich, dotenv, and httpx present. No dependencies will be installed.
Broader EVA runtime, CLI, FastAPI and PWA acceptance remains unverified.

## Work record

2026-10-31: Read connected main and recursive source tree through existing GitHub
connection. Workspace inspection was read-only and found no files. Acquisition
uses only this authorized repository; no user private data or secrets inspected.

All 33 blobs verified before edits (Git blob SHA-1 including header). One workflow
file has no final newline; its acquisition-added newline was removed to match its
upstream blob exactly. The immutable source-baseline/ copy matches every manifest
blob. jarvis-source/ holds the local repaired tree; no local Git metadata needed.

Confirmed trace: server.main(read_only) uses exclude_tool_tags=(destructive,shell).
Agent.__post_init__ filtered API schemas, but _execute_pending_tools (the actual
method name at this commit) dispatched through unrestricted TOOL_BY_NAME. Shell
used a substring blacklist before subprocess.run(shell=True). The repair snapshots
the advertised custom tool names as a frozenset and requires explicit allowed names
at dispatch, returning ToolResult errors for unknown/excluded tools before run().
Provider-side tool names are not included in that local allow set.

Shell now checks the existing operator callback for every command. Only the boolean
True authorizes execution; false/missing/throwing/non-boolean callbacks fail closed.
The legacy confirm input remains accepted but cannot disable authorization. The
same CLI confirmation and server Authorizer modes remain in use. Documentation and
persona wording describe the changed shell policy.

Independent read-only review confirmed only one in-repository dispatch caller and
compatibility with existing callback bool returns. Existing memory mutations,
voice tools, server reset/memory endpoints and provider-side tools are outside this
bounded exclusion/approval repair; --read-only is not a global sandbox guarantee.
All 18 Python source files parsed successfully with ast.parse; no imports or live
tool execution used for that check.

## Test evidence

- `python verify_source.py` (workspace): 33/33 baseline source blobs match the
  connected tree, including byte lengths/newline identity.
- `python -m unittest discover -s tests -v` (jarvis-source/, independent test
  author run): 28 tests passed; no live provider or tool handler invoked.
- `python run_offline_checks.py --baseline` (workspace): exactly 2 expected
  assertion failures, 0 errors, on the verified unmodified source. Reproduced
  excluded shell execution and shell bypassing the default deny authorizer.
  Subprocess/tool handlers were mocks even during this reproduction. Harness
  exits 0 only when both expected failures are present.
- `python run_offline_checks.py` (workspace, root verification): 28 tests passed,
  0 failures, 0 errors; output saved in offline-test-results.txt. Real code under
  test: Agent construction/execution, tool registry, shell, Authorizer. SDK import
  is stubbed; provider client, registry handlers, subprocess.run/Popen, memory,
  workstation probes and config data are mocked or synthetic. No server starts.

Coverage: all default advertised custom names, read-only shell/write exclusion,
allowed read call, unknown names, explicit empty allow set, required dispatch
policy, registration after construction, schema mutation, per-agent isolation,
provider block skipping/provider names rejected locally, exact result envelopes,
handler exception reporting, and excluded calls preserving one-shot grants.
Shell tests cover approval/refusal with confirm omitted/false/true, non-boolean
truthy responses, missing callback, callback exception/EOF/interrupt, exact
command/cwd/timeout, blank input, timeout, nonzero exit/output/truncation and
server deny/one-shot/session expiry. Approved subprocess calls are mocks.

Independent final source review found no material execution bug; the one-shot
documentation was clarified to show that informational shell commands consume a
grant too. No existing tests/CI were present in the source tree. pytest, Anthropic
and FastAPI remain unavailable in this Python environment; no packages installed.

Limitations: this validates the local execution/approval boundary only, using
synthetic fixtures. No live CLI session, HTTP/PWA integration, model response,
provider tool, credentials, listeners, platform shell execution, production
environment, or broader EVA acceptance was exercised. No changes were committed,
pushed, merged, published or deployed. No blocked gated action was attempted.

## Patch delivery

`python build_patch.py` generated execution-approval-boundary.patch and
changed-files.json (SHA-256 inventory). Exactly 7 repository paths changed:
README.md, MOBILE.md, jarvis/agent.py, jarvis/persona.py,
jarvis/tools/__init__.py, jarvis/tools/shell.py, tests/test_execution_policy.py.

`git -c core.autocrlf=false -c core.eol=lf -C source-baseline apply --check
<absolute-path-to-execution-approval-boundary.patch>` passed. Applied with the
same settings to the separate patch-validation-lf/ copy; all 34 repository and
test files match the repaired copy byte-for-byte, including the 7 changed-file
SHA-256 values. All 19 Python source/test files parse successfully with ast.parse.

The first apply check without explicit line-ending settings passed, but Windows
Git converted all 7 changed files to CRLF, so exact byte comparison failed.
Comparison confirmed only newline differences. The explicit settings above
resolved this artifact validation issue without changing user Git/OS settings.
source-baseline/ remains unchanged for all 33 tracked source blobs.

Supporting local audit files: source-manifest.json, verify_source.py,
build_patch.py, run_offline_checks.py, baseline-regression-results.txt,
offline-test-results.txt, changed-files.json, and this WORK_LOG.md.
No remaining blocker for the bounded local repair. Missing runtime dependencies
and prohibited live actions limit broader acceptance; they were not bypassed.
