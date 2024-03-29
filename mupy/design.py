from collections.abc import MutableSet
import os
import pathlib
import shutil
import subprocess
import yaml
import zlib

from . import version
from . import syntax
from . import tag

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
        def checkShlet(shlet):
            if not isinstance(shlet, dict):
                raise EnsembleSemanticError(
                    f"Shell variables ('shlet') must be a dictionary in {location}"
                )
            for key in shlet.keys():
                syntax.Identifier.check(key, location)
            return shlet
        SHLET = 'shlet'
        shletTagIndex = tag.TagIndex()
        for tagString, shlet in [
                (k[len(SHLET):], v)
                for (k, v) in dictionary.items()
                if k.startswith(SHLET)
        ]:
            shletTagIndex.add(
                tag.TagRay.fromString(tagString), checkShlet(shlet),
            )

        shellTagIndex = tag.TagIndex()
        for prefix, isQuiet in (
                ('shell', False),
                ('shhell', True),
        ):
            for tagString, shellList in [
                    (k[len(prefix):], v)
                    for (k, v) in dictionary.items()
                    if k.startswith(prefix)
            ]:
                shellTagIndex.add(
                    tag.TagRay.fromString(tagString), (shellList, isQuiet),
                )
        def checkPath(path, isNoneOkay=False):
            if path is not None:
                path = pathlib.Path(path)
            elif isNoneOkay:
                return None
            else:
                raise EnsembleSemanticError(
                    f"Missing path or shell for '{name}' in {location}"
                )
            if path.is_absolute():
                raise EnsembleSemanticError(
                    f"Absolute path '{path}' in {location}"
                )
            return path
        PATH = 'path'
        path = checkPath(dictionary.get(PATH), bool(shellTagIndex.count))
        pathTagIndex = tag.TagIndex(
            [(tag.TagRay.fromString(tagString), checkPath(path))
             for tagString, path in [
                     (k[len(PATH):], v)
                     for (k, v) in dictionary.items()
                     if k.startswith(PATH)
            ]]
        )
        uses = tuple(
            [syntax.Identifier.check(e, location)
             for e in dictionary.get('uses', ())]
        )
        return cls(name, path, pathTagIndex, shletTagIndex, shellTagIndex, uses)

    def __init__(self, name, path, pathTagIndex, shletTagIndex, shellTagIndex, uses):
        self._name = name
        self._path = path
        self._pathTagIndex = pathTagIndex
        self._shletTagIndex = shletTagIndex
        self._shellTagIndex = shellTagIndex
        self._uses = uses

    @property
    def name(self): return self._name

    @property
    def path(self): return self._path

    def taggedPath(self, tagRay):
        return self._pathTagIndex.max(tagRay)

    def taggedShlet(self, tagRay):
        return self._shletTagIndex.max(tagRay)

    def taggedShell(self, tagRay):
        return self._shellTagIndex.max(tagRay)

    @property
    def uses(self): return self._uses

    def asYAML(self, delimiter='', margin=0, indent=2):
        return delimiter + ('\n'.join([f'{" "*margin}{line}' for line in (
            f'name: {self._name}',
            f'path: "{self._path}"',
            # TODO self._pathTagIndex
            # TODO self._shellTagIndex
            f'uses: [ {", ".join(self._uses)} ]' if self._uses else '',
        ) if line]))

