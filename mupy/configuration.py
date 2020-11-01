from collections import namedtuple, OrderedDict
import pathlib

import semantic_version
import yaml

from . import mupy
from . import version
from .quiet import qprint

class ConfigurationError(OSError): pass
class ConfigurationInstallError(OSError): pass
class ConfigurationMissingError(ValueError): pass
class ConfigurationOverwriteError(OSError): pass
class ConfigurationSyntaxError(ValueError): pass
    
class Configuration:

    @staticmethod
    def init(path, doForce=False):
        try:
            mode = 'x'
            if path.is_file() and doForce:
                rename = path.with_suffix('.bak')
                path.rename(rename)
                qprint(f"Renamed to '{rename}'")
                mode = 'w'
            with open(path, mode) as file:
                file.write(mupy.YAML)
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
        self._mode = yamlContent.get('mode', {})
        self._libs = yamlContent.get('libs', [])
        self._apps = yamlContent.get('apps', [])
        self._files = yamlContent.get('files', [])
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
    def mode(self): return self._mode

    @property
    def libs(self): return self._libs

    @property
    def apps(self): return self._apps

    @property
    def targets(self): return self._targets

    @property
    def files(self): return self._files
        
