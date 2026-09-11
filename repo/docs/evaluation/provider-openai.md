# OpenAI subscription provider

## Current evidence

The dedicated Linux evaluation profile is signed in through Codex CLI 0.153.4.
The supported status interface reports ChatGPT sign-in; the official app-server
reports account type `chatgpt`, plan `pro`, and all four requested OpenAI IDs
with their requested effort levels. The catalog probe sends initialize,
account/read and model/list only, with zero inference turns.

Evidence: `live_subscription_catalog.py` and the authored metadata under
`live-subscription-access/062209-517974/codex/results` in the external evidence
directory. The earlier Windows catalog remains separate evidence in
`codex-account-models.json`. The probe removes API-key environment inputs, forces
ChatGPT login mode and the OpenAI provider, records no email/token, and shuts
down its subprocess.

One native `AcpProvider` turn passes using `gpt-5.6-terra` and `high` effort.
The adapter reports those exact settings before and after the prompt, returns
the expected harmless text canary with a native completion frame, and shuts
down cleanly. Evidence is `codex/results/native-smoke.json` in that snapshot.
This proves the bounded native chat case; broader provider acceptance remains
incomplete. Account mode and cleared inputs support the subscription route;
there is no independent service-side billing audit.

## Native lifecycle acceptance

The latest retained suite, `safe-test-proof/subscription-adapter-full-v4`, passes
after the task-review fix: 93,979 passed, 850 skipped and nine expected failures,
with zero failures/errors. The current 573 targeted TaskRunner regressions and
quality checks also pass. `native-capability-checkpoint-verification-v1.json`
records source hashes, scan reports and the remaining acceptance scope. Earlier
proof tables below describe their own historical milestones.

The dedicated profile has completed twenty-three bounded prompts in total: the chat
canary, two denied read attempts, a three-prompt continuity scenario, and a
metadata diagnostic turn that completed without attempting a tool, followed by
one positive command approval, three MCP acceptance turns and one native
session-manager turn with exact binding enabled, six TaskRunner execution/review
turns across the preserved pause failure and successful checkpoint/resume, and
one fresh-session memory recall, two heartbeat turns and two native child turns.
The TaskRunner startup experiment and its
diagnostic sent no inference prompts.
All retained evidence contains counts, booleans and redacted diagnostics,
without raw model/tool output or credentials.

| Scenario | Observed result | Scope |
| --- | --- | --- |
| Initial exact-bound chat | NARROW_BUG, repaired; canary passes | Terra/high readback before and after; native completion and clean shutdown |
| Permission rejection | PASS_NATIVE for callback and denial | Read request reaches Crew; rejecting it ends the turn without returning the canary or changing its fixture |
| Narrow read approval | INCONCLUSIVE | The event is not classified as a shell command, so the evaluator cannot match its exact-command allow rule and rejects it; no broad approval is granted |
| One-time command approval | PASS_NATIVE | Trusted command metadata matches one prepared Python command; one permission is approved, the tool result arrives, and a synthetic receipt proves execution |
| MCP broker delivery | PASS_CONFIGURED | Native overlay and broker deliver the canary tool; one confined backend launch and call, broker tenant metadata, exact Terra/high, clean shutdown |
| Session-bound MCP caller | INCONCLUSIVE | Native factory, SessionManager and identity publication start correctly; the two managed turns complete without calling the tool |
| Provider process restart/resume | PASS_NATIVE after configuration compatibility fixes | Native resume reported, session identity preserved, prior canary recalled without tools, exact binding maintained |
| Active-turn cancellation | PASS_NATIVE | Active before cancel, acknowledged with a positive wait budget, inactive afterwards, clean shutdown |
| TaskRunner pause/process restart | PASS_CONFIGURED after two native bug fixes | Completed result and dependency preserved; remaining task executes once after approval; exact Terra/high throughout |
| Durable memory in a fresh session | PASS_CONFIGURED | Twelve expected fields recovered through native Markdown memory/context, including correction and retirement; no added fields or tool requests |
| Heartbeat starts useful work | PASS_CONFIGURED | Two timer-driven tasks complete with exact Terra/high; idle ticks do not duplicate completed work |
| Two native children | PASS_CONFIGURED | One child completes while another waits for approval; both results return with recorded ownership and exact binding |

