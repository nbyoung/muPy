from array import array
import logging
import struct

from . import codes
from . import data

class PDU:

    @property
    def functionCode(self): return self._functionCode

    @property
    def bytes(self): return self._bytes
    
    def __init__(self, functionCode, bytes=b''):
        self._functionCode = functionCode
        self._bytes = bytes

    def exception(self, code): # Move to Transcoder
        return 

class IllegalFunction(Exception): code = codes.Exception.IllegalFunction

class Handler:

    _logger = logging.getLogger("main") # TODO Move to uPy context

    @staticmethod
    def _exceptionPDU(exceptionCode, functionCode):
        return PDU(
            functionCode | codes.Exception.Mask,
            struct.pack('>B', exceptionCode)
        )

    def __init__(self, dataModel=data.Model()):
        self._dataModel = dataModel

    async def handle(self, pdu):
        try:
            code = pdu.functionCode
            if code == codes.Function.ReadMultipleHoldingRegisters:
                fromRegion = data.Region(
                    *struct.unpack('>HH', pdu.bytes), max=125
                )
                self._dataModel.holdingBlock.valid(fromRegion)
                bytes = await self.ReadMultipleHoldingRegisters(
                    self._dataModel, fromRegion
                )
            elif code == codes.Function.WriteMultipleHoldingRegisters:
                format = '>HHB'
                toAddress, toCount, byteCount = struct.unpack(
                    format, pdu.bytes[:struct.calcsize(format)]
                )
                max = 0x7B
                toRegion = data.Region(toAddress, toCount, max)
                self._dataModel.holdingBlock.valid(toRegion)
                values = tuple(struct.unpack(
                    '>%dH' % toCount, pdu.bytes[struct.calcsize(format):]
                ))
                bytes = await self.WriteMultipleHoldingRegisters(
                    self._dataModel, toRegion, values
                )
            else:
                raise IllegalFunction()
            return PDU(code, bytes)
        except IllegalFunction as exception:
            Handler._logger.info(
                'Function code=%d %s not implemented',
                pdu.functionCode, str(exception)
            )
            return Handler._exceptionPDU(pdu.functionCode, exception.code)
        except data.IllegalDataAddress as exception:
            Handler._logger.info(
                'Function code=%d %s', pdu.functionCode, str(exception)
            )
            return Handler._exceptionPDU(pdu.functionCode, exception.code)

    async def ReadMultipleHoldingRegisters(self, dataModel, fromRegion):
        raise IllegalFunction("ReadMultipleHoldingRegisters")

    async def WriteMultipleHoldingRegisters(self, dataModel, fromRegion):
        raise IllegalFunction("WriteMultipleHoldingRegisters")
