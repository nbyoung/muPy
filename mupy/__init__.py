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

import docker as Docker

from . import version

def command(commands, help='Subcommand help', subcommands={}):
    def _command(cls):
        class _Command(cls):
            COMMAND = commands[0]
            HELP = help
            SUBCOMMANDS = subcommands
        return _Command
    return _command

class Command:

    VERSION = version.VERSION
    EPILOG = 'See also: mupy-host, mupy-target, mupy'

    def __init__(self, args):
        self._args = args

    def _do(self, subcommand):
        return getattr(self, subcommand)()

@command(
    ('mupy-host', ),
    help='Host',
    subcommands = {
        'install': {},
    },
)
class Host(Command):

    def install(self):
        docker = Docker.from_env()
        print(docker.images.list())


@command(
    ('mupy-target', ),
    help='Target',
    subcommands = {
        'list': {},
    },
)
class Target(Command):
    pass


@command(
    ('mupy', 'mu.py'),
    help='Application',
    subcommands = {
        'run': {},
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
    subparsers = parser.add_subparsers(help=cls.HELP, dest='subcommand')
    for subcommand, options in cls.SUBCOMMANDS.items():
        subparsers.add_parser(subcommand, **options)
    args = parser.parse_args()
    if args.subcommand:
        cls(args)._do(args.subcommand)
    else:
        parser.print_help()

def main_host():
    _main(Host)

def main_target():
    _main(Target)

def main():
    _main(MuPy)
