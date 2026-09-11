# Anthropic subscription provider

The dedicated Linux Claude Code 2.1.263 profile is signed in through the
supported `auth login --claudeai` flow. Official status and the SDK catalog
report `claude.ai`, first-party provider, Max subscription and no API-key source.
The native ACP session also reports account/Claude Max through its status
notifications. Only account mode and plan are retained, without personal
identifiers or credential values.

The pinned Linux client and ACP adapter are also installed in WSL. The Linux
client has completed fresh subscription sign-in; Windows credential files are
not copied into the Linux environment.
Networking for isolated subscription sign-ins and bounded live acceptance is
explicitly authorized. Automated tests remain offline with fake credentials.
The fresh Linux profile has no inherited cloud environment or host-home mounts.
Interactive sign-in uses Windows Terminal and a controlling terminal. A private
input reader shows asterisks and forwards the manual code only to the official
CLI's standard input. It resolves the unusable native input widget without
putting the code in arguments, environment variables or logs. No login output
or credential file is copied into evidence.

Upstream already implements `agent.acp_backend="claude"` through
`@agentclientprotocol/claude-agent-acp`. Registry metadata for 0.76.0 declares
official `@anthropic-ai/claude-agent-sdk 0.3.257`.
Reuse requires testing its subscription authentication, concrete model catalog,
permission behavior and native lifecycle.

The [owning spec](../system-specs/modules/claude-code-provider.md) records
inherited Claude settings as a permission-gate gap. A caller-supplied
`CLAUDE_CONFIG_DIR` is forwarded, but no isolated authenticated root is created
by core. Do not copy credentials or run inherited project hooks to solve this.
Use a supported client login in the evaluation environment.

Ambient API keys, provider overrides, API-key helpers, Console/profile
authentication and model substitution must not silently change account mode.
A status result is a prerequisite, not proof that a subsequent turn used it.

The official programmatic guide says `--bare` does not use subscription login;
therefore bare mode cannot satisfy this handoff.

## Catalog probe

The official Agent SDK 0.3.257 initialized the installed Linux Claude Code
2.1.263 client with an empty input stream. `accountInfo()` reports first-party
Claude Max and no API-key source; `supportedModels()` supplies concrete resolved
IDs. The probe passes no prompts, denies tools, disables hooks, uses an empty
working directory, excludes user/project settings, removes ambient API/provider
environment inputs and requests `forceLoginMethod="claudeai"`.

| Requested family | Advertised concrete resolution | Effort evidence |
| --- | --- | --- |
| Fable | Absent from the fresh Linux catalog; requested binding remains blocked | not verified in this environment |
| Opus | `claude-opus-5[1m]` | high supported |
| Sonnet | `claude-sonnet-5` | high supported |
| Haiku | `claude-haiku-4-5-20251001` | no effort capability/selector advertised |

Evidence: `live_subscription_catalog.py`, `live_claude_catalog.mjs` and
`live-subscription-access/062209-517974/claude/results/catalog.json` in the
external evidence directory. The earlier Windows catalog in
`claude-account-models.json` advertises Fable with selector
`claude-fable-5-1[1m]` and resolved ID `claude-fable-5-1`. That result does not
establish availability in the fresh Linux profile; no replacement is selected.

## Native session, quota pause and successful resumption

Native startup passes with adapter 0.76.0 and exact `claude-sonnet-5` / `high`
settings, permission mode `default`, and clean shutdown. The authored fresh
profile sets both `model` and `availableModels` to the concrete Sonnet ID.
This supported configuration preserves the concrete selector instead of the
adapter's `sonnet` alias. It does not alone enforce every native entry point.

