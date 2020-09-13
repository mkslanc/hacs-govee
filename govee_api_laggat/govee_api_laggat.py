""" client to connect to the govee API """

import sys
import logging
import time
import asyncio
import aiohttp
from dataclasses import dataclass
from typing import List, Tuple
from .__version__ import VERSION

_LOGGER = logging.getLogger(__name__)
_API_URL = "https://developer-api.govee.com"

@dataclass
class GoveeDevices(object):
    device: str
    model: str
    device_name: str
    controllable: bool
    retrievable: bool
    support_turn: bool
    support_brightness: bool
    support_color: bool
    support_color_tem: bool

class Govee(object):
    """ client to connect to the govee API """

    async def __aenter__(self):
        """ async context manager enter """
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *err):
        """ async context manager exit """
        if self._session:
            await self._session.close()
        self._session = None
    
    def __init__(self, api_key: str):
        """ init with an API_KEY """
        self._api_key = api_key
        self._devices = []
        
    @classmethod
    async def create(cls, api_key: str):
        self = Govee(api_key)
        await self.__aenter__()
        return self
    
    async def close(self):
        await self.__aexit__()
    
    def _getAuthHeaders(self):
        return {'Govee-API-Key': self._api_key}

    @property
    def devices(self):
        """ returns the cached devices list """
        return self._devices
    
    async def ping_async(self) -> Tuple[ float, str ]:
        """ Ping the api endpoint. No API_KEY is needed
            Returns: timeout_ms, error
        """
        _LOGGER.debug("ping_async")
        ping_ok_delay = None
        err = None

        url = (_API_URL + "/ping")
        start = time.time()
        async with self._session.get(url=url) as response:
            result = await response.text()
            delay = int((time.time() - start) * 1000)
            if response.status == 200:
                if 'Pong' == result:
                    ping_ok_delay = max(1, delay)
                else:
                    err = f'API-Result wrong: {result}'
            else:
                result = await response.text()
                err = f'API-Error {response.status}: {result}'
        return ping_ok_delay, err
        
            
    async def get_devices(self) -> Tuple[ List[GoveeDevices], str ]:
        """ get and cache devices, returns: list, error """
        _LOGGER.debug("get_devices")
        devices = []
        err = None
        
        url = (
            _API_URL
            + "/v1/devices"
        )
        async with self._session.get(url=url, headers = self._getAuthHeaders()) as response:
            if response.status == 200:
                result = await response.json()
                devices = [
                    GoveeDevices(
                        item["device"],
                        item["model"],
                        item["deviceName"],
                        item["controllable"],
                        item["retrievable"],
                        "turn" in item["supportCmds"],
                        "brightness" in item["supportCmds"],
                        "color" in item["supportCmds"],
                        "colorTem" in item["supportCmds"]
                    ) for item in result["data"]["devices"]
                ]
            else:
                result = await response.text()
                err = f'API-Error {response.status}: {result}'
        # cache last get_devices result
        self._devices = devices
        return devices, err


if __name__ == '__main__':
    """ test connectivity """

    async def main():
        print("Govee API client v" + VERSION)
        print()

        if(len(sys.argv) == 1):
            print("python3 govee_api_laggat.py [command <API_KEY>]")
            print("<command>'s: ping, devices")
            print()

        command = "ping"
        api_key = ""
        if len(sys.argv) > 1:
            command = sys.argv[1]
            if len(sys.argv) > 2:
                api_key = sys.argv[2]
        
        # show usage with content manager
        async with Govee(api_key) as govee:
            if command=="ping":
                ping_ms, err = await govee.ping_async()
                print(f"Ping success? {bool(ping_ms)} after {ping_ms}ms")
            elif command=="devices":
                print("Devices found: " + ", ".join([
                    item.device_name + " (" + item.device + ")"
                    for item
                    in govee.get_devices()
                ]))
        
        # show usage without content manager, but await and close()
        govee = await Govee.create(api_key)
        if command=="ping":
            ping_ms, err = await govee.ping_async()
            print(f"second Ping success? {bool(ping_ms)} after {ping_ms}ms")
        await govee.close()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    