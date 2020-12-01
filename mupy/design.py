import os
import pathlib
import yaml

from . import version
from . import syntax

_MUPY = version.NAME

class StockError(ValueError): pass

class Stock:

    @classmethod
    def fromPath(cls, path, grade=None):
        if not (path.exists() and path.is_dir()):
            raise StockError(f"Stock directory does not exist, '{path}'")
        def pathGrade(path):
            return os.path.basename(path)
        gradeFilter = (
            (lambda _: True) if grade is None
            else (lambda name: name <= grade)
        )
        gradePaths = sorted([
            dE.path for dE in os.scandir(path)
            if dE.is_dir() and gradeFilter(pathGrade(dE.path))
        ], key=pathGrade, reverse=True)
        return cls(
            path, grade, tuple([Ensemble.setFromPath(gP) for gP in gradePaths])
        )

    def __init__(self, path, grade, ensembleSets=()):
        self._path = path
        self._grade = grade
        self._ensembleSets = ensembleSets

    @property
    def path(self): return self._path

    @property
    def grade(self): return self._grade
    
class Part:

    @classmethod
    def fromDictionary(cls, dictionary, location):
        name = syntax.Identifier.check(dictionary.get('name'), location)
        if not name:
            raise EnsembleSemanticError(
                f"Missing part name in {location}"
            )
        path = pathlib.Path(dictionary.get('path'))
        if not path:
            raise EnsembleSemanticError(
                f"Missing path for '{name}' at {location+name}"
            )
        uses = tuple(
            [syntax.Identifier.check(e, location)
             for e in dictionary.get('uses', ())]
        )
        return cls(name, path, uses)

    def __init__(self, name, path, uses):
        self._name = name
        self._path = path
        self._uses = uses

    def __str__(self): return f'{self._name}@{self._path.basename()}'

    @property
    def name(self): return self._name

    @property
    def path(self): return self._path

    @property
    def uses(self): return ()

class Import:

    @classmethod
    def fromDictionary(cls, dictionary, location):
        name = syntax.Identifier.check(dictionary.get('name'), location)
        if not name:
            raise EnsembleSemanticError(
                f"Missing import ensemble name in {location}"
            )
        l = f"{location} parts"
        aliases = {}
        for p in dictionary.get('parts', ()):
            if 'name' not in p:
                raise EnsembleSemanticError(
                    f"Missing import name in {l}"
                )
            name = syntax.Identifier.check(p['name'], l)
            alias = syntax.Identifier.check(p.get('as', name), l)
            aliases[name] = alias
        version = dictionary.get('version')
        return cls(name, aliases, version)

    def __init__(self, name, aliases=(), version=None):
        self._name = name
        self._aliases = aliases
        self._version = version
    
class EnsembleFileError(OSError): pass
class EnsembleSyntaxError(ValueError): pass
class EnsembleSemanticError(ValueError): pass

class Ensemble:

    @classmethod
    def setFromPath(cls, path):
        def isMuPy(filename):
            return pathlib.PurePath(filename).suffix == f'.{_MUPY}'
        ensembleSet=set()
        for dirpath, dirnames, filenames in os.walk(path, followlinks=True):
            for filename in filenames:
                if isMuPy(filename):
                    mupyPath = pathlib.Path(dirpath) / filename
                    name = Ensemble.nameFromPath(mupyPath)
                    if name in [e.name for e in ensembleSet]:
                        raise EnsembleError(
                            f'Duplicate ensemble {name} in {mupyPath}'
                        )
                    else:
                        ensembleSet.add(
                            Ensemble.fromPaths(path, mupyPath)
                        )
        return ensembleSet

    @staticmethod
    def nameFromPath(path):
        return path.stem

    @classmethod
    def fromPaths(cls, path, mupyPath):
        try:
            with open(mupyPath) as file:
                content = yaml.safe_load(file)
        except IsADirectoryError:
            raise EnsembleFileError(f"Path is a directory '{path}'")
        except FileNotFoundError:
            raise EnsembleFileError(f"Ensemble file not found {path}'")
        except (
                yaml.scanner.ScannerError,
                yaml.parser.ParserError,
        ) as exception:
            raise EnsembleSyntaxError(str(exception))
        else:
            content = content if content else {}
            version = content.get('version')
            exports = tuple(
                [syntax.Identifier.check(e, f'{mupyPath} exports')
                 for e in content.get('exports', ())]
            )
            parts = tuple(
                [Part.fromDictionary(p, f'{mupyPath} parts')
                 for p in content.get('parts', ())]
            )
            imports = tuple(
                [Import.fromDictionary(i, f'{mupyPath} imports')
                 for i in content.get('imports', ())]
            )
            return cls(mupyPath.relative_to(path), cls.nameFromPath(mupyPath))

    def __init__(
            self, rpath, name, parts, exports=(), imports=(), version=None
    ):
        self._rpath = rpath
        self._name = name
        self._parts = parts
        self._exports = exports
        self._imports = imports
        self._version = version

    @property
    def rpath(self): return self._rpath

    @property
    def name(self): return self._name

    @property
    def parts(self): return self._parts

    @property
    def exports(self): return self._exports

    @property
    def imports(self): return self._imports

    @property
    def version(self): return self._version
