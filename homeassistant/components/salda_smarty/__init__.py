"""Support to control a Salda Smarty XP/XV ventilation unit."""

import asyncio

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SLAVES, DEFAULT_SLAVE
from .coordinator import SmartyConfigEntry, SmartyCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: SmartyConfigEntry) -> bool:
    """Set up the Smarty environment from a config entry."""
    # Get slaves list, with backward compatibility for existing configs
    slaves: list[int] = entry.data.get(CONF_SLAVES, [DEFAULT_SLAVE])

    # Shared lock to serialize Modbus requests and avoid conflicts
    modbus_lock = asyncio.Lock()

    coordinators: dict[int, SmartyCoordinator] = {}

    for slave in slaves:
        coordinator = SmartyCoordinator(hass, entry, slave, modbus_lock)
        await coordinator.async_config_entry_first_refresh()
        coordinators[slave] = coordinator

    entry.runtime_data = coordinators

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: SmartyConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
