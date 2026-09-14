"""Unit tests for LiteLLMApiClient."""
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.litellm_cost.api import (
    LiteLLMApiClient,
    LiteLLMAuthError,
    LiteLLMConnectionError,
    LiteLLMData,
)


@pytest.mark.asyncio
async def test_client_init_and_headers():
    """Test URL normalization and authorization headers."""
    client = LiteLLMApiClient("localhost:4000/", api_key="sk-test-123")
    assert client.base_url == "http://localhost:4000"
    assert client.headers["Authorization"] == "Bearer sk-test-123"
    assert client.headers["x-litellm-api-key"] == "sk-test-123"

    client_https = LiteLLMApiClient("https://proxy.example.com", api_key=None)
    assert client_https.base_url == "https://proxy.example.com"
    assert "Authorization" not in client_https.headers
    assert "x-litellm-api-key" not in client_https.headers


@pytest.mark.asyncio
async def test_check_health_success():
    """Test health check returns True on valid response."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = LiteLLMApiClient("http://localhost:4000", session=session)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json = AsyncMock(return_value={"status": "healthy"})
    session.request.return_value.__aenter__.return_value = mock_resp

    healthy = await client.check_health()
    assert healthy is True


@pytest.mark.asyncio
async def test_auth_error_handling():
    """Test 401/403 triggers LiteLLMAuthError."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = LiteLLMApiClient("http://localhost:4000", api_key="bad-key", session=session)

    mock_resp = AsyncMock()
    mock_resp.status = 401
    mock_resp.text = AsyncMock(return_value="Unauthorized")
    session.request.return_value.__aenter__.return_value = mock_resp

    with pytest.raises(LiteLLMAuthError):
        await client._request("GET", "key/info")


@pytest.mark.asyncio
async def test_connection_error_handling():
    """Test connection error triggers LiteLLMConnectionError."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = LiteLLMApiClient("http://localhost:4000", session=session)
    session.request.side_effect = aiohttp.ClientConnectorError(
        connection_key=MagicMock(), os_error=OSError("Connection refused")
    )

    with pytest.raises(LiteLLMConnectionError):
        await client._request("GET", "health")


@pytest.mark.asyncio
async def test_get_key_info():
    """Test parsing key info and budget."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = LiteLLMApiClient("http://localhost:4000", api_key="sk-1234", session=session)

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.json = AsyncMock(
        return_value={
            "info": {
                "spend": 14.52,
                "max_budget": 50.0,
                "user_id": "test-user",
                "team_id": "test-team",
                "models": ["gpt-4o", "claude-3-5-sonnet"],
            }
        }
    )
    session.request.return_value.__aenter__.return_value = mock_resp

    info = await client.get_key_info()
    assert info["spend"] == 14.52
    assert info["max_budget"] == 50.0
    assert info["user_id"] == "test-user"


@pytest.mark.asyncio
async def test_fetch_all_data():
    """Test full data aggregation."""
    session = MagicMock(spec=aiohttp.ClientSession)
    client = LiteLLMApiClient("http://localhost:4000", api_key="sk-test", session=session)

    # Mock health, key/info, global/spend/report, spend/keys, spend/users, spend/tags, user/daily/activity
    async def mock_request(method, endpoint, params=None, json_data=None):
        if "health" in endpoint:
            return {"status": "healthy"}
        if "key/info" in endpoint:
            return {
                "info": {
                    "spend": 25.5,
                    "max_budget": 100.0,
                    "user_id": "u-1",
                    "models": ["gpt-4o"],
                }
            }
        if "global/spend/report" in endpoint:
            return [{"spend": 150.0}, {"spend": 75.0}]
        if "spend/keys" in endpoint:
            return [{"api_key": "k1", "spend": 25.5}, {"api_key": "k2", "spend": 50.0}]
        if "spend/tags" in endpoint:
            return [{"tag": "customer-bot", "spend": 30.0}]
        if "daily/activity" in endpoint:
            return {
                "results": [
                    {
                        "date": "2026-09-14",
                        "metrics": {"spend": 12.0},
                        "breakdown": {"models": {"gpt-4o": {"spend": 12.0}}},
                    }
                ],
                "metadata": {
                    "total_spend": 225.0,
                    "total_tokens": 5000,
                    "total_api_requests": 20,
                },
            }
        return {}

    client._request = AsyncMock(side_effect=mock_request)

    data: LiteLLMData = await client.fetch_all_data()
    assert data.healthy is True
    assert data.key_spend == 25.5
    assert data.key_max_budget == 100.0
    assert data.key_budget_remaining == 74.5
    assert data.total_spend == 225.0
    assert data.keys_count == 2
    assert data.tag_spend == {"customer-bot": 30.0}
    assert data.model_spend == {"gpt-4o": 12.0}
    assert data.today_spend == 12.0
    assert data.total_tokens == 5000
    assert data.total_requests == 20
