from homeassistant.components.climate import PLATFORM_SCHEMA, ClimateEntity, HVACMode
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
import logging
from .const import DOMAIN, ELEMENT_PREFIX  # Add this import

# Setup logging
_LOGGER = logging.getLogger(__name__)

class Climate(CoordinatorEntity, ClimateEntity):
    """Representation of a climate entity for room heating."""

    def __init__(self, coordinator, name, idx, parentId) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, context=idx)
        self._name = name
        self._parentId = parentId
        self._attr_unique_id = "hitachi_pump" + name
        self.idx = idx
        self.coordinator = coordinator
        self.hub = coordinator.hub
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]  # Valid HVAC modes
        self._attr_hvac_mode = HVACMode.OFF  # Default HVAC mode
        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
        self._attr_target_temperature = 22.0

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode."""
        try:
            if hvac_mode == HVACMode.OFF:
                self._attr_hvac_mode = HVACMode.OFF
                self.async_write_ha_state()
                await self.hub.toggle(self._parentId, self.idx, 0, self._attr_target_temperature)
            elif hvac_mode == HVACMode.HEAT:
                self._attr_hvac_mode = HVACMode.HEAT
                self.async_write_ha_state()
                await self.hub.toggle(self._parentId, self.idx, 1, self._attr_target_temperature)
        except Exception as e:
            _LOGGER.error(f"Error setting HVAC mode: {e}")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature."""
        try:
            self._attr_target_temperature = kwargs["temperature"]
            self.async_write_ha_state()
            await self.hub.toggle(self._parentId, self.idx, 1, kwargs["temperature"])
        except Exception as e:
            _LOGGER.error(f"Error setting temperature: {e}")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.idx in self.coordinator.data:
            self._attr_current_temperature = self.coordinator.data[self.idx]["currentTemperature"]
            self._attr_hvac_mode = HVACMode.OFF if self.coordinator.data[self.idx]["onOff"] == 0 else HVACMode.HEAT
            self.async_write_ha_state()
        else:
            _LOGGER.error(f"Element with idx {self.idx} not found in coordinator data.")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the climate platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    elements = coordinator.data

    entities = []
    for key, element in elements.items():  # Iterate over key-value pairs
        mode_icon = element.get("mode_icon", "")
        class_name = element.get("class_name", "")
        zone_name = element.get("zone_name", "")

        # Check if the element is a climate entity (e.g., air heater)
        if mode_icon == "ic_heat.svg" or "unitCardHeat" in class_name or "Room" in zone_name:
            entity = Climate(
                coordinator,
                ELEMENT_PREFIX + str(key),  # Use the key as the unique identifier
                element["elementType"],     # Pass the element type
                element["parentId"],        # Pass the parent ID
            )
            entities.append(entity)

    async_add_entities(entities)
