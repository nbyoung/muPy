##############################################################################
##############################################################################
##############################################################################
##############################################################################
####
#### name:      mupy/__init__.py
####
#### usage:     mupy-host | mupy-target | mupy [options] subcommand ...
####
#### synopsis:  Invoke the muPy framework commands.
####
#### description:
####
####    Develop unified MicroPython applications across multiple targets.
####
#### copyright: (c) 2020 nbyoung@nbyoung.com
####
#### license:   MIT License
####            https://mit-license.org/
####

import os
import pathlib
import sys

from .configuration import (
    Configuration,
    ConfigurationError,
    ConfigurationMissingError, ConfigurationOverwriteError,
    ConfigurationSyntaxError,
    )
from . import content
from .quiet import isQuiet, qprint
from . import version

_MUPY = version.NAME
_MUPY_HOST = f'{_MUPY}-host'
_MUPY_TARGET = f'{_MUPY}-target'
_MUPY_YAML = 'mupy.yml'

def command(name, help='Command help', subcommands={}):
    def _command(cls):
        class _Command(cls):
            COMMAND = name
            HELP = help
            SUBCOMMANDS = subcommands
        return _Command
    return _command

class Command:

    VERSION = version.VERSION
    EPILOG = f'''
Enviroment: MUPY_QUIET, MUPY_DIRECTORY, MUPY_CONFIGURATION
Commands: {_MUPY_HOST}, {_MUPY_TARGET}, {_MUPY}
'''

    def __init__(self, configuration, args):
        self._configuration = configuration
        self._args = args

    def _do(self, subcommand):
        return getattr(self, subcommand)()

@command(
    _MUPY_HOST,
    help='Modify the host setup',
    subcommands = {
        'init': ({'help': f"1. Create the host configuration file, '{_MUPY_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing file', 'action': 'store_true' },
        }),
        'install': ({'help': f"2. Install the files specified in '{_MUPY_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing files', 'action': 'store_true' },
        }),
        'remove': ({'help': f"3. Remove the Docker images"}, {
        }),
        'show': ({'help': f'4. Display the host setup details'}, {
        }),
        'remove': ({'help': f'5. Remove the host setup'}, {
            '--force': { 'action': 'store_true' },
        }),
    },
)
class Host(Command):

    def install(self):
        content.CrossTarget.isInstalled(lambda m: print(m, file=sys.stderr))
        qprint(f"Installing from '{self._configuration.path}'")
        host = content.Host.fromConfiguration(self._configuration)
        host.install(self._args.force)
        for name in ('cpython', 'micropython'):
            try:
                content.Mode.fromConfiguration(self._configuration, name).install()
            except KeyError:
                raise ConfigurationMissingError(
                    f"Missing mode configuration for '{name}'"
                )
        for fileC in self._configuration.files:
            path = pathlib.Path(fileC['path'])
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w') as file:
                file.write(fileC['content'])
            qprint(f"Wrote file '{path}'")

    def remove(self):
        content.DockerMode.removeAllImages()

@command(
    _MUPY_TARGET,
    help='Modify the target runtimes',
    subcommands = {
        'list': ({}, {}),
    },
)
class Target(Command):
    pass

_ARG = {
    'arg': {
        'help': 'Select a non-default app',
        'type': str, 'nargs': '?', 'default': '@'
    },
}

@command(
    version.NAME,
    help='Build and run an application',
    subcommands = {
        'kit': ({'help': 'Prepare an application to build'}, _ARG),
        'build': ({'help': 'Prepare to install app@target'}, _ARG),
        'install': ({'help': 'Prepare to run app@target'}, _ARG),
        'run': ({'help': 'Run app@target'}, _ARG),
    },
)
class MuPy(Command):

    class Arg:

        @classmethod
        def fromString(cls, string):
            string = string.strip()
            string = string if '@' in string else string + '@'
            app, target = string.split('@')
            return cls(app or None, target or None)

        def __init__(self, app, target):
            self._app = app
            self._target = target

        def __repr__(self): return f'{self._app or ""}@{self._target or ""}'

        @property
        def app(self): return self._app

        @property
        def target(self): return self._target

    def _getHost(self):
        return content.Host.fromConfiguration(self._configuration)
        
    def _getApp(self):
        return content.App.fromConfiguration(
            self._configuration, MuPy.Arg.fromString(self._args.arg).app
        )

    def _getLibs(self):
        return content.Libs.fromConfiguration(self._configuration)

    def _getTarget(self):
        return content.Target.fromConfiguration(
            self._configuration, MuPy.Arg.fromString(self._args.arg).target
        )

    def kit(self):
        return self._getApp().kit(self._getHost(), self._getLibs())

    def build(self):
        return self.kit().build(self._getTarget())
        
    def install(self):
        return self.build().install()

    def run(self):
        return self.install().run()


def _main(cls):
    from argparse import ArgumentParser, RawTextHelpFormatter
    parser = ArgumentParser(
        prog=cls.COMMAND,
        epilog=Command.EPILOG,
        formatter_class=RawTextHelpFormatter,
    )
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s {0}'.format(version.VERSION),
    )
    parser.add_argument(
        '-d', '--directory',
        default=os.environ.get('MUPY_DIRECTORY', os.getcwd()),
        help="Root directory\ndefault='%(default)s'",
    )
    parser.add_argument(
        '-c', '--configuration',
        default=os.environ.get('MUPY_CONFIGURATION', _MUPY_YAML),
        help="Configuration file name\ndefault='%(default)s'",
    )
    parser.add_argument(
        '-q', '--quiet',
        default=os.environ.get('MUPY_QUIET', False),
        action='store_true',
        help="Configuration file name\ndefault='%(default)s'",
    )
    subparsers = parser.add_subparsers(help=cls.HELP, dest='subcommand')
    for subcommand, (arguments, suboptions) in cls.SUBCOMMANDS.items():
        subparser = subparsers.add_parser(subcommand, **arguments)
        for suboption, subarguments in suboptions.items():
            subparser.add_argument(suboption, **subarguments)
    args = parser.parse_args()
    quiet.isQuiet = bool(args.quiet)
    if args.subcommand:
        filename = pathlib.Path(args.configuration).name
        try:
            directory = pathlib.Path(args.directory).resolve()
            if cls == Host and args.subcommand == 'init':
                path = pathlib.Path(directory, filename)
                Configuration.init(path, args.force)
                qprint(f"Created '{path}'")
                qprint(f"  Edit the configuration in '{filename}'")
                qprint(f"  Then run '{Host.COMMAND} install'")
                return
            configuration = Configuration.fromSearch(directory, filename)
            command = cls(configuration, args)
            command._do(args.subcommand)
        except Exception as exception:
            print(
                f'{exception.__class__.__name__}: {str(exception)}',
                file=sys.stderr,
            )
            raise exception # TODO Remove in production
            sys.exit(1)
    else:
        parser.print_help()

def main(cls=MuPy):
    _main(cls)

def main_host():
    main(Host)

def main_target():
    main(Target)
