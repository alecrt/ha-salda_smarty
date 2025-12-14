"""Platform to control a Salda Smarty XP/XV ventilation unit."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from typing import Any

from pysmarty2 import Smarty

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import SmartyConfigEntry, SmartyCoordinator
from .entity import SmartyEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class SmartySwitchDescription(SwitchEntityDescription):
    """Class describing Smarty switch."""

    is_on_fn: Callable[[Smarty], bool]
    turn_on_fn: Callable[[Smarty], bool | None]
    turn_off_fn: Callable[[Smarty], bool | None]


ENTITIES: tuple[SmartySwitchDescription, ...] = (
    SmartySwitchDescription(
        key="boost",
        translation_key="boost",
        is_on_fn=lambda smarty: smarty.boost,
        turn_on_fn=lambda smarty: smarty.enable_boost(),
        turn_off_fn=lambda smarty: smarty.disable_boost(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartyConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Smarty Switch Platform."""
    coordinators = entry.runtime_data

    async_add_entities(
        SmartySwitch(coordinator, description)
        for coordinator in coordinators.values()
        for description in ENTITIES
    )


class SmartySwitch(SmartyEntity, SwitchEntity):
    """Representation of a Smarty Switch."""

    entity_description: SmartySwitchDescription

    def __init__(
        self,
        coordinator: SmartyCoordinator,
        entity_description: SmartySwitchDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self.entity_description = entity_description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{coordinator.slave}_{entity_description.key}"
        )

    @property
    def is_on(self) -> bool:
        """Return the state of the switch."""
        return self.entity_description.is_on_fn(self.coordinator.client)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        # Use execute_command to ensure we have a live connection
        await self.coordinator.execute_command(self.entity_description.turn_on_fn)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        # Use execute_command to ensure we have a live connection
        await self.coordinator.execute_command(self.entity_description.turn_off_fn)
        await self.coordinator.async_request_refresh()
