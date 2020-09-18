from config import Config
import ipv4
import logging
import sys

LOGGER = "main"

if sys.implementation.name == 'micropython':
    import uasyncio as asyncio
else:
    import asyncio
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
    logging.getLogger(LOGGER).addHandler(handler)

async def forever(networkStore):
    logger = logging.getLogger(LOGGER)
    flag = False
    i = 0
    while True:
        logger.debug("forever %s" % ("tick" if flag else "tock"))
        await asyncio.sleep(1)
        flag = not flag
        i += 1
        if i == 5:
            i = 0
            dhcp_enable = await networkStore.get('dhcp_enable')
            async with networkStore:
               networkStore.set('dhcp_enable', not dhcp_enable)

async def _network(store):
    logger = logging.getLogger(LOGGER)
    while True:
        await store.event.wait()
        store.event.clear()
        lan = ipv4.LAN()
        try:
            if await store.get('dhcp_enable'):
                await lan.dhcp()
                logger.debug('network DHCP')
            else:
                address = await store.get('static.address')
                gateway=await store.get('static.gateway')
                await lan.static(
                    address, gateway,
                    dns=(await store.get('static.dns'), 53)
                )
                logger.debug('network address=%s gateway=%s', address, gateway)
        except ipv4.LocalAreaNetworkError as exception:
            logger.critical(str(exception))

async def _main(configDir='/flash/configuration'):
    config = Config(configDir)
    asyncio.create_task(_network(config.network))
    await config.load()
    await forever(config.network)

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
