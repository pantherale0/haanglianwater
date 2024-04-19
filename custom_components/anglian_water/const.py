"""Constants for integration_blueprint."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

NAME = "Anglian Water"
DOMAIN = "anglian_water"
VERSION = "0.0.0"

CONF_DEVICE_ID = "device_id"
CONF_TARIFF = "tariff"
CONF_CUSTOM_RATE = "custom_rate"
