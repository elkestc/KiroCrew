"""Exact-binding admission at the real wire seam, with synthetic responses only."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call

import pytest

from kiro_crew import model_registry
from kiro_crew.acp.client import AcpBindingMismatch, AcpClient, AcpError
from kiro_crew.acp.types import ACP_BACKEND_CLAUDE, ACP_BACKEND_CODEX, METHOD_PROMPT, JsonRpcMessage
from kiro_crew.config.loader import KiroCrewConfig
from kiro_crew.providers.acp import AcpProvider


@pytest.fixture(
    params=[
        (ACP_BACKEND_CODEX, "gpt-5.6-terra", "reasoning_effort"),
        (ACP_BACKEND_CLAUDE, "claude-sonnet-5", "effort"),
    ]
)
def bound(request, tmp_path, monkeypatch):
    backend, model, effort_id = request.param
    monkeypatch.setattr(model_registry, "_ADVERTISED_MODELS", {})
    provider = AcpProvider(
        work_dir=tmp_path,
        model=model,
        acp_backend=backend,
        effort_per_model={model: "high"},
        require_exact_binding=True,
    )
    client = provider.client
    client._session_id = "synthetic-session"
    options = [
        {"id": "model", "currentValue": model, "options": [{"value": model}]},
        {"id": effort_id, "currentValue": "high", "options": [{"value": "low"}, {"value": "high"}]},
    ]
    client._store_session_config({"configOptions": options})
    writer = SimpleNamespace(write=Mock(), drain=AsyncMock())
    client._process = SimpleNamespace(stdin=writer)
    return provider, client, model, effort_id, options, writer


@pytest.mark.asyncio
async def test_exact_readback_admits_one_prompt(bound):
    _, client, _, _, _, writer = bound
    await client._send_request(METHOD_PROMPT, {"sessionId": "synthetic-session", "prompt": []})
    writer.write.assert_called_once()
    assert json.loads(writer.write.call_args.args[0])["method"] == METHOD_PROMPT


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["model", "effort", "missing", "duplicate", "malformed"])
async def test_mismatched_readback_never_writes_prompt(bound, corruption):
    _, client, _, _, options, writer = bound
    if corruption == "model":
        options[0]["currentValue"] = "unrequested-model"
    elif corruption == "effort":
        options[1]["currentValue"] = "low"
    elif corruption == "missing":
        options.pop()
    elif corruption == "duplicate":
        options.append(dict(options[0]))
    else:
        options[:] = [{"id": "model"}, None]
    with pytest.raises(AcpBindingMismatch, match="readback"):
        await client._send_request(METHOD_PROMPT, {"sessionId": "synthetic-session", "prompt": []})
    writer.write.assert_not_called()
    writer.drain.assert_not_awaited()


@pytest.mark.asyncio
async def test_another_session_cannot_use_parent_readback(bound):
    _, client, _, _, _, writer = bound
    with pytest.raises(AcpBindingMismatch, match="another session"):
        await client._send_request(METHOD_PROMPT, {"sessionId": "synthetic-child", "prompt": []})
    writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_drift_after_a_successful_turn_blocks_next_prompt(bound):
    _, client, _, _, options, writer = bound
    params = {"sessionId": "synthetic-session", "prompt": []}
    await client._send_request(METHOD_PROMPT, params)
    writer.write.reset_mock()
    changed = [dict(option) for option in options]
    changed[1]["currentValue"] = "low"
    client._store_session_config({"configOptions": changed})
    with pytest.raises(AcpBindingMismatch):
        await client._send_request(METHOD_PROMPT, params)
    writer.write.assert_not_called()


def test_transport_reset_keeps_policy_but_requires_fresh_readback(bound):
    _, client, model, _, _, _ = bound
    client._process = None
    client._reset_state()
    assert client._exact_binding == (model, "high")
    with pytest.raises(AcpBindingMismatch):
        client.check_exact_binding()


@pytest.mark.parametrize("payload", [{}, {"configOptions": None}, {"configOptions": {}}])
def test_reinitialization_without_readback_invalidates_old_snapshot(bound, payload):
    _, client, _, _, _, _ = bound
    client._store_session_config(payload)
    with pytest.raises(AcpBindingMismatch):
        client.check_exact_binding()


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, {}, {"configOptions": None}])
async def test_missing_setting_response_cannot_reuse_stale_readback(bound, monkeypatch, response):
    _, client, _, effort_id, _, _ = bound
    monkeypatch.setattr(client, "_send_request", AsyncMock(return_value=7))
    monkeypatch.setattr(client, "_wait_for_response", AsyncMock(return_value=response))
    await client.set_config_option(effort_id, "high")
    with pytest.raises(AcpBindingMismatch):
        client.check_exact_binding()


@pytest.mark.parametrize("update", [{}, {"configOptions": None}, None])
def test_malformed_config_notification_invalidates_readback(bound, update):
    _, client, _, _, _, _ = bound
    client._handle_config_option_update(
        JsonRpcMessage(method="session/update", params={"update": update})
    )
    with pytest.raises(AcpBindingMismatch):
        client.check_exact_binding()


@pytest.mark.asyncio
async def test_settings_change_cannot_replace_fixed_binding(bound, monkeypatch):
    provider, client, model, effort_id, _, _ = bound
    sender = AsyncMock()
    monkeypatch.setattr(client, "_send_request", sender)
    for config_id, value in (("model", "unrequested-model"), (effort_id, "low")):
        with pytest.raises(AcpBindingMismatch):
            await client.set_config_option(config_id, value)
    with pytest.raises(AcpBindingMismatch):
        await client.set_model("unrequested-model")
    with pytest.raises(AcpBindingMismatch):
        await provider.change_effort("low")
    with pytest.raises(AcpBindingMismatch):
        await provider.clear_effort()
    sender.assert_not_awaited()
    assert provider._effort_per_model == {model: "high"}


@pytest.mark.asyncio
async def test_startup_does_not_step_down_after_effort_rejection(bound, monkeypatch):
    provider, client, _, effort_id, _, _ = bound
    monkeypatch.setattr(client, "ensure_ready", AsyncMock())
    setter = AsyncMock(side_effect=AcpError(f"Invalid value for config option {effort_id}: high"))
    monkeypatch.setattr(client, "set_config_option", setter)
    shutdown = AsyncMock()
    monkeypatch.setattr(client, "shutdown", shutdown)
    with pytest.raises(AcpError):
        await provider.start()
    setter.assert_awaited_once_with(effort_id, "high")
    shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_missing_effort_selector_fails_start_and_closes(bound, monkeypatch):
    provider, client, _, _, options, _ = bound
    client._store_session_config({"configOptions": options[:1]})
    monkeypatch.setattr(client, "ensure_ready", AsyncMock())
    shutdown = AsyncMock()
    monkeypatch.setattr(client, "shutdown", shutdown)
    with pytest.raises(AcpBindingMismatch, match="selector"):
        await provider.start()
    shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_successful_but_wrong_config_response_fails_start(bound, monkeypatch):
    provider, client, _, _, options, _ = bound
    monkeypatch.setattr(client, "ensure_ready", AsyncMock())
    monkeypatch.setattr(client, "_send_request", AsyncMock(return_value=9))
    returned = [dict(option) for option in options]
    returned[1]["currentValue"] = "low"
    monkeypatch.setattr(
        client, "_wait_for_response", AsyncMock(return_value={"configOptions": returned})
    )
    shutdown = AsyncMock()
    monkeypatch.setattr(client, "shutdown", shutdown)
    with pytest.raises(AcpBindingMismatch, match="readback"):
        await provider.start()
    shutdown.assert_awaited_once()


@pytest.mark.asyncio
async def test_exact_start_uses_original_model_without_substitution(bound, monkeypatch):
    _, client, model, _, _, _ = bound
    client._model = "unrequested-default"
    setter = AsyncMock()
    monkeypatch.setattr(client, "set_config_option", setter)
    await client._apply_startup_model()
    setter.assert_awaited_once_with("model", model)
    assert client._model == model


@pytest.mark.asyncio
async def test_rejected_startup_model_has_nonretryable_binding_error(bound, monkeypatch):
    _, client, _, _, _, _ = bound
    monkeypatch.setattr(
        client, "set_config_option", AsyncMock(side_effect=AcpError("Synthetic rejection"))
    )
    with pytest.raises(AcpBindingMismatch):
        await client._apply_startup_model()


@pytest.mark.asyncio
async def test_unconfigured_provider_retains_legacy_effort_step_down(bound, monkeypatch):
    provider, client, _, effort_id, _, _ = bound
    provider._require_exact_binding = False
    client._exact_binding = None
    setter = AsyncMock(
        side_effect=[AcpError(f"Invalid value for config option {effort_id}: high"), None]
    )
    monkeypatch.setattr(client, "set_config_option", setter)
    await provider._set_effort_config_option("high")
    assert setter.await_args_list == [call(effort_id, "high"), call(effort_id, "medium")]


@pytest.mark.parametrize(
    "model", [None, "", "auto", "latest", "default", "sonnet", "opus", "haiku", "fable"]
)
def test_unresolved_models_are_rejected_before_client_start(tmp_path, model):
    with pytest.raises(ValueError, match="concrete model"):
        AcpProvider(
            work_dir=tmp_path,
            model=model,
            acp_backend=ACP_BACKEND_CODEX,
            require_exact_binding=True,
        )


def test_exact_binding_requires_explicit_effort(tmp_path):
    with pytest.raises(ValueError, match="reasoning effort"):
        AcpProvider(
            work_dir=tmp_path,
            model="gpt-5.6-terra",
            acp_backend=ACP_BACKEND_CODEX,
            require_exact_binding=True,
        )


def test_invalid_effort_cannot_inherit_a_different_default(tmp_path):
    with pytest.raises(ValueError, match="invalid reasoning effort"):
        AcpProvider(
            work_dir=tmp_path,
            model="gpt-5.6-terra",
            acp_backend=ACP_BACKEND_CODEX,
            effort_per_model={"gpt-5.6-terra": "invalid"},
            effort_defaults={"gpt-5.6-terra": "high"},
            require_exact_binding=True,
        )


def test_unverified_backend_cannot_accept_exact_binding(tmp_path):
    with pytest.raises(ValueError, match="no verified"):
        AcpProvider(work_dir=tmp_path, model="synthetic", require_exact_binding=True)


@pytest.mark.parametrize(
    "binding", [(), ("synthetic",), ("synthetic", ""), ("synthetic", None), "synthetic"]
)
def test_client_refuses_malformed_binding_before_start(tmp_path, binding):
    with pytest.raises(ValueError, match="model and reasoning effort"):
        AcpClient(work_dir=tmp_path, acp_backend=ACP_BACKEND_CODEX, exact_binding=binding)


def test_factory_refuses_configured_fallback():
    cfg = KiroCrewConfig()
    cfg.agent.require_exact_binding = True
    with pytest.raises(ValueError, match="fallback_model"):
        cfg.create_provider_factory()


def test_exact_factory_refuses_warm_pool_that_can_reuse_another_binding():
    cfg = KiroCrewConfig()
    cfg.agent.acp_backend = ACP_BACKEND_CLAUDE
    cfg.agent.model = "claude-opus-4.8"
    cfg.agent.require_exact_binding = True
    cfg.agent.fallback_model = ""
    cfg.session.pool_size = 1
    # Pool claims can fold a caller's older version into the pool default and
    # skip the model switch; exact admission requires a fresh per-session tuple.
    with pytest.raises(ValueError, match="session.pool_size=0"):
        cfg.create_provider_factory()


def test_config_load_and_factory_preserve_exact_constraint(tmp_path, monkeypatch):
    monkeypatch.setenv("KIROCREW_HOME", str(tmp_path))
    monkeypatch.setattr(model_registry, "_ADVERTISED_MODELS", {})
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "agent": {
                    "acp_backend": "codex",
                    "model": "gpt-5.6-terra",
                    "reasoning_effort": "high",
                    "require_exact_binding": True,
                    "fallback_model": "",
                }
            }
        )
    )
    cfg = KiroCrewConfig.load()
    assert cfg.agent.require_exact_binding is True
    factory = cfg.create_provider_factory()
    provider = factory("dashboard:synthetic", cwd=str(tmp_path / "work"))
    assert provider.client._exact_binding == ("gpt-5.6-terra", "high")
    assert provider._require_exact_binding is True


@pytest.mark.parametrize("model", ["claude-opus-4.6", "claude-haiku-4.5"])
def test_exact_selection_preserves_model_before_alias_folding(model):
    cfg = KiroCrewConfig()
    cfg.agent.acp_backend = ACP_BACKEND_CLAUDE
    cfg.agent.model = model
    cfg.agent.require_exact_binding = True
    assert model_registry.to_provider_id(model, "claude_code") != model
    assert cfg.acp_effective_model(None, None) == model
    assert cfg.acp_effective_model(None, model_override=model) == model


def test_factory_binds_original_model_instead_of_registry_replacement(tmp_path, monkeypatch):
    monkeypatch.setattr(model_registry, "_ADVERTISED_MODELS", {})
    cfg = KiroCrewConfig()
    cfg.agent.acp_backend = ACP_BACKEND_CLAUDE
    cfg.agent.model = "claude-opus-4.6"
    cfg.agent.reasoning_effort = "high"
    cfg.agent.require_exact_binding = True
    cfg.agent.fallback_model = ""
    provider = cfg.create_provider_factory()("dashboard:synthetic", cwd=str(tmp_path))
    assert provider.client._exact_binding == ("claude-opus-4.6", "high")


def test_factory_cannot_resolve_auto_to_a_different_exact_binding(tmp_path, monkeypatch):
    cfg = KiroCrewConfig()
    cfg.agent.acp_backend = ACP_BACKEND_CODEX
    cfg.agent.model = "auto"
    cfg.agent.reasoning_effort = "high"
    cfg.agent.require_exact_binding = True
    cfg.agent.fallback_model = ""
    monkeypatch.setattr(cfg, "_resolve_agent_model", lambda: "gpt-5.6-terra")
    factory = cfg.create_provider_factory()
    with pytest.raises(ValueError, match="concrete model"):
        factory("dashboard:synthetic", cwd=str(tmp_path))
    provider = factory("dashboard:synthetic", cwd=str(tmp_path), model_override="gpt-5.6-terra")
    assert provider.client._exact_binding == ("gpt-5.6-terra", "high")
