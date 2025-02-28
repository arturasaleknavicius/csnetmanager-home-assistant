# __init__.py
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
import logging

from .const import DOMAIN
from .coordinator import CSnetCoordinator
from .hub import CSnetHub

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CLIMATE, Platform.WATER_HEATER, Platform.SENSOR]  # Add Platform.SENSOR

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up csnet from a config entry."""
    _LOGGER.debug("Setting up csnet integration.")
    hass.data.setdefault(DOMAIN, {})
    hub = CSnetHub(entry.data["username"], entry.data["password"])
    coordinator = CSnetCoordinator(hass, hub)

    _LOGGER.debug("Coordinator created. Refreshing data for the first time.")
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator
    _LOGGER.debug("Coordinator stored in hass.data.")

    # Forward setup for all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Platforms forwarded.")

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading csnet integration.")

    if DOMAIN in hass.data and entry.entry_id in hass.data[DOMAIN]:
        coordinator = hass.data[DOMAIN][entry.entry_id]
        if coordinator and coordinator.hub:
            _LOGGER.debug("Closing hub session.")
            await coordinator.hub.close()  # Close the session
        hass.data[DOMAIN].pop(entry.entry_id)
        _LOGGER.debug("Coordinator removed from hass.data.")

    # Unload all platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        _LOGGER.debug("All platforms unloaded successfully.")
    else:
        _LOGGER.error("Failed to unload one or more platforms.")

    return unload_ok
