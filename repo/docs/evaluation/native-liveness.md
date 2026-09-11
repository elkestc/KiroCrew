# Native liveness evaluation

Runtime result: `PASS_CONFIGURED` for bounded heartbeat timer turns on both
subscriptions, plus offline queue/restart cases. No persistent unattended
service is activated. Cron, durable retry bounds and persistent channels remain
`INCONCLUSIVE` or limited as described below.

## LIVE-01: timer dispatch, completion and work after idle

Each provider uses native `GatewayOrchestrator._init_heartbeat`,
`HeartbeatService`, `ContextBuilder`, `SessionManager`, the scoped heartbeat
hooks and `stream_and_collect`. The evaluation sets a one-second interval and
stops the timer after two text-only arithmetic tasks. The only replaced
delivery surface is a local result observer; it sends no external message.
An external prompt cap and tool-approval stop keep this experiment bounded.

A separate process queues task 1 through `append_heartbeat_task`. The timer
starts a real provider turn, returns the expected value and removes the task.
An idle interval sends no duplicate prompt. Appending task 2 starts another real
turn on the next tick, returns its expected value and clears the queue. Both
providers emit two native completions, retain exact model/effort readback, and
close their processes and timers. Codex uses Terra/high; Claude uses Sonnet 5/high.

Evidence: Codex `native-heartbeat-live-v3.json`, Claude
`native-heartbeat-live-v4.json`, and `native-heartbeat-offline-v4.json`. All use
`/tmp/kirocrew-offline-9aj0edac/data/repo`.

Two configuration failures are preserved. The first connected setup stored an
empty fallback only in its config object; the gateway reloads fallback from
disk, so an explicit preflight stopped before provider construction. Persisting
the disposable native config resolved it. The next Claude attempt was refused
before inference because its installed `kirocrew-heartbeat` template pins
`auto`, outranking the global default. The exact-binding constraint correctly
refused that unresolved selection. A native `config.agents.kirocrew-heartbeat`
record with concrete model and effort overrides the template; no production
change or fallback was needed. The zero-inference allocation traces are
`native-heartbeat-allocation-diagnostic-v1.json` and `-v2.json`.

## LIVE-02: retained queue and restart without inference

In the offline namespace, one task returns `HEARTBEAT_KEEP`, one raises a
synthetic provider-limit exception, and one completes while appending new work.
The native service retains the first two, removes completed work, preserves the
append and attempts each only once that cycle. A new process recovers and
finishes the retained queue. Empty cycles do not duplicate work, and the native
timer dispatches a task arriving after idle.

This proves retention and restart for the controlled callback; it does not turn
the synthetic error into evidence of a real provider quota response. Heartbeat
has no maximum retry count, so persistent errors repeat every configured cycle
indefinitely. Keep this limitation separate from cron's failure counter. A
marker-based completion convention also cannot establish exact reconciliation
of an interrupted external write.

## Native ownership

`HeartbeatService` reads workspace `HEARTBEAT.md` and dispatches each task through
the gateway callback. It retains exception results and responses containing
`HEARTBEAT_KEEP`; normal results without that marker remove the task. The file
rewrite merges tasks appended during a cycle under the native lock. The gateway
callback uses a dedicated heartbeat session, context builder and scoped approval
gate, with a bounded turn timeout and cycle-end session recycling.

This is an operational convention, not an exact completed-task ledger: an
incorrectly omitted marker can remove incomplete work. The live test must compare
the resulting artifact with the retained/removed task, including a provider
exception and a full process restart.

`CronService` persists schedules and execution metadata in `crons.json`, using
advisory locks for mutations. Jobs support persistent or per-run sessions.
`record_failure` advances a consecutive-failure counter and durably auto-pauses
at the native threshold; `record_success` clears execution-owned pause state
without lifting a user pause. An unreadable store cannot be rewritten as a
fresh empty store. Actual provider limit responses still need testing against
this failure accounting and the provider retry path.

Persistent agent channels have their own atomic serialized messages, member
configuration and routing metadata. Restored members start with fresh provider
sessions; they do not resume a live approval future. These are separate native
liveness mechanisms, so a passing heartbeat cannot establish channel or cron
restart behavior.

## Required experiments

Use bounded heartbeat/schedule experiments with isolated state. Prove a real
provider turn acknowledges and advances the intended task; a timestamp alone
does not pass. Test incomplete-work retention, bounded retry, process restart,
waiting dependencies, subscription limits and new work for an idle agent.

Sources: [heartbeat](../system-specs/modules/heartbeat.md),
[cron](../system-specs/modules/learn-cron-dashboard.md),
[persistent channels](../system-specs/modules/persistent-agent-channels.md).
