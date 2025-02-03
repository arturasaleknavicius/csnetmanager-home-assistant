# hub.py
import json
import logging
import time

import requests
import aiohttp

_LOGGER = logging.getLogger(__name__)

class CSnetHub:
    """Handles communication with the CSNet API."""

    def __init__(self, username, password) -> None:
        """Initialize the CSnetHub."""
        self.xsrf = ""
        self.session = None  # Initialize session to None
        self.username = username
        self.password = password

    async def auth(self):
        """Authenticate and establish a session with CSNet."""
        url = "https://www.csnetmanager.com"

        if self.session is None:
            # Create a session here (only once)
            self.session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar())
            _LOGGER.debug("Session created.")
        try:
            # Perform the GET request to retrieve the XSRF token
            response = await self.session.get(url + "/login")
            _LOGGER.info("Initial CSRF Token retrieved.")

            # Extract cookies for the session
            cookies = self.session.cookie_jar.filter_cookies(url)
            if "XSRF-TOKEN" in cookies:
                self.xsrf = cookies["XSRF-TOKEN"].value
            else:
                # If XSRF-TOKEN is not in cookies, check the response body
                response_text = await response.text()
                if "XSRF-TOKEN" in response_text:
                    self.xsrf = response_text.split("XSRF-TOKEN=")[1].split(";")[0]
                else:
                    _LOGGER.error("XSRF-TOKEN not found in cookies or response body.")
                    return

            AWSALBTG = cookies["AWSALBTG"].value if "AWSALBTG" in cookies else ""
            AWSALBTGCORS = cookies["AWSALBTGCORS"].value if "AWSALBTGCORS" in cookies else ""
            _LOGGER.info("XSRF Token: %s", self.xsrf)
            _LOGGER.info("AWSALBTG: %s", AWSALBTG)
            _LOGGER.info("AWSALBTGCORS: %s", AWSALBTGCORS)

            # Perform the POST request to log in
            response = await self.session.post(
                url + "/login",
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                cookies={
                    "AWSALBTG": AWSALBTG,
                    "AWSALBTGCORS": AWSALBTGCORS,
                    "XSRF-TOKEN": self.xsrf,
                },
                data={
                    "username": self.username,
                    "password": self.password,
                    "token": "",
                    "password_unsanitized": self.password,
                    "_csrf": self.xsrf,
                },
                timeout=5,
                allow_redirects=False,
            )
            _LOGGER.info("Authentication response status: %s", response.status)
            _LOGGER.info("Session ID: %s", self.session.cookie_jar.filter_cookies(url)["SESSION"].value)
            _LOGGER.info("Login successful.")

        except Exception as e:
            _LOGGER.error("Error during authentication: %s", e)
            if self.session:
                await self.session.close()
            self.session = None

    async def update(self):
        """Fetch updated data from the API."""
        await self.auth()  # Ensure authentication is done first

        if not self.session:
            _LOGGER.error("Session is not initialized. Cannot fetch data.")
            return {}

        url = "https://www.csnetmanager.com/data/elements"

        try:
            # Fetch elements data
            response = await self.session.get(
                url, cookies={"SESSION": self.session.cookie_jar.filter_cookies(url)["SESSION"].value, "XSRF-TOKEN": self.xsrf}, timeout=5
            )
            # Log the response status and text
            _LOGGER.info("Fetching elements data. Response status: %s", response.status)
            text = await response.text()
            _LOGGER.info("Response text: %s", text)

            if response.status != 200:
                _LOGGER.error("Failed to fetch data. Status code: %d", response.status)
                return {}

            # Try to parse the JSON data
            try:
                data = json.loads(text)
                _LOGGER.debug(f"Parsed data: {data}")

                # Add mode_icon, class_name, and zone_name to each element
                for element in data["data"]["elements"]:
                    element["mode_icon"] = self._get_mode_icon(element["elementType"])
                    element["class_name"] = self._get_class_name(element["elementType"])
                    element["zone_name"] = self._get_zone_name(element["elementType"])

                return data["data"]["elements"]
            except json.JSONDecodeError as e:
                _LOGGER.error("Failed to parse JSON: %s", e)
                return {}

        except Exception as e:
            _LOGGER.error("Error fetching data from CSNet: %s", e)
            return {}

#aded might be not required
    async def _get_element_data(self, room):
        """Fetch element data for a specific room."""
        try:
            # Fetch the latest data from the API
            data = await self.update()
        
            # Iterate through the list of elements to find the one matching the room
            for element in data:
                if element.get("elementType") == room:
                    return element
        
            # If no matching element is found, return an empty dictionary
            __init__LOGGER.warning(f"No element found for room {room}.")
            return {}
        except Exception as e:
            _LOGGER.error(f"Error fetching element data for room {room}: {e}")
            return {}

    async def toggle(self, parentId, room, on, temp) -> None:
        """Send a toggle command to the device."""
        await self.auth()  # Ensure authentication is done first

        if not self.session:
            _LOGGER.error("Session is not initialized. Cannot send toggle command.")
            return

        ts = round(time.time() * 1000)
        try:
            # Determine if this is a water heater or air heater command
            is_water_heater = await self._is_water_heater(room)
            # Prepare the base payload
            data = {
                "id": 29249,  # Example ID, adjust as needed
                "updatedOn": ts,
                "orderStatus": "PENDING",
                "indoorId": parentId,
                "_csrf": self.xsrf,
            }

            if is_water_heater:
                # Water heater control
                if on is not None:
                    data["runStopDHW"] = on  # 1 for on, 0 for off
                if temp is not None:
#                    data["settingTempDHW"] = temp  # Always send the target temperature
                    await self.set_water_heater_temperature(parentId, temp)  # Set water heater temperature
                _LOGGER.debug(f"Sending toggle command with data: {data}")
            else:
                # Air heater control
                data[f"runStopC{room}Air"] = on  # For climate (heating)
                data[f"runStopC{room}Water"] = on  # For water heater
                if temp is not None:
                    data[f"settingTempRoomZ{room}"] = round(temp * 10)  # Temperature in tenths of a degree

            _LOGGER.debug(f"Sending toggle command with data: {data}")  # Properly indented

            # Send the request
            response = await self.session.post(
                "https://www.csnetmanager.com/data/indoor/heat_setting",
                cookies={
                    "SESSION": self.session.cookie_jar.filter_cookies("https://www.csnetmanager.com")["SESSION"].value,
                    "XSRF-TOKEN": self.xsrf,
                },
                data=data,
                timeout=5,
            )

            _LOGGER.info(f"Toggle response status: {response.status}")
            _LOGGER.info(f"Toggle response text: {await response.text()}")
        except Exception as e:
            _LOGGER.error(f"Error sending toggle command: {e}")

    async def set_water_heater_state(self, parentId, on) -> None:
        """Set the on/off state of the water heater."""
        await self.auth()  # Ensure authentication is done first

        if not self.session:
            _LOGGER.error("Session is not initialized. Cannot send on/off command.")
            return

        ts = round(time.time() * 1000)
        try:
            # Prepare the base payload
            data = {
                "id": 29249,  # Example ID, adjust as needed
                "updatedOn": ts,
                "orderStatus": "PENDING",
                "indoorId": parentId,
                "_csrf": self.xsrf,
                "runStopDHW": on,  # 1 for on, 0 for off
            }

            _LOGGER.debug(f"Sending water heater on/off command with data: {data}")

            # Send the request
            response = await self.session.post(
                "https://www.csnetmanager.com/data/indoor/heat_setting",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                cookies={
                    "SESSION": self.session.cookie_jar.filter_cookies("https://www.csnetmanager.com")["SESSION"].value,
                    "XSRF-TOKEN": self.xsrf,
                },
                data=data,
                timeout=5,
            )

            _LOGGER.info(f"Water heater on/off response status: {response.status}")
            _LOGGER.info(f"Water heater on/off response text: {await response.text()}")
        except Exception as e:
            _LOGGER.error(f"Error sending water heater on/off command: {e}")

    async def set_water_heater_temperature(self, parentId, temp) -> None:
        """Set the target temperature of the water heater."""
        await self.auth()  # Ensure authentication is done first

        if not self.session:
            _LOGGER.error("Session is not initialized. Cannot send temperature command.")
            return

        ts = round(time.time() * 1000)
        try:
            # Prepare the base payload
            data = {
                "id": 29249,  # Example ID, adjust as needed
                "updatedOn": ts,
                "orderStatus": "PENDING",
                "indoorId": parentId,
                "_csrf": self.xsrf,
                "settingTempDHW": temp,  # Target temperature
            }

            _LOGGER.debug(f"Sending water heater temperature command with data: {data}")

            # Send the request
            response = await self.session.post(
                "https://www.csnetmanager.com/data/indoor/heat_setting",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                },
                cookies={
                    "SESSION": self.session.cookie_jar.filter_cookies("https://www.csnetmanager.com")["SESSION"].value,
                    "XSRF-TOKEN": self.xsrf,
                },
                data=data,
                timeout=5,
            )

            _LOGGER.info(f"Water heater temperature response status: {response.status}")
            _LOGGER.info(f"Water heater temperature response text: {await response.text()}")
        except Exception as e:
            _LOGGER.error(f"Error sending water heater temperature command: {e}")

    def _get_mode_icon(self, element_type):
        """Get the mode icon based on the element type."""
        if element_type == "air_heater" or element_type == 1:  # Handle both string and numeric values
            return "ic_heat.svg"
        elif element_type == "water_heater" or element_type == 3:  # Handle both string and numeric values
            return "ic_dhw.svg"
        else:
            _LOGGER.warning(f"Unknown element type: {element_type}")
            return "unknown.svg"

    def _get_class_name(self, element_type):
        """Get the class name based on the element type."""
        if element_type == "air_heater" or element_type == 1:  # Handle both string and numeric values
            return "unitCardHeat"
        elif element_type == "water_heater" or element_type == 3:  # Handle both string and numeric values
            return "unitCard"
        else:
            _LOGGER.warning(f"Unknown element type: {element_type}")
            return "unknown"

    async def _is_water_heater(self, room):
        """Determine if the given room is a water heater."""
        element = await self._get_element_data(room)
        if not element:
            return False  # If no element data is found, assume it's not a water heater

        # Check if the zone_name contains "Hot Water"
        return "Hot Water" in element.get("zone_name", "")
#        return (
#            element.get("mode_icon") == "ic_dhw.svg"
#            or "unitCard" in element.get("class_name", "")
#            or "Hot Water" in element.get("zone_name", "")
#        )
        _LOGGER.debug(f"Checking if room {room} is a water heater: {element}")

    def _get_zone_name(self, element_type):
        """Get the zone name based on the element type."""
        if element_type == "air_heater" or element_type == 1:  # Handle both string and numeric values
            return "Room"
        elif element_type == "water_heater" or element_type == 3:  # Handle both string and numeric values
            return "Hot Water Tank"
        else:
            _LOGGER.warning(f"Unknown element type: {element_type}")
            return "Unknown"

    async def close(self):
        """Close the session."""
        if self.session:
            _LOGGER.debug("Closing session.")
            await self.session.close()
            self.session = None
            _LOGGER.debug("Session closed.")
        else:
            _LOGGER.debug("No active session to close.")
