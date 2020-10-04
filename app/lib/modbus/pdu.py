import logging
import struct

from . import codes

class _IllegalDataAddress(Exception): code = codes.Exception.IllegalDataAddress

class Region:

    def __init__(self, address=0, count=0, max=0):
        last = address + count
        if address < 0 or count < 0 or Block.MAX < last:
            raise _IllegalDataAddress(
                'Illegal region address %d+%d=%d' % (
                    address, count, last
                )
            )
        if max < count:
            raise _IllegalDataAddress(
                'Illegal region address %d count exceeds %d max' % (
                    count, max
                )
            )
        self._address = address
        self._count = count

    def __str__(self): return '%s(%d, %d)' % (
            self.__class__.__name__, self._address, self._count
    )

    @property
    def address(self): return self._address

    @property
    def count(self): return self._count

    @property
    def last(self): return self._address + self._count

class Block(Region):

    MAX = 0xFFFF

    def __init__(self, count=0):
        super().__init__(0, count, count)
    
    def valid(self, region):
        if self.last < region.last:
            raise _IllegalDataAddress(
                'Region address (%d+%d=%d) exceeds data block (%d+%d=%d)' % (
                    region.address, region.count, region.last,
                    self.address, self.count, self.last,
                )
            )

class DataModel:

    def __init__(
            self,
            coilCount=0,
            discreteCount=0,
            inputCount=0,
            holdingCount=0,
    ):
        self._coilBlock = Block(count=coilCount)
        self._discreteBlock = Block(count=discreteCount)
        self._inputBlock = Block(count=inputCount)
        self._holdingBlock = Block(count=holdingCount)

    def _valid(
            self,
            coilRegion=Region(),
            discreteRegion=Region(),
            inputRegion=Region(),
            holdingRegion=Region(),
    ):
        self._coilBlock.valid(coilRegion)
        self._discreteBlock.valid(discreteRegion)
        self._inputBlock.valid(inputRegion)
        self._holdingBlock.valid(holdingRegion)

    @property
    def coilBlock(self): return self._coilBlock
    
    @property
    def discreteBlock(self): return self._discreteBlock

    @property
    def inputBlock(self): return self._inputBlock

    @property
    def holdingBlock(self): return self._holdingBlock

    def getBlah(self):
        pass # return blah

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

class _IllegalFunction(Exception): code = codes.Exception.IllegalFunction

class Handler:

    _logger = logging.getLogger("main") # TODO Move to uPy context

    @staticmethod
    def _exceptionPDU(exceptionCode, functionCode):
        return PDU(
            functionCode | codes.Exception.Mask,
            struct.pack('>B', exceptionCode)
        )

    def __init__(self, dataModel=DataModel()):
        self._dataModel = dataModel

    async def handle(self, pdu):
        try:
            if pdu.functionCode == codes.Function.ReadCoils:
                max = 2000
                max = 0
                fromRegion = Region(*struct.unpack('>HH', pdu.bytes), max=max)
                self._dataModel.holdingBlock.valid(fromRegion)
                data = await self.ReadCoils(self._dataModel, fromRegion)
            elif pdu.functionCode == codes.Function.ReadMultipleHoldingRegisters:
                fromRegion = Region(*struct.unpack('>HH', pdu.bytes), max=125)
                self._dataModel.holdingBlock.valid(fromRegion)
                data = await self.ReadMultipleHoldingRegisters(
                    self._dataModel, fromRegion
                )
            else:
                raise _IllegalFunction()
            return PDU(pdu.functionCode, data)
        except _IllegalFunction as exception:
            Handler._logger.info(
                'Function code=%d %s not implemented',
                pdu.functionCode, str(exception)
            )
            return Handler._exceptionPDU(pdu.functionCode, exception.code)
        except _IllegalDataAddress as exception:
            Handler._logger.info(
                'Function code=%d %s', pdu.functionCode, str(exception)
            )
            return Handler._exceptionPDU(pdu.functionCode, exception.code)

    async def ReadCoils(
            self, dataModel, fromRegion
    ):
        raise _IllegalFunction("ReadCoils")

    async def ReadMultipleHoldingRegisters(
            self, dataModel, fromRegion
    ):
        raise _IllegalFunction("ReadMultipleHoldingRegisters")
