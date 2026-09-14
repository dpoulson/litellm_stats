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
    key_alias: str | None = None
    key_spend: float | None = None
    key_max_budget: float | None = None
    key_budget_remaining: float | None = None
    key_budget_duration: str | None = None
    key_budget_reset_at: str | None = None
    key_user_id: str | None = None
    key_team_id: str | None = None
    key_models: list[str] = field(default_factory=list)
    keys_count: int = 0
    users_count: int = 0
    model_spend: dict[str, float] = field(default_factory=dict)
    tag_spend: dict[str, float] = field(default_factory=dict)
    today_spend: float | None = None
    monthly_spend: float | None = None
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_requests: int = 0
    failed_requests: int = 0
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
            headers["x-litellm-api-key"] = self.api_key
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
        # Only pass ?key= parameter if querying an external key different from authenticated key.
        # Self-lookup must omit the query parameter so non-admin virtual keys can read their own stats.
        params = {"key": key} if key and key != self.api_key else None

        # Try GET /key/info
        try:
            data = await self._request("GET", "key/info", params=params)
            if isinstance(data, dict):
                return data.get("info", data)
            return None
        except LiteLLMAuthError:
            if params:
                try:
                    data = await self._request("GET", "key/info")
                    if isinstance(data, dict):
                        return data.get("info", data)
                except Exception:
                    pass
            raise
        except LiteLLMApiError:
            pass

        # Try POST /key/info with JSON body
        if key:
            try:
                data = await self._request("POST", "key/info", json_data={"key": key})
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
        """Fetch spend per API key using /key/list or /spend/keys."""
        # Try /key/list?return_full_object=true first
        try:
            res = await self._request("GET", "key/list", params={"return_full_object": "true"})
            if isinstance(res, list):
                return res
            if isinstance(res, dict) and "keys" in res:
                return res["keys"]
        except (LiteLLMAuthError, LiteLLMApiError) as err:
            _LOGGER.debug("Key list endpoint unavailable: %s", err)

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
        for endpoint in ("spend/tags", "global/spend/tags"):
            try:
                res = await self._request("GET", endpoint)
                if isinstance(res, list):
                    return res
                if isinstance(res, dict) and "tags" in res:
                    return res["tags"]
            except (LiteLLMAuthError, LiteLLMApiError) as err:
                _LOGGER.debug("%s endpoint unavailable: %s", endpoint, err)
        return None

    async def get_aggregated_activity(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch aggregated spend and token metrics from daily activity endpoints."""
        params: dict[str, Any] = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date

        for endpoint in ("user/daily/activity/aggregated", "team/daily/activity/aggregated", "user/daily/activity"):
            try:
                res = await self._request("GET", endpoint, params=params or None)
                if isinstance(res, dict) and ("metadata" in res or "results" in res):
                    return res
                if isinstance(res, list):
                    return {"results": res, "metadata": {}}
            except (LiteLLMAuthError, LiteLLMApiError) as err:
                _LOGGER.debug("%s endpoint unavailable: %s", endpoint, err)
        return None

    async def get_spend_logs(self, page_size: int = 100) -> list[dict[str, Any]] | None:
        """Fetch latest spend logs to capture master key and unallocated requests."""
        for endpoint, params in (
            ("spend/logs/v2", {"page_size": page_size}),
            ("spend/logs", None),
        ):
            try:
                res = await self._request("GET", endpoint, params=params)
                if isinstance(res, dict) and "results" in res:
                    return res["results"]
                if isinstance(res, list):
                    return res
            except (LiteLLMAuthError, LiteLLMApiError) as err:
                _LOGGER.debug("%s endpoint unavailable: %s", endpoint, err)
        return None

    async def fetch_all_data(self) -> LiteLLMData:
        """Aggregate all available LiteLLM metrics."""
        is_healthy = await self.check_health()
        data = LiteLLMData(healthy=is_healthy)

        # 1. Fetch key info (if a specific key is configured)
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
            data.key_alias = key_info.get("key_alias")
            spend_val = key_info.get("spend")
            if spend_val is not None:
                try:
                    data.key_spend = float(spend_val)
                    data.total_spend = max(data.total_spend, data.key_spend)
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

            data.key_budget_duration = key_info.get("budget_duration")
            data.key_budget_reset_at = str(key_info.get("budget_reset_at")) if key_info.get("budget_reset_at") else None
            data.key_user_id = key_info.get("user_id")
            data.key_team_id = key_info.get("team_id")
            models = key_info.get("models")
            if isinstance(models, list):
                data.key_models = [str(m) for m in models]

            model_budgets_usage = key_info.get("model_max_budget_usage")
            if isinstance(model_budgets_usage, dict):
                for m_name, m_spend in model_budgets_usage.items():
                    try:
                        data.model_spend[m_name] = float(m_spend)
                    except (ValueError, TypeError):
                        pass

        # 2. Aggregated Proxy Activity (covers master key and all proxy requests)
        agg = await self.get_aggregated_activity()
        if agg and isinstance(agg, dict):
            metadata = agg.get("metadata", {})
            if isinstance(metadata, dict):
                total_spend_meta = metadata.get("total_spend")
                if total_spend_meta is not None:
                    try:
                        parsed_total = float(total_spend_meta)
                        if parsed_total > 0 or data.total_spend == 0.0:
                            data.total_spend = max(data.total_spend, parsed_total)
                    except (ValueError, TypeError):
                        pass

                data.total_tokens = int(metadata.get("total_tokens", 0) or 0)
                data.prompt_tokens = int(metadata.get("total_prompt_tokens", 0) or 0)
                data.completion_tokens = int(metadata.get("total_completion_tokens", 0) or 0)
                data.total_requests = int(metadata.get("total_api_requests", 0) or 0)
                data.failed_requests = int(metadata.get("total_failed_requests", 0) or 0)

            results = agg.get("results", [])
            if isinstance(results, list):
                today_str = date.today().isoformat()
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    metrics = item.get("metrics", {})
                    item_date = str(item.get("date", ""))
                    if item_date == today_str and isinstance(metrics, dict):
                        t_spend = metrics.get("spend")
                        if t_spend is not None:
                            try:
                                data.today_spend = float(t_spend)
                            except (ValueError, TypeError):
                                pass

                    breakdown = item.get("breakdown", {})
                    if isinstance(breakdown, dict):
                        models_data = breakdown.get("models", {})
                        if isinstance(models_data, dict):
                            for m_name, m_info in models_data.items():
                                if isinstance(m_info, dict) and "spend" in m_info:
                                    try:
                                        data.model_spend[m_name] = data.model_spend.get(m_name, 0.0) + float(m_info["spend"])
                                    except (ValueError, TypeError):
                                        pass

        # 3. Fetch global spend report (support group_by=api_key and default)
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
                    data.total_spend = max(data.total_spend, calc_spend)
            elif isinstance(report, dict):
                total = report.get("total_spend") or report.get("spend")
                if total is not None:
                    try:
                        data.total_spend = max(data.total_spend, float(total))
                    except (ValueError, TypeError):
                        pass

        # 4. Spend per key list (admin)
        keys = await self.get_spend_keys()
        if keys:
            data.keys_count = len(keys)
            sum_keys = sum(
                float(k.get("spend", 0.0) or 0.0)
                for k in keys
                if isinstance(k, dict) and k.get("spend") is not None
            )
            if sum_keys > 0:
                data.total_spend = max(data.total_spend, sum_keys)

        # 5. Spend per user list (admin)
        users = await self.get_spend_users()
        if users:
            data.users_count = len(users)

        # 6. Spend per tag list
        tags = await self.get_spend_tags()
        if tags and isinstance(tags, list):
            for t in tags:
                if isinstance(t, dict) and "tag" in t and "spend" in t:
                    try:
                        data.tag_spend[t["tag"]] = float(t["spend"])
                    except (ValueError, TypeError):
                        pass

        # 7. Fallback: If total spend is still 0, check spend logs
        if data.total_spend == 0.0:
            logs = await self.get_spend_logs(page_size=100)
            if logs and isinstance(logs, list):
                logs_spend = 0.0
                today_str = date.today().isoformat()
                for log in logs:
                    if not isinstance(log, dict):
                        continue
                    cost = float(log.get("spend", 0.0) or 0.0)
                    logs_spend += cost
                    model = log.get("model")
                    if model and cost > 0:
                        data.model_spend[model] = data.model_spend.get(model, 0.0) + cost
                    # Check today's spend
                    start_time = str(log.get("startTime", "") or log.get("created_at", ""))
                    if today_str in start_time:
                        data.today_spend = (data.today_spend or 0.0) + cost
                if logs_spend > 0:
                    data.total_spend = logs_spend

        return data

