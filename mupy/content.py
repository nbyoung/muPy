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

class Mode:

    @classmethod
    def fromConfiguration(cls, configuration, name):
        modeConfiguration = configuration.mode[name]
        return (
            {
            'docker': DockerMode,
            }[modeConfiguration['type']]
        ).fromMeta(name, modeConfiguration['meta'])

    def __init__(self, name):
        self._name = name

    @property
    def name(self): return self._name

    def run(self):
        raise NotImplementedError()

class DockerMode(Mode):

    repository = f'{version.NAME}'

    @staticmethod
    def getTag(name): return f'{DockerMode.repository}:{name}'

    class Container:

        def __init__(self, type, name, args, stopTimeout=1, **kwargs):
            self._stopTimeout = stopTimeout
            docker = Docker.from_env()
            self._container = docker.containers.run(
                DockerMode.getTag(type),
                args,
                detach=True,
                name=name,
                network_mode='host',
                auto_remove=True,
                stderr=True,
                stdout=True,
                **kwargs
            )

        def __enter__(self):
            return self._container

        def __exit__(self, exc_type, exc_value, exc_traceback):
            self._container.stop(timeout=self._stopTimeout)
            

    @staticmethod
    def removeAllImages():
        docker = Docker.from_env()
        for image in docker.images.list(
                name=DockerMode.repository
        ):
            docker.images.remove(str(image.id), force=True, noprune=False)
            qprint(f'Removed Docker image {image.tags[0]} {image.short_id.split(":")[1]}')

    @classmethod
    def fromMeta(cls, name, meta):
        return cls(name, meta['dockerfile'])

    @property
    def tag(self): return DockerMode.getTag(self.name)

    def __init__(self, name, dockerfile):
        super().__init__(name)
        self._dockerfile = dockerfile

    def install(self):
        docker = Docker.from_env()
        image, _ = docker.images.build(
            fileobj=io.BytesIO(self._dockerfile.encode('utf-8')),
            tag=f'{self.tag}',
            rm=True,
        )
        qprint(f'Installed Docker image {self.tag} {image.short_id.split(":")[1]}')

    def run(self, app):
        return
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

class TargetConfigurationError(ValueError): pass

class Target:

    @staticmethod
    def fromConfiguration(configuration, name=None):
        nullC = {'name': 'null', 'mode': None, 'type': None}
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
        mode = targetC.get('mode', 'cross')
        type = targetC.get('type', 'micropython')
        name = targetC.get('name', (nullC['name'] if type == None else type) + 'Target')
        meta = targetC.get('meta')
        try:
            return {
                None: NullTarget,
                'docker': DockerTarget,
                'cross': CrossTarget,
            }[mode](name, type, meta)
        except KeyError:
            raise TargetConfigurationError(f"Unknown target type: '{type}'")

    def __init__(self, name, type):
        self._name = name
        self._type = type

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type
                 
    def run(self, app):
        raise NotImplementedError

class NullTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def run(self, app):
        qprint(f"Run {app} on null-type target, '{self.name}'")

class DockerTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

class CrossTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    
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
        qprint(f'k: {appPath}->{kitPath}')
        for libName in self._libNames:
            fromPath = host.dev / Host.LIB / libs[libName]
            toPath = kitPath / libName
            if not fromPath.is_dir():
                fromPath = host.lib / libs[libName]
            common = os.path.commonprefix((fromPath, toPath))
            qprint(f'  {os.path.relpath(fromPath, common)} -> {os.path.relpath(toPath, common)}')
            shutil.copytree(fromPath, toPath, symlinks=True)
        return Kit(host, self, kitPath)

class Kit:

    SUFFIX_PY   = '.py'
    SUFFIX_PYC  = '.pyc'

    def __init__(self, host, app, path):
        self._host = host
        self._app = app
        self._path = path

    def build(self, target):
        installPath = self._host.installPath(target.name, self._app.name)
        shutil.rmtree(installPath, onerror=lambda type, value, tb: None )
        qprint(f'Build: {installPath}')
        for directory, dirNames, fileNames in os.walk(self._path):
            relative = os.path.relpath(directory, self._path)
            iPath = installPath / relative
            iPath.mkdir(parents=True, exist_ok=True)
            for fileName in [fN for fN in fileNames
                             if pathlib.Path(fN).suffix == Kit.SUFFIX_PY]:
                fromPath = pathlib.Path(directory) / fileName
                toPath = (iPath / fileName).with_suffix(Kit.SUFFIX_PYC)
                common = os.path.commonprefix((fromPath, toPath))
                fromRPath = pathlib.Path(os.path.relpath(fromPath, common))
                toRPath = pathlib.Path(os.path.relpath(toPath, common))
                args = [ # TODO Also for micropython mpy-cross
                    'python', '-c',
                    f'''
from py_compile import compile
compile('/{fromRPath}', '/{toRPath}')
print('b: {fromRPath} -> {toRPath}')
''',
                ]
                volumes={
                    f'{fromPath.parent}': {'bind': f'/{fromRPath.parent}', 'mode': 'ro'},
                    f'{toPath.parent}': {'bind': f'/{toRPath.parent}', 'mode': 'rw'},
                }
                with DockerMode.Container(
                        target.type, f'{target.type}-compile', args, volumes=volumes,
                ) as container:
                    for output in container.logs(stream=True):
                        qprint(output.decode('utf-8'), end='')
        # TODO Move to content.Install.run()
        workingDir = '/flash'
        args = ['python', 'main.pyc']
        volumes = {
            f'{installPath}': {'bind': workingDir, 'mode': 'ro'},
        }
        with DockerMode.Container(
                target.type, f'{target.type}-run', args, volumes=volumes, working_dir=workingDir
        ) as container:
            for output in container.logs(stream=True):
                qprint(output.decode('utf-8'), end='')
        #
        return Build.withDocker(installPath, target)

class Build:

    @classmethod
    def withDocker(cls, path, target):
        pass
        # return cls()

    def __init__(self, path, target):
        self._path = path
        self._target = target

    def install(self):
        raise NotImplementedError()

class Install:

    def __init__(self, build):
        self._build = build

    def run(self):
        raise NotImplementedError()

class Runtime:

    def __init__(self, install):
        self._install = install
