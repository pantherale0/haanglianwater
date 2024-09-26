# Anglian Water

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Integration to integrate with [haanglianwater][haanglianwater]._

**This integration will set up the following platforms.**

| Platform | Description                                    |
| -------- | ---------------------------------------------- |
| `sensor` | Show the previous day water usage information. |

This integration will also collect the past year worth of smart meter readings from your dashboard and import them into a statistic for use with your energy dashboard.

## Installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `anglian_water`.
1. Download _all_ the files from the `custom_components/anglian_water/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Anglian Water"

## Configuration is done in the UI

<!---->

You should generally leave the Device ID field blank, the integration will generate this automatically after clicking submit.

Note, during first sign in, the integration needs to "register" Home Assistant as a mobile device to your Anglian Water account, to configure the access token and device IDs correctly a number of requests must be sent in a specific order. Enabling debug mode you will see it makes two requests to "register_device", a request to "get_dashboard_details" and finally a request to "get_bills_payments".

If the integration does not send the above queries in that order, the API to retrieve usage details continues to stay locked and this integration will not work. The integration does not store or process the data returned from the APIs for these extra endpoints, they are simply used to replicate the calls the mobile app creates.

Starting in version 2024.10.0 different areas and tariff options are available, the config flow has been updated to reflect this. Defining your area is optional, however the import rate for your water usage will be inaccurate. Issues reporting an inaccurate water rate with a undefined area will be closed.

If you receive any additional discounts on top of any existing tariff's, ensure you select "Custom" and provide the custom rate (£/m3) from your latest bill. If you are unsure, please contact Anglian Water to confirm your tariff and current water rate.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

---

[haanglianwater]: https://github.com/pantherale0/haanglianwater
[buymecoffee]: https://www.buymeacoffee.com/pantherale0
[buymecoffeebadge]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=for-the-badge
[commits-shield]: https://img.shields.io/github/commit-activity/y/pantherale0/haanglianwater.svg?style=for-the-badge
[commits]: https://github.com/pantherale0/haanglianwater/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/pantherale0/haanglianwater.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-%40pantherale0-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/pantherale0/haanglianwater.svg?style=for-the-badge
[releases]: https://github.com/pantherale0/haanglianwater/releases
