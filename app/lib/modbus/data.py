
from . import codes

class IllegalDataAddress(Exception): code = codes.Exception.IllegalDataAddress

class Region:

    def __init__(self, address=0, count=0, max=0):
        last = address + count
        if address < 0 or count < 0 or Block.MAX < last:
            raise IllegalDataAddress(
                'Illegal region address %d+%d=%d' % (
                    address, count, last
                )
            )
        if max < count:
            raise IllegalDataAddress(
                'Illegal region address count of %d exceeds max of %d' % (
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
    
    def validRegion(self, region):
        if self.last < region.last:
            raise IllegalDataAddress(
                'Region address (%d+%d=%d) exceeds data block (%d)' % (
                    region.address, region.count, region.last, self.last,
                )
            )

class Model:

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
