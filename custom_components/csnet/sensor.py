import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class OutdoorTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of the outdoor temperature sensor."""

    def __init__(self, coordinator, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._state = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Outdoor Temperature"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return UnitOfTemperature.CELSIUS

    async def async_update(self):
        """Fetch the outdoor temperature from the coordinator."""
        # Access the coordinator's data
        coordinator_data = self.coordinator.data

        # Extract temperature safely
        if "avOuTemp" in coordinator_data:
            self._state = coordinator_data["avOuTemp"]
        else:
            _LOGGER.warning("Outdoor temperature (avOuTemp) not found in coordinator data.")

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the CSNet sensor platform."""
    _LOGGER.debug("Setting up CSNet sensor platform.")
    
    # Get the coordinator from Home Assistant's stored data
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Fetch full data
    full_data = coordinator.hub.last_full_data if hasattr(coordinator.hub, "last_full_data") else {}

    # Store full data separately in coordinator (without modifying elements)
    coordinator.full_data = full_data

    # Create and add the outdoor temperature sensor
    if "avOuTemp" in full_data:
        _LOGGER.debug("✅ Found avOuTemp in data. Adding sensor.")
        async_add_entities([OutdoorTemperatureSensor(coordinator, "CSNet")])
    else:
        _LOGGER.warning("❌ avOuTemp not found in data. Sensor will not be created.")


async def async_update(self):
    """Force the hub to refresh data and update the sensor."""
    await self.coordinator.async_request_refresh()  # 🔄 Force data refresh

    full_data = self.coordinator.hub.last_full_data if hasattr(self.coordinator.hub, "last_full_data") else {}

    _LOGGER.debug(f"✅ Full data in sensor after forced refresh: {full_data}")

    if "avOuTemp" in full_data:
        self._state = float(full_data["avOuTemp"])
        _LOGGER.debug(f"✅ Outdoor temperature updated: {self._state}°C")
    else:
        _LOGGER.warning("❌ ERROR: Outdoor temperature (avOuTemp) not found in API response.")
