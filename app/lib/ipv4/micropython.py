
from . import _LAN, LocalAreaNetworkError
import uasyncio as asyncio
import network
import time

class LAN(_LAN):

    async def _connect(self, lan, timeout_seconds=5):
        interval = 1
        lan.active(True)
        while True:
            if lan.isconnected():
                break
            if timeout_seconds <= 0:
                raise LocalAreaNetworkError(
                    'Timeout connecting network %s' % str(lan)
                )
            await asyncio.sleep(interval)
            timeout_seconds -= interval

    async def dhcp(self, timeout_seconds=5):
        await self._connect(network.LAN(), timeout_seconds=5)

    async def static(
            self,
            address, netmask=_LAN.netmask, gateway=_LAN.gateway, dns=_LAN.dns,
            timeout_seconds=5
    ):
        lan = network.LAN()
        lan.ifconfig((address, netmask, gateway, dns[0]))
        await self._connect(lan, timeout_seconds=5)
