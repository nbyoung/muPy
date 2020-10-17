from collections import namedtuple
import pathlib

import semantic_version
import yaml

from . import version

_DEFAULT = """
version:      "{version}"

target:
  default:      upy
  ghost:
    native:
    docker:
      cpython:
        aka:      cpy
        Dockerfile: |
          FROM python:3.7.9-slim-stretch
          ENV PYTHONPATH={pythonpath}
          CMD ["python3"]
      micropython:
        aka:      upy
        # Dockerfile: |
        #  FROM python:3.7.9-slim-stretch
        #  ENV PYTHONPATH={pythonpath}
        #  CMD ["python3"]
  cross:
    directory:  "target"
    micropython:
      stm32f769:
        aka:  stm32
  
lib:
  directory:    "lib"
  python:
    directory:  "python"

app:
  directory:    "app"
  default:      hello
  python:
    hello:      
      directory:        "hello"

dev:
  directory:    "dev"

build:
  directory:    "build"
""".format(
    version=version.VERSION,
    pythonpath='/flash/lib'
)

class ConfigurationError(OSError): pass
class ConfigurationInstallError(OSError): pass
class ConfigurationMissingError(ValueError): pass
class ConfigurationOverwriteError(OSError): pass
class ConfigurationSyntaxError(ValueError): pass
    
class Configuration:

    @staticmethod
    def _content(value, typename='_Content'):
        if isinstance(value, dict):
            cls = namedtuple(typename, tuple(value.keys()))
            return cls(
                *[Configuration._content(v, f'{typename}_{k}') for k, v in value.items()]
            )
        else:
            return value

    @staticmethod
    def install(path, doForce=False):
        try:
            with open(path, 'w' if doForce else 'x') as file:
                file.write(_DEFAULT)
        except:
            raise ConfigurationOverwriteError(
                'Cannot create {0}'.format(path))

    @classmethod
    def fromSearch(cls, directory, filename):
        def searchPath(directory, filename):
            for path in (
                    pathlib.Path(d, filename)
                    for d in [directory] + list(directory.parents)
            ):
                if path.exists() and path.is_file():
                    return path
            raise ConfigurationMissingError(
                '{1} not found in or above {0}'.format(directory, filename))
        path = searchPath(directory, filename)
        try:
            with open(path) as file:
                content = yaml.safe_load(file)
                try:
                    return cls(path, content)
                except KeyError as exception:
                    raise ConfigurationError(
                        "Missing configuration for {0}".format(str(exception)))
        except IsADirectoryError:
            raise ConfigurationMissingError(
                'Path is a directory {0}'.format(path))
        except FileNotFoundError:
            raise ConfigurationMissingError(
                'Configuration file not found {0}'.format(path))
        except (
                yaml.scanner.ScannerError,
                yaml.parser.ParserError,
        ) as exception:
            raise ConfigurationSyntaxError(str(exception))

    def __init__(self, path, content):
        self._path = path
        self._content = Configuration._content(content)

    @property
    def path(self): return self._path

    @property
    def content(self): return self._content

    @property
    def __getitem__(self, key):
        return self._content[key]
