import sys

if sys.implementation.name == 'micropython':
    import uasyncio as asyncio
    import ujson as json
else:
    import asyncio
    import json

_DOT = '.'

class StatusNotLoaded(Exception):
    pass

class StatusNotLockedError(Exception):
    pass

class Status:

    @property
    def event(self): return self._event

    def __init__(self):
        self._event = asyncio.Event()
        self._lock = asyncio.Lock()

    def load(self, data):
        self._data = data

    async def get(self, path):
        try: self._data
        except AttributeError:
            raise StatusNotLoadedError
        def get(dictionary, path):
            if -1 < path.find(_DOT):
                head, tail = path.split(_DOT)
                return get(dictionary[head], tail)
            else:
                return dictionary[path]
        await self._lock.acquire()
        value = get(self._data, path)
        self._lock.release()
        return value

    async def __aenter__(self):
        await self._lock.acquire()
        self._event.clear()
        return self

    async def __aexit__(self, *args):
        self._lock.release()
        self._event.set()

    def set(self, path, value):
        try: self._data
        except AttributeError:
            raise StatusNotLoadedError
        def set(dictionary, path, value):
            if -1 < path.find(_DOT):
                head, tail = path.split(_DOT)
                set(dictionary[head], tail, value)
            else:
                dictionary[path] = value
        if self._event.is_set():
            raise StatusNotLockedError
        else:
            set(self._data, path, value)
            pass

class StatusFile(Status):

    def load(self, filename):
        self._filename = filename
        with open(filename) as f:
            super().load(json.load(f))

    async def __aexit__(self, *args):
        with open(self._filename, 'w') as f:
            json.dump(self._data, f)
        await super().__aexit__(*args)
