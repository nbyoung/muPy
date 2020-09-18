from store import FileStore
import os
import sys

class Config:

    @property
    def network(self): return self._network

    def __init__(self, directory):
        self._directory = directory
        self._network = FileStore()

    async def load(self):
        if sys.implementation.name == 'micropython':
            self._network.load("/".join((self._directory, 'network.json')))
            async with self._network: # Trigger change event
                pass
        else:
            from argparse import ArgumentParser
            argumentParser = ArgumentParser()
            argumentParser.add_argument(
                '--network-dhcp-enable', action='store_true', default=False
            )
            for option, value in (
                    ('--config-directory',              self._directory),
                    ('--network-static-address',        '192.168.1.11'),
                    ('--network-static-mask',           '255.255.255.0'),
                    ('--network-static-gateway',        '192.168.1.1'),
                    ('--network-static-dns',            '8.8.8.8'),
            ):
                argumentParser.add_argument(option, action='store', default=value)
            args = argumentParser.parse_args()
            self._network.load(args.config_directory + os.sep + 'network.json')
            async with self._network:
                self._network.set('dhcp_enable', args.network_dhcp_enable)
                self._network.set('static.address', args.network_static_address)
                self._network.set('static.mask', args.network_static_mask)
                self._network.set('static.gateway', args.network_static_gateway)
                self._network.set('static.dns', args.network_static_dns)
