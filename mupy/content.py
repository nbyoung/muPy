import io

import docker as Docker

from . import version

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
        libs = appC.get('libs', ())
        return cls(name, directory, libs)

    def __init__(self, name, directory, libs):
        self._name = name
        self._directory = directory
        self._libs = libs

    @property
    def name(self): return self._name

class Host:

    @classmethod
    def fromConfiguration(cls, configuration):
        parent = configuration.path.parent
        def get(name):
            return parent / getattr(configuration, name, name)
        return cls(
            parent, get('lib'), get('app'), get('dev'), get('build')
        )

    def __init__(self, parent, lib, app, dev, build):
        self._parent = parent

    def install(self, doForce=False):
        pass

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
                 
    def run(self, app):
        raise NotImplementedError

class NullTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def install(self):
        print(f"Installed null-type target, '{self.name}'")

    def run(self, app):
        print(f"Run {app} on null-type target, '{self.name}'")

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
        print(f'Created Docker image {self.tag} {image.short_id.split(":")[1]}')

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
        print(f"Running '{app.name}' on target '{self.name}' in Docker {container.name}")
        try:
            for output in container.logs(stream=True):
                print(output.decode('utf-8'), end='')
        except KeyboardInterrupt:
            print(f' Stopping Docker {container.name}')
            container.stop(timeout=1)

class CrossTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def install(self):
        print(f'{self.name}\n{self.type}')


