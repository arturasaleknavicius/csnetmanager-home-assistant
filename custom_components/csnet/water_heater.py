# water_heater.py
from homeassistant.components.water_heater import WaterHeaterEntity, WaterHeaterEntityFeature
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.core import callback
import logging

from .const import DOMAIN, ELEMENT_PREFIX  # Add this import

_LOGGER = logging.getLogger(__name__)

class WaterHeater(CoordinatorEntity, WaterHeaterEntity):
    """Representation of a water heater entity."""

    def __init__(self, coordinator, name, idx, parentId) -> None:
        """Initialize the water heater."""
        super().__init__(coordinator, context=idx)
        self._name = name
        self._parentId = parentId
        self._attr_unique_id = f"hitachi_pump_water_{name}"
        self.idx = idx
        self.coordinator = coordinator
        self.hub = coordinator.hub
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_operation_list = ["off", "heat"]  # Supported operation modes
        self._attr_current_operation = "off"  # Default operation mode
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE | WaterHeaterEntityFeature.OPERATION_MODE
        )
        self._attr_target_temperature = 50.0  # Default target temperature
        self._attr_min_temp = 35  # Minimum temperature for water heater
        self._attr_max_temp = 65  # Maximum temperature for water heater

    @property
    def name(self) -> str:
        """Return the name of the water heater."""
        return self._name

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set the operation mode of the water heater."""
        _LOGGER.debug(f"Setting operation mode to {operation_mode} for {self._name}")
        try:
            if operation_mode == "off":
                self._attr_current_operation = "off"
                self.async_write_ha_state()
                await self.hub.set_water_heater_state(self._parentId, 0)  # Turn off
            elif operation_mode == "heat":
                self._attr_current_operation = "heat"
                self.async_write_ha_state()
                await self.hub.set_water_heater_state(self._parentId, 1)  # Turn on
        except Exception as e:
            _LOGGER.error(f"Error setting operation mode: {e}")

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the target temperature of the water heater."""
        _LOGGER.debug(f"Setting temperature for {self._name} to {kwargs.get('temperature')}")
        try:
            temperature = kwargs.get("temperature")
            if temperature is not None:
                self._attr_target_temperature = temperature
                self.async_write_ha_state()
                await self.hub.set_water_heater_temperature(self._parentId, temperature)
        except Exception as e:
            _LOGGER.error(f"Error setting temperature: {e}")

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if self.idx in self.coordinator.data:
            self._attr_current_temperature = self.coordinator.data[self.idx]["currentTemperature"]
            self._attr_current_operation = "off" if self.coordinator.data[self.idx]["onOff"] == 0 else "heat"
            self.async_write_ha_state()
        else:
            _LOGGER.error(f"Element with idx {self.idx} not found in coordinator data.")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the water heater platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    elements = coordinator.data

    entities = []
    for key, element in elements.items():
        mode_icon = element.get("mode_icon", "")
        class_name = element.get("class_name", "")
        zone_name = element.get("zone_name", "")

        # Check if the element is a water heater
        if mode_icon == "ic_dhw.svg" or "unitCard" in class_name or "Hot Water" in zone_name:
            entity = WaterHeater(
                coordinator,
                ELEMENT_PREFIX + str(key),  # Use the key as the unique identifier
                element["elementType"],     # Pass the element type
                element["parentId"],        # Pass the parent ID
            )
            entities.append(entity)

    async_add_entities(entities)