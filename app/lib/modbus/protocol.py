import struct

class PDU:

    @property
    def function(self): return self._function
    
    def __init__(self, function, data):
        self._function = function
        self._data = data

class SerialADU:
    pass
