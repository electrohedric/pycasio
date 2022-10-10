import os
from ast import *
import symtable
from typing import Any
from functools import cache
import pkgutil
import importlib.util
import inspect

__CASIO_PACKAGE_NAME__ = "casio"

END_STATEMENT = b"\xc3\x99\r\n"  # ↵
ASSIGN = b"\xc3\xa3"  # ➔


@cache
def get_pycasio_packages():
    casio_lib = f"{__package__}.{__CASIO_PACKAGE_NAME__}"
    casio_path = f"{__package__}/{__CASIO_PACKAGE_NAME__}"
    libs = {}

    for _, mod_name, is_pkg in pkgutil.iter_modules([casio_path]):
        assert not is_pkg, "only 1-level deep packages allowed"
        for lib in pkgutil.iter_modules([f"{casio_path}/{mod_name}"]):
            full_lib = f"{casio_lib}.{lib}"
            spec = importlib.util.find_spec(full_lib)
            loaded_mod = spec.loader.load_module(full_lib)
            libs[lib] = set()
            toplevel_filter = lambda x: not x.startswith("_") and (inspect.isfunction(x) or inspect.isclass(x))
            for name, _ in inspect.getmembers(loaded_mod, toplevel_filter):
                libs[lib].add(name)
    POSSIBLE_PACKAGES = {f"{casio_lib}.{x}" for x in LIBS}
    POSSIBLE_PACKAGES.add(__package__)
    POSSIBLE_PACKAGES.add(casio_lib)
    return POSSIBLE_PACKAGES


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
        POSSIBLE_PACKAGES = get_pycasio_packages()

        for name in node.names:
            if name.name in POSSIBLE_PACKAGES:
                self.ctx.casio[name.asname or name.name] = name.name
            elif name.name.startswith(f"{__package__}."):
                raise CasioImportException(self.ctx, name,
                                           f"{name.name} is not a {__package__} package",
                                           f"Possible packages: {POSSIBLE_PACKAGES}")

    def visit_ImportFrom(self, node: ImportFrom) -> Any:
        POSSIBLE_PACKAGES = get_pycasio_packages()

        if node.module in POSSIBLE_PACKAGES:
            for name in node.names:
                full_name = f"{node.module}.{name}"

                self.ctx.casio[name.asname or name.name] = ""

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
