
from modbus import data

class Model(data.Model):

    def __init__(self):
        super().__init__(holdingCount=1400)
        self._holdingDict = {}

    def holdingRead(self, address):
        return self._holdingDict.get(address, 0)

    def holdingWrite(self, address, value):
        self._holdingDict[address] = value
        return self.holdingRead(address)
    
