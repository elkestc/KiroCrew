"""An independent review needs the task contract and its observed result."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from kiro_crew import task_executor
from kiro_crew.task_models import Project, Task


@pytest.mark.asyncio
@pytest.mark.parametrize("branch", ["", "fixture-branch"])
async def test_no_diff_review_can_verify_the_task_result(tmp_path, monkeypatch, branch):
    task = Task(
        index=2,
        title="Continue the calculation",
        description="Compute 42 plus 8 and return FINAL_VALUE=50 without changing files.",
        result="FINAL_VALUE=50",
    )
    run = Project("", "", task_id="fixture-review", work_dir=str(tmp_path), branch_name=branch)
    client = object()
    sessions = SimpleNamespace(
        open_task_session=AsyncMock(return_value=(client, True, False)),
        release=Mock(),
        reset=AsyncMock(),
    )
    observed = []

    async def review(_client, prompt):
        observed.append(prompt)
        return {
            "ok": task.description in prompt and task.result in prompt,
            "issue": "The independent reviewer was not given the task contract and result",
        }

    monkeypatch.setattr(task_executor.git_coord, "get_step_diff", AsyncMock(return_value=""))
    monkeypatch.setattr(task_executor, "stream_and_collect_json", review)
    assert await task_executor.self_review(run, task, sessions, "")
    assert len(observed) == 1
    assert not task.error and not run.memory.blockers
    sessions.release.assert_called_once_with("taskrunner:fixture-review:review")
    sessions.reset.assert_awaited_once_with("taskrunner:fixture-review:review")


@pytest.mark.asyncio
async def test_diff_review_still_receives_the_actual_changes(tmp_path, monkeypatch):
    task = Task(1, "Change fixture", "Change the fixture value to two", result="Claim only")
    run = Project("", "", task_id="fixture-diff", work_dir=str(tmp_path), branch_name="branch")
    sessions = SimpleNamespace(
        open_task_session=AsyncMock(return_value=(object(), True, False)),
        release=Mock(),
        reset=AsyncMock(),
    )
    diff = "--- fixture.txt\n+++ fixture.txt\n-one\n+two"
    observed = []

    async def review(_client, prompt):
        observed.append(prompt)
        return {"ok": diff in prompt and task.description in prompt}

    monkeypatch.setattr(task_executor.git_coord, "get_step_diff", AsyncMock(return_value=diff))
    monkeypatch.setattr(task_executor, "stream_and_collect_json", review)
    assert await task_executor.self_review(run, task, sessions, "")
    assert len(observed) == 1 and task.result not in observed[0]
