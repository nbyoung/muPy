import random
import yaml

class Host:
    pass

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
  version:      "0.0.1"
  unique:       "{unique:02d}"
  directory:    "host"

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
""".format(unique=random.randint(10,100))

class ConfigurationInstallError(OSError): pass
class ConfigurationMissingError(ValueError): pass
class ConfigurationOverwriteError(OSError): pass
    
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
    def fromPath(cls, path):
        try:
            with open(path) as file:
                content = yaml.safe_load(file)
                import pprint
                pprint.pprint(content)
        except IsADirectoryError:
            raise ConfigurationMissingError(
                'Path is a directory {0}'.format(path))
        except FileNotFoundError:
            raise ConfigurationMissingError(
                'Configuration file not found {0}'.format(path))
