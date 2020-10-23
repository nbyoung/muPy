from collections import namedtuple, OrderedDict
import pathlib

import semantic_version
import yaml

from . import version

_DEFAULT = """

default:
  target:       cpython
  app:          demo

directory:
  lib:          "lib"
  app:          "app"
  dev:          "dev"
  build:        "build"
  
libs:

  - name:       logger
    directory:  "logger"

apps:

  - name:       demo
    directory:  "demo"

  - name:       demo_log
    directory:  "demo_log"
    libs:
      - logger
      - bar

targets:

  - name:       cpython
    type:       docker
    meta:
      dockerfile: |
        FROM python:3.7.9-slim-stretch
        ENV PYTHONPATH={pythonpath}
        CMD ["python3"]

  - name:       unix
    type:       docker
    meta:
      dockerfile: |
        FROM debian:stretch-slim
        CMD ["echo", "Hello, Unix!"]

  - name:       stm32
    type:       cross
    meta:

version:
  name:         "{name}"
  version:      "{version}"

""".format(
    name=version.NAME,
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

    def __init__(self, path, yamlContent):
        self._path = path
        self._version = yamlContent.get(
            'version', { 'name': version.NAME, 'version': version.VERSION }
        )
        self._default = yamlContent.get('default', {})
        self._directory = yamlContent.get('directory', {})
        self._libs = yamlContent.get('libs', [])
        self._apps = yamlContent.get('apps', [])
        self._targets = yamlContent.get('targets', [])

    @property
    def path(self): return self._path

    @property
    def version(self): return self._version

    @property
    def default(self): return self._default

    @property
    def directory(self): return self._directory

    @property
    def libs(self): return self._libs

    @property
    def apps(self): return self._apps

    @property
    def targets(self): return self._targets
        
