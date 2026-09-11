# Native multiple-agent evaluation

Runtime result: `PASS_CONFIGURED` for two bounded native children on each
subscription provider. Broader role/permission and restart behavior remains
`INCONCLUSIVE`. No permanent team is created.

## CHILD-01: independent progress while one child waits

The experiment uses the pinned upstream plus snapshot
`/tmp/kirocrew-offline-9aj0edac/data/repo`, exact Terra/high or Sonnet/high,
native `SubagentManager`, `SessionManager` and context/streaming hooks. An
offline denial scenario first verifies no provider is constructed when both
spawns are denied. The initial fixture's cwd was outside native allowed roots;
the corrected configuration allows only the disposable scenario directory.

In each live run, child A waits for spawn approval while child B completes its
bounded arithmetic task. B's native completion callback releases A, which then
completes. Both return the expected result to the recorded parent identity,
with distinct child/session IDs, one prompt each and matching model/effort
readback. Native capacity is two in the constructed manager; the author launches
exactly two children. The parent completion receiver is a local observer, not a
live parent model or an outbound channel. All tool requests are denied and an
external guard stops any attempted approval. Providers close cleanly.

Evidence: `native-subagent-offline-v2.json` and each provider's
`native-subagent-live-v2.json` plus its start record. This proves overlapping
waiting/execution, ownership and native result delivery. It does not prove two
simultaneous writing models, peer consultation, separate reviewer permissions,
live parent injection or orphan reconciliation after restart.

Native configuration loading clamps an explicit `max_subagents=2` to three.
The reviewable configuration fragments now declare that minimum of three
explicitly; the live fixture's two-child bound remains separate. Resolver
v2/v3 preserve the rejected assertion and v4 verifies the corrected fragments.

## Native design and remaining scope

`SubagentManager` acquires native sessions, injects context, streams provider
events, applies the tool-approval cascade and returns results to the originating
parent. Capacity, turn limits, timeouts, cancellation and result delivery are
already part of this path. Explicit user stop, failed work and successful
completion have distinct terminal outcomes.

Native run artifacts and tombstones support orphan reconciliation after gateway
restart. The source preserves provider/session provenance and protected cleanup
ownership separately from agent-writable run data. The evaluation must compare
live result delivery, undelivered results and restarted parents, without using
outbound owner-message fallbacks in the test environment.

Model choice needs special attention: the native `background` and `subagent`
role defaults are `auto` and do not automatically inherit the main chat model.
Testing one pinned chat therefore cannot establish fixed child/background
models. Requested-versus-served model evidence must accompany each child run.

Start with two or three disposable concurrent tasks. Observe native child bounds,
ownership, independent progress while one task waits, read-only/writing
permissions, consultation/review responsibilities and restart continuity.
Treat the eventual role matrix as a scorecard, not a deployment instruction.

Sources: [subagents](../system-specs/modules/subagent.md),
[crew mode](../system-specs/modules/crew-mode.md).
