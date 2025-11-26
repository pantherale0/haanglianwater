# Anglian Water

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
![Install Stats][stats]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Integration to integrate with [haanglianwater][haanglianwater]._

**This integration will set up the following platforms.**

| Platform | Description                                    |
| -------- | ---------------------------------------------- |
| `sensor` | Show the latest and previous day water usage information. |

## Future plans

This integration will be deprecated following the release of 2025.12 as this is now a core integration.

## Installation

Ensure you have logged into the new Anglian Water mobile app at least once before configuring this integration.

### Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. Download the zip from the latest release titled `anglian_water.zip`
1. Extract downloaded zip into the `custom_components` folder
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anglian Water"

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pantherale0&category=integration&repository=haanglianwater)

1. Open HACS on your HA instance.
1. Copy the repository URL: [https://github.com/pantherale0/haanglianwater](https://github.com/pantherale0/haanglianwater).
1. In the HACS menu (3 dots in the top right corner), choose "Custom repositories."
1. Paste the copied URL into the repository field.
1. Set the Type as "Integration."
1. Click "Add."
1. Restart Home Assistant.
1. In the HA UI, go to "Configuration" -> "Integrations," click "+," and search for "Anglian Water."

## Configuration is done in the UI

<!---->

Starting in version 2024.10.0 different areas and tariff options are available, the config flow has been updated to reflect this.

If you receive any additional discounts on top of any existing tariff's, ensure you select "Custom" and provide the custom rate (£/m3) from your latest bill. If you are unsure, please contact Anglian Water to confirm your tariff and current water rate.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[haanglianwater]: https://github.com/pantherale0/haanglianwater
[buymecoffee]: https://www.buymeacoffee.com/pantherale0
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/pantherale0/haanglianwater.svg?style=for-the-badge
[commits]: https://github.com/pantherale0/haanglianwater/commits/main
[stats]: https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=integration%20usage&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.anglian_water.total&style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/pantherale0/haanglianwater.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40pantherale0-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/pantherale0/haanglianwater.svg?style=for-the-badge
[releases]: https://github.com/pantherale0/haanglianwater/releases
