import importlib.util
import inspect
import pkgutil
from functools import cache
from typing import Iterable, Iterator

CASIO_PACKAGE_NAME = "casio"


class ModulePath:
    """
    Immutable and normalized path for a module:

    e.g. pycasio.casio.helpers.some_function

    Functionally equivalent to splitting dot paths into list paths and back.
    This class just wraps these operations and makes them transparent.

    - Provides addition operators to add a module to path (``a.b + c.d = a.b.c.d``)
    - Provides searching functions (startsWith, endsWith, contains)
    """

    def __init__(self, path: str|list[str] = None):
        """
        Initialize the module path with either a dot path or a list path

        e.g. "1.2.3" and ["1", "2", "3"] are equal

        :param path: path of the module to hold
        """
        self._path: list[str] = []
        self._cstr = None
        if isinstance(path, str):
            self._path = path.split(".")
        elif isinstance(path, list):
            for m in path:
                self._path.extend(m.split("."))

    @staticmethod
    def _norm(path: 'ModulePathType'):
        if isinstance(path, str) or isinstance(path, list):
            return ModulePath(path)
        return path

    def is_direct_child(self, child: 'ModulePathType'):
        child = ModulePath._norm(child)

        # if more or less, it can't be a direct descendant
        if len(self) + 1 != len(child):
            return False

        # everything up to the child must be the same
        return self[:-1] == child

    def is_child(self, child: 'ModulePathType'):
        child = ModulePath._norm(child)

        # it can't be a descendant
        if len(child) <= len(self):
            return False

        # everything in parent must exist in child
        return self == child[:len(self)]

    def get_direct_children(self, modules: Iterable['ModulePathType']) -> Iterator['ModulePath']:
        for module in modules:
            if self.is_direct_child(module):
                yield module

    def __contains__(self, item):
        item = ModulePath._norm(item)
        if isinstance(item, ModulePath):
            return self == item or self.is_child(item)
        return False

    def __len__(self):
        return len(self._path)

    def __lt__(self, other):
        return str(self) < str(other)

    def __add__(self, other):
        # self + other
        other = ModulePath._norm(other)
        if isinstance(other, ModulePath):
            return ModulePath(self._path + other._path)
        return NotImplemented

    def __radd__(self, other):
        # other + self
        other = ModulePath._norm(other)
        if isinstance(other, ModulePath):
            return ModulePath(other._path + self._path)
        return NotImplemented

    def __getitem__(self, item):
        # self[1:5] or self[0]
        # bypass nested checking for lists by setting path directly
        return ModulePath(self._path[item])

    def __str__(self):
        if self._cstr is None:
            self._cstr = ".".join(self._path)
        return self._cstr

    def __repr__(self):
        return f"ModulePath{{{self}}}"

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

ModulePathType = str|list[str]|ModulePath

PACKAGE: ModulePath = ModulePath(__package__)
CASIO_LIB: ModulePath = PACKAGE + CASIO_PACKAGE_NAME


@cache
def get_pycasio_functions() -> dict[ModulePath, set[str]]:
    casio_path = str(CASIO_LIB).replace(".", "/")
    libs = {}

    for _, mod_name, is_pkg in pkgutil.iter_modules([casio_path]):
        assert not is_pkg, "only 1-level deep packages implemented"
        full_lib = CASIO_LIB + mod_name
        spec = importlib.util.find_spec(str(full_lib))
        loaded_mod = importlib.util.module_from_spec(spec)
        libs[full_lib] = set()
        for name, member in inspect.getmembers(loaded_mod):
            if name.startswith("_"):
                continue
            if inspect.isfunction(member) or inspect.isclass(member):
                libs[full_lib].add(name)
    return libs


@cache
def get_pycasio_modules() -> set[ModulePath]:
    POSSIBLE_PACKAGES = {*get_pycasio_functions()}
    POSSIBLE_PACKAGES.add(PACKAGE)
    POSSIBLE_PACKAGES.add(CASIO_LIB)
    return POSSIBLE_PACKAGES

