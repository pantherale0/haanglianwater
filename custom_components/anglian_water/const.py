"""Constants for integration_blueprint."""

from logging import Logger, getLogger
import voluptuous as vol

LOGGER: Logger = getLogger(__package__)

NAME = "Anglian Water"
DOMAIN = "anglian_water"
VERSION = "0.0.0"

CONF_DEVICE_ID = "device_id"
CONF_TARIFF = "tariff"
CONF_CUSTOM_RATE = "custom_rate"
CONF_VERSION = 2
CONF_AREA = "area"

SVC_GET_USAGES_SCHEMA = vol.Schema(
    {vol.Required("start"): str, vol.Required("end"): str}
)

SVC_FORCE_REFRESH_STATISTICS = vol.Schema(
    {vol.Required("start"): str, vol.Required("end"): str}
)
