from collections.abc import MutableSet
import os
import pathlib
import shutil
import yaml
import zlib

from . import version
from . import syntax

_MUPY = version.NAME

def EntryName(ensembleName, partName): return f'{ensembleName}^{partName}'

class App:

    def __init__(self, ensemble, entry=None, target=None):
        self._ensemble = ensemble
        self._entry = entry
        self._target = target

    @property
    def ensemble(self): return self._ensemble

    @property
    def entry(self): return self._entry

    @property
    def entryName(self): return EntryName(self._ensemble, self._entry)

    @property
    def target(self): return self._target

    @property
    def name(self):
        return self.entryName + f'@{self._target}' if self._target else ''
    
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
                f"Missing path for '{name}' in {location}"
            )
        if path.is_absolute():
            raise EnsembleSemanticError(
                f"Absolute path '{path}' in {location}"
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

    @property
    def name(self): return self._name

    @property
    def path(self): return self._path

    @property
    def uses(self): return self._uses

    def asYAML(self, delimiter='', margin=0, indent=2):
        return delimiter + ('\n'.join([f'{" "*margin}{line}' for line in (
            f'name: {self._name}',
            f'path: "{self._path}"',
            f'uses: [ {", ".join(self._uses)} ]' if self._uses else '',
        ) if line]))

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
            aname = syntax.Identifier.check(p['name'], l)
            alias = syntax.Identifier.check(p.get('as', aname), l)
            if alias in aliases:
                raise EnsembleSemanticError(
                    f"Duplicate import alias '{alias}' in {l}"
                )
            aliases[alias] = aname
        version = dictionary.get('version')
        return cls(name, aliases, version)

    def __init__(self, name, aliases, version):
        self._name = name
        self._aliases = aliases
        self._version = version

    @property
    def name(self): return self._name

    @property
    def version(self): return self._version

    @property
    def aliases(self): return self._aliases

    def asYAML(self, delimiter='', margin=0, indent=2):
        return delimiter + ('\n'.join([f'{" "*margin}{line}' for line in (
            f'name: {self._name}',
            f'version: "{self._version}"',
            f'parts:\n%s' % (
            '\n'.join([f'{" "*(margin+indent)}- {{ import: {v}, as: {k} }}'
                       for k, v in self._aliases.items()])
            )
        )]))
    
class EnsembleFileError(OSError): pass
class EnsembleSyntaxError(ValueError): pass
class EnsembleSemanticError(ValueError): pass

class Ensemble:

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
            return cls(
                os.path.basename(path),
                mupyPath.parent, cls.nameFromPath(mupyPath), parts,
                exports=exports, imports=imports, version=version,
            )

    def __init__(
            self, grade, path, name, parts,
            exports=(), imports=(), version=None,
    ):
        self._grade = grade
        self._path = path
        self._name = name
        self._parts = parts
        self._exports = exports
        self._imports = imports
        self._version = version

    @property
    def grade(self): return self._grade

    @property
    def path(self): return self._path

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

    def isExport(self, name): return name in self._exports

    def getPart(self, name):
        parts = [p for p in self._parts if p.name == name]
        if 1 == len(parts):
            return parts[0]
        elif 1 < len(parts):
            raise EnsembleSemanticError(
                f"Duplicate part '{name}' in ensemble '{self._name}'"
            )

    def asYAML(self, delimiter='', margin=0, indent=2):
        return delimiter + '\n'.join([f'{" "*margin}{line}' for line in (
            f'# {self._name} "{self._path}"',
            f'exports: [ {", ".join(self._exports)} ]',
            f'parts:\n%s' % '\n'.join(
                [i.asYAML(' '*(margin+indent)+'-\n', margin+indent*2, indent)
                 for i in self._parts]
            ) if self._parts else '',
            f'imports:\n%s' % '\n'.join(
                [i.asYAML(' '*(margin+indent)+'-\n', margin+indent*2, indent)
                 for i in self._imports]
            ) if self._imports else '',
        ) if line])

class EnsembleSet(MutableSet):

    @classmethod
    def fromPath(cls, grade, path):
        def isMuPy(filename):
            return pathlib.PurePath(filename).suffix == f'.{_MUPY}'
        ensembleSet=cls(grade)
        for dirpath, dirnames, filenames in os.walk(path, followlinks=True):
            for filename in filenames:
                if isMuPy(filename):
                    mupyPath = pathlib.Path(dirpath) / filename
                    name = Ensemble.nameFromPath(mupyPath)
                    if name in [e.name for e in ensembleSet]:
                        gradeLevel = f'grade level {grade} ' if grade else ''
                        raise EnsembleSemanticError(
                            f"Stock {gradeLevel}contains duplicate ensemble '{name}'"
                        )
                    else:
                        ensembleSet.add(
                            Ensemble.fromPaths(path, mupyPath)
                        )
        return ensembleSet

    def __init__(self, grade):
        self._grade = grade
        self._set = set()
        
    def __contains__(self, member): return self._set.__contains__(member)
    def __iter__(self): return self._set.__iter__()
    def __len__(self): return self._set.__len__()
    def add(self, member): return self._set.add(member)
    def discard(self, member): return self._set.discard(member)

    @property
    def grade(self): return self._grade
    
class Component:

    def __init__(self, origin, ensemble, part):
        self._origin = origin
        self._ensemble = ensemble
        self._part = part

    @property
    def origin(self): return self._origin

    @property
    def ensemble(self): return self._ensemble

    @property
    def part(self): return self._part

    @property
    def name(self): return f'{EntryName(self._ensemble.name, self._part.name)}'

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
            path, grade, tuple([EnsembleSet.fromPath(grade, gP)
                                for gP in gradePaths])
        )

    def __init__(self, path, grade, ensembleSets=()):
        self._path = path
        self._grade = grade
        self._ensembleSets = ensembleSets

    @property
    def path(self): return self._path

    @property
    def grade(self): return self._grade

    @property
    def ensembleSets(self): return self._ensembleSets

    def getComponent(self, originPartName, ensembleName, partName, isLocal=False):
        entryName = EntryName(ensembleName, partName)
        for ensembleSet in self._ensembleSets:
            components = [
                Component(originPartName, e, e.getPart(partName))
                for e in ensembleSet
                if (
                        e.name == ensembleName
                        and
                        (isLocal or e.isExport(partName))
                )]
            if 1 == len(components):
                return components[0]
            elif 1 < len(components):
                raise StockError(
                    f"Grade level {ensembleSet.grade} contains duplicate '{entryName}'"
                )
        gradeLevel = f'grade level {self._grade} ' if self._grade else ''
        raise StockError(
            f"Stock {gradeLevel}does not export '{entryName}'"
        )

