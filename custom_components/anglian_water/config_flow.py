"""Adds config flow for Blueprint."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector
from pyanglianwater import API
from pyanglianwater.exceptions import InvalidUsernameError, InvalidPasswordError


from .const import DOMAIN, LOGGER, CONF_DEVICE_ID


class BlueprintFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Blueprint."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                if user_input.get(CONF_DEVICE_ID, "") == "":
                    await API.create_via_login(
                        email=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                    )
                else:
                    await API.create_via_login_existing_device(
                        email=user_input[CONF_USERNAME],
                        password=user_input[CONF_PASSWORD],
                        dev_id=user_input[CONF_DEVICE_ID],
                    )
            except InvalidUsernameError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except InvalidPasswordError as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            except Exception as exception:
                LOGGER.exception(exception)
                _errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_DEVICE_ID, default=(user_input or {}).get(CONF_DEVICE_ID)
                    ): selector.TextSelector(),
                    vol.Required(
                        CONF_USERNAME,
                        default=(user_input or {}).get(CONF_USERNAME),
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
                }
            ),
            errors=_errors,
        )
