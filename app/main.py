from config import Config
import ipv4
import logging
from modbus import pdu
from modbus.slave.tcp import Server as ModbusTCPServer
from modbus.slave.tcp import Slave as ModbusTCPSlave
from modbus.slave.tcp import Handler as ModbusTCPHandler
import sys

from demo.modbus.slave import pdu, data

LOGGER = "main"

if sys.implementation.name == 'micropython':
    import uasyncio as asyncio
else:
    import asyncio
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    logging.getLogger(LOGGER).addHandler(handler)

async def forever():
    logger = logging.getLogger(LOGGER)
    flag = False
    i = 0
    while True:
        logger.debug("forever %s" % ("tick" if flag else "tock"))
        flag = not flag
        await asyncio.sleep(1)

async def _network(status):
    logger = logging.getLogger(LOGGER)
    while True:
        await status.event.wait()
        status.event.clear()
        lan = ipv4.LAN()
        try:
            if await status.get('dhcp_enable'):
                await lan.dhcp()
                logger.debug('network DHCP')
            else:
                address = await status.get('static.address')
                gateway=await status.get('static.gateway')
                await lan.static(
                    address, gateway,
                    dns=(await status.get('static.dns'), 53)
                )
                logger.debug('network address=%s gateway=%s', address, gateway)
        except ipv4.LocalAreaNetworkError as exception:
            logger.critical(str(exception))

async def _main(configDir='/flash/configuration'):
    config = Config(configDir)
    asyncio.create_task(_network(config.network))
    await config.load()
    modbusTCPServer = ModbusTCPServer()
    modbusTCPSlave = ModbusTCPSlave(pdu.Handler(data.Model()))
    modbusTCPHandler = ModbusTCPHandler(modbusTCPSlave)
    asyncio.create_task(modbusTCPServer.start(modbusTCPHandler))
    await forever()

def main():
    asyncio.run(_main())

def debug():
    logger = logging.getLogger(LOGGER)
    logger.setLevel(logging.DEBUG)
    asyncio.run(_main())

if __name__ == '__main__':
   try:
       main()
   except KeyboardInterrupt:
       pass
   except Exception as exception:
       traceback.print_exc()
   finally:
       sys.exit(0)
