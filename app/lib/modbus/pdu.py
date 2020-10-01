import struct

from . import codes

class Handler:

    async def handle(self, pdu):
        raise NotImplemented()

class DoNothingHandler(Handler):

    async def handle(self, pdu):
        return pdu.exception(codes.Exception.IllegalFunction)

class PDU:

    @property
    def function(self): return self._function

    @property
    def data(self): return self._data
    
    def __init__(self, function, data=b''):
        self._function = function
        self._data = data

    def exception(self, code):
        return PDU(
            self._function | codes.Exception.Mask,
            struct.pack('>B', code)
        )
