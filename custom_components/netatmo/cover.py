"""Support for Netatmo/Bubendorff covers."""
from __future__ import annotations

import logging
from typing import Any, cast

from .pyatmo import modules as NaModules

from homeassistant.components.cover import (
    ATTR_POSITION,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    CoverDeviceClass,
    CoverEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_URL_CONTROL, NETATMO_CREATE_COVER
from .data_handler import HOME, SIGNAL_NAME, NetatmoDevice
from .netatmo_entity_base import NetatmoBase

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Netatmo cover platform."""

    @callback
    def _create_entity(netatmo_device: NetatmoDevice) -> None:
        entity = NetatmoCover(netatmo_device)
        _LOGGER.debug("Adding cover %s", entity)
        async_add_entities([entity])

    entry.async_on_unload(
        async_dispatcher_connect(hass, NETATMO_CREATE_COVER, _create_entity)
    )


class NetatmoCover(NetatmoBase, CoverEntity):
    """Representation of a Netatmo cover device."""

    def __init__(self, netatmo_device: NetatmoDevice) -> None:
        """Initialize the Netatmo device."""
        CoverEntity.__init__(self)
        super().__init__(netatmo_device.data_handler)
        self.optimistic = True

        self._cover = cast(NaModules.Shutter, netatmo_device.device)

        self._id = self._cover.entity_id
        self._attr_name = self._device_name = self._cover.name
        self._model = self._cover.device_type
        self._config_url = CONF_URL_CONTROL

        self._home_id = self._cover.home.entity_id
        self._closed: bool | None = None
        self._attr_is_closed = None

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

    @property
    def supported_features(self) -> int:
        """Flag supported features."""
        supported_features = 0
        supported_features |= SUPPORT_OPEN
        supported_features |= SUPPORT_CLOSE
        supported_features |= SUPPORT_STOP
        supported_features |= SUPPORT_SET_POSITION

        return supported_features

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._attr_is_closing = True
        self.async_write_ha_state()
        try:
            await self._cover.async_close()
            if self.optimistic:
                self._attr_is_closed = True
        finally:
            self._attr_is_closing = None
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._attr_is_opening = True
        self.async_write_ha_state()
        try:
            await self._cover.async_open()
            if self.optimistic:
                self._attr_is_closed = False
        finally:
            self._attr_is_opening = None
            self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        await self._cover.async_stop()

        if self.optimistic:
            if self._attr_is_closing:
                self._attr_is_closed = True
            elif self._attr_is_opening:
                self._attr_is_closed = False

            self._attr_is_closing = None
            self._attr_is_opening = None

        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover shutter to a specific position."""
        await self._cover.async_set_target_position(kwargs[ATTR_POSITION])

    @property
    def device_class(self) -> str:
        """Return the device class."""
        return CoverDeviceClass.SHUTTER

    async def async_added_to_hass(self) -> None:
        """Complete the initialization."""
        await super().async_added_to_hass()

    @callback
    def async_update_callback(self) -> None:
        """Update the entity's state."""
        self._attr_is_closed = self._cover.current_position == 0
        self._attr_current_cover_position = self._cover.current_position
