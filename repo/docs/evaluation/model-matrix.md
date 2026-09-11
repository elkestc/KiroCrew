# Fixed model matrix

Evaluation matrix version: 1. Requested role bindings below come from the
handoff. No operational role team is created before native session acceptance.
The [binding index](model-bindings.json) preserves the exact choices and failure
policy in versioned data. The reviewable [Codex](native-codex-config.json) and
[Claude](native-claude-config.json) configuration files use Crew's existing
`agent` and `agents` schema. They are evaluation artifacts, not installed live
profiles or a running team. Subscription authentication remains a separate
admission prerequisite.

| Role | OpenAI exact ID | Effort | Anthropic concrete target |
| --- | --- | --- | --- |
| Owner representative | gpt-6-astra | high | claude-fable-5-1[1m] |
| Architect | gpt-5.6-sol | high | claude-opus-5[1m] |
| A lead | gpt-5.6-sol | high | claude-opus-5[1m] |
| B lead | gpt-5.6-sol | high | claude-opus-5[1m] |
| Correctness reviewer | gpt-5.6-sol | high | claude-opus-5[1m] |
| Rules reviewer | gpt-5.6-sol | high | claude-opus-5[1m] |
| Implementer | gpt-5.6-terra | high | claude-sonnet-5 |
| Test engineer | gpt-5.6-terra | high | claude-sonnet-5 |
| Researcher | gpt-5.6-terra | high | claude-sonnet-5 |
| Mechanical worker | gpt-5.6-luna | low | claude-haiku-4-5-20251001; effort unresolved |

Official app-server catalog probe confirms these four OpenAI IDs and effort
levels for the dedicated Linux ChatGPT Pro profile. One native chat passes with
exact `gpt-5.6-terra` / `high` adapter readback before and after the turn.
Other role bindings remain catalog evidence only.

The fresh Linux Claude SDK catalog advertises Opus, Sonnet and Haiku. Fable is
absent, so the requested owner binding remains blocked in this environment.
The earlier Windows catalog's Fable selector includes `[1m]` while its `resolvedModel`
field is `claude-fable-5-1`; preserve both in evidence instead of assuming all
suffixes are interchangeable. Haiku advertises no effort capability, so its
required low-effort binding is not yet launchable under the handoff's invariant.
Native Claude now completes one Sonnet/high turn after the owner's reported
quota reset. Both providers pass the native session manager with exact binding
enabled. Other model bindings retain catalog-only evidence; no role team has
been launched.

## Native compatibility concerns

After one successful native turn from each provider, the offline resolver check
loads both configurations through `KiroCrewConfig.load`, resolves crew models
through the same `session._session_model` function used by allocation, and
constructs providers through the native factory without calling `start`.
All 20 role rows retain their requested model and effort. The 18 catalog-eligible
rows produce the expected immutable binding. Fable's requested binding is
retained but remains catalog-blocked; the factory refuses Haiku's unsupported
effort. No role provider process or inference is used. Evidence:
`native-role-resolver-v1.json` and the expanded v4 record, including input hashes.

These configurations default ordinary chat to the implementation model. Their
named crew records carry each role's explicit override. Background and subagent
task classes now explicitly use the implementation model/high, and a named
`kirocrew-heartbeat` record prevents an installed agent's `auto` model from
overriding that choice. Resolver v4 verifies both role maps and heartbeat factory
bindings without starting providers. The configured child limit is three, the
native fixed minimum; the earlier two-child value was clamped and failed the
resolver assertion. The live experiment still starts only two children. This
check is not proof of every surface's role assignment or entitlement.

The installed Codex ACP adapter 1.11.0 exposes `model` and `reasoning_effort`
configuration options. Offline ACP response replay reproduced three failures
caused by Crew looking for `effort`. The focused compatibility fix uses Codex's
wire id for discovery and initial/live pushes; see the
[provider evidence](provider-openai.md#offline-effort-compatibility). Legacy
Codex ACP model strings can also carry `[effort]`; distinguish that transport
representation from the exact underlying model ID.

Native startup treats a persisted model differently from an explicit picker
change: unavailable startup values can inherit a served default, while an
explicit switch raises `AcpModelUnavailable`. Native initial effort is
best-effort and may step down unless `agent.require_exact_binding` is enabled.
The new option requires exact model/effort readback at the prompt wire and an
empty configured fallback. Its verification is recorded in the
[provider report](provider-openai.md#exact-binding-constraint).

The fork must fail visibly on unresolved/unavailable bindings. The handoff's
fixed-model requirement overrides upstream's default-auto guidance.
`agent.fallback_model=""` is the native opt-out for transient fallback.
That setting alone does not prove startup substitution or role override
behavior. Test those separately before accepting a configuration.
