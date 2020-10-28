from collections import UserDict
import io
import os
import pathlib
import py_compile
import shutil
import stat

import docker as Docker

from .quiet import qprint
from . import version
    
class Host:

    LIB         = 'lib'
    APP         = 'app'
    DEV         = 'dev'
    BUILD       = 'build'
    KIT         = 'kit'
    INSTALL     = 'install'

    @classmethod
    def fromConfiguration(cls, configuration):
        parent = configuration.path.parent
        def get(name):
            return parent / getattr(configuration.directory, name, name)
        return cls(
            parent, get(Host.LIB), get(Host.APP), get(Host.DEV), get(Host.BUILD)
        )

    def __init__(self, parent, lib, app, dev, build):
        self._parent = parent
        self._lib = lib
        self._app = app
        self._dev = dev
        self._build = build

    @property
    def lib(self): return self._lib

    @property
    def app(self): return self._app

    @property
    def dev(self): return self._dev
    
    def kitPath(self, appName):
        return pathlib.Path(self._build / Host.KIT / appName)
    
    def installPath(self, targetName, appName):
        return pathlib.Path(self._build / Host.INSTALL / targetName / appName)
    
    def install(self, doForce=False):

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
                self._parent, self._lib, self._app, self._dev,
                self._build, self._build / Host.KIT
        ):
            if makeWriteable(path): qprint(path)
            else: isOkay = False
        if not isOkay: raise OSError('Failed creating host directory')

class TargetConfigurationError(ValueError): pass

class Target:

    @staticmethod
    def fromConfiguration(configuration, name=None):
        nullC = {'name': 'null', 'type': None}
        def _targetC():
            try:
                targetName = name or configuration.default.get('target')
                return next(
                    (targetC for targetC in configuration.targets
                     if targetC.get('name') == targetName),
                    nullC if targetName == 'null' else configuration.targets[0]
                )
            except IndexError:
                return nullC
        targetC = _targetC()
        type = targetC.get('type')
        name = targetC.get('name', (nullC['name'] if type == None else type) + 'Target')
        meta = targetC.get('meta')
        try:
            return {
                None: NullTarget,
                'docker': DockerTarget,
                'cross': CrossTarget,
            }[type](name, type, meta)
        except KeyError:
            raise TargetConfigurationError(f"Unknown target type: '{type}'")

    def __init__(self, name, type):
        self._name = name
        self._type = type

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type
                 
    def install(self):
        raise NotImplementedError
                 
    def run(self, app):
        raise NotImplementedError

class NullTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def install(self):
        qprint(f"Installed null-type target, '{self.name}'")

    def run(self, app):
        qprint(f"Run {app} on null-type target, '{self.name}'")

class DockerTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)
        self._dockerfile = meta['dockerfile']

    @property
    def dockerfile(self): return self._dockerfile
    
    @property
    def repository(self): return f'{version.NAME}'

    @property
    def tag(self): return f'{self.repository}:{self.name}'

    def install(self):
        docker = Docker.from_env()
        image, _ = docker.images.build(
            fileobj=io.BytesIO(self._dockerfile.encode('utf-8')),
            tag=f'{self.tag}',
            rm=True,
        )
        qprint(f'Installed Docker image {self.tag} {image.short_id.split(":")[1]}')

    def run(self, app):
        docker = Docker.from_env()
        container = docker.containers.run(
            self.tag,
            ['bash', '-c', f'while true; do sleep 1; echo {app.name}; done'],
            detach=True,
            name=f'{self.name}-{app.name}',
            network_mode='host',
            auto_remove=True,
            stderr=True,
            stdout=True,
        )
        qprint(f"Running '{app.name}' on target '{self.name}' in Docker {container.name}")
        try:
            for output in container.logs(stream=True):
                qprint(output.decode('utf-8'), end='')
        except KeyboardInterrupt:
            qprint(f' Stopping Docker {container.name}')
            container.stop(timeout=1)

class CrossTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def install(self):
        qprint(f'{self.name}\n{self.type}')

    
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
            appName = name or configuration.default.get('app')
            try:
                return next(
                    (appC for appC in configuration.apps if appC.get('name') == appName),
                    configuration.apps[0]
                )
            except IndexError:
                raise AppConfigurationError('Missing app configuration')
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
        shutil.copytree(appPath, kitPath, symlinks=True)
        qprint(f'  {appPath}->{kitPath}')
        for libName in self._libNames:
            fromPath = host.dev / Host.LIB / libs[libName]
            toPath = kitPath / libName
            if not fromPath.is_dir():
                fromPath = host.lib / libs[libName]
            common = os.path.commonprefix((fromPath, toPath))
            qprint(f'  {os.path.relpath(fromPath, common)} -> {os.path.relpath(toPath, common)}')
            shutil.copytree(fromPath, toPath, symlinks=True)
        return Kit(self._name, kitPath)

class Kit:

    SUFFIX_PY   = '.py'
    SUFFIX_PYC  = '.pyc'

    def __init__(self, appName, path):
        self._appName = appName
        self._path = path

    def compile(self, host, target):
        installPath = host.installPath(target.name, self._appName)
        shutil.rmtree(installPath, onerror=lambda type, value, tb: None )
        qprint(f'Compile: {installPath}')
        for directory, dirNames, fileNames in os.walk(self._path):
            relative = os.path.relpath(directory, self._path)
            iPath = installPath / relative
            iPath.mkdir(parents=True, exist_ok=True)
            for fileName in [fN for fN in fileNames
                             if pathlib.Path(fN).suffix == Kit.SUFFIX_PY]:
                fromPath = pathlib.Path(directory) / fileName
                toPath = (iPath / fileName).with_suffix(Kit.SUFFIX_PYC)
                common = os.path.commonprefix((fromPath, toPath))
                qprint(f'  {os.path.relpath(fromPath, common)} -> {os.path.relpath(toPath, common)}')
                py_compile.compile(fromPath, toPath)
        
        
