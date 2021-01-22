import os
import pathlib

class ShellError(ValueError): pass

class Shell:

    @classmethod
    def fromDictionary(cls, dictionary, directory):
        bin = dictionary.get('bin', os.environ.get('SHELL'))
        if bin is not None:
           if not os.path.isfile(bin): raise ShellError(f"Not a file: '{bin}'")
           if not os.access(bin, os.X_OK): raise ShellError(f"Not executable: '{bin}'")
        path = pathlib.Path(directory)
        if not path.exists():
            raise ShellError(f"Working directory does not exist: '{path}'")
        env = {**os.environ, **dictionary.get('env', {})}
        return cls(bin, path, env)

    def __init__(self, bin, cwd, env):
        self._bin = bin
        self._cwd = cwd
        self._env = env

    @property
    def bin(self): return self._bin

    @property
    def cwd(self): return self._cwd

    @property
    def env(self): return self._env
