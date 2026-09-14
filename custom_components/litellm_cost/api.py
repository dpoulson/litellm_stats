"""API Client for LiteLLM Proxy."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)


class LiteLLMApiError(Exception):
    """General LiteLLM API exception."""


class LiteLLMAuthError(LiteLLMApiError):
    """Authentication or authorization failure."""


class LiteLLMConnectionError(LiteLLMApiError):
    """Connection error when reaching LiteLLM proxy."""


@dataclass
class LiteLLMData:
    """Consolidated metrics from LiteLLM proxy."""

    healthy: bool = True
    total_spend: float = 0.0
    key_spend: float | None = None
    key_max_budget: float | None = None
    key_budget_remaining: float | None = None
    key_user_id: str | None = None
    key_team_id: str | None = None
    key_models: list[str] = field(default_factory=list)
    keys_count: int = 0
    users_count: int = 0
    model_spend: dict[str, float] = field(default_factory=dict)
    tag_spend: dict[str, float] = field(default_factory=dict)
    today_spend: float | None = None
    monthly_spend: float | None = None
    raw_key_info: dict[str, Any] = field(default_factory=dict)


class LiteLLMApiClient:
    """Client for interacting with LiteLLM proxy."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        session: aiohttp.ClientSession | None = None,
        verify_ssl: bool = True,
        timeout: int = 10,
    ) -> None:
        """Initialize client."""
        clean_url = base_url.strip().rstrip("/")
        if not clean_url.startswith(("http://", "https://")):
            clean_url = f"http://{clean_url}"
        self.base_url = clean_url
        self.api_key = api_key.strip() if api_key else None
        self._session = session
        self._verify_ssl = verify_ssl
        self._timeout = aiohttp.ClientTimeout(total=timeout)

    @property
    def headers(self) -> dict[str, str]:
        """Generate authorization headers."""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Execute HTTP request with error handling."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        should_close = False
        session = self._session

        if session is None:
            session = aiohttp.ClientSession(timeout=self._timeout)
            should_close = True

        try:
            async with session.request(
                method,
                url,
                headers=self.headers,
                params=params,
                json=json_data,
                ssl=self._verify_ssl,
            ) as response:
                if response.status in (401, 403):
                    error_text = await response.text()
                    raise LiteLLMAuthError(
                        f"Authentication failed ({response.status}): {error_text}"
                    )

                if response.status >= 400:
                    error_text = await response.text()
                    raise LiteLLMApiError(
                        f"LiteLLM error ({response.status}): {error_text}"
                    )

                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    return await response.json()
                text = await response.text()
                return text

        except (aiohttp.ClientConnectorError, aiohttp.ServerTimeoutError, asyncio.TimeoutError) as err:
            raise LiteLLMConnectionError(f"Failed to connect to LiteLLM at {url}: {err}") from err
        except (LiteLLMApiError, LiteLLMAuthError):
            raise
        except Exception as err:
            raise LiteLLMApiError(f"Unexpected error communicating with LiteLLM: {err}") from err
        finally:
            if should_close and session is not None:
                await session.close()

    async def check_health(self) -> bool:
        """Check if LiteLLM is reachable and healthy."""
        for endpoint in ("health/liveliness", "health", "health/readiness"):
            try:
                res = await self._request("GET", endpoint)
                if isinstance(res, dict):
                    status = str(res.get("status", "")).lower()
                    if status in ("healthy", "ok", "live", "true") or res.get("healthy") is True:
                        return True
                elif isinstance(res, str) and "healthy" in res.lower():
                    return True
                return True
            except LiteLLMAuthError:
                # If health check requires auth or auth failed, we know host is reachable
                return True
            except LiteLLMApiError:
                continue
            except LiteLLMConnectionError:
                raise
        # If /health endpoints are not found (404), try root
        try:
            await self._request("GET", "/")
            return True
        except (LiteLLMConnectionError, LiteLLMAuthError):
            raise
        except LiteLLMApiError:
            return True

    async def get_key_info(self, key: str | None = None) -> dict[str, Any] | None:
        """Fetch info and spend for the current or specified key."""
        target_key = key or self.api_key
        if not target_key:
            return None

        # Try GET /key/info?key=...
        try:
            data = await self._request("GET", "key/info", params={"key": target_key})
            if isinstance(data, dict):
                # Info might be nested under data['info']
                return data.get("info", data)
            return None
        except LiteLLMAuthError:
            raise
        except LiteLLMApiError:
            pass

        # Try POST /key/info with JSON body
        try:
            data = await self._request("POST", "key/info", json_data={"key": target_key})
            if isinstance(data, dict):
                return data.get("info", data)
        except Exception as err:
            _LOGGER.debug("Could not retrieve key info: %s", err)

        return None

    async def get_global_spend_report(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any] | None:
        """Fetch global spend report."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        try:
            return await self._request("GET", "global/spend/report", params=params or None)
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Global spend report unavailable: %s", err)
            return None

    async def get_spend_keys(self) -> list[dict[str, Any]] | None:
        """Fetch spend per API key."""
        try:
            res = await self._request("GET", "spend/keys")
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "keys" in res:
                return res["keys"]
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Spend keys endpoint unavailable: %s", err)
        return None

    async def get_spend_users(self) -> list[dict[str, Any]] | None:
        """Fetch spend per user."""
        try:
            res = await self._request("GET", "spend/users")
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "users" in res:
                return res["users"]
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Spend users endpoint unavailable: %s", err)
        return None

    async def get_spend_tags(self) -> list[dict[str, Any]] | None:
        """Fetch spend per tag."""
        try:
            res = await self._request("GET", "spend/tags")
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "tags" in res:
                return res["tags"]
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Spend tags endpoint unavailable: %s", err)
        return None

    async def get_daily_activity(self) -> list[dict[str, Any]] | None:
        """Fetch daily user/proxy activity."""
        today_str = date.today().isoformat()
        try:
            res = await self._request(
                "GET",
                "user/daily/activity",
                params={"start_date": today_str, "end_date": today_str},
            )
            if isinstance(res, list):
                return res
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Daily activity endpoint unavailable: %s", err)
        return None

    async def fetch_all_data(self) -> LiteLLMData:
        """Aggregate all available LiteLLM metrics."""
        is_healthy = await self.check_health()
        data = LiteLLMData(healthy=is_healthy)

        # 1. Fetch key info
        key_info = None
        if self.api_key:
            try:
                key_info = await self.get_key_info()
            except LiteLLMAuthError:
                raise
            except Exception as err:
                _LOGGER.debug("Failed fetching key info: %s", err)

        if key_info:
            data.raw_key_info = key_info
            spend_val = key_info.get("spend")
            if spend_val is not None:
                try:
                    data.key_spend = float(spend_val)
                    data.total_spend = data.key_spend
                except (ValueError, TypeError):
                    pass

            max_budget = key_info.get("max_budget")
            if max_budget is not None:
                try:
                    data.key_max_budget = float(max_budget)
                    if data.key_spend is not None:
                        data.key_budget_remaining = max(0.0, data.key_max_budget - data.key_spend)
                except (ValueError, TypeError):
                    pass

            data.key_user_id = key_info.get("user_id")
            data.key_team_id = key_info.get("team_id")
            models = key_info.get("models")
            if isinstance(models, list):
                data.key_models = [str(m) for m in models]

        # 2. Fetch global spend report (if accessible)
        report = await self.get_global_spend_report()
        if report:
            calc_spend = 0.0
            if isinstance(report, list):
                for item in report:
                    item_spend = item.get("spend")
                    if item_spend is None and "user_info" in item:
                        item_spend = item["user_info"].get("spend")
                    if item_spend is not None:
                        try:
                            calc_spend += float(item_spend)
                        except (ValueError, TypeError):
                            pass
                if calc_spend > 0:
                    data.total_spend = calc_spend
            elif isinstance(report, dict):
                total = report.get("total_spend") or report.get("spend")
                if total is not None:
                    try:
                        data.total_spend = float(total)
                    except (ValueError, TypeError):
                        pass

        # 3. Spend per key list (admin)
        keys = await self.get_spend_keys()
        if keys:
            data.keys_count = len(keys)
            if data.total_spend == 0.0:
                sum_keys = sum(
                    float(k.get("spend", 0.0) or 0.0)
                    for k in keys
                    if isinstance(k, dict) and k.get("spend") is not None
                )
                if sum_keys > 0:
                    data.total_spend = sum_keys

        # 4. Spend per user list (admin)
        users = await self.get_spend_users()
        if users:
            data.users_count = len(users)

        # 5. Spend per tag list
        tags = await self.get_spend_tags()
        if tags and isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict) and "tag" in t and "spend" in t:
                    try:
                        data.tag_spend[t["tag"]] = float(t["spend"])
                    except (ValueError, TypeError):
                        pass

        # 6. Daily activity
        activity = await self.get_daily_activity()
        if activity and isinstance(activity, list):
            today_cost = 0.0
            for act in activity:
                if isinstance(act, dict):
                    today_cost += float(act.get("spend", 0.0) or 0.0)
                    model = act.get("model")
                    if model:
                        data.model_spend[model] = data.model_spend.get(model, 0.0) + float(
                            act.get("spend", 0.0) or 0.0
                        )
            if today_cost > 0:
                data.today_spend = today_cost

        return data