class BOMError(ValueError): pass

class BOM:

    @classmethod
    def fromStock(cls, stock, component, ancestorComponents=[]):
        if component.part in [aC.part for aC in ancestorComponents]:
            raise BOMError(
                f"Circular reference with {component.name}>"
                + ">".join([EntryName(aC.ensemble.name, aC.part.name)
                           for aC in reversed(ancestorComponents)])
            )
        def componentArgs(partName):
            def getImport():
                for imprt in component.ensemble.imports:
                    if partName in imprt.aliases:
                        return imprt
            isLocal = partName in [p.name for p in component.ensemble.parts]
            imprt = getImport()
            if isLocal and imprt:
                raise BOMError(
                    f"Local {EntryName(component.ensemble.name, partName)} also imported"
                )
            elif isLocal:
                return (component.ensemble.name, partName, True)
            elif imprt:
                return (imprt.name, imprt.aliases[partName], False)
            raise BOMError(
                f"Undefined {EntryName(component.ensemble.name, partName)}"
            )
        children = [
            cls.fromStock(
                stock,
                stock.getComponent(childPartName, *componentArgs(childPartName)),
                ancestorComponents + [component],
            )
            for childPartName in component.part.uses
        ]
        return cls(component, children)

    def __init__(self, component, children=()):
        self._component = component
        self._children = children

    def walk(
            self,
            callback=lambda component, arg: None,
            nextArg=lambda arg: None, arg=None,
    ):
        callback(self._component, arg)
        for child in self._children:
            child.walk(callback, nextArg, nextArg(arg))
    
