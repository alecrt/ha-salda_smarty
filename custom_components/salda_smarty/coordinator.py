"""Smarty Coordinator."""

import asyncio
from datetime import timedelta
from typing import Any, Callable
import logging

from pysmarty2 import Smarty

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds between retries

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

    def _update_once(self) -> Smarty | None:
        """Perform a single update attempt with a fresh client.
        
        Returns the updated client if successful, None otherwise.
        """
        client = Smarty(host=self.config_entry.data[CONF_HOST], device_id=self.slave)
        try:
            if client.update():
                return client
        except Exception as err:
            _LOGGER.debug(
                "Slave %d: Update attempt failed with error: %s",
                self.slave,
                err,
            )
        
        # Close connection on failure
        if hasattr(client, "connection") and hasattr(client.connection, "close"):
            try:
                client.connection.close()
            except Exception:  # noqa: BLE001
                pass
        return None

    async def _async_update_with_retry(self) -> None:
        """Update data with retry logic and on-demand connection.
        
        Creates a fresh connection for the update and closes it afterwards.
        Raises UpdateFailed if all retry attempts fail.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            updated_client = await self.hass.async_add_executor_job(self._update_once)
            
            if updated_client:
                # Update our reference to the client with the new one containing updated registers
                # We do NOT close the connection of the new client yet if we want to be safe,
                # but since we are in "on-demand" mode, we should close it.
                # HOWEVER, entities read from this client object. 
                # Pysmarty2 reads from internal registers, so closing connection is fine for READs.
                if hasattr(updated_client, "connection") and hasattr(updated_client.connection, "close"):
                     await self.hass.async_add_executor_job(updated_client.connection.close)
                
                self.client = updated_client
                
                if attempt > 1:
                    _LOGGER.debug(
                        "Slave %d: Update succeeded on attempt %d",
                        self.slave,
                        attempt,
                    )
                return

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

        raise UpdateFailed(
            f"Failed to update Smarty data for slave {self.slave} after {MAX_RETRIES} attempts"
        )
        
    async def execute_command(self, func: Callable[[Smarty], Any]) -> Any:
        """Execute a command using a temporary on-demand connection."""
        async with self._modbus_lock:
            return await self.hass.async_add_executor_job(self._execute_command_sync, func)

    def _execute_command_sync(self, func: Callable[[Smarty], Any]) -> Any:
        """Synchronous helper to execute command with ephemeral connection."""
        client = Smarty(host=self.config_entry.data[CONF_HOST], device_id=self.slave)
        try:
            # We assume the command (func) will open/use the connection.
            # But pysmarty2 usually opens connection in __init__.
            # So client is ready to use.
            return func(client)
        finally:
             if hasattr(client, "connection") and hasattr(client.connection, "close"):
                try:
                    client.connection.close()
                except Exception:  # noqa: BLE001
                    pass

    async def _async_setup(self) -> None:
        async with self._modbus_lock:
            await self._async_update_with_retry()
            # Since we just updated, self.client has data.
            # But connection is closed. get_software_version reads from registers?
            # Let's verify pysmarty2 source code snippet provided earlier.
            # get_software_version calls registers.get_register(...).state
            # This should work without active connection if registers are populated.
            self.software_version = self.client.get_software_version()
            self.configuration_version = self.client.get_configuration_version()

    async def _async_update_data(self) -> None:
        """Fetch data from Smarty."""
        async with self._modbus_lock:
            await self._async_update_with_retry()
