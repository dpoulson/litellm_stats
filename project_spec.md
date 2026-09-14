# Home Assistant LiteLLM Cost Integration Project Specification

## Overview
A custom Home Assistant integration for monitoring [LiteLLM](https://github.com/BerriAI/litellm) proxy spend and usage statistics. Exposes sensors for total spend, API key spend, budget remaining, percentage used, model breakdowns, and daily spend.

## Architecture
- **Domain**: `litellm_cost`
- **Class**: `local_polling`
- **Client**: `aiohttp` async client contacting LiteLLM Proxy API (`/health`, `/key/info`, `/global/spend/report`, `/spend/keys`, `/user/daily/activity`)
- **Coordinator**: `DataUpdateCoordinator[LiteLLMData]` with configurable polling frequency (default 60s)
- **Entities**:
  - `sensor.litellm_proxy_total_spend` (Monetary, Total)
  - `sensor.litellm_proxy_key_spend` (Monetary, Total)
  - `sensor.litellm_proxy_remaining_budget` (Monetary, Measurement)
  - `sensor.litellm_proxy_budget_usage` (%, Measurement)
  - `sensor.litellm_proxy_today_spend` (Monetary, Total Increasing)
  - `sensor.litellm_proxy_active_keys` (Measurement)
  - `sensor.litellm_proxy_top_model_by_spend`

## Configuration Options
- `api_host`: Host and port for LiteLLM proxy (e.g. `http://localhost:4000`)
- `api_key`: Optional LiteLLM API key or Master Key
- `currency`: Currency unit (USD, EUR, GBP, etc.)
- `scan_interval`: Polling interval in seconds (default: 60s)
- `verify_ssl`: Boolean for SSL certificate verification

## Roadmap & Status
- [x] Project structure and HACS compatibility (`hacs.json`, `manifest.json`)
- [x] Asynchronous API client with health checks, auth handling, fallback logic (`api.py`)
- [x] DataUpdateCoordinator with resilient polling (`coordinator.py`)
- [x] Config Flow and Options Flow with validation (`config_flow.py`)
- [x] Home Assistant Sensors (`sensor.py`)
- [x] Full unit test suite with 15 passing tests (`pytest`)
- [x] Alert automations (`automations/cost_alert_automation.yaml`)
- [x] Lovelace dashboard example (`examples/dashboard.yaml`)
- [ ] ESP32 / Display hardware integration (Phase 2 stretch goal)
