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

import io
import os
import pathlib

import docker as Docker

from . import version
from .configuration import (
    Configuration,
    ConfigurationError,
    ConfigurationMissingError, ConfigurationOverwriteError,
    ConfigurationSyntaxError,
    )

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
Enviroment: MUPY_DIRECTORY, MUPY_CONFIGURATION
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
        print(f"Installing from '{self._configuration.path}'")
        # TODO
        ghost = self._configuration.content.target.ghost
        if ghost.docker.cpython:
            print('Creating CPython Docker image')
            docker = Docker.from_env()
            docker.images.build(
                fileobj=io.BytesIO(
                    ghost.docker.cpython.Dockerfile.encode('utf-8')
                ),
                rm=True,
            )
            print('TODO: Print docker image results')

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
        'run': ({}, {}),
    },
)
class MuPy(Command):

    def run(self):
        print(f"Running from '{self._configuration.path}'")


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
    subparsers = parser.add_subparsers(help=cls.HELP, dest='subcommand')
    for subcommand, (arguments, suboptions) in cls.SUBCOMMANDS.items():
        subparser = subparsers.add_parser(subcommand, **arguments)
        for suboption, subarguments in suboptions.items():
            subparser.add_argument(suboption, **subarguments)
    args = parser.parse_args()
    if args.subcommand:
        filename = pathlib.Path(args.configuration).name
        try:
            directory = pathlib.Path(args.directory).resolve()
            if cls == Host and args.subcommand == 'init':
                path = pathlib.Path(directory, filename)
                Configuration.install(path, args.force)
                print(f'Created {path}')
                print(f'  Edit the configuration in {filename}')
                print(f"  Then run '{Host.COMMAND} install'")
                return
            configuration = Configuration.fromSearch(directory, filename)
            command = cls(configuration, args)
            command._do(args.subcommand)
        except (
                ConfigurationError,
                ConfigurationOverwriteError, ConfigurationMissingError,
                ConfigurationSyntaxError,
        ) as exception:
            print(str(exception))
    else:
        parser.print_help()

def main_host():
    _main(Host)

def main_target():
    _main(Target)

def main():
    _main(MuPy)
