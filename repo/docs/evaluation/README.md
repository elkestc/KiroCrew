# Subscription fork evaluation

The governing task is the owner's fresh-start handoff dated 2026-09-11 JST.
This evaluation preserves native execution, memory and scheduling.

## Evidence and status

The [credential incident safety gate](security-incident.md) is complete: technical
checks passed and the owner confirmed R2 credential revocation. Provider and
native capability evaluation may resume with the test isolation controls retained.

Both dedicated Linux subscription profiles are authenticated. Codex completes
an exact Terra/high native turn, provider-process resume, cancellation and
one-time command approval. Native MCP broker delivery also passes; the managed
session caller scenario remains inconclusive. Claude completes native Sonnet/high
work after the reported quota reset. Both providers pass exact-bound chat,
TaskRunner checkpoint/resume, memory recall, heartbeat and two-child scenarios.
Focused task routing, pause and text-review fixes retain their failed baselines.
Offline semantic memory and disposable Git checks survive process restart.
Local Discord events establish authorization and mapping, with limits in
duplicate and edit/delete handling. The reports state each experiment's scope.
The full native capability evaluation and Jira spike remain
incomplete. See the provider reports for bounded results and proof locations.

The latest isolated retained suite passes with 93,979 passed, 850 skipped and
nine expected failures, with zero failures/errors. The source/proof checkpoint
is `native-capability-checkpoint-verification-v1.json` in the external evidence
directory. The fork is not yet accepted for unattended operation.

- [Upstream baseline](upstream-baseline.md)
- [Source map](source-map.md)
- [OpenAI provider](provider-openai.md)
- [Anthropic provider](provider-anthropic.md)
- [Model matrix](model-matrix.md)
- [Memory](native-memory.md)
- [TaskRunner](native-taskrunner.md)
- [Liveness](native-liveness.md)
- [Multiple agents](native-multi-agent.md)
- [Git and GitHub](native-git-github.md)
- [Security](native-security.md)
- [Credential incident and safety gate](security-incident.md)
- [Discord](native-discord.md)
- [Jira spike](jira-spike.md)
- [Capability matrix](capability-matrix.md)
- [Decision report](decision-report.md)

Raw local evidence lives outside the worktree at
`../evaluation-artifacts/2026-09-11/` relative to the repository root.
Reports distinguish static findings, fixture tests and actual provider turns.
A catalog response or a mocked provider is not proof of subscription inference.

## Scenario record

Every completed scenario records its ID, purpose, upstream SHA, provider/model,
configuration, initial state, inputs, actions, expected and observed behavior,
evidence paths, explanatory source locations, and classification.

Allowed results: `PASS_NATIVE`, `PASS_CONFIGURED`, `NARROW_BUG`,
`FEATURE_GAP`, `SAFETY_GAP`, `INCONCLUSIVE`.