Crew also needs the shared configuration-response readback fix documented in
the [OpenAI report](provider-openai.md#configuration-response-readback).
The acceptance helper requires exact readback before dispatching its prompt.

Three bounded one-prompt attempts returned a generic ACP `Internal error`.
The diagnostic artifact contains only known error phrases and fingerprints;
no successful Claude inference is claimed. The owner subsequently reported
exhausted quota, with a reset expected in approximately two hours. That quota
attribution comes from the owner, not from the generic adapter error frame.
Claude inference was paused with no automatic retry, alternative model or
provider substitution. No reset timer was installed.

Evidence is the authored `native-preflight.json`, `native-smoke*.json` and
`quota-pause.json` in the same metadata snapshot. That pause record remains
unchanged.

At 08:21 UTC, one bounded attempt after the reported reset succeeded. Native
`SessionManager` and `KiroCrewConfig.create_provider_factory` used
`agent.require_exact_binding=true`, no configured fallback, concrete
`claude-sonnet-5` and `high`. The runtime reported matching settings before and
after the turn, returned the exact canary, emitted native completion and shut
down cleanly. Official status reported `claude.ai`, first-party provider and Max
before launch. This was the fourth inference attempt, including the three
pre-pause failures; there was no automatic retry.

Evidence: `native-exact-binding-claude-v1.json` and its `-started.json` record in
the dedicated profile's results, exported as authored metadata only. The source
snapshot is `/tmp/kirocrew-offline-wp226qg7/data/repo`. A preceding launcher
attempt stopped before session creation because its helper filename collided
with the Codex helper; the distinct Claude scenario name resolved that local
issue without changing either client or using inference.

Subsequent bounded native runs pass Markdown memory recall, two timer-driven
heartbeat tasks and two child agents. TaskRunner's first pause succeeds, but
resume exposes a no-diff reviewer prompt that omitted the task result. After
the focused prompt fix and 573 passing regressions, the repeated pause and
fresh-process resume both succeed with completed results preserved. Every
successful phase keeps Sonnet/high and closes its providers. Evidence is linked
from the corresponding native capability reports.

Twenty-two inference attempts have been made in total: three pre-quota failures,
one exact chat, one memory recall, two heartbeat turns, two child turns, four
initial TaskRunner turns, four post-fix TaskRunner turns and three continuity
turns and two command-approval attempts. No automatic quota
retry or model substitution occurs.

Chat, the tested task checkpoint, heartbeat and children are `PASS_CONFIGURED`.
Provider-session resume and active cancellation also pass in
`native-continuity-claude-v1.json`: the native resume flag and session identity
match, the restarted provider recalls the previous synthetic canary, and a
separate active turn acknowledges cancellation. Exact binding and clean shutdown
hold throughout.

## Bounded command approval

`native-tool-approval-claude-v1.json` preserves the initial rejected attempt:
trusted shell metadata names the exact command, but its permission payload lacks
Codex's cwd field. The evaluator refuses, the fixture is unchanged and no receipt
is written. A separate read event completes before that denied command; this is
not proof that every read asks permission. No raw content or path is exported.

The v2 scenario admits only the prepared absolute Python executable and absolute
fixture-script path. The script uses exclusively absolute paths within the
disposable workspace. A supplied cwd must match; missing cwd is not needed to
interpret that command. An explicit metadata key allowlist, bounded timeout,
and refusal of background execution exclude extra capabilities. Native trusted
shell classification and exact command matching remain required.

One native approval executes once, writes the exact synthetic receipt, returns
the canary, and keeps the fixture unchanged. Sonnet/high and clean shutdown hold.
Evidence: `native-tool-approval-claude-v2.json` and its start record. This is
`PASS_CONFIGURED` for one bounded command and `PASS_NATIVE` for the preceding
rejection callback, not full governance or inherited-setting permission parity.
The fixed-low-effort Haiku mechanical role also remains unresolved; silently
discarding its effort setting would not meet the handoff.

References:
[Claude authentication](https://code.claude.com/docs/en/authentication),
[programmatic mode](https://code.claude.com/docs/en/headless),
[model configuration](https://code.claude.com/docs/en/model-config).
