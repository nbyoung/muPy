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

    regex = r'[_a-zA-Z][_a-zA-Z0-9]*'
    _pattern = re.compile(regex)

    @classmethod
    def _check(cls, string):
        return cls._pattern.fullmatch(string)

class App(_Syntax):

    regex = f'({Identifier.regex})(\^{Identifier.regex})(@{Identifier.regex})?'
    _pattern = re.compile(regex)
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
