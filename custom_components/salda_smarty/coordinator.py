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

    async def _async_setup(self) -> None:
        async with self._modbus_lock:
            if not await self.hass.async_add_executor_job(self.client.update):
                raise UpdateFailed(f"Failed to update Smarty data for slave {self.slave}")
            self.software_version = self.client.get_software_version()
            self.configuration_version = self.client.get_configuration_version()

    async def _async_update_data(self) -> None:
        """Fetch data from Smarty."""
        async with self._modbus_lock:
            if not await self.hass.async_add_executor_job(self.client.update):
                raise UpdateFailed(f"Failed to update Smarty data for slave {self.slave}")
