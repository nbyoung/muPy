from collections import UserDict
import os
import pathlib
import shutil

from .quiet import Quiet; qprint = Quiet.qprint
    
class Libs(UserDict):

    @classmethod
    def fromConfiguration(cls, configuration):
        return cls([(d['name'], d.get('directory', d['name']))
                    for d in configuration.libs])

class AppConfigurationError(ValueError): pass

class App:

    @classmethod
    def fromConfiguration(cls, configuration, name=None):
        def _appC():
            appName = configuration.default.get('app') if name==None else name
            try:
                return next(
                    (appC for appC in configuration.apps
                     if appC.get('name') == appName),
                )
            except StopIteration:
                raise AppConfigurationError(
                    f"Missing app configuration '{appName}'"
                )
        appC = _appC()
        name = appC.get('name', 'app')
        directory = appC.get('directory', name)
        libNames = appC.get('libs', ())
        return cls(name, directory, libNames)

    def __init__(self, name, directory, libNames):
        self._name = name
        self._directory = directory
        self._libNames = libNames

    @property
    def name(self): return self._name

    def kit(self, host, libs):
        appPath = host.app / self._directory
        kitPath = host.kitPath(self._name)
        shutil.rmtree(kitPath, onerror=lambda type, value, tb: None )
        qprint(f'Kit: {kitPath}')
        shutil.copytree(
            appPath, kitPath, symlinks=True, copy_function=shutil.copy2
        )
        qprint(f'k: {appPath}->{kitPath}')
        for libName in self._libNames:
            fromPath = host.dev / Host.LIB / libs[libName]
            toPath = kitPath / libName
            if not fromPath.is_dir():
                fromPath = host.lib / libs[libName]
            common = os.path.commonprefix((fromPath, toPath))
            qprint(f'k: {os.path.relpath(fromPath, common)} -> {os.path.relpath(toPath, common)}')
            shutil.copytree(
                fromPath, toPath, symlinks=True, copy_function=shutil.copy2
            )
        return Kit(host, self, kitPath)

class Kit:

    SUFFIX = '.py'

    def __init__(self, host, app, path):
        self._host = host
        self._app = app
        self._path = path

    @property
    def host(self): return self._host

    @property
    def app(self): return self._app

    @property
    def path(self): return self._path

    def build(self, target):
        buildPath = self._host.buildPath
        installPath = self._host.installPath(target.name, self._app.name)
        cachePath = self._host.installPath(target.name, '.' + self._app.name)
        if installPath.is_dir():
            shutil.rmtree(cachePath, onerror=lambda type, value, tb: None )
            installPath.rename(cachePath)
        else:
            shutil.rmtree(installPath, onerror=lambda type, value, tb: None )
        qprint(f'Build: {installPath}')
        sourceFromTo = []
        for directory, dirNames, fileNames in os.walk(self._path):
            directory = pathlib.Path(directory)
            cPath = cachePath / os.path.relpath(directory, self._path)
            iPath = installPath / os.path.relpath(directory, self._path)
            iPath.mkdir(parents=True, exist_ok=True)
            for filePath in [pathlib.Path(fN) for fN in fileNames
                             if pathlib.Path(fN).suffix == Kit.SUFFIX]:
                targetFilePath = filePath.with_suffix(target.suffix)
                if (
                        (cPath / targetFilePath).exists()
                        and
                        os.path.getmtime(cPath / targetFilePath)
                        >= os.path.getmtime(directory / filePath)
                ):
                    shutil.copy2(cPath / targetFilePath, iPath / targetFilePath)
                else:
                    sourceFromTo.append((
                        os.path.relpath(
                            directory / filePath, self._path),
                        os.path.relpath(
                            directory / filePath, buildPath),
                        os.path.relpath(
                            (iPath / targetFilePath), buildPath)
                    ))
        if sourceFromTo:
            with target.buildContainer(buildPath, sourceFromTo) as container:
                for output in container.logs(stream=True):
                    qprint('b: %s' % output.decode('utf-8'), end='')
        return Build(self, installPath, target)

class Build:

    def __init__(self, kit, path, target):
        self._kit = kit
        self._path = path
        self._target = target

    @property
    def kit(self): return self._kit

    @property
    def path(self): return self._path

    @property
    def target(self): return self._target

    def install(self):
        qprint(f'Install: {self._path} to {self._target.name}')
        self._target.install(self)
        return Install(self)

class Install:

    def __init__(self, build):
        self._build = build

    @property
    def build(self): return self._build

    def run(self, isSilent=False):
        self._build.target.run(self, isSilent=isSilent)
        return Runner(self)

class Runner:

    def __init__(self, install):
        self._install = install

    @property
    def install(self): return self._install
