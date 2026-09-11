"""A denied task gate must preserve its pause without invoking replanning."""

from unittest.mock import AsyncMock

import pytest

from kiro_crew.config import KiroCrewConfig
from kiro_crew.session import SessionManager
from kiro_crew.task_models import Project, Task, TaskStatus
from kiro_crew.taskrunner import TaskRunner


@pytest.mark.asyncio
@pytest.mark.parametrize("parallel", [False, True])
async def test_denied_gate_preserves_plan_and_completed_boundary(tmp_path, monkeypatch, parallel):
    def forbidden_factory(*args, **kwargs):
        raise AssertionError("A denied gate may not start a provider")

    manager = SessionManager(KiroCrewConfig(), provider_factory=forbidden_factory)
    denied = AsyncMock(return_value=False)
    runner = TaskRunner(manager, work_dir=tmp_path, on_approval=denied, on_notify=AsyncMock())
    completed = Task(1, "Completed", "Synthetic completed task", status=TaskStatus.PASSED)
    completed.result = "Preserve this completed result"
    gated = Task(2, "Gated", "Wait for authorization", depends_on=[1], force_approval=True)
    tasks = [completed, gated]
    if parallel:
        tasks.append(
            Task(3, "Other gate", "Wait independently", depends_on=[1], force_approval=True)
        )
    run = Project(
        spec_path="",
        spec_content="Synthetic plan",
        task_id="denied-gate",
        work_dir=str(tmp_path),
        status="running",
        tasks=tasks,
    )
    decompose = AsyncMock(side_effect=AssertionError("A paused plan may not invoke a planner"))
    monkeypatch.setattr(runner, "_decompose", decompose)
    try:
        await runner._execute_tasks(run, "taskrunner:synthetic")
        assert run.status == "paused"
        assert run.replan_count == 0
        assert run.tasks == tasks
        assert completed.status == TaskStatus.PASSED
        assert completed.result == "Preserve this completed result"
        assert all(task.status == TaskStatus.PENDING for task in tasks[1:])
        assert denied.await_count == len(tasks) - 1
        decompose.assert_not_awaited()
    finally:
        await manager.close_all(drain_timeout=0)


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["paused", "pausing", "cancelled", "cancelling", "failed"])
async def test_stopped_run_cannot_spend_replan_budget(tmp_path, monkeypatch, status):
    manager = SessionManager(KiroCrewConfig())
    runner = TaskRunner(manager, work_dir=tmp_path)
    task = Task(1, "Stopped", "Synthetic gate", force_approval=True)
    run = Project(spec_path="", spec_content="Synthetic", status=status, tasks=[task])
    decompose = AsyncMock(side_effect=AssertionError("Stopped runs cannot invoke a planner"))
    monkeypatch.setattr(runner, "_decompose", decompose)
    try:
        assert await runner._try_replan(run, task) is False
        assert run.status == status and run.replan_count == 0
        decompose.assert_not_awaited()
    finally:
        await manager.close_all(drain_timeout=0)
