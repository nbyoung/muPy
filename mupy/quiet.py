##############################################################################
##############################################################################
##############################################################################
##############################################################################
####
#### name:      mupy/quiet.py
####
#### synopsis:  Provide quietable replacement for built-in print()
####
#### copyright: (c) 2020 nbyoung@nbyoung.com
####
#### license:   MIT License
####            https://mit-license.org/
####

class Quiet:

    _isQuiet = False

    @classmethod
    def set(cls, isQuiet=True):
        cls._isQuiet = bool(isQuiet)
        return cls.get()

    @classmethod
    def get(cls):
        return cls._isQuiet

    @classmethod
    def qprint(cls, *args, **kwargs):
        if not cls._isQuiet: print(*args, **kwargs)
