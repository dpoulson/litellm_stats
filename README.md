<p align="center">
  <img src="logo.png" alt="LiteLLM Cost & Stats for Home Assistant" width="160">
</p>

# LiteLLM Cost & Stats Integration for Home Assistant

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dpoulson&repository=litellm_stats&category=integration)
[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=litellm_cost)
[![GitHub Release](https://img.shields.io/github/v/release/dpoulson/litellm_stats?style=flat-square)](https://github.com/dpoulson/litellm_stats/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=flat-square)](https://github.com/hacs/default)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

A modern Home Assistant custom component to monitor [LiteLLM](https://github.com/BerriAI/litellm) proxy spend, token usage, API request volumes, and active budgets in real time.

---

## Features

- **Real-Time Spend Monitoring**: Track proxy-wide expenditure across all applications as well as individual key-level spend.
- **Token & Request Telemetry**: Sensors for total tokens, prompt tokens, completion tokens, and total/failed API requests.
- **Budget Tracking & Proactive Alerts**: Expose remaining budget, budget consumption percentage, and configure native threshold notifications before quotas are exhausted.
- **Model Attribution**: Identify your highest-spending models and view granular model spend breakdown attributes.
- **Asynchronous & Non-Blocking**: Built on `aiohttp` and Home Assistant's `DataUpdateCoordinator` for fast, lightweight local polling.
- **Native UI Configuration**: Set up directly via **Settings &rarr; Devices & Services &rarr; Add Integration** with automatic connectivity and credential validation.
- **Customizable Options**: Adjust polling intervals (10s to 24h) and preferred currency (USD, EUR, GBP, CAD, AUD, etc.) at any time.

---

## Available Sensors

| Sensor | Entity ID | Device Class | State Class | Description |
|---|---|---|---|---|
| **Total Spend** | `sensor.litellm_proxy_total_spend` | `monetary` | `total` | Aggregate proxy expenditure across all keys and models |
| **Key Spend** | `sensor.litellm_proxy_key_spend` | `monetary` | `total` | Current billing window spend for the configured key |
| **Remaining Budget** | `sensor.litellm_proxy_remaining_budget` | `monetary` | `measurement` | Remaining balance before reaching the key's max budget |
| **Budget Usage** | `sensor.litellm_proxy_budget_usage` | - | `measurement` | Percentage of budget consumed (`%`) |
| **Today Spend** | `sensor.litellm_proxy_today_spend` | `monetary` | `total_increasing` | Total cost recorded today |
| **Total Tokens** | `sensor.litellm_proxy_total_tokens` | - | `total` | Total prompt + completion tokens processed |
| **Total Requests** | `sensor.litellm_proxy_total_requests` | - | `total` | Total API requests handled by the proxy |
| **Active Keys** | `sensor.litellm_proxy_active_keys` | - | `measurement` | Total number of registered virtual keys (admin mode) |
| **Top Model by Spend** | `sensor.litellm_proxy_top_model_by_spend` | - | - | Model responsible for the highest spend |

---

## Installation

### Method 1: One-Click HACS Install (Recommended)

Click the badge below to open the repository directly inside HACS on your Home Assistant instance:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=dpoulson&repository=litellm_stats&category=integration)

1. Click **Download**.
2. Select the latest version and confirm.
3. Restart Home Assistant.

### Method 2: Manual HACS Custom Repository

1. In Home Assistant, open **HACS** &rarr; **Integrations**.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Enter repository URL: `https://github.com/dpoulson/litellm_stats`
4. Set Type: **Integration**.
5. Click **Add**, then find **LiteLLM Cost & Stats** in the store and click **Download**.
6. Restart Home Assistant.

### Method 3: Manual File Copy

1. Download the latest [`litellm_cost.zip`](https://github.com/dpoulson/litellm_stats/releases/latest) release or clone the repository.
2. Copy the `custom_components/litellm_cost/` folder into your Home Assistant directory:
   ```
   <config>/custom_components/litellm_cost/
   ```
3. Restart Home Assistant.

---

## Configuration

Once installed and Home Assistant has restarted, add the integration:

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=litellm_cost)

Or navigate manually to:
**Settings** &rarr; **Devices & Services** &rarr; **Add Integration** &rarr; search for **LiteLLM Cost & Stats**.

### Configuration Fields

- **LiteLLM Host**: The base URL of your LiteLLM proxy (e.g. `http://localhost:4000` or `https://litellm.example.com`).
- **API Key**: 
  - **Master Key (`LITELLM_MASTER_KEY`)**: Recommended if you want global proxy-wide spend, token metrics, and active key counts.
  - **Virtual Key**: If using a virtual key, ensure it has the **`Proxy Admin View Only`** role (`proxy_admin_viewer`) or the permission `{"get_spend_routes": true}` in the LiteLLM UI to allow spend metric lookups.
- **Currency**: Your preferred currency code (`USD`, `EUR`, `GBP`, `CAD`, `AUD`, etc.).
- **Update Interval**: Polling frequency in seconds (default: `60`).
- **Verify SSL**: Toggle off if using internal self-signed certificates.

---

## Dashboard Card Example

Add a Lovelace gauge and metrics card to your dashboard:

```yaml
type: vertical-stack
cards:
  - type: gauge
    entity: sensor.litellm_proxy_budget_usage
    name: "LiteLLM Budget Consumed"
    min: 0
    max: 100
    needle: true
    severity:
      green: 0
      yellow: 70
      red: 90

  - type: entities
    title: "LiteLLM AI Metrics"
    entities:
      - entity: sensor.litellm_proxy_total_spend
        name: "Total Spend"
      - entity: sensor.litellm_proxy_key_spend
        name: "Key Spend"
      - entity: sensor.litellm_proxy_remaining_budget
        name: "Remaining Budget"
      - entity: sensor.litellm_proxy_today_spend
        name: "Spend Today"
      - entity: sensor.litellm_proxy_total_tokens
        name: "Total Tokens"
      - entity: sensor.litellm_proxy_total_requests
        name: "Total Requests"
      - entity: sensor.litellm_proxy_top_model_by_spend
        name: "Highest Spend Model"
```

---

## Budget Alert Automation

Notify your phone or persistent dashboard when your LiteLLM budget hits 80% or 100%:

```yaml
alias: "LiteLLM Budget Warning"
trigger:
  - platform: numeric_state
    entity_id: sensor.litellm_proxy_budget_usage
    above: 80
action:
  - service: persistent_notification.create
    data:
      title: "LiteLLM Budget Warning"
      message: "LiteLLM has used {{ states('sensor.litellm_proxy_budget_usage') }}% of its allocated budget."
```

*(See [`automations/cost_alert_automation.yaml`](automations/cost_alert_automation.yaml) for full multi-tier notification rules).*

---

## Testing & Development

Run the test suite locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r <(pip list) pytest pytest-asyncio aiohttp voluptuous
pytest
```

---

## License

MIT License &copy; Darren Poulson