Evidence: `live_codex_lifecycle.py` and the authored `native-lifecycle.json`,
`native-lifecycle-approved.json` and `native-continuity.json` under the exported
Codex results. The first two scenarios stop after the rejected read; the
continuity scenario separately uses no tools. None of these exercises the full
gateway's persistent memory, MCP broker, TaskRunner or heartbeat. The read
approval gap needs inspection of the adapter's authoritative tool metadata
before a narrower implementation change or a positive-approval claim.
The diagnostic turn produces no tool or permission frame and therefore adds no
approval evidence. It does report the native adapter's account mode as ChatGPT
Pro. Its `native-permission-shape.json` is retained separately.

## TOOL-01: positive command approval

Source remains the full-suite snapshot at
`/tmp/kirocrew-offline-dmg3jf87/data/repo`, based on the pinned upstream SHA.
The connected namespace retains the dedicated subscription home and no host
home mounts. `live_codex_tool_acceptance.py` prepares one harmless Python
program and permits its exact command once, requiring trusted notification
parameters, matching permission-frame command/cwd, and no requested additional
permissions or network grant. Every other request is rejected.

`native-tool-approval-v1.json` records one tool call, one permission request,
one tool result and native completion. The program creates its expected scratch
receipt and prints a synthetic canary; its source remains unchanged. The model
returns that canary, retains Terra/high and read-only mode, and shuts down.
No durable approval is granted and no raw model/tool output is exported.

The earlier read mismatch is explained by the pinned adapter's
`createCommandActionEvent`: recognized reads carry `kind="read"` and locations,
but no command input. Its later execution permission carries `kind="execute"`
and `rawInput`. Crew deliberately trusts the prior notification for shell
provenance. Unclassified commands retain `kind="execute"` and command input
through `createTerminalCommandEvent`, which is the shape TOOL-01 verifies.
Crew's provenance protection was not changed to obtain this result.

## MCP-01: native overlay and broker

`native_mcp_acceptance.py` calls the native `rewrite_agents`,
`pooled_session_servers` and `run_gatewayd` APIs with one explicitly stubbed
canary server. Backend sharing is disabled. The server runs inside an additional
offline namespace with only its synthetic workspace, a fake home and the runtime.
It records only protocol method names and caller/tenant presence or equality.
No credential watcher is configured for this credential-free server.

`native-mcp-offline-v1.json`, `native-mcp-offline-v2.json` and
`native-mcp-offline-v3.json` preserve successive helper checks in the verified
offline namespace, each with a fresh fake home and scratch subtree. Each proves
initialize, tool listing, one call, the expected result, one backend process,
broker tenant injection and clean shutdown. They send zero inference prompts;
the offline checks do not exercise SessionManager with a real provider.

`native-mcp-connected-v1.json` then proves the native Codex provider receives
the injected tool and returns its canary through a structured tool result. There
is one backend launch and one call. The read-only tool triggers no approval
callback. Tenant metadata proves broker routing; caller identity is absent in
this standalone provider scenario, so it cannot prove session-scoped tools.

The managed follow-ups use `KiroCrewConfig.create_provider_factory` and
`SessionManager` with exact Terra/high, empty model fallback and no warm pool.
The first helper omitted the surface's identity-publication step. The corrected
helper calls native `publish_turn_identity` and verifies the published mapping.
Both provider turns return a native text completion without calling any tool.
The corrected run observes MCP initialize and tools/list, but zero tools/call.
It therefore establishes neither correct caller injection nor a product bug.
These results remain `INCONCLUSIVE`, with both providers and brokers shut down.

Evidence: `native-mcp-managed-connected-v2.json` and
`native-mcp-surface-connected-v3.json`. A zero-inference diagnostic asks the
official app-server to read only those two owned turns; it retains phrase labels,
counts and fingerprints in `native-mcp-owned-diagnostic-v1.json`, with no raw
transcript or credentials. Repeated identical live prompts are not scheduled.

## Existing integration

Upstream already selects `agent.acp_backend="codex"` through `AcpProvider`.
Its public adapter package is `@agentclientprotocol/codex-acp`; registry metadata
for 1.11.0 declares `@openai/codex ^0.153.4`.
The installed adapter starts the official Codex app-server and maps ACP session
configuration and MCP servers onto app-server requests. A replacement transport
is not justified by the source inventory.

Source limitations: direct MCP projection is empty; pooled gateway overlays
need testing. Credential-mask preflight prevents a native Windows session.
Pinned native Linux clients and ACP adapters are installed in WSL scratch
storage. Crew's unchanged sandbox preflight passes there. Fresh interactive
Linux sign-in is complete; no credential files are copied between environments.

