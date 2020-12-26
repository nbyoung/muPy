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
import pkgutil
import sys

from .configuration import (
    Configuration,
    ConfigurationError,
    ConfigurationMissingError, ConfigurationOverwriteError,
    ConfigurationSyntaxError,
    )
from . import design
from . import host
from .quiet import Quiet; qprint = Quiet.qprint
from . import syntax
from . import target
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

_GHOST = 'ghost'
_RUN_PIP_INSTALL_DOCKER = f'''
Docker not installed. Use only the '@ghost' local target.
Run 'pip install docker' and '{_MUPY_HOST} setup' again to use other targets.
'''
_IS_DOCKER =  bool(pkgutil.find_loader('docker'))

class Command:

    VERSION = version.VERSION
    EPILOG = f'''
Environment: MUPY_DEBUG, MUPY_QUIET, MUPY_DIRECTORY, MUPY_CONFIGURATION
Commands: {_MUPY_HOST}, {_MUPY_TARGET}, {_MUPY}
''' + _RUN_PIP_INSTALL_DOCKER if not _IS_DOCKER else ''



    def __init__(self, configuration, args):
        self._configuration = configuration
        self._args = args

    def _do(self, subcommand):
        return getattr(self, subcommand)()

@command(
    _MUPY_HOST,
    help='Modify the host setup',
    subcommands = {
        'init': ({'help': f"Create the host configuration file, '{_MUPY_HOST_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing file', 'action': 'store_true' },
        }),
        'setup': ({'help': f"Set up the configuration in '{_MUPY_HOST_YAML}'"}, {
            '--force': { 'help': 'Overwrite any existing files', 'action': 'store_true' },
        }),
        # 'demo': ({'help': f"Install the demo files"}, {
        #     '--force': { 'help': 'Overwrite any existing files', 'action': 'store_true' },
        # }),
        # 'show': ({'help': f'Display the host setup details'}, {
        # }),
        'remove': ({'help': f'Remove the host setup'}, {
            '--force': { 'action': 'store_true' },
        }),
    },
)
class Host(Command):

    def setup(self):
        target.CrossTarget.isInstalled(lambda m: qprint(m, file=sys.stderr))
        qprint(f"Setting up from '{self._configuration.path}'")
        host.Host.fromConfiguration(self._configuration).setup(self._args.force)
        if _IS_DOCKER:
            for name in ('cpython', 'micropython'):
                try:
                    target.Mode.fromConfiguration(
                        self._configuration, name
                    ).install(qprint)
                except KeyError:
                    raise ConfigurationMissingError(
                        f"Missing mode configuration for '{name}'"
                    )

    def remove(self):
        target.DockerMode.removeAllImages(qprint)

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
            'help': 'Only use stock at this grade and higher',
            'type': str,
        },
        _APP: {
            'help': 'Select an ensemble and entry part with an optional target',
            'type': str, 'nargs': '?', 'default': '+',
        },
    }
    args.update(options)
    return args

class CommandError(ValueError): pass

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

    def __init__(self, configuration, args):
        super().__init__(configuration, args)
        self._configuration = configuration
        self._args = args

    @property
    def _host(self): return host.Host.fromConfiguration(self._configuration)

    @property
    def _grade(self):
        grade = vars(self._args)['grade']
        return None if grade is None else syntax.Identifier.check(grade)

    @property
    def _app(self):
        app = syntax.App.parse(vars(self._args)[_APP])
        if not app.target == _GHOST and not _IS_DOCKER:
            raise CommandError(_RUN_PIP_INSTALL_DOCKER)
        return design.App(*app) if vars(self._args)[_APP] else None

    @property
    def _target(self):
        return target.Target.fromConfiguration(self._configuration, self._app.target)

    def _stock(self):
        return design.Stock.fromPath(
            self._host.stockPath, self._target.type, self._grade
        )

    def stock(self):
        stock = self._stock()
        for ensembleSet in stock.ensembleSets:
            for ensemble in ensembleSet:
                qprint(ensemble.asYAML(delimiter='--\n'))
                    
    def _bom(self, ensembleName, entryName):
        stock = self._stock()
        component = stock.getComponent(entryName, self._app.ensemble, self._app.entry)
        return design.BOM.fromStock(stock, component)
                    
    def bom(self):
        def printComponent(component, indent):
            qprint(
                f'{" "*indent}'
                + f'{component.ensemble.grade}[{component.name}]'
            )
        self._bom(self._app.ensemble, self._app.entry).walk(
            printComponent, lambda arg: arg + 2, 0
        )
                    
    def kit(self):
        def callback(fromPath, toPath):
            qprint(f'  {fromPath.relative_to(self._host.stockPath)}')
            qprint(toPath.relative_to(self._host.buildPath))
        return design.Kit.fromBOM(
            self._bom(self._app.ensemble, self._app.entry),
            self._host.kitPath(self._app),
            callback,
        )

    def build(self):
        return design.Build.fromKit(
            self.kit(),
            self._host.buildPath,
            self._app.entryName,
            self._target,
            qprint,
        )
        
    def install(self):
        return design.Install.fromBuild(self.build(), qprint, Quiet.get())

    def run(self):
        if self._args.silent: Quiet.set(True)
        return design.Runner.fromInstall(
            self.install(), qprint, isSilent=self._args.silent
        )


def _main(cls):
    
    def affirmative(string):
        try:
            return bool(int(string))
        except ValueError:
            return string.lower() in ('1', 'y', 'yes', 't', 'true')
        
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
        default=affirmative(os.environ.get('MUPY_QUIET', '')),
        action='store_true',
        help='Suppress terminal output',
    )
    parser.add_argument(
        '--debug',
        default=affirmative(os.environ.get('MUPY_DEBUG', '')),
        action='store_true',
        help='Include exception traceback',
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
            if args.debug: raise exception
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
