# Native source map

Pinned source: `395dc8df14610973b0753f5e88fa9bd8b08e1830`.
This is a navigation map; runtime sufficiency requires the scenario reports.

## Turn lifecycle

Surfaces enter Crew's session/provider factory, construct context, acquire or
resume a session, stream ACP events, route permission requests through Crew's
hook/approval controls, and persist native transcript/state.
TaskRunner, heartbeat and subagents reuse the provider lifecycle.

The provider selector stays `agent.provider="acp"`. Harness choice lives at
`agent.acp_backend`. Source exposes Kiro, Claude, KAS and Codex; public prose
that says Kiro CLI is the only backend is not authoritative.

| Concern | Source entry points |
| --- | --- |
| Provider interface/events | `src/kiro_crew/providers/base.py`, `providers/acp.py` |
| Harness registry/capabilities | `agent_sdk/backends.py`, `agent_sdk/capabilities.py` |
| ACP transport/dispatch | `acp/client.py`, `acp/_dispatch.py`, `acp/types.py` |
| Shared process/session handles | `acp/runtime.py`, `acp/session_handle.py`, `acp/session_provider.py` |
| Pool, expiry, resume, compaction | `session.py`, `session_pool.py`, `session_lifecycle.py`, `session_storage.py`, `session_compaction.py` |
| Prompt/context | `context.py`, `context_blocks.py`, `acp/prompt_blocks.py` |
| Memory/history/learning | `memory.py`, `vector_memory.py`, `history.py`, `history_consolidation.py`, `learn.py`, `knowledge/` |
| Tasks/checkpoints | `task_models.py`, `taskrunner.py`, `task_planner.py`, `task_executor.py`, `task_reporter.py` |
| Concurrent child work | `subagent.py` |
| Background work | `heartbeat.py`, `cron.py`, `channel.py` |
| MCP projection | `acp/session_mcp.py`, `providers/mirrors/`, `mcp_gateway/` |
| Approval/security | `hooks.py`, `security/`, `agent_sdk/tool_gate.py`, `sandbox.py` |
| Governance/identity | `platform/governance.py`, `agent_sdk/host_auth.py` |
| Audit/redaction | `sel.py`, `security/` |
| Git/GitHub integrations | `git_coord.py`, `github_runner.py`, `dashboard/handlers/source_providers.py`, `apps/builtins/issue_radar/` |
| Discord/message routing | `discord/`, `messaging/`, `channel.py` |
| Dashboard | `dashboard/`, `website/src/` |
| Config | `config/loader.py`, `config/validation.py`, `config/paths.py` |

All abbreviated source paths above are relative to `src/kiro_crew/`.
`task.py` separately tracks the lifecycle of one message-processing task;
it is not the TaskRunner plan/checkpoint schema.
The [architecture overview](../architecture/overview.md) and
[module index](../system-specs/modules/README.md) describe the remaining modules.

## Adapter findings to reproduce

- Codex already uses a public ACP adapter backed by official Codex.
- `AcpClient._codex_session_mcp_servers` returns an empty list. Pooled broker
  overlays can still supply tools; the direct projection alone cannot.
- Codex's `_sandbox_preflight` refuses hosts where credential masks cannot apply.
- Claude has a native MCP projection and session settings writer.
  `Routing.SEEDED_SETTINGS` is explicitly reported as indeterminate.
- `agent.fallback_model=""` disables the configured transient fallback chain;
  startup substitution and readback need separate verification.
- The native effort setter steps down after an unsupported effort value. The
  handoff requires a fixed effort, so startup/readback must reject such a change.

See [harness contract](../system-specs/modules/harness-parity.md),
[Claude provider](../system-specs/modules/claude-code-provider.md), and
[model fallback](../system-specs/modules/model-fallback.md).
