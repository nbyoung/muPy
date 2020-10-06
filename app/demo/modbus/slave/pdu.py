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

    async def WriteSingleHoldingRegister(
            self, dataModel, toAddress, value
    ):
        dataModel.holdingWrite(toAddress, value)
        return struct.pack('>HH', toAddress, value)

    async def WriteMultipleHoldingRegisters(
            self, dataModel, toRegion, values
    ):
        for i in range(toRegion.count):
            dataModel.holdingWrite(toRegion.address + i, values[i])
        return struct.pack('>HH', toRegion.address, toRegion.count)

    async def ReadWriteMultipleRegisters(
            self, dataModel, fromRegion, toRegion, values
    ):
        for i in range(toRegion.count):
            dataModel.holdingWrite(toRegion.address + i, values[i])
        return struct.pack(
            '>B%dH' % fromRegion.count,
            fromRegion.count * 2,
            *[dataModel.holdingRead(fromRegion.address + i)
              for i in range(fromRegion.count)]
        )
