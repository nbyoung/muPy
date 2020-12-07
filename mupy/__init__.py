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
from . import design
from . import host
from .quiet import Quiet; qprint = Quiet.qprint
from . import syntax
from . import version

_MUPY = version.NAME
_MUPY_HOST = f'{_MUPY}-host'
_MUPY_TARGET = f'{_MUPY}-target'
_MUPY_HOST_YAML = 'mupy-host.yaml'

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
        'init': ({'help': f"1. Create the host configuration file, '{_MUPY_HOST_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing file', 'action': 'store_true' },
        }),
        'setup': ({'help': f"2. Set up the configuration in '{_MUPY_HOST_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing files', 'action': 'store_true' },
        }),
        'demo': ({'help': f"3. Install the demo files"}, {
            '--force': { 'help': 'Overwrite any existing files', 'action': 'store_true' },
        }),
        'show': ({'help': f'4. Display the host setup details'}, {
        }),
        'remove': ({'help': f'5. Remove the host setup'}, {
            '--force': { 'action': 'store_true' },
        }),
    },
)
class Host(Command):

    def setup(self):
        host.CrossTarget.isInstalled(lambda m: qprint(m, file=sys.stderr))
        qprint(f"Setting up from '{self._configuration.path}'")
        host.Host.fromConfiguration(self._configuration).setup(self._args.force)
        for name in ('cpython', 'micropython'):
            try:
                host.Mode.fromConfiguration(self._configuration, name).install()
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
        host.DockerMode.removeAllImages()

@command(
    _MUPY_TARGET,
    help='Modify the target',
    subcommands = {
        'list': ({}, {}),
    },
)
class Target(Command):
    pass

_APP = 'ensemble^entry[@target]'

def _mupyOptions(options={}):
    args = {
        '--grade': {
            'help': 'Do not use stock lower than this grade',
            'type': str,
        },
        _APP: {
            'help': 'Select an ensemble and entry part with an optional target',
            'type': str, 'nargs': '?', 'default': '+',
        },
    }
    args.update(options)
    return args

@command(
    version.NAME,
    help='Build and run an application',
    subcommands = {
        'stock': ({ 'help': 'Show the available stock' }, _mupyOptions()),
        'bom': ({ 'help': 'Show the import tree for a part' }, _mupyOptions()),
        'kit': ({ 'help': 'Prepare an application to build' }, _mupyOptions()),
        'build': ({ 'help': 'Prepare to install app@target' }, _mupyOptions()),
        'install': ({ 'help': 'Prepare to run app@target' }, _mupyOptions()),
        'run': ({ 'help': 'Run app@target' },
                _mupyOptions({
                    '--silent': {
                        'action': 'store_true', 'default': False,
                        'help': 'Suppress execution output; Implies --quiet',
                    }
                })
        ),
    },
)
class MuPy(Command):

    class App:

        @classmethod
        def fromString(cls, string):
            string = string.strip()
            string = string if ':' in string else ':' + string
            string = string if '#' in string else string + '#'
            app, target = string.split('@')
            return cls(app or None, target or None)

        def __init__(self, ensemble, entry=None, target=None):
            self._ensemble = ensemble
            self._entry = entry
            self._target = target

        def __repr__(self): return f'{self._app or ""}@{self._target or ""}'

        @property
        def ensemble(self): return self._ensemble

        @property
        def entry(self): return self._entry

        @property
        def target(self): return self._target

    def __init__(self, configuration, args):
        super().__init__(configuration, args)
        self._host = host.Host.fromConfiguration(configuration)
        self._grade = vars(args)['grade'] or None
        if self._grade: syntax.Identifier.check(self._grade)
        self._app = (
            syntax.App.parse(vars(args)[_APP]) if vars(args)[_APP] else None
        )

    def _stock(self):
        return design.Stock.fromPath(self._host.stockPath, self._grade)

    def stock(self):
        stock = self._stock()
        for ensembleSet in stock.ensembleSets:
            for ensemble in ensembleSet:
                qprint(ensemble.asYAML(delimiter='--\n'))
                    
    def _bom(self, ensembleName, entryName):
        return self._stock().bom(self._app.ensemble, self._app.entry)
                    
    def bom(self):
        def printComponent(component, indent):
            qprint(
                f'{" "*indent}'
                + f'{component.ensemble.grade}'
                + f'[{component.ensemble.name}^{component.part.name}]'
            )
        self._bom(self._app.ensemble, self._app.entry).walk(
            printComponent, lambda arg: arg + 2, 0
        )

    # def kit(self):
    #     return self._getApp().kit(self._host)

    # def build(self):
    #     return self.kit().build(self._getTarget())
        
    # def install(self):
    #     return self.build().install()

    # def run(self):
    #     if self._args.silent: Quiet.set(True)
    #     return self.install().run(isSilent=self._args.silent)


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
        default=os.environ.get('MUPY_HOST', _MUPY_HOST_YAML),
        help="Configuration file name\ndefault='%(default)s'",
    )
    parser.add_argument(
        '-q', '--quiet',
        default=os.environ.get('MUPY_QUIET', False),
        action='store_true',
        help='Suppress terminal output',
    )
    subparsers = parser.add_subparsers(help=cls.HELP, dest='subcommand')
    for subcommand, (arguments, suboptions) in cls.SUBCOMMANDS.items():
        subparser = subparsers.add_parser(subcommand, **arguments)
        for suboption, subarguments in suboptions.items():
            subparser.add_argument(suboption, **subarguments)
    args = parser.parse_args()
    Quiet.set(bool(args.quiet))
    if args.subcommand:
        filename = pathlib.Path(args.configuration).name
        try:
            directory = pathlib.Path(args.directory).resolve()
            if cls == Host and args.subcommand == 'init':
                path = pathlib.Path(directory, filename)
                Configuration.init(path, args.force)
                qprint(f"Created '{path}'")
                qprint(f"  Edit the configuration in '{filename}'")
                qprint(f"  Then run '{Host.COMMAND} setup'")
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
