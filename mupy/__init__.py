##############################################################################
##############################################################################
##############################################################################
##############################################################################
####
#### name:      mupy/__init__.py
####
#### usage:     mupy-host | mupy-target | mupy [options] subcommand [suboptions]
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


def _commands(commands, help='Command help'):
    def _command(cls):
        class _Command(cls):
            COMMAND = commands[0]
            HELP = help
            @staticmethod
            def isCommand(command):
                return command in commands
        return _Command
    return _command

@_commands(
    ('mupy-host', ),
    help='Development environment',
)
class Host:
    pass

@_commands(
    ('mupy-target', ),
    help='MicroPython targets',
)
class Target:
    pass

@_commands(
    ('mupy', 'mu.py'),
    help='MicroPython applications'
)
class MuPy:
    pass

from argparse import ArgumentParser
import os

def _argumentParser(cls):
    parser = ArgumentParser(prog=cls.COMMAND)
    parser.add_argument(
        '-d', '--directory',
        default=os.environ.get('MUPY_DIRECTORY', os.getcwd()),
        help='muPy working directory',
    )
    return parser

def main_host():
    parser = _argumentParser(Host)
    subparsers = parser.add_subparsers(help=Host.HELP)
    parser_install = subparsers.add_parser('install')
    args = parser.parse_args()
    print(args)

def main_target():
    parser = _argumentParser(Target)
    subparsers = parser.add_subparsers(help=Target.HELP)
    parser_list = subparsers.add_parser('list')
    args = parser.parse_args()
    print(args)

def main():
    parser = _argumentParser(MuPy)
    subparsers = parser.add_subparsers(help=MuPy.HELP)
    parser_run = subparsers.add_parser('run')
    args = parser.parse_args()
    print(args)
