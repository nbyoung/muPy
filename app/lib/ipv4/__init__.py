
from collections import namedtuple
import sys

IPService = namedtuple('IPService', 'address port')

GoogleDNS = IPService('8.8.8.8', 53)

class _LAN:
    netmask = '255.255.255.0'
    gateway = '192.168.1.1'
    dns = GoogleDNS

class LocalAreaNetworkError(ValueError): pass

if sys.implementation.name == 'micropython' and sys.platform != 'linux':

    from .micropython import LAN
    
else:

    from .cpython import LAN

__all__ = ('LocalAreaNetworkError', 'LAN', )
