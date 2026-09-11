# Native TaskRunner evaluation

Runtime result: `PASS_CONFIGURED` for bounded Codex and Claude dependencies,
forced pause and fresh-process resume after focused native bug fixes. The failed
native baselines remain below. Broader specification, retry and interrupted
external-effect scenarios remain pending.

## TASK-01: dependency checkpoint baseline

The native YAML planner loads two text-only arithmetic tasks with a dependency
and a forced approval gate on the second task. The offline check persists and
reloads that plan, preserving the dependency, gate and original input without
constructing a provider. This proves the plan/registry roundtrip, not a full
process restart or model memory retrieval.

The connected attempt uses the native factory, `SessionManager` and
`TaskRunner`, exact Terra/high, no configured fallback, a disposable non-Git
workspace, and no automated test command. An external experiment guard limits
it to two prompts and stops any tool approval attempt. This extra boundary is
needed because `task_executor.self_review` calls `stream_and_collect_json`,
whose default approval policy is `AUTO_APPROVE`; review approval safety is not
claimed by this experiment.

The run fails with task statuses `failed/pending`, three task attempts and zero
prompts. Four configured provider objects are constructed across native task
retries and replanning. The dependent approval gate is never reached. Its
native registry and redacted diagnostic fingerprints are retained.

A separate zero-prompt trace confirms the selected provider starts successfully
at Terra/high, then `_get_or_bootstrap_run_runtime` falls through to
`get_subagent_runtime` because its ACP client exposes no shared `_runtime`.
`open_task_session` unconditionally enters that shared-runtime path. The trace
stops at the fallback boundary and closes its owned provider; it does not start
an unconfigured Kiro runtime. The default fallback has no registered parent
provider from which to recover backend settings. This routing is incompatible
with the already-supported dedicated subscription provider path.

Evidence: `native-taskrunner-plan-offline-v1.json`,
`native-taskrunner-pause-v1.json` and `native-taskrunner-diagnose-v1.json`.
All use the pinned source plus snapshot
`/tmp/kirocrew-offline-wp226qg7/data/repo`. The diagnosis is a successful trace
of the failure path, not successful TaskRunner acceptance.

Four offline regressions reproduce the unwanted shared-runtime fallback for
both Codex and Claude, including task admission after manager shutdown.
`ACP_BACKENDS_DEDICATED_TASK_SESSIONS` now selects the existing
`get_or_create` path for these task steps. Task state, retries, review and
checkpoint ownership remain native. The focused suite passes all 853 cases in
`safe-test-proof/task-routing-regressions-v1`, including both providers' lease,
reuse, independent review-session and clean-close cases and the retained Kiro
shared-runtime tests.

## TASK-02: denied gate must preserve pause

With routing repaired, the second live attempt executes and reviews task 1:
two native completions, exact Terra/high before and after both prompts, and the
expected first result. Denying task 2's forced gate correctly sets its local
state to pending/paused, but `_execute_tasks` then calls `_try_replan` regardless
of run status. The planner attempts another prompt. The external two-prompt cap
stops it before inference, leaving the run cancelled with task 1 preserved.
No tool approval is attempted. Evidence: `native-taskrunner-pause-v2.json`.

Seven offline regressions reproduce this `NARROW_BUG`, including sequential and
parallel denied gates and stopped-run states. `_try_replan` now admits only a
`running` run before spending its budget or invoking a planner. The original
plan and pause/cancel/failure state remain intact. All 570 retained TaskRunner
checks pass in `safe-test-proof/task-pause-regressions-v1`; formatting, lint and
type checks pass in `safe-test-proof/task-pause-quality-v1`.

## TASK-03 / MEM-03: completed boundary survives process restart

The repaired scenario uses the validated snapshot
`/tmp/kirocrew-offline-9aj0edac/data/repo`. Native YAML planning sends zero
prompts. The first process executes and reviews task 1, then denies task 2's
forced gate. It stops as `paused`, with task statuses `passed/pending` and
attempts `1/0`. It sends exactly two prompts, attempts no replanning or tool
approval, and shuts down cleanly.

A separate process creates a new TaskRunner, loads the same native run ID and
verifies the completed result hash before resuming. Approval of task 2 starts
only the remaining execution and review. The final state is `completed`, tasks
are `passed/passed`, and attempts are `1/1`. The first result hash is unchanged.
Both actual results match the arithmetic fixture, both processes close all
their providers, and every turn retains exact Terra/high readback. There is no
Git operation, external notification or automated test command.

