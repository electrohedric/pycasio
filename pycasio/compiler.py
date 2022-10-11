from ast import *
import symtable
from typing import Any
from functools import cache
import pkgutil
import importlib.util
import inspect

__CASIO_PACKAGE_NAME__ = "casio"
__CASIO_LIB__ = f"{__package__}.{__CASIO_PACKAGE_NAME__}"

END_STATEMENT = b"\xc3\x99\r\n"  # ↵
ASSIGN = b"\xc3\xa3"  # ➔


@cache
def get_pycasio_functions():
    casio_path = __CASIO_LIB__.replace(".", "/")
    libs = {}

    for _, mod_name, is_pkg in pkgutil.iter_modules([casio_path]):
        assert not is_pkg, "only 1-level deep packages implemented"
        full_lib = f"{__CASIO_LIB__}.{mod_name}"
        spec = importlib.util.find_spec(full_lib)
        loaded_mod = spec.loader.load_module(full_lib)
        libs[mod_name] = set()
        for name, member in inspect.getmembers(loaded_mod):
            if name.startswith("_"):
                continue
            if inspect.isfunction(member) or inspect.isclass(member):
                libs[mod_name].add(name)
    return libs


@cache
def get_pycasio_modules():
    POSSIBLE_PACKAGES = {f"{__CASIO_LIB__}.{x}" for x in get_pycasio_functions()}
    POSSIBLE_PACKAGES.add(__package__)
    POSSIBLE_PACKAGES.add(__CASIO_LIB__)
    return POSSIBLE_PACKAGES


def get_children(modules, parent):
    parents = parent.split(".")
    for module in modules:
        children = module.split(".")
        if len(children) - 1 != len(parents):
            continue  # not a direct child
        for i in range(len(parents)):
            if parents[i] != children[i]:
                break
        else:
            # loop never broke, true child
            yield children[-1]


class CasioContext:
    def __init__(self, source, table: symtable.SymbolTable):
        self.source = source
        self.symtable = table
        self.casio = {}  # casio package aliases
        self.lines = []


class CasioException(Exception):
    def __init__(self, ctx: CasioContext, lineinfo: Any, msg: str, helptxt: str = None):
        lines = ctx.source.splitlines()
        print(lines)
        self.line = "<Invalid lineno>"
        self.col_offset = self.end_col_offset = -1
        if hasattr(lineinfo, "lineno"):
            self.lineno = lineinfo.lineno
            if len(lines) >= self.lineno:
                self.line = lines[self.lineno - 1]
            if hasattr(lineinfo, "col_offset"):
                self.col_offset = lineinfo.col_offset
                if hasattr(lineinfo, "end_col_offset"):
                    self.end_col_offset = lineinfo.end_col_offset
                else:
                    self.end_col_offset = len(self.line)
        self.msg = msg
        self.helptxt = f"\nHelp:\n{helptxt}" if helptxt else ""

    def __str__(self):
        HEADER = f"{'=' * 20} CASIO COMPILER {'=' * 20}"
        linespan = ''
        if self.end_col_offset != -1:
            span = max(self.end_col_offset - self.col_offset, 0)
            linespan = f"\n{' ' * self.col_offset}^{'~' * span}"
        return f"\n{HEADER}\nLine {self.lineno}:\n{self.line}{linespan}\nError: {self.msg}{self.helptxt}"


class CasioImportException(CasioException):
    pass


class CasioNodeVisitor(NodeVisitor):
    def __init__(self, context: CasioContext):
        self.ctx = context

    def visit_Import(self, node: Import) -> Any:
        POSSIBLE_MODULES = get_pycasio_modules()

        for name in node.names:
            if name.name in POSSIBLE_MODULES:
                self.ctx.casio[name.asname or name.name] = name.name
            elif name.name.startswith(f"{__package__}."):
                raise CasioImportException(self.ctx, name,
                                           f"{name.name} is not a {__package__} module",
                                           f"Possible modules: {list(sorted(POSSIBLE_MODULES))}")

    def visit_ImportFrom(self, node: ImportFrom) -> Any:
        POSSIBLE_MODULES = get_pycasio_modules()
        POSSIBLE_FUNCTIONS = get_pycasio_functions()

        # could be literally any 'from' import
        modules = node.module.split(".")
        if modules[0] != __package__:
            return  # completely ignore other packages

        # from pycasio.? import ?
        if node.module not in POSSIBLE_MODULES:
            raise CasioImportException(self.ctx, node,
                                       f"{node.module} is not a valid {__package__} module",
                                       f"Possible modules: {list(sorted(POSSIBLE_MODULES))}")

        # from pycasio import casio, invalid
        # from pycasio.casio import lib_name, invalid
        # from pycasio.casio.lib_name import func_name, invalid
        for name in node.names:
            full_name = f"{node.module}.{name.name}"

            if len(modules) <= 2:
                # from pycasio import casio, invalid
                # from pycasio.casio import lib_name, invalid
                if full_name not in POSSIBLE_MODULES:
                    # from pycasio import invalid
                    # from pycasio.casio import invalid
                    raise CasioImportException(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} module",
                                               f"Possible modules: {list(sorted(get_children(POSSIBLE_MODULES, node.module)))}")
                # from pycasio import casio
                # from pycasio.casio import lib_name
            else:
                # from pycasio.casio.lib_name import func_name, invalid
                lib_name = '.'.join(modules[2:])
                valid_func_names = POSSIBLE_FUNCTIONS[lib_name]

                if name.name not in valid_func_names:
                    # from pycasio.casio.lib_name import invalid
                    raise CasioImportException(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} function",
                                               f"Possible functions: {list(sorted(valid_func_names))}")
                # from pycasio.casio.lib_name import func_name

            self.ctx.casio[name.asname or name.name] = full_name

    def visit_Assign(self, node: Assign) -> Any:
        pass


def compile_file(file: str):
    with open(file) as f:
        src = f.read()

    node = parse(src)
    table = symtable.symtable(src, file, "exec")
    print(dump(node, indent=2))
    context = CasioContext(src, table)
    vistor = CasioNodeVisitor(context)
    vistor.visit(node)
    print(context.casio)