class Import:

    @classmethod
    def fromDictionary(cls, dictionary, location):
        name = dictionary.get('name')
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
            rpath = pathlib.Path(content.get('path', ''))
            if rpath.is_absolute(): raise EnsembleSemanticError(
                    f"Optional path must be relative, not '{rpath}'"
            )
            exports = tuple(
                [syntax.Identifier.check(e, f'{mupyPath} exports')
                 for e in (content.get('exports', ()) or ())]
            )
            parts = tuple(
                [Part.fromDictionary(p, f'{mupyPath} parts')
                 for p in (content.get('parts', ()) or ())]
            )
            imports = tuple(
                [Import.fromDictionary(i, f'{mupyPath} imports')
                 for i in (content.get('imports', ()) or ())]
            )
            return cls(
                os.path.basename(path),
                mupyPath.parent / rpath,
                cls.nameFromPath(mupyPath), parts,
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
                [p.asYAML(' '*(margin+indent)+'-\n', margin+indent*2, indent)
                 for p in self._parts]
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
    def fromBOM(
            cls, bom, path, tagRay, shell, callback=lambda fromPath, toPath: None
    ):
        shutil.rmtree(path, onerror=lambda type, value, tb: None )
        path.mkdir(parents=True)
        toPaths = {}
        def doKit(component, isMain):
            name = 'main' if isMain else component.origin
            shellDictionary = {
                'origin': component.origin,
                'name': name,
                'here': component.ensemble.path,
                'there': path,
            }
            if component.part.path is not None:
                def rebase(path): return path.parent / (name + path.suffix)
                fromPath = component.ensemble.path / component.part.taggedPath(tagRay)
                toPath = path / rebase(component.part.path)
                if toPath in toPaths:
                    if toPaths[toPath].samefile(fromPath):
                        return
                    raise KitError(f"Invalid duplicates '{toPaths[toPath]}' and '{fromPath}' both map to {toPath}")
                toPaths[toPath] = fromPath
                shellDictionary['this'] = fromPath
                shellDictionary['that'] = toPath
            try:
                shlet = component.part.taggedShlet(tagRay)
            except tag.TagIndexError:
                shlet = {}
            try:
                shellStrings, isQuiet = (
                    component.part.taggedShell(tagRay)
                    or ((), False)
                )
                input = ''
                substitutions = {**shellDictionary, **shlet}
                for shellString in [
                        s.format(**substitutions)
                        for s in shellStrings
                ]:
                    completedProcess = subprocess.run(
                        shellString,
                        check=True, shell=True, text=True, input=input,
                        executable=shell.bin, cwd=shell.cwd, env=shell.env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    )
                    input = completedProcess.stdout
                    if not isQuiet: callback(shellString, completedProcess.stdout)
            except tag.TagIndexError:
                pass    
            if component.part.path is None or toPath.exists():
                return
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
        bom.walk(doKit, lambda arg: False, arg=True)
        return Kit(path)

    def __init__(self, path):
        self._path = path

    @property
    def path(self): return self._path
    
class BuildError(ValueError): pass

class Build:

    _COMPILE = '.compile'
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
    def fromKit(cls, kit, buildPath, entryName, target, callback=lambda line: None):
        compilePath = buildPath / Build._COMPILE / entryName / target.name
        cachePath = buildPath / Build._COMPILE / entryName / f'.{target.name}'
        if compilePath.is_dir():
            shutil.rmtree(cachePath, onerror=lambda type, value, tb: None )
            compilePath.rename(cachePath)
        else:
            shutil.rmtree(compilePath, onerror=lambda type, value, tb: None )
        sourceFromTo = []
        copyRPaths = []
        for directory, dirNames, fileNames in os.walk(kit.path):
            directory = pathlib.Path(directory)
            hPath = cachePath / directory.relative_to(kit.path)
            cPath = compilePath / directory.relative_to(kit.path)
            cPath.mkdir(parents=True, exist_ok=True)
            for filePath in [pathlib.Path(fN) for fN in fileNames]:
                if filePath.suffix == Build._SUFFIX:
                    sourceHash = Build.hash(directory / filePath)
                    targetFilePath = filePath.with_suffix(f'{target.suffix}.{sourceHash}')
                    if (hPath / targetFilePath).exists():
                        shutil.copy2(hPath / targetFilePath, cPath / targetFilePath)
                    else:
                        sourceFromTo.append((
                            os.path.relpath(
                                directory / filePath, kit.path),
                            os.path.relpath(
                                directory / filePath, buildPath),
                            os.path.relpath(
                                (cPath / targetFilePath), buildPath)
                        ))
                else:
                    copyRPaths.append(directory.relative_to(kit.path) / filePath)
            copyRPaths.extend(
                [directory.relative_to(kit.path) / pathlib.Path(dN) for dN in dirNames]
            )
        if sourceFromTo:
            with target.buildContainer(buildPath, sourceFromTo) as container:
                for output in container.logs(stream=True):
                    callback(output)
        installPath = buildPath / Build._INSTALL / entryName / target.name
        shutil.rmtree(installPath, onerror=lambda type, value, tb: None )
        for directory, dirNames, fileNames in os.walk(compilePath):
            directory = pathlib.Path(directory)
            iPath = installPath / directory.relative_to(compilePath)
            iPath.mkdir(parents=True, exist_ok=True)
            for fileName in [pathlib.Path(fN) for fN in fileNames]:
                shutil.copy2(directory / fileName, iPath / fileName.stem)
                callback(str((iPath / fileName.stem).relative_to(buildPath)))
        for copyRPath in copyRPaths:
            fromPath = kit.path / copyRPath
            toPath = installPath / copyRPath
            if fromPath.exists():
                if fromPath.is_file():
                    toPath.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fromPath, toPath)
                elif fromPath.is_dir():
                    toPath.mkdir(parents=True, exist_ok=True)
                else:
                    raise BuildError(f"File is not valid '{fromPath}'")
            callback(toPath.relative_to(buildPath))
        return cls(installPath, target)

    def __init__(self, path, target):
        self._path = path
        self._target = target

    @property
    def path(self): return self._path

    @property
    def target(self): return self._target

class Install:

    @classmethod
    def fromBuild(cls, build, callback=lambda line: None, isQuiet=False):
        callback(f"Install {build.path}")
        build.target.install(build.path, isQuiet=isQuiet)
        return cls(build)

    def __init__(self, build):
        self._build = build

    @property
    def build(self): return self._build

class Runner:

    @classmethod
    def fromInstall(cls, install, callback=lambda line: None, isSilent=False):
        callback(f"Run {install.build.path}")
        install.build.target.run(install.build.path, isSilent)
        return cls(install)

    def __init__(self, install):
        self._install = install

    @property
    def install(self): return self._install
