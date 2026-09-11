# Native Git and GitHub evaluation

Runtime result: `PASS_CONFIGURED` for disposable local Git coordination across
process restart. Remote GitHub PR/review and ambiguous network outcomes remain
`INCONCLUSIVE`.

## GIT-01: isolated worktrees and resumed ownership

`native-git-v4-seed.json` and `native-git-v4-restart.json` use the pinned upstream
plus `/tmp/kirocrew-offline-9aj0edac/data/repo`, with no provider or network.
The outer offline namespace contains a newly initialized fixture repository,
fake Git identity and two native `Project` records. Native `init_workspace`
discovers the repository from a nested directory and concurrently creates two
distinct task branches/worktrees. Each commits its own file through
`commit_step`; neither sees the other's change. A no-change step creates no
commit. An independent base-branch commit preserves both task histories, and
the original checkout's dirty file retains its hash. A non-Git directory remains
non-Git.

A fresh process reconstructs the recorded Project Git fields and validates both
workspaces. Switching an owned worktree to a different branch fails native
identity validation; restoring its branch succeeds. Native `revert_step` removes
only a newly created fixture commit. `finalize` removes each verified, clean
fixture worktree; the original dirty file remains unchanged. Checkpoint fields
are an authored export for this Git-only scenario, not TaskRunner registry proof.

The initial fixture fails closed before Git execution because the capability-free
outer namespace cannot create a nested sandbox. The isolated profile explicitly
declares `agent.sandbox_allow_unsandboxed_exec=true` so native Git can run inside
the already verified offline outer boundary. No host/live profile is changed.
Earlier v2/v3 attempts also fail: one used the wrong configuration key, and
`KiroCrewConfig.save()` deliberately strips undeclared consent. v4 declares the
key in the disposable config file and verifies native readback. This is evidence
for local Git behavior under outer isolation, not native nested-sandbox parity.

## Native scope

Native `git_coord.init_workspace` discovers an existing repository and creates
a `kirocrew/task/{task_id}` branch in a sibling `.kirocrew-work` worktree.
Non-repository folders run in place with Git coordination disabled. Native
per-step commit, revert and finalization functions operate on that run's
workspace; their external effects need the disposable-repository scenarios.

GitHub surfaces share `github_runner.py` for trusted executable selection and a
minimal child environment. The dashboard keeps a bounded asynchronous spawn
path; Issue Radar and Code Review Sage use the shared synchronous runner.
Testing one path does not establish every surface's network-outcome handling.

Use a disposable repository for discovery, branches/worktrees, concurrency,
commits, dirty state, validation, rejected operations, base movement and restart.
External PR/review tests require an explicitly authorized disposable target.
Inspect authoritative remote state before repeating uncertain writes.
Never force-push or discard user changes.

Sources: [architecture map](source-map.md) and
[contributor workflow](../../CONTRIBUTING.md).
