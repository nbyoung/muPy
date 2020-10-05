import struct

from modbus import pdu

class Handler(pdu.Handler):

    def __init__(self, dataModel):
        super().__init__(dataModel)

    async def ReadMultipleHoldingRegisters(self, dataModel, fromRegion):
        return struct.pack(
            '>B%dH' % fromRegion.count,
            fromRegion.count * 2,
            *[dataModel.holdingRead(fromRegion.address + i)
              for i in range(fromRegion.count)]
        )

    async def WriteMultipleHoldingRegisters(
            self, dataModel, toRegion, values
    ):
        for i in range(toRegion.count):
            dataModel.holdingWrite(toRegion.address + i, values[i])
        return struct.pack('>HH', toRegion.address, toRegion.count)