## Smallest integration plan

1. Finish and record untouched baseline checks.
2. Install pinned ACP packages in isolated evaluation storage.
3. Prove native preflight outcomes without changing security controls.
4. Enumerate/select the exact model and disable configured fallback.
5. Prefer the native pooled MCP path if it meets tools, approval and lifecycle
   acceptance; add a narrow mirror only if a controlled test shows a gap.
6. Add subscription-only admission and exact-model readback where the existing
   adapter demonstrably lacks them.
7. Exercise one chat, tool/approval, cancel, resume, TaskRunner, heartbeat and
   subagent path, then run retained regressions.

Current provider acceptance classification: `INCONCLUSIVE` overall;
the two configuration compatibility defects are `NARROW_BUG`, repaired and
verified by the initial native chat and exact settings readback.

## Offline effort compatibility

The pinned `@agentclientprotocol/codex-acp` 1.11.0 bundle defines
`REASONING_EFFORT_CONFIG_ID="reasoning_effort"` in `dist/index.js` and
advertises that id with category `thought_level`. Crew previously looked for
`effort`, returning an empty effort list and skipping both live and startup
pushes. The synthetic ACP response in `test/test_codex_effort_transport.py`
reproduced all three failures in the isolated offline environment; five control
cases passed. Evidence is `safe-test-proof/provider-effort-before`.

The focused fix shares the backend's wire id through
`agent_sdk.backends.effort_config_id_for`, using it for discovery, capability
checks and pushes. It preserves native hooks, scheduling, model selection and
transport ownership. Verification is separate from the incident safety proof:

| Evidence | Result |
| --- | --- |
| `safe-test-proof/provider-effort-regressions` | 1,216 passed; zero failures, errors or skips; all three former Codex failures now pass |
| `safe-test-proof/provider-effort-quality` | Formatting, lint, full source/test Flake8, mypy for 1,391 files, docs and encoding gates pass |
| `safe-test-proof/provider-effort-namespace` | Namespace and actual added-line harness-parity checks pass |
| `safe-test-proof/provider-effort-docs-final` | Final documentation and namespace checks pass |
| `safe-test-proof/provider-effort-full` | 93,881 passed, 851 skipped, 9 expected failures; zero failures/errors; 1321.53 seconds |

All changed Python files match the full-run inventory. A documentation-only
follow-up removed a prohibited line-number citation; the final docs gate
checks that revision. Reports are finalized with results after execution.
`provider-effort-verification.json` records source hashes, counts and proof
locations. Earlier failed reproduction and documentation evidence is retained.

This compatibility fix does not provide global admission control. Existing
best-effort startup/effort step-down behavior is retained unless the new exact
binding option is enabled. Earlier acceptance helpers reject mismatched readback
before their own prompts; the new native constraint is being verified below.
Native TaskRunner, heartbeat and subagent acceptance remains incomplete.

## Exact binding constraint

The preserved native snapshot accepts a rejected `high` effort by applying
`medium`, then writes a prompt without requiring the requested readback.
`exact-binding-native-baseline.json` proves this with a synthetic adapter and
memory-only stdin in the offline namespace; it sends no inference. This is a
`FEATURE_GAP` against the handoff's fixed-binding requirement.

`agent.require_exact_binding=true`, paired with `agent.fallback_model=""`, now
threads a fixed model/effort constraint through the native provider factory.
It rejects unresolved settings, unsupported adapters, effort reductions and
setting changes. Startup requires matching adapter readback, and the client
checks the same constraint immediately before every prompt write. Transport
reset and missing/malformed snapshots invalidate old readback. Startup refusal
closes the owned client. The option defaults off for existing configurations.

Verification is in progress. The first targeted run retained 1,611 passes and
two failures that exposed stale readback after transport reset. The reset repair
passes all 1,613 cases in `safe-test-proof/exact-binding-regressions-v2`.
The final missing-snapshot cases bring the targeted result to 1,636 passes in
`safe-test-proof/exact-binding-regressions-v3`. Formatting, full lint, type,
documentation and subprocess-encoding checks pass in
`safe-test-proof/exact-binding-quality-v3`. The first full suite completed with
three failures: the generated config baseline and capability disposition row
needed updating, and an upstream SQLite fallback test left a replacement module
loaded. The original failures are retained in `safe-test-proof/exact-binding-full-v1`.
The baseline is regenerated offline; the missing disposition is documented;
the fallback test now restores both module and parent-package identities.
All 853 targeted routing/config/knowledge checks pass. A fresh full suite is
running with those repairs and the task-routing change.

