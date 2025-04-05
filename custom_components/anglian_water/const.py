"""Constants for integration_blueprint."""

from logging import Logger, getLogger
import voluptuous as vol

from pyanglianwater import _version

LOGGER: Logger = getLogger(__package__)

NAME = "Anglian Water"
DOMAIN = "anglian_water"
VERSION = _version.__version__

CONF_ACCOUNT_ID = "account_id"
CONF_TARIFF = "tariff"
CONF_CUSTOM_RATE = "custom_rate"
CONF_VERSION = 2
CONF_AREA = "area"

SVC_GET_USAGES_SCHEMA = vol.Schema({})

SVC_FORCE_REFRESH_STATISTICS = vol.Schema({})
