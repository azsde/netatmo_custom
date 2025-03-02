"""Support for Netatmo/BTicino/Legrande switches."""
from __future__ import annotations

import logging
from typing import Any, cast

from .pyatmo import modules as NaModules

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_URL_CONTROL, NETATMO_CREATE_SWITCH
from .data_handler import HOME, SIGNAL_NAME, NetatmoDevice
from .netatmo_entity_base import NetatmoBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Netatmo switch platform."""

    @callback
    def _create_entity(netatmo_device: NetatmoDevice) -> None:
        entity = NetatmoSwitch(netatmo_device)
        _LOGGER.debug("Adding switch %s", entity)
        async_add_entities([entity])

    entry.async_on_unload(
        async_dispatcher_connect(hass, NETATMO_CREATE_SWITCH, _create_entity)
    )


class NetatmoSwitch(NetatmoBase, SwitchEntity):
    """Representation of a Netatmo switch device."""

    def __init__(
        self,
        netatmo_device: NetatmoDevice,
    ) -> None:
        """Initialize the Netatmo device."""
        SwitchEntity.__init__(self)
        super().__init__(netatmo_device.data_handler)

        self._switch = cast(NaModules.Switch, netatmo_device.device)

        self._id = self._switch.entity_id
        self._attr_name = self._device_name = self._switch.name
        self._model = self._switch.device_type
        self._config_url = CONF_URL_CONTROL

        self._home_id = self._switch.home.entity_id

        self._signal_name = f"{HOME}-{self._home_id}"
        self._publishers.extend(
            [
                {
                    "name": HOME,
                    "home_id": self._home_id,
                    SIGNAL_NAME: self._signal_name,
                },
            ]
        )
        self._attr_unique_id = f"{self._id}-{self._model}"
        self._attr_is_on = self._switch.on

    async def async_added_to_hass(self) -> None:
        """Entity created."""
        await super().async_added_to_hass()

    @callback
    def async_update_callback(self) -> None:
        """Update the entity's state."""
        self._attr_is_on = self._switch.on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the zone on."""
        await self._switch.async_on()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the zone off."""
        await self._switch.async_off()