`native-exact-binding-v1.json` proves a native `SessionManager` turn built by
`KiroCrewConfig.create_provider_factory` with the constraint enabled. The signed-in
ChatGPT profile returns the canary at Terra/high, with matching adapter readback
before and after, native completion and clean shutdown. Source snapshot:
`/tmp/kirocrew-offline-wp226qg7/data/repo`. Authentication is still verified
separately through the official client. This option does not itself establish
subscription mode or consume the candidate role matrix.

## Configuration response readback

Both adapters return the current configuration in successful
`session/set_config_option` responses without necessarily sending an update
notification. Crew discarded that response, leaving its public snapshot at the
initial model, effort and mode. The initial live preflight sent no prompt after
detecting this stale readback. Its evidence is retained as
`native-preflight-initial.json`.

`AcpClient.set_config_option` now consumes the returned `configOptions` and
refreshes advertised effort choices, preserving separately advertised modes.
It never substitutes the requested value for an actual adapter response.
Missing/malformed lists and rejected requests preserve the existing snapshot;
an empty list clears it. The owning ACP spec and focused regressions cover both
backends.

| Evidence | Result |
| --- | --- |
| `safe-test-proof/config-readback-before` | 18 passed, 4 expected reproduction failures |
| `safe-test-proof/config-readback-regressions` | 819 passed; zero failures, errors or skips |
| `safe-test-proof/config-readback-regressions-v2` | 988 passed, including the catalog-cache isolation repair; zero failures, errors or skips |
| `safe-test-proof/config-readback-quality` | Formatting, full lint, mypy, documentation and encoding checks pass |
| `safe-test-proof/config-readback-quality-v2` | All quality checks pass after the test-fixture repair |
| `safe-test-proof/config-readback-full` | One existing routing test failed after receiving a catalog cached by an earlier test; original failure retained |
| `safe-test-proof/config-readback-full-v2` | 93,895 passed, 851 skipped, 9 expected failures; zero failures/errors; 1329.40 seconds |

The full run exposed a shared test-state dependency: a stale advertised catalog
folded the routing test's prefixed model ID to a bare ID. A module fixture gives
each ACP coverage test a fresh catalog cache and restores the prior object.
The original wire-routing assertions remain unchanged; no test is disabled.

## Isolated live acceptance environment

The authorized connected step uses fresh, dedicated Linux evaluation homes,
read-only client/runtime mounts, an empty working repository, a cleared
environment and no host-home/Windows-drive mounts. Subscription login must use
the clients' interactive flows; credentials stay in those dedicated profiles.
Codex is pinned to ChatGPT login and the OpenAI provider; Claude uses its
explicit subscription login flag. Account results are reduced to account mode
and plan, excluding tokens and personal identifiers.

The initial implementation binding is `gpt-5.6-terra` with `high` effort.
An unavailable binding or unverifiable account mode stops the acceptance helper
before a prompt. Broader lifecycle, TaskRunner and background acceptance must
be recorded separately from the passing chat canary.

The owner explicitly authorized networking for these isolated sign-ins and
bounded live provider acceptance. Automated regression tests remain offline
with disposable fake homes and credentials. The connected namespace verifies
that host homes and Windows mounts are absent and checks TLS to the providers.
The Node dependency mount retains its `node_modules` basename for package
resolution. Both pinned clients pass an offline version check, and the login
terminal passes an offline input check with a harmless canary. Interactive
login output is not captured in the evidence artifacts.

The owner enabled Codex device code authorization and completed its supported
interactive sign-in. Both Linux provider profiles are authenticated. Claude's
live inference is paused because the owner reports exhausted quota and an
approximately two-hour reset; see the [Anthropic report](provider-anthropic.md).

Official references:
[App-server protocol](https://learn.chatgpt.com/docs/app-server),
[authentication](https://learn.chatgpt.com/docs/auth).

The final documentation and actual added-line harness-parity checks are retained
in `safe-test-proof/config-readback-final-docs`. Changed Python files match
the full, targeted and quality source inventories. The milestone report is
`subscription-checkpoint-verification.json`; it links the redacted scans
and records the incomplete live acceptance without altering incident proof.
