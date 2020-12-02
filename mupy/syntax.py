from collections import namedtuple
import re

class _Syntax(ValueError):

    @classmethod
    def check(cls, string, location=None):
        if not isinstance(string, str) or not cls._check(string):
            message = f"'{string}'"
            if location: message += f" at {location}"
            raise cls(message)
        return string

class Identifier(_Syntax):

    _re = r'[_a-zA-Z][_a-zA-Z0-9]*'
    _pattern = re.compile(_re)

    @classmethod
    def _check(cls, string):
        return cls._pattern.fullmatch(string)

class App(_Syntax):

    _re = f'({Identifier._re})(\+{Identifier._re})(@{Identifier._re})?'
    _pattern = re.compile(_re)
    _namedtuple = namedtuple('App', ('ensemble', 'entry', 'target', ))

    @classmethod
    def _check(cls, string):
        return cls._pattern.fullmatch(string)

    @classmethod
    def parse(cls, string, location=None):
        cls.check(string, location)
        match = cls._pattern.fullmatch(string)
        return cls._namedtuple(
            match.group(1),
            match.group(2) and match.group(2)[1:],
            match.group(3) and match.group(3)[1:],
        )
