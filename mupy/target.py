import getpass
import io
import os
import pathlib
import py_compile
import shutil
import subprocess
import sys

try:
    import docker as Docker
except ImportError:
    pass

from . import tag
from . import version

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
            return self

        def __exit__(self, exc_type, exc_value, exc_traceback):
            self._container.stop(timeout=self._stopTimeout)

        def logs(self, *args, **kwargs):
            try:
                for output in self._container.logs(*args, **kwargs):
                    yield output.decode('utf-8')
            except KeyboardInterrupt:
                pass
            

    @staticmethod
    def removeAllImages(callback=lambda line: None):
        docker = Docker.from_env()
        for image in docker.images.list(
                name=DockerMode.repository
        ):
            docker.images.remove(str(image.id), force=True, noprune=False)
            callback(f'Removed Docker image {image.tags[0]} {image.short_id.split(":")[1]}')

    @classmethod
    def fromMeta(cls, name, meta):
        return cls(name, meta['dockerfile'], meta.get('message'))

    @property
    def tag(self): return DockerMode.getTag(self.name)

    def __init__(self, name, dockerfile, message=None):
        super().__init__(name)
        self._dockerfile = dockerfile
        self._message = message

    def install(self, callback=lambda line: None):
        docker = Docker.from_env()
        if self._message:
            callback(f'Installing Docker image {self.tag}; {self._message}...')
        image, _ = docker.images.build(
            fileobj=io.BytesIO(self._dockerfile.encode('utf-8')),
            tag=f'{self.tag}',
            rm=True,
        )
        callback(f'Installed Docker image {self.tag} {image.short_id.split(":")[1]}')

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
        tagRay = tag.TagRay.fromString(targetC.get('tags', ''))
        name = targetC.get('name', (nullC['name'] if type == None else type) + 'Target')
        meta = targetC.get('meta', {})
        try:
            return {
                None: LocalTarget,
                'local': LocalTarget,
                'docker': DockerTarget,
                'cross': CrossTarget,
            }[mode](name, type, precompile, tagRay, meta)
        except KeyError:
            raise TargetConfigurationError(f"Unknown target type: '{type}'")

    def __init__(self, name, type, precompile, tagRay):
        self._name = name
        self._type = type
        self._precompile = precompile
        self._tagRay = tagRay

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type

    @property
    def precompile(self): return self._precompile

    @property
    def tagRay(self): return self._tagRay

    @property
    def suffix(self): return (
            ('.pyc' if self._type == 'cpython' else '.mpy') if self._precompile
            else '.py'
    )

    def buildContainer(self, buildPath, sourceFromTo):
        raise NotImplementedError()

    def install(self, *args, **kwargs):
        raise NotImplementedError()

    def run(self, *args, **kwargs):
        raise NotImplementedError()


class LocalTarget(Target):

    class Container:

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, exc_traceback):
            pass

        @property
        def output(self):
            self._outputs = []
            return self._outputs

        def logs(self, *args, **kwargs):
            for output in self._outputs:
                yield output

    @property
    def suffix(self): return '.pyc' if self._precompile else '.py'

    def __init__(self, name, type, precompile, tagRay, meta):
        super().__init__(name, type, precompile, tagRay)
        self._container = LocalTarget.Container()

    def buildContainer(self, buildPath, sourceFromTo):
        output = self._container.output
        for sourcePath, fromPath, toPath in sourceFromTo:
            if self._precompile:
                py_compile.compile(buildPath/fromPath, buildPath/toPath)
            else:
                # TODO precompile: false
                shutil.copy2(buildPath/sourcePath, toPath)
            output.append(toPath)
        return self._container

    def install(self, path, isQuiet=False):
        pass

    def run(self, path, isSilent=False):
        try:
            subprocess.run(
                (sys.executable, (path/'main').with_suffix(self.suffix), ),
                cwd=path,
                check=True,
                stdout=subprocess.DEVNULL if isSilent else None,
                stderr=subprocess.STDOUT,
            )
        except KeyboardInterrupt:
            pass
        if not isSilent: print()

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

    def __init__(self, name, type, precompile, tagRay, meta={}):
        super().__init__(name, type, precompile, tagRay)
        self._baud = meta.get('baud', 115200)
        self._port = meta.get('port', '/dev/ttyACM0')

    def buildContainer(self, buildPath, sourceFromTo):
        baseName = os.path.basename(buildPath)
        containerPath = pathlib.Path('/' + baseName)
        script = '.compile.sh'
        with open(buildPath / script, 'w') as scriptFile:
            cP = containerPath
            for sP, fP, tP in sourceFromTo:
                scriptFile.write(
                    f'mpy-cross -s {sP} -o {cP / tP} {cP / fP}\n'
                    if self._precompile
                    else
                    f'cp --preserve=all {cP / fP} {(cP / tP).parent / os.path.basename(tP)}\n'
                )
                scriptFile.write(f'echo {tP}\n')
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

    def install(self, path, isQuiet=False):
        self._rshellCommand(f'rsync {path} /flash', isQuiet=isQuiet)

    def run(self, path, isSilent=False):
        try:
            self._rshellCommand('repl ~ import main ~', isQuiet=isSilent)
        except KeyboardInterrupt:
            pass

class DockerTarget(CrossTarget):

    def __init__(self, name, type, precompile, tagRay, meta):
        super().__init__(name, type, precompile, tagRay)

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
                'python', '-B', '-c',
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

    def install(self, path, isQuiet=False):
        pass

    def run(self, path, isSilent=False):
        containerPath = '/flash'
        args = (
            ['python', '-u', 'main.pyc'] if self._type == 'cpython'
            else ['micropython', '-m', 'main']
        )
        volumes = {
            f'{path}': {'bind': containerPath, 'mode': 'rw'},
        }
        with DockerMode.Container(
                self._type,
                f'{self._type}-run',
                args,
                volumes=volumes,
                working_dir=containerPath,
        ) as container:
            for output in container.logs(stream=True):
                if not isSilent: print(output, end='')
            if not isSilent: print()
            
