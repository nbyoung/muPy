import io
import pathlib

import docker as Docker
import semantic_version
import yaml

from . import version

class Host:

    @classmethod
    def fromConfiguration(cls, dictionary, doInstall=False):
        return cls(
            semantic_version.Version(dictionary['version']),
            dictionary['docker']['cpython'],
            doInstall,
        )

    def __init__(self, version, dockerCPython, doInstall=False):
        self._version = version
        if doInstall:
            docker = Docker.from_env()
            docker.images.build(
                fileobj=io.BytesIO(dockerCPython.encode('utf-8')),
                rm=True,
            )

class Target:
    pass

class MuLib:
    pass

class App:
    pass

class Build:
    pass

_DEFAULT = """
host:
  version:      "{version}"
  docker:
    cpython: |
      FROM python:3.7.9-slim-stretch
      ENV PYTHONPATH={pythonpath}
      CMD ["python3"]

target:
  defaults:     []
  directory:    "target"

mulib:
  directory:    "mulib"
#  pkg:
#    directory:  "dev/mulib/pkg"
#    as:         "alias"

app:
  directory:    "app"
  default:
#  demo:
#    directory:  "dev/app/demo"
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
    def install(path, doForce=False):
        try:
            with open(path, 'w' if doForce else 'x') as file:
                file.write(_DEFAULT)
        except:
            raise ConfigurationOverwriteError(
                'Cannot create {0}'.format(path))

    @classmethod
    def fromSearch(cls, directory, filename, doInstall=False, doForce=False):
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
                return cls.fromConfiguration(path, content, doInstall, doForce)
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

    @classmethod
    def fromConfiguration(
            cls, path, dictionary, doInstall=False, doForce=False
    ):
        try:
            return cls(
                path, host=Host.fromConfiguration(dictionary['host'], doInstall)
            )
        except KeyError as exception:
            raise ConfigurationError(
                "Missing configuration for {0}".format(str(exception)))

    def __init__(self, path, host=None):
        print('Configuration(%s)' % str(path))
        self._path = path
        self._host = host

    @property
    def path(self): return self._path

    @property
    def host(self): return self._host