class KitError(ValueError): pass
    
class Kit:

    @classmethod
    def fromBOM(cls, bom, path, callback=lambda fromPath, toPath: None):
        shutil.rmtree(path, onerror=lambda type, value, tb: None )
        toPaths = {}
        def doKit(component, _):
            def rebase(path, name): return path.parent / (name + path.suffix)
            fromPath = component.ensemble.path / component.part.path
            toPath = path / rebase(component.part.path, component.origin)
            if toPath in toPaths:
                if toPaths[toPath].samefile(fromPath):
                    return
                raise KitError(f"Invalid duplicates '{toPaths[toPath]}' and '{fromPath}' both map to {toPath}")
            toPaths[toPath] = fromPath
            if fromPath.exists():
                toPath.parent.mkdir(parents=True, exist_ok=True)
                if fromPath.is_file():
                    shutil.copy2(fromPath, toPath)
                elif fromPath.is_dir():
                    shutil.copytree(
                        fromPath, toPath, symlinks=True, copy_function=shutil.copy2
                    )
                else:
                    raise KitError(f"Kit part is not valid '{fromPath}'")
                callback(fromPath, toPath)
            else:
                raise KitError(f"Kit part does not exist '{fromPath}'")
        bom.walk(doKit)
        return Kit(path)

    def __init__(self, path):
        self._path = path

    @property
    def path(self): return self._path

class BuildError(ValueError): pass

class Build:

    _INSTALL = 'install'
    _SUFFIX = '.py'

    @staticmethod
    def hash(path):
        blksize = os.stat(path).st_blksize
        adler32 = zlib.adler32(b'')
        with open(path, 'rb') as file:
            while True:
                data = file.read(blksize)
                if not data: break
                adler32 = zlib.adler32(data, adler32)
        return f'{adler32:0>8X}'

    @classmethod
    def fromKit(cls, kit, path, entryName, target, callback=lambda line: None):
        buildPath = path
        installPath = buildPath / Build._INSTALL / target.name
        cachePath = buildPath / Build._INSTALL / f'{target.name}.{entryName}'
        if installPath.is_dir():
            shutil.rmtree(cachePath, onerror=lambda type, value, tb: None )
            installPath.rename(cachePath)
        else:
            shutil.rmtree(installPath, onerror=lambda type, value, tb: None )
        sourceFromTo = []
        for directory, dirNames, fileNames in os.walk(kit.path):
            directory = pathlib.Path(directory)
            cPath = cachePath / directory.relative_to(kit.path)
            iPath = installPath / directory.relative_to(kit.path)
            iPath.mkdir(parents=True, exist_ok=True)
            for filePath in [pathlib.Path(fN)
                             for fN in fileNames
                             if pathlib.Path(fN).suffix == Build._SUFFIX]:
                sourceHash = Build.hash(directory / filePath)
                targetFilePath = filePath.with_suffix(f'{target.suffix}.{sourceHash}')
                if (cPath / targetFilePath).exists():
                    shutil.copy2(cPath / targetFilePath, iPath / targetFilePath)
                else:
                    sourceFromTo.append((
                        os.path.relpath(
                            directory / filePath, kit.path),
                        os.path.relpath(
                            directory / filePath, buildPath),
                        os.path.relpath(
                            (iPath / targetFilePath), buildPath)
                    ))
        if sourceFromTo:
            with target.buildContainer(buildPath, sourceFromTo) as container:
                for output in container.logs(stream=True):
                    callback('b: %s' % output.decode('utf-8'))
        return cls(installPath, target)

    def __init__(self, path, target):
        self._path = path
        self._target = target

    @property
    def path(self): return self._path

    @property
    def target(self): return self._target
