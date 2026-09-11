# Decision report

This is an interim evidence record, not the phase-5 decision.

The pinned upstream contains more provider support than the handoff assumes:
Claude and Codex are already selectable. Start with those paths and their
native MCP broker before introducing another provider implementation.

Concrete concerns to resolve are subscription-only admission, exact-model
enforcement, Codex tool projection, Claude permission parity, and OS sandbox
availability. Native memory, scheduling and TaskRunner have not yet demonstrated
a reason to replace them.

The Windows build, lint/type checks and wheel packaging pass, but the full
Windows Python baseline fails and aborts after worker timeouts. The Linux
baseline completes with 42 failures; frontend and Linux Electron tests pass.
A native WSL sentinel experiment verifies that a relocated
credential-file mask hides its contents without changing the host file.

The Linux baseline also exposed a critical host-isolation defect: native
sensitive-path checks followed a credential-directory link into the Windows
profile, and a test overwrote the credential file. The prior profile text was
recovered and verified, and credential values redacted from local evidence.
The owner has confirmed revocation of the exposed R2 credential. The completed
[safety gate](security-incident.md) adds an explicit allowed test root, disposable
fake homes, OS isolation without host-home mounts or network, and escaping-link
read/write regressions. The repaired isolated suite reports 93,874 passed,
850 skipped and 9 expected failures, with no failures or errors. These controls
remain required for further tests; the earlier sentinel result alone did not
establish this boundary.

Supported Windows clients expose the requested OpenAI models/efforts and
concrete Anthropic family resolutions without inference prompts. Both dedicated
Linux profiles have completed supported subscription sign-in. The fresh Linux
Claude catalog does not advertise Fable, so that requested binding stays
blocked despite its presence in the earlier Windows catalog. Haiku does not
advertise an effort selector; a fixed low-effort binding cannot be silently
accepted. The Codex effort-option mismatch has now been reproduced offline and
given a narrow compatibility fix; see the
[provider evidence](provider-openai.md#offline-effort-compatibility). A second
focused fix consumes the adapters' successful configuration-response snapshots.
One native Codex turn now passes with exact Terra/high readback before and after
the prompt. Claude's three pre-pause prompts returned generic ACP errors. After
the owner's reported quota reset, a fourth bounded attempt succeeds at exact
Sonnet/high. Both providers now pass native session-manager turns with the
new exact-binding constraint enabled. The earlier quota evidence is preserved;
no fallback or automatic retry was scheduled.

These bounded results do not establish global subscription-only admission or
exact model/effort enforcement across every entry point. The bounded Codex
TaskRunner, heartbeat and two-child scenarios retain exact binding on both
providers. Other role models retain catalog/resolver evidence only.

Codex now also passes a one-time command approval with trusted metadata and a
synthetic execution receipt. Native MCP overlay/broker delivery passes without
a new direct projection. SessionManager and the shared turn-identity publisher
start correctly, but the managed canary turns do not call a tool; caller
injection and session-scoped managed tools remain inconclusive. These results
support continuing through existing native paths before adding a transport.
Claude now also passes provider-process resume, canary recall, active cancellation
and one bounded command approval. Its first command attempt is preserved as a
denial caused by missing cwd metadata; the accepted absolute fixture command
needs no cwd inference and excludes extra capabilities. Passive read behavior
and broad inherited-setting permission parity remain distinct open questions.

TaskRunner's first attempt fails before inference because dedicated providers
fall into shared-runtime allocation. After a narrow routing fix, a second
baseline exposes replanning after a denied pause gate. Both defects are repaired
with regressions. The next live Codex run pauses and resumes in a fresh process,
preserving its completed result and executing only the remaining task.
Claude's corresponding resume exposes missing text-output evidence in the
no-diff review prompt. The focused fix passes 573 related regressions and the
repeated Claude checkpoint/resume passes with two prompts per phase. Native
self-review's auto-approval default, fail-open exception handling and unchecked
post-review retry remain safety limits for unattended writing tasks.

Both providers also recover twelve expected fields from native Markdown memory
and context in fresh sessions, including corrected/retired preferences and
planning relationships. These bounded results support retaining the native task
and memory designs. Offline semantic and lesson stores preserve correction,
retirement, inspection/import/deletion and current guidance across processes.
Lesson deduplication can replace a general rule with a longer conditional rule;
it reports the superseded rule but cannot serve as an exact authority invariant.
Automatic consolidation, issue deduplication and full gateway restart have not
yet been established.

Both providers advance real heartbeat work and two bounded native children,
including useful work while another child waits. Operational model pins are
required, including a named heartbeat-agent override. Native configuration's
minimum fixed child limit is three; the fixture still launches only two.
Heartbeat retains failed work but has no demonstrated finite retry budget.
An offline active-registry restart removes prior task auto-approval and preserves
the completed/pending boundary. Native percentage compaction does not enforce
the desired absolute token stop: the 450k/1M replay remains below its threshold.

Disposable native Git coordination passes worktree discovery, independent
commits, dirty-checkout preservation, base movement and identity checks after
restart. Local Discord events pass sender/thread authorization and persisted
session links. That transport dispatches repeated message IDs twice and ignores
edit/delete events; it supplies no exact underlying-issue identity. These are
bounded findings, not proof of remote GitHub workflows or a live Discord gateway.

The retained `subscription-adapter-full-v4` suite passes after the text-review
fix: 93,979 passed, 850 skipped and nine expected failures, with zero failures
or errors. Its JUnit aggregate records 96,539 cases and 1143.960 seconds. The
573 targeted regressions, formatting, lint, type, documentation and harness
checks also pass. The checkpoint manifest verifies current Python hashes against
the test inventories and records recursive redacted scans without secret values.
The initial
project is not accepted while live-provider scenarios remain incomplete. Jira and larger architectural additions remain
behind their prescribed evaluation phases.