Evidence: `native-taskrunner-plan-offline-v3.json`,
`native-taskrunner-pause-v3.json` and `native-taskrunner-resume-v3.json`.
This proves the native persisted boundary and dependency/gate recovery for a
graceful pause. Task 2's prompt includes its arithmetic input, so this is not
proof of model memory recall or recovery from an ambiguous external side effect.

## TASK-04: Claude text-result review and restart

The first Claude checkpoint run (`native-taskrunner-pause-v4.json`) pauses
correctly after two Sonnet/high prompts. Its new-process resume restores task 1
and computes the correct task 2 result, but self-review rejects it because the
reviewer was not supplied the output. Native execution then attempts a third
prompt, which the external two-prompt cap stops before inference. The cancelled
baseline and redacted review diagnostic remain preserved.

`task_executor.self_review` included neither the task description nor its result
when no Git diff existed. Two offline regressions fail before the fix. The
no-diff prompt now includes the task description and bounded, already-redacted
result, labels the result as untrusted evidence, and requests files only when
the task requires them. The real-diff branch is unchanged. All 573 related
regressions and quality checks pass in `safe-test-proof/task-review-*-v1`.

The repeated native scenario uses `/tmp/kirocrew-offline-cydywohc/data/repo`.
`native-taskrunner-pause-v5.json` ends paused, `passed/pending`, attempts `1/0`.
`native-taskrunner-resume-v5.json` runs in a new process and ends completed,
`passed/passed`, attempts `1/1`, with the original completed-result hash intact.
Both phases send exactly two prompts, keep Sonnet/high readback, attempt no tool
approval or excess prompt, and close their providers. This repairs the observed
review defect without disabling a test or increasing the experiment budget.

The review permission default and fail-open handling of review exceptions remain
separate safety findings. A failed review also allows one execution retry without
a second review. The external text-only guard is not a production fix for those
policies; this result does not authorize unattended writing tasks.

## TASK-05: recovery of persisted active work

The offline `native-recovery-policy-v1-seed.json` stores an authored native run
as running, with one passed step, one in-progress step and prior auto-approval
intent. A fresh process loads it through TaskRunner's ordinary registry path.
The run becomes paused, the active step becomes pending with its interrupted
attempt removed, the completed result hash and dependency remain intact, and
the auto-approval intent is removed. Evidence is
`native-recovery-policy-v1-restart.json`. No provider starts. This exercises
active-state recovery in a new process; it does not crash a live gateway or
reconcile an uncertain external effect.

## Native execution and persistence

`taskrunner.py` coordinates the native `Project` and `Task` models from
`task_models.py`. Planning and dependency grouping live in `task_planner.py`;
execution, validation and retries live in `task_executor.py`; reporting and the
spec checkpoint live in `task_reporter.py`. `git_coord.py` owns branch/worktree
operations. Optional workflow identity/event metadata wraps this execution;
it does not replace it with another task engine.

The run registry is `runs.json` under the runner work directory. Its snapshot
contains task IDs, titles, descriptions, dependencies, approval flags, statuses,
attempts, errors and results truncated to 2,000 characters. It also preserves
the spec/input, workflow identity/revision, lessons, tokens, branch/base branch,
worktree path, repository root, Git-enabled flag and commit hashes. Cron-source
runs are excluded from this registry and need their own liveness test.

Registry writes use atomic replacement with fsync and monotonically ordered
snapshots. Read failures preserve the file; malformed JSON is retained as a
`.corrupt` sidecar. Recovery converts active runs with tasks to paused/resumable,
resets in-progress tasks to pending and removes the previous auto-approval
grant. Interrupted planning requires replanning. A stored task boundary is
therefore useful evidence, but not proof that interrupted external effects are
automatically reconciled.

`TASK_PROGRESS.md` sits beside a specification and contains human-readable task
status. This writer uses a direct file write, separately from the atomic run
registry. `load_checkpoint` extracts completed task titles, lowercased; the
checkpoint path needs a duplicate-title/renamed-task scenario before it can
support an exact identity claim. Ad-hoc plans without a spec do not write this
Markdown file.

## Required experiment

Use a disposable specification with dependent steps and acceptance criteria,
a safe failure requiring retry, an interrupted run and a resumed run.
Observe native decomposition, bounded child work, validation, checkpoints,
progress and pending/completed boundaries. Record task IDs and checkpoint files.

Do not introduce Jira execution state or another specification framework before
this test. Compare Spec Kit only after recording demonstrated gaps.

Sources: [tasks](../system-specs/modules/task.md),
[TaskRunner](../system-specs/modules/taskrunner.md).
