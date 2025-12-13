"""Smarty Coordinator."""

import asyncio
from datetime import timedelta
import logging

from pysmarty2 import Smarty

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds between retries

type SmartyConfigEntry = ConfigEntry[dict[int, "SmartyCoordinator"]]


class SmartyCoordinator(DataUpdateCoordinator[None]):
    """Smarty Coordinator."""

    config_entry: SmartyConfigEntry
    software_version: str
    configuration_version: str

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: SmartyConfigEntry,
        slave: int,
        modbus_lock: asyncio.Lock,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=f"Smarty (Slave {slave})",
            update_interval=timedelta(seconds=30),
        )
        self.slave = slave
        self.client = Smarty(host=config_entry.data[CONF_HOST], device_id=slave)
        self._modbus_lock = modbus_lock

    async def _async_update_with_retry(self) -> None:
        """Update data with retry logic.

        Raises UpdateFailed if all retry attempts fail.
        """
        last_error: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = await self.hass.async_add_executor_job(self.client.update)
                if result:
                    if attempt > 1:
                        _LOGGER.debug(
                            "Slave %d: Update succeeded on attempt %d",
                            self.slave,
                            attempt,
                        )
                    return
                # Reset last_error since this failure was a False return, not an exception
                last_error = None
                _LOGGER.debug(
                    "Slave %d: Update returned False (attempt %d/%d)",
                    self.slave,
                    attempt,
                    MAX_RETRIES,
                )
            except Exception as err:  # noqa: BLE001
                last_error = err
                _LOGGER.debug(
                    "Slave %d: Update raised exception on attempt %d/%d: %s",
                    self.slave,
                    attempt,
                    MAX_RETRIES,
                    err,
                )

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

        if last_error:
            raise UpdateFailed(
                f"Failed to update Smarty data for slave {self.slave} after {MAX_RETRIES} attempts: {last_error}"
            )
        raise UpdateFailed(
            f"Failed to update Smarty data for slave {self.slave} after {MAX_RETRIES} attempts (update returned False)"
        )

    async def _async_setup(self) -> None:
        async with self._modbus_lock:
            await self._async_update_with_retry()
            self.software_version = self.client.get_software_version()
            self.configuration_version = self.client.get_configuration_version()

    async def _async_update_data(self) -> None:
        """Fetch data from Smarty."""
        async with self._modbus_lock:
            await self._async_update_with_retry()
