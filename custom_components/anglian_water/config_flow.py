"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, CONF_ACCESS_TOKEN
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pyanglianwater.auth import MSOB2CAuth
from pyanglianwater.exceptions import (
    ServiceUnavailableError,
    SelfAssertedError,
    SmartMeterUnavailableError,
)


from .const import (
    DOMAIN,
    LOGGER,
    CONF_TARIFF,
    CONF_CUSTOM_RATE,
    CONF_VERSION,
    CONF_AREA,
    ANGLIAN_WATER_AREAS
)


class AnglianWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = CONF_VERSION
    _user_input: dict = {}

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                auth = MSOB2CAuth(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                    session=async_get_clientsession(self.hass),
                )
                await auth.send_login_request()
                user_input[CONF_ACCESS_TOKEN] = auth.refresh_token
            except SelfAssertedError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except ServiceUnavailableError:
                LOGGER.warning(
                    "Anglian Water app service is unavailable. Check the app for more information."
                )
                _errors["base"] = "maintenance"
            else:
                self._user_input = user_input
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )
        areas = [selector.SelectOptionDict(
            value=k, label=k) for k in ANGLIAN_WATER_AREAS]
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME, ""),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                    vol.Required(CONF_PASSWORD): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        ),
                    ),
                    vol.Required(
                        CONF_AREA,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=areas,
                            multiple=False,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=_errors,
        )

    async def async_step_tariff(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle tariff step."""
        if user_input is None:
            tariffs = [
                selector.SelectOptionDict(value=k, label=k) for k in ANGLIAN_WATER_AREAS[
                    self._user_input.get(CONF_AREA, "Anglian")
                ]
            ]
            return self.async_show_form(
                step_id="tariff",
                data_schema=vol.Schema(
                    {
                        vol.Required(
                            CONF_TARIFF,
                            default=(user_input or {}).get(
                                CONF_TARIFF, "Standard"),
                        ): selector.SelectSelector(
                            selector.SelectSelectorConfig(
                                options=tariffs,
                                multiple=False,
                                mode=selector.SelectSelectorMode.DROPDOWN,
                            )
                        )
                    }
                )
            )

        self._user_input = {**self._user_input, **user_input}
        tariff_config = ANGLIAN_WATER_AREAS[self._user_input[CONF_AREA]
                                            ][user_input[CONF_TARIFF]]

        if tariff_config.get("custom", False):
            return await self.async_step_custom_rate()
        else:
            self._user_input = {**self._user_input,
                                CONF_CUSTOM_RATE: tariff_config["rate"]}
            return self.async_create_entry(
                title=self._user_input[CONF_USERNAME],
                data=self._user_input,
            )

    async def async_step_custom_rate(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle rate step."""
        if user_input is None:
            return self.async_show_form(
                step_id="custom_rate",
                data_schema=vol.Schema(
                    {
                        vol.Optional(
                            CONF_CUSTOM_RATE,
                            description={"suggested_value": 2.0954},
                        ): selector.NumberSelector(
                            selector.NumberSelectorConfig(
                                unit_of_measurement="GBP",
                                mode=selector.NumberSelectorMode.BOX,
                            )
                        )
                    }
                )
            )

        self._user_input = {**self._user_input, **user_input}
        return self.async_create_entry(
            title=self._user_input[CONF_USERNAME],
            data=self._user_input,
        )
