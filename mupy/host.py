import os
import pathlib
import stat

from .quiet import Quiet; qprint = Quiet.qprint
    
class Host:

    STOCK       = 'stock'
    BUILD       = 'build'
    KIT         = 'kit'
    INSTALL     = 'install'

    @classmethod
    def fromConfiguration(cls, configuration):
        parent = configuration.path.parent
        def get(name):
            return parent / getattr(configuration.directory, name, name)
        return cls(
            parent, get(Host.STOCK), get(Host.BUILD)
        )

    def __init__(self, parent, stock, build):
        self._parent = parent
        self._stockPath = stock
        self._buildPath = build

    @property
    def parentPath(self): return self._parent

    @property
    def stockPath(self): return self._stockPath

    @property
    def buildPath(self): return self._buildPath
    
    def kitPath(self, app):
        return pathlib.Path(self._buildPath / Host.KIT / app.entryName)
    
    def installPath(self, targetName, appName):
        return pathlib.Path(self._build / Host.INSTALL / targetName / appName)

    def setup(self, doForce=False):

        def makeWriteable(path):

            def reportError(message, useForce):
                print(f"Error: {message}")
                print(f"Try renaming '{path}'"
                      + (" or use --force" if useForce else "")
                )

            result = False
            if path.exists():
                if path.is_dir():
                    if os.access(path, os.W_OK, effective_ids=True):
                        result = True
                    else:
                        if doForce:
                            os.chmod(path, stat.S_IWUSR | os.stat(path).st_mode)
                            result = True
                        else:
                            reportError(
                                f"'{path}' exists but not writeable",
                                True,
                            )
                else:
                    reportError(
                        f"'{path}' exists as a file",
                        False,
                    )
            else:
                path.mkdir(parents=doForce, exist_ok=True)
                result = True
            return result

        isOkay = True
        for path in (
                self._parent, self._stockPath,
                self._buildPath, self._buildPath / Host.KIT
        ):
            if makeWriteable(path): qprint(path)
            else: isOkay = False
        if not isOkay: raise OSError('Failed creating host directory')
