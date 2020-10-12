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

import docker as Docker

from . import version
from .configuration import (
    Configuration, ConfigurationMissingError, ConfigurationOverwriteError,
    )

def command(name, help='Subcommand help', subcommands={}):
    def _command(cls):
        class _Command(cls):
            COMMAND = name
            HELP = help
            SUBCOMMANDS = subcommands
        return _Command
    return _command

class Command:

    VERSION = version.VERSION
    EPILOG = 'See also: {0}-host, {0}-target, {0}'.format(version.NAME)

    def __init__(self, args):
        self._args = args

    def _do(self, subcommand):
        return getattr(self, subcommand)()

@command(
    '{0}-host'.format(version.NAME),
    help='Host',
    subcommands = {
        'install': ({}, {
            '--force': { 'action': 'store_true'},
        }),
    },
)
class Host(Command):

    def install(self):
        pass

@command(
    '{0}-target'.format(version.NAME),
    help='Target',
    subcommands = {
        'list': ({}, {}),
    },
)
class Target(Command):
    pass


@command(
    version.NAME,
    help='Application',
    subcommands = {
        'run': ({}, {}),
    },
)
class MuPy(Command):
    pass

def _main(cls):
    from argparse import ArgumentParser
    parser = ArgumentParser(prog=cls.COMMAND, epilog=Command.EPILOG)
    parser.add_argument(
        '-v', '--version',
        action='version',
        version='%(prog)s {0}'.format(version.VERSION),
    )
    parser.add_argument(
        '-d', '--directory',
        default=os.environ.get('MUPY_DIRECTORY', os.getcwd()),
        help='muPy working directory',
    )
    parser.add_argument(
        '-c', '--configuration',
        default=os.environ.get('MUPY_CONFIGURATION', 'mupy.yml'),
        help='muPy configuration',
    )
    subparsers = parser.add_subparsers(help=cls.HELP, dest='subcommand')
    for subcommand, (arguments, suboptions) in cls.SUBCOMMANDS.items():
        subparser = subparsers.add_parser(subcommand, **arguments)
        for suboption, subarguments in suboptions.items():
            subparser.add_argument(suboption, **subarguments)
    args = parser.parse_args()
    if args.subcommand:
        try:
            path = pathlib.Path(args.directory, args.configuration)
            if cls == Host and args.subcommand == 'install':
                Configuration.install(path, args.force)
            configuration = Configuration.fromPath(path)
            command = cls(args)
            command._do(args.subcommand)
        except (
                ConfigurationOverwriteError, ConfigurationMissingError
        ) as exception:
            print(exception)
        finally:
            print("Install the host configuration: '{0} install'"
                  .format(Host.COMMAND))
    else:
        parser.print_help()

def main_host():
    _main(Host)

def main_target():
    _main(Target)

def main():
    _main(MuPy)
