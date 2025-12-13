"""Config flow for Smarty integration."""

import logging
from typing import Any

from pysmarty2 import Smarty
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST

from .const import CONF_SLAVES, DEFAULT_SLAVE, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _parse_slaves(slaves_str: str) -> list[int] | None:
    """Parse comma-separated slave addresses string into list of integers."""
    try:
        slaves = [int(s.strip()) for s in slaves_str.split(",") if s.strip()]
        # Validate range (Modbus addresses 1-247)
        if all(1 <= s <= 247 for s in slaves) and slaves:
            return slaves
    except ValueError:
        pass
    return None


class SmartyConfigFlow(ConfigFlow, domain=DOMAIN):
    """Smarty config flow."""

    def _test_connection(self, host: str, device_id: int) -> str | None:
        """Test the connection to the Smarty API."""
        smarty = Smarty(host=host, device_id=device_id)
        try:
            if smarty.update():
                return None
        except Exception:
            _LOGGER.exception("Unexpected exception")
            return "unknown"
        else:
            return "cannot_connect"

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Parse slaves string
            slaves_str = user_input.get(CONF_SLAVES, str(DEFAULT_SLAVE))
            slaves = _parse_slaves(slaves_str)

            if slaves is None:
                errors[CONF_SLAVES] = "invalid_slaves"
            else:
                # Test connection with first slave
                error = await self.hass.async_add_executor_job(
                    self._test_connection, user_input[CONF_HOST], slaves[0]
                )
                if not error:
                    # Store parsed slaves list
                    data = {
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_SLAVES: slaves,
                    }
                    self._async_abort_entries_match({CONF_HOST: data[CONF_HOST]})
                    return self.async_create_entry(
                        title=user_input[CONF_HOST], data=data
                    )
                errors["base"] = error

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_SLAVES, default=str(DEFAULT_SLAVE)): str,
            }),
            errors=errors,
        )