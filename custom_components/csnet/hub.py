import json
import logging
import time

import requests
import aiohttp

_LOGGER = logging.getLogger(__name__)


class CSnetHub:
    def __init__(self, username, password) -> None:
        self.xsrf = ""
        self.session = ""
        self.username = username
        self.password = password

    async def auth(self):
        url = "https://www.csnetmanager.com"
        # A GET request to the API
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            response = await session.get(url + "/login")

        _LOGGER.info("Initial CSRF")
        self.xsrf = session.cookie_jar.filter_cookies(url)["XSRF-TOKEN"].value
        AWSALBTG = session.cookie_jar.filter_cookies(url)["AWSALBTG"].value
        AWSALBTGCORS = session.cookie_jar.filter_cookies(url)["AWSALBTGCORS"].value
        _LOGGER.info(self.xsrf)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            response = await session.post(
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
        self.session = session.cookie_jar.filter_cookies(url)["SESSION"].value
        _LOGGER.info(response.status)
        _LOGGER.info(self.session)
        _LOGGER.info(await response.text())

    async def update(self):
        await self.auth()
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            response = await session.get(
                "https://www.csnetmanager.com/data/elements",
                cookies={"SESSION": self.session, "XSRF-TOKEN": self.xsrf},
                timeout=5,
            )
            data = await response.text()
            _LOGGER.info(data)
            data = json.loads(data)

        _LOGGER.info("Updating hitachi heatpump")
        _LOGGER.info(data)
        return data["data"]["elements"]

    async def toggle(self, parentId, room, on, temp) -> None:
        await self.auth()
        ts = round(time.time() * 1000)
        async with aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar()) as session:
            response = await session.post(
                "https://www.csnetmanager.com/data/indoor/heat_setting",
                cookies={"SESSION": self.session, "XSRF-TOKEN": self.xsrf},
                data={
                    "id": 29249,
                    "updatedOn": ts,
                    "orderStatus": "APPLYING",
                    "runStopC" + str(room) + "Air": on,
                    "settingTempRoomZ" + str(room): round(temp * 10),
                    "indoorId": parentId,
                    "_csrf": self.xsrf,
                },
                timeout=5,
            )
        _LOGGER.info(response.status)
        _LOGGER.info(response.content)
