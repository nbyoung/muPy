import io

import docker as Docker

from . import version

class App:
    pass

class Target:

    @staticmethod
    def fromConfiguration(configuration, name=None):
        def _configuration():
            try:
                targetName = name or configuration.default.target
                return configuration.targets[targetName]
            except AttributeError:
                return configuration.targets.values()[0]
        targetConfiguration = _configuration()
        return {
            'docker': DockerTarget,
            'cross': CrossTarget,
            }[targetConfiguration.type](
                targetConfiguration.name,
                targetConfiguration.type,
                targetConfiguration.meta,
            )

    def __init__(self, name, type):
        self._name = name
        self._type = type

    @property
    def name(self): return self._name

    @property
    def type(self): return self._type
                 
    def run(self, app):
        raise NotImplementedError

class DockerTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)
        self._dockerfile = meta.dockerfile

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

class CrossTarget(Target):

    def __init__(self, name, type, meta):
        super().__init__(name, type)

    def install(self):
        print(f'{self.name}\n{self.type}')


