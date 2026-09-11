"""Replay subscription-adapter config frames without clients, credentials or network."""

from unittest.mock import AsyncMock

import pytest

from kiro_crew.acp.client import AcpClient, AcpError
from kiro_crew.acp.types import ACP_BACKEND_CLAUDE, ACP_BACKEND_CODEX
from kiro_crew.providers.acp import AcpProvider


@pytest.fixture(params=[(ACP_BACKEND_CLAUDE, "effort"), (ACP_BACKEND_CODEX, "reasoning_effort")])
def advertised_provider(request, tmp_path, monkeypatch):
    backend, config_id = request.param
    model = "gpt-5.6-terra" if backend == ACP_BACKEND_CODEX else "claude-sonnet-5"
    provider = AcpProvider(work_dir=tmp_path, model=model, acp_backend=backend)
    client = provider._client
    assert isinstance(client, AcpClient)
    # Same shape as codex-acp 1.11.0 createReasoningEffortConfigOption; all
    # values are synthetic. Use the real config parser and capability query.
    client._store_session_config(
        {
            "configOptions": [
                {"id": "model", "currentValue": model, "options": [{"value": model}]},
                {
                    "id": config_id,
                    "category": "thought_level",
                    "type": "select",
                    "currentValue": "low",
                    "options": [{"value": "low"}, {"value": "high"}],
                },
            ]
        }
    )
    monkeypatch.setattr(client, "set_config_option", AsyncMock())
    monkeypatch.setattr(client, "send_command", AsyncMock())
    monkeypatch.setattr(client, "ensure_ready", AsyncMock())
    return provider, config_id, model


def test_advertised_effort_levels_reach_provider(advertised_provider):
    provider, _, _ = advertised_provider
    assert provider.get_valid_effort_levels() == ["low", "high"]


@pytest.mark.asyncio
async def test_live_effort_uses_advertised_wire_id(advertised_provider):
    provider, config_id, model = advertised_provider
    assert await provider.change_effort("high") is True
    provider._client.set_config_option.assert_awaited_once_with(config_id, "high")
    provider._client.send_command.assert_not_awaited()
    assert provider._effort_per_model[model] == "high"


@pytest.mark.asyncio
async def test_initial_effort_uses_advertised_wire_id(advertised_provider):
    provider, config_id, model = advertised_provider
    provider._effort_per_model[model] = "high"
    await provider.start()
    provider._client.ensure_ready.assert_awaited_once()
    provider._client.set_config_option.assert_awaited_once_with(config_id, "high")
    provider._client.send_command.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_selector_does_not_claim_live_success(advertised_provider):
    provider, _, model = advertised_provider
    provider._client._store_session_config({"configOptions": [{"id": "model"}]})
    assert await provider.change_effort("high") is False
    provider._client.set_config_option.assert_not_awaited()
    assert model not in provider._effort_per_model


@pytest.fixture(params=[(ACP_BACKEND_CLAUDE, "effort"), (ACP_BACKEND_CODEX, "reasoning_effort")])
def config_response_client(request, tmp_path, monkeypatch):
    backend, effort_id = request.param
    client = AcpClient(work_dir=tmp_path, acp_backend=backend)
    client._session_id = "synthetic-config-session"
    client._store_session_config(
        {
            "configOptions": [
                {"id": effort_id, "currentValue": "low", "options": [{"value": "low"}]}
            ],
            "modes": {"currentModeId": "agent", "availableModes": [{"id": "agent"}]},
        }
    )
    monkeypatch.setattr(client, "_send_request", AsyncMock(return_value=41))
    monkeypatch.setattr(client, "_wait_for_response", AsyncMock())
    return client, effort_id


@pytest.mark.asyncio
async def test_config_reply_refreshes_readback_without_notification(config_response_client):
    client, effort_id = config_response_client
    client._wait_for_response.return_value = {
        "configOptions": [
            {"id": "model", "currentValue": "returned-model"},
            {"id": "mode", "currentValue": "read-only"},
            {
                "id": effort_id,
                "currentValue": "high",
                "options": [{"value": "low"}, {"value": "high"}],
            },
        ]
    }

    await client.set_config_option("model", "requested-model")

    # Public readback must reflect the server's full returned snapshot, even
    # when it differs from our request and no session/update frame follows.
    current = {option["id"]: option["currentValue"] for option in client.acp_config_options}
    assert current == {"model": "returned-model", "mode": "read-only", effort_id: "high"}
    assert client.get_valid_effort_levels() == ["low", "high"]
    assert client._modes_advertised is True
    assert client._available_mode_ids == ["agent"]


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, {}, {"configOptions": None}, {"configOptions": {}}])
async def test_config_reply_without_options_preserves_readback(config_response_client, response):
    client, effort_id = config_response_client
    before = list(client.acp_config_options)
    client._wait_for_response.return_value = response
    await client.set_config_option(effort_id, "high")
    assert client.acp_config_options == before


@pytest.mark.asyncio
async def test_empty_config_reply_clears_stale_selectors(config_response_client):
    client, effort_id = config_response_client
    client._wait_for_response.return_value = {"configOptions": []}
    await client.set_config_option(effort_id, "high")
    assert client.acp_config_options == []
    assert client.get_valid_effort_levels() == []


@pytest.mark.asyncio
async def test_rejected_config_write_preserves_readback(config_response_client):
    client, effort_id = config_response_client
    before = list(client.acp_config_options)
    client._wait_for_response.side_effect = AcpError("Synthetic configuration rejection")
    with pytest.raises(AcpError, match="Synthetic configuration rejection"):
        await client.set_config_option(effort_id, "high")
    assert client.acp_config_options == before
