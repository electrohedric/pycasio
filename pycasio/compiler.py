import ast
import os.path
from typing import Any

from . import module_helper as mh
from .exceptions import CasioImportException, CasioNameError
from .context import CasioContext

END_STATEMENT = b"\xc3\x99\r\n"  # ↵
ASSIGN = b"\xc3\xa3"  # ➔


def resolve_attr(attr: ast.Attribute) -> list[str]:
    if isinstance(attr.value, ast.Attribute):
        return resolve_attr(attr.value) + [attr.attr]
    elif isinstance(attr.value, ast.Name):
        return [attr.value.id, attr.attr]
    print("UNKNOWN SUB-ATTRIBUTE", attr.value)
    return []



class CasioNodeVisitor(ast.NodeVisitor):
    def __init__(self, context: CasioContext):
        self.ctx = context

    def visit_Import(self, node: ast.Import) -> Any:
        POSSIBLE_MODULES = mh.get_pycasio_modules()

        # import pycasio, pycasio.casio, abc
        for name in node.names:
            if name.name in POSSIBLE_MODULES:
                # import pycasio, pycasio.casio
                self.ctx.casio[name.asname or name.name] = mh.ModulePath(name.name)
            elif mh.PACKAGE.is_child(name.name):
                # import pycasio.invalid
                raise CasioImportException(self.ctx, name,
                                           f"{name.name} is not a {__package__} module",
                                           f"Possible modules: {list(sorted(str(x) for x in POSSIBLE_MODULES))}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        POSSIBLE_MODULES = mh.get_pycasio_modules()
        POSSIBLE_FUNCTIONS = mh.get_pycasio_functions()

        # could be literally any 'from' import
        mod = mh.ModulePath(node.module)
        if mod not in mh.PACKAGE:
            return  # completely ignore other packages

        # from pycasio.? import ?
        if mod not in POSSIBLE_MODULES:
            raise CasioImportException(self.ctx, node,
                                       f"{node.module} is not a valid {__package__} module",
                                       f"Possible modules: {list(sorted(str(x) for x in POSSIBLE_MODULES))}")

        # from pycasio import casio, invalid
        # from pycasio.casio import lib_name, invalid
        # from pycasio.casio.lib_name import func_name, invalid
        for name in node.names:
            full_name = mod + name.name

            if len(mod) <= 2:
                # from pycasio import casio, invalid
                # from pycasio.casio import lib_name, invalid
                if full_name not in POSSIBLE_MODULES:
                    # from pycasio import invalid
                    # from pycasio.casio import invalid
                    raise CasioImportException(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} module",
                                               f"Possible modules: {list(sorted(str(x) for x in mod.get_direct_children(POSSIBLE_MODULES)))}")
                # from pycasio import casio
                # from pycasio.casio import lib_name
            else:
                # from pycasio.casio.lib_name import func_name, invalid
                valid_func_names = POSSIBLE_FUNCTIONS[mod]

                if name.name not in valid_func_names:
                    # from pycasio.casio.lib_name import invalid
                    raise CasioImportException(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} function",
                                               f"Possible functions: {list(sorted(valid_func_names))}")
                # from pycasio.casio.lib_name import func_name

            self.ctx.casio[name.asname or name.name] = full_name

    def visit_Assign(self, node: ast.Assign) -> Any:
        left = node.targets
        right = node.value
        if isinstance(right, ast.Attribute):
            value = ".".join(resolve_attr(right))
            full_ref = self.ctx.lookup_casio_ref(value)
            if full_ref:
                # is a casio alias
                for left_sym in left:
                    if isinstance(left_sym, ast.Name):
                        self.ctx.casio[left_sym.id] = full_ref
            else:
                raise CasioImportException(self.ctx, right,
                                           f"{value} is not a valid casio reference")
        elif isinstance(right, ast.Name):
            value = right.id
            if value in self.ctx.symbols:
                pass  # TODO: blah
            else:
                raise CasioNameError(self.ctx, right,
                                     f"{value} is not defined")
        elif isinstance(right, ast.Call):
            pass


def compile_source(filename: str, src: str) -> CasioContext:
    """
    Compile source code using the filename as reference

    :param filename: name of file, used in exception output
    :param src: source code of said file
    """
    node = ast.parse(src)
    context = CasioContext(filename, src, node)
    vistor = CasioNodeVisitor(context)
    vistor.visit(node)
    return context


def compile_file(file: str) -> CasioContext:
    """
    Load and compile a file

    :param file: path to file
    """
    with open(file) as f:
        src = f.read()
    return compile_source(os.path.basename(file), src)
