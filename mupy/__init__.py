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
        'show': ({'help': f'3. Display the host setup details'}, {
        }),
        'remove': ({'help': f'4. Remove the host setup'}, {
            '--force': { 'action': 'store_true' },
        }),
    },
)
class Host(Command):

    def install(self):
        qprint(f"Installing from '{self._configuration.path}'")
        for target in [
                content.Target.fromConfiguration(
                    self._configuration, targetConfiguration.get('name')
                )
                for targetConfiguration in self._configuration.targets
        ]:
            target.install()
        host = content.Host.fromConfiguration(self._configuration)
        host.install(self._args.force)

@command(
    _MUPY_TARGET,
    help='Modify the target runtimes',
    subcommands = {
        'list': ({}, {}),
    },
)
class Target(Command):
    pass


@command(
    version.NAME,
    help='Build and run an application',
    subcommands = {
        'run': ({'help': 'Run an application on a target'}, {
            '--app': { 'help': 'Select a non-default app', 'type': str },
            '--target': { 'help': 'Select a non-default target', 'type': str },
        }),
    },
)
class MuPy(Command):

    def run(self):
        app = content.App.fromConfiguration(
            self._configuration, self._args.app
        )
        target = content.Target.fromConfiguration(
            self._configuration, self._args.target
        )
        target.run(app)


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
                Configuration.install(path, args.force)
                qprint(f'Created {path}')
                qprint(f'  Edit the configuration in {filename}')
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
            sys.exit(1)
    else:
        parser.print_help()

def main(cls=MuPy):
    _main(cls)

def main_host():
    main(Host)

def main_target():
    main(Target)
