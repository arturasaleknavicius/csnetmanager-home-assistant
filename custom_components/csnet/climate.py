"""Platform for switch integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity, HVACMode

# Import the device class from the component that you want to support
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, ELEMENT_PREFIX

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_USERNAME, default="admin"): cv.string,
        vol.Optional(CONF_PASSWORD): cv.string,
    }
)


# This function is called as part of the __init__.async_setup_entry (via the
# hass.config_entries.async_forward_entry_setup call)
async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    # The hub is loaded from the associated hass.data entry that was created in the
    # __init__.async_setup_entry function
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    elements = coordinator.data
    for key in elements:
        async_add_entities(
            [
                Climate(
                    coordinator,
                    ELEMENT_PREFIX + str(key),
                    elements[key]["elementType"],
                    elements[key]["parentId"],
                )
            ]
        )


class Climate(CoordinatorEntity, ClimateEntity):  # noqa: D101
    def __init__(self, coordinator, name, idx, parentId) -> None:
        super().__init__(coordinator, context=idx)
        self._name = name
        self._parentId = parentId
        self._is_on = None
        self._attr_unique_id = "hitachi_pump" + name
        self.idx = idx
        self.coordinator = coordinator
        self.hub = coordinator.hub
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_supported_features = 1
        self._attr_target_temperature = 25.0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self.async_write_ha_state()
            await self.hub.toggle(
                self._parentId, self.idx, 0, self._attr_target_temperature
            )
        else:
            self._attr_hvac_mode = HVACMode.HEAT
            self.async_write_ha_state()
            await self.hub.toggle(
                self._parentId, self.idx, 1, self._attr_target_temperature
            )

    async def async_set_temperature(self, **kwargs):
        self._attr_target_temperature = kwargs["temperature"]
        self.async_write_ha_state()
        await self.hub.toggle(self._parentId, self.idx, 1, kwargs["temperature"])

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._attr_current_temperature = self.coordinator.data[self.idx][
            "currentTemperature"
        ]
        self._attr_hvac_mode = (
            HVACMode.OFF
            if self.coordinator.data[self.idx]["onOff"] == 0
            else HVACMode.HEAT
        )
        self.async_write_ha_state()
