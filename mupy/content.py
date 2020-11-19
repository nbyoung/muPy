from collections import UserDict
import io
import os
import pathlib
import py_compile
import shutil
import stat
import subprocess
import sys

import docker as Docker

from .quiet import Quiet; qprint = Quiet.qprint

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

    @property
    def buildPath(self): return self._build
    
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
        return cls(name, meta['dockerfile'], meta.get('message'))

    @property
    def tag(self): return DockerMode.getTag(self.name)

    def __init__(self, name, dockerfile, message=None):
        super().__init__(name)
        self._dockerfile = dockerfile
        self._message = message

    def install(self):
        docker = Docker.from_env()
        if self._message:
            qprint(f'Installing Docker image {self.tag}; {self._message}...')
        image, _ = docker.images.build(
            fileobj=io.BytesIO(self._dockerfile.encode('utf-8')),
            tag=f'{self.tag}',
            rm=True,
        )
        qprint(f'Installed Docker image {self.tag} {image.short_id.split(":")[1]}')

class TargetConfigurationError(ValueError): pass

class Target:

    @staticmethod
    def fromConfiguration(configuration, name=None):
        nullC = {
            'name': '_null_', 'mode': None, 'type': None, 'precompile': False
        }
        def _targetC():
            if name == "": return nullC
            try:
                targetName = (
                    configuration.default.get('target') if name==None else name
                )
                return next(
                    (targetC for targetC in configuration.targets
                     if targetC.get('name') == targetName)
                )
            except IndexError:
                return nullC
            except StopIteration:
                raise TargetConfigurationError(
                    f"Missing configuration for target '{name}'"
                )
        targetC = _targetC()
        mode = targetC.get('mode', 'cross')
        type = targetC.get('type', 'micropython')
        precompile = targetC.get('precompile', True)
        name = targetC.get('name', (nullC['name'] if type == None else type) + 'Target')
        meta = targetC.get('meta', {})
        try:
            return {
                None: NullTarget,
                'docker': DockerTarget,
                'cross': CrossTarget,
            }[mode](name, type, precompile, meta)
        except KeyError:
            raise TargetConfigurationError(f"Unknown target type: '{type}'")

    def __init__(self, name, type, precompile):
        self._name = name
        self._type = type
        self._precompile = precompile

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type

    @property
    def precompile(self): return self._precompile

    @property
    def suffix(self): return (
            ('.pyc' if self._type == 'cpython' else '.mpy') if self._precompile
            else '.py'
    )

    def buildContainer(self, buildPath, sourceFromTo):
        raise NotImplementedError()

    def install(self, build):
        raise NotImplementedError()
        

class NullTarget(Target):

    class PseudoContainer:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, exc_traceback):
            pass

        def logs(self, *args, **kwargs):
            return ()


    @property
    def suffix(self): return ''

    def __init__(self, name, type, precompile, meta):
        super().__init__(name, type, precompile)

    def buildContainer(self, buildPath, sourceFromTo):
        return NullTarget.PseudoContainer()

    def install(self, build):
        pass

    def run(self, install):
        print(
            f"Ran app '{install.build.kit.app.name}' on target '{self.name}'"
        )

class CrossTarget(Target):

    _RSHELL = 'rshell'

    @staticmethod
    def isInstalled(onError):
        try:
            subprocess.run((CrossTarget._RSHELL, '--version'))
        except FileNotFoundError:
            onError(
                '>>> %s <<<' %
                f"Missing {CrossTarget._RSHELL} for Micropython."
                " Please install"
            )

    def __init__(self, name, type, precompile, meta={}):
        super().__init__(name, type, precompile)
        self._baud = meta.get('baud', 115200)
        self._port = meta.get('port', '/dev/ttyACM0')

    def buildContainer(self, buildPath, sourceFromTo):
        baseName = os.path.basename(buildPath)
        containerPath = pathlib.Path('/' + baseName)
        script = 'compile'
        with open(buildPath / script, 'w') as scriptFile:
            cP = containerPath
            for sP, fP, tP in sourceFromTo:
                scriptFile.write(
                    f'mpy-cross -s {sP} -o {cP / tP} {cP / fP}\n'
                    if self._precompile
                    else
                    f'cp --preserve=all {cP / fP} {(cP / tP).parent}\n'
                )
                scriptFile.write(f'echo {fP} {tP}\n')
        args = ('cat', script)
        args = ('bash', script)
        kwargs = {
            'volumes': {
                f'{buildPath}': {'bind': str(containerPath), 'mode': 'rw'},
            },
            'working_dir': str(containerPath),
        }
        return DockerMode.Container(
            self.type, f'{self.type}-build', args, **kwargs,
        )

    def _rshellCommand(self, command, isQuiet=False):
        subprocess.run(
            (
                CrossTarget._RSHELL,
                '--baud', str(self._baud), '--port', self._port,
                command,
            ),
            check=True,
            stdout=subprocess.DEVNULL if isQuiet else None,
            stderr=subprocess.STDOUT,
        )

    def install(self, build):
        self._rshellCommand(f'rsync {build.path} /flash', isQuiet=Quiet.get())

    def run(self, install):
        qprint(
            f"Run app '{install.build.kit.app.name}' on target '{self.name}'"
        )
        self._rshellCommand('repl ~ import main ~', isQuiet=Quiet.get())

class DockerTarget(CrossTarget):

    def __init__(self, name, type, precompile, meta):
        super().__init__(name, type, precompile)

    def buildContainer(self, buildPath, sourceFromTo):
        if self.type == 'cpython':
            moduleName = os.path.basename(buildPath)
            with open(buildPath / '__init__.py', 'w') as moduleFile:
                moduleFile.write(f'sourceFromTo = {sourceFromTo}')
            operation = (
                'from py_compile import compile' if self._precompile
                else 'from shutil import copy'
            )
            args = [
                'python', '-c',
                f'''
import pathlib
{operation} as operation
from {moduleName} import sourceFromTo
path = pathlib.Path('{moduleName}')
for _, fromPath, toPath in sourceFromTo:
    operation(path / fromPath, path / toPath)
    print('%s -> %s' % (fromPath, toPath))
''',
            ]
            kwargs = {
                'volumes': {
                    f'{buildPath}': {'bind': '/' + moduleName, 'mode': 'rw'},
                },
            }
            return DockerMode.Container(
                self.type, f'{self.type}-build', args, **kwargs,
            ) 
        else:
            return super().buildContainer(buildPath, sourceFromTo)

    def install(self, build):
        pass

    def run(self, install):
        qprint(
            f"Run app '{install.build.kit.app.name}' on target '{self.name}'"
        )
        containerPath = '/flash'
        args = (
            ['python', 'main.pyc'] if self._type == 'cpython'
            else ['micropython', '-m', 'main']
        )
        volumes = {
            f'{install.build.path}': {'bind': containerPath, 'mode': 'rw'},
        }
        with DockerMode.Container(
                self._type,
                f'{self._type}-run',
                args,
                volumes=volumes,
                working_dir=containerPath,
        ) as container:
            for output in container.logs(stream=True):
                print(output.decode('utf-8'), end='')

    
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

    def run(self):
        self._build.target.run(self)
        return Runtime(self)

class Runtime:

    def __init__(self, install):
        self._install = install

    @property
    def install(self): return self._install
