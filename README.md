# LiteLLM Cost & Stats for Home Assistant

A custom integration for [Home Assistant](https://www.home-assistant.io/) to monitor [LiteLLM](https://github.com/BerriAI/litellm) API spend, budget utilization, and model metrics in real-time.

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## Features

- **Real-Time Spend Monitoring**: Track total spend across your proxy and specific API key spend.
- **Budget Alerts**: Expose remaining budget and percentage consumed with native threshold alerts.
- **Model Attribution**: Monitor top models by spend and model breakdown attributes.
- **Config Flow & Options Flow**: Simple UI setup and options configuration in Home Assistant.
- **Multi-Currency Support**: Configure USD, GBP, EUR, CAD, AUD, and more.
- **Configurable Scan Interval**: Adjust update rates from 10 seconds to daily.

---

## Available Sensors

| Sensor | Device Class | State Class | Description |
|---|---|---|---|
| `Total Spend` | `monetary` | `total` | Aggregate spend across LiteLLM proxy |
| `Key Spend` | `monetary` | `total` | Total spend for configured API key |
| `Remaining Budget` | `monetary` | `measurement` | Remaining budget allocated to the API key |
| `Budget Usage` | `%` | `measurement` | Percentage of budget consumed |
| `Today Spend` | `monetary` | `total_increasing` | Today's recorded spend |
| `Active Keys` | `keys` | `measurement` | Count of registered keys (admin mode) |
| `Top Model by Spend` | - | - | Model accounting for highest spend |

---

## Installation

### Method 1: HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Add the repository URL: `https://github.com/daz/litellm_stats_integration`
4. Select Category: **Integration**.
5. Click **Add**, then find and install **LiteLLM Cost & Stats**.
6. Restart Home Assistant.

### Method 2: Manual Installation
1. Download or clone this repository.
2. Copy the directory `custom_components/litellm_cost/` into your Home Assistant `<config>/custom_components/` directory.
3. Restart Home Assistant.

---

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**.
2. Search for **LiteLLM Cost & Stats**.
3. Enter your LiteLLM Proxy details:
   - **LiteLLM Host**: `http://localhost:4000` (or your remote proxy URL)
   - **API Key**: Your master key or virtual API key (optional for unauthenticated proxies)
   - **Currency**: `USD` (or GBP, EUR, etc.)
   - **Update Interval**: `60` seconds

---

## Example Automations & Dashboards

- **Alert Automations**: See [`automations/cost_alert_automation.yaml`](automations/cost_alert_automation.yaml) for notifications when budget hits 80% and 100%.
- **Lovelace Dashboard**: See [`examples/dashboard.yaml`](examples/dashboard.yaml) for cards and gauges.

---

## Testing

Run the test suite using pytest:
```bash
pytest
```
