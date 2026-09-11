"""Task steps must retain their configured provider and native lease lifecycle."""

from unittest.mock import AsyncMock

import pytest

from kiro_crew.agent_sdk.backends import ACP_BACKEND_CLAUDE, ACP_BACKEND_CODEX
from kiro_crew.config import KiroCrewConfig
from kiro_crew.session import SessionClosingError, SessionManager


@pytest.fixture(params=[ACP_BACKEND_CLAUDE, ACP_BACKEND_CODEX])
def dedicated_manager(request, monkeypatch):
    cfg = KiroCrewConfig()
    cfg.agent.acp_backend = request.param
    cfg.session.pool_size = 0
    created = []

    def factory(session_key=None, **kwargs):
        provider = AsyncMock()
        provider._client = None
        provider.is_process_alive = lambda: True
        provider.has_active_turn = lambda: False
        provider.context_usage_pct = lambda: 0.0
        provider.context_window_tokens = lambda: 0
        provider.runtime_info = lambda: (None, None)
        created.append((session_key, kwargs, provider))
        return provider

    manager = SessionManager(cfg, provider_factory=factory)
    unrequested = AsyncMock(side_effect=AssertionError("Unrequested shared runtime"))
    monkeypatch.setattr(manager, "get_subagent_runtime", unrequested)
    return manager, created, unrequested


@pytest.mark.asyncio
async def test_task_steps_keep_provider_leases_and_independent_sessions(
    dedicated_manager, tmp_path
):
    manager, created, unrequested = dedicated_manager
    first_key, second_key = "taskrunner:synthetic:task1", "taskrunner:synthetic:review"
    try:
        first, new, resumed = await manager.open_task_session(
            "taskrunner:synthetic:runtime", first_key, cwd=str(tmp_path), approval_policy="ask"
        )
        assert new and not resumed
        assert manager._sessions[first_key].semaphore.locked()
        assert manager._sessions[first_key].approval_policy == "ask"
        manager.release(first_key)
        again, new, resumed = await manager.open_task_session(
            "taskrunner:synthetic:runtime", first_key, cwd=str(tmp_path)
        )
        assert again is first and not new and not resumed
        manager.release(first_key)
        second, new, resumed = await manager.open_task_session(
            "taskrunner:synthetic:runtime", second_key, cwd=str(tmp_path)
        )
        assert second is not first and new and not resumed
        manager.release(second_key)
        assert [key for key, _, _ in created] == [first_key, second_key]
        assert all(kwargs["cwd"] == str(tmp_path) for _, kwargs, _ in created)
        for _, _, provider in created:
            provider.start.assert_awaited_once()
        unrequested.assert_not_awaited()
        assert not manager._subagent_runtimes
    finally:
        await manager.close_all(drain_timeout=0)
    for _, _, provider in created:
        provider.shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_task_admission_refuses_a_closing_manager(dedicated_manager, tmp_path):
    manager, created, unrequested = dedicated_manager
    await manager.close_all(drain_timeout=0)
    with pytest.raises(SessionClosingError):
        await manager.open_task_session(
            "taskrunner:synthetic:runtime", "taskrunner:synthetic:task1", cwd=str(tmp_path)
        )
    assert not created
    unrequested.assert_not_awaited()
