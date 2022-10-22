import ast
import os.path
from typing import Any

from . import module_helper as mh
from .exceptions import *
from .bytecode import Bytecode as B
from .context import CasioContext


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

    def check_eval(self, node: ast.expr):
        # evaluate the value of the node by executing visit_<NodeType>
        node_eval = self.visit(node)
        if node_eval is None:
            # TODO: convert to assert. more of a check for me since unknown visit calls will return None
            # but for now the exact location printout is very nice
            raise CasioAssignmentError(self.ctx, node,
                                       f"Right side of assignment ({type(node).__name__}) evaluates to NULL")
        return node_eval

    def visit_Import(self, node: ast.Import) -> Any:
        POSSIBLE_MODULES = mh.get_pycasio_modules()

        # import pycasio, pycasio.casio, abc
        for name in node.names:
            if name.name in POSSIBLE_MODULES:
                # import pycasio, pycasio.casio
                self.ctx.symbols[name.asname or name.name] = mh.ModulePath(name.name)
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

            self.ctx.symbols[name.asname or name.name] = full_name

    def visit_Name(self, node: ast.Name) -> Any:
        # variable_name
        print("NAME!")
        value = node.id
        if value in self.ctx.symbols:
            pass  # TODO: blah
        else:
            raise CasioNameError(self.ctx, node,
                                 f"{value} is not defined")

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        # module.path.attribute
        value = ".".join(resolve_attr(node))
        full_ref = self.ctx.lookup_casio_ref(value)
        if full_ref:
            # is a casio alias
            return full_ref
        else:
            raise CasioImportException(self.ctx, node,
                                       f"{value} is not a valid casio reference")

    def visit_Call(self, node: ast.Call) -> Any:
        # module.func() aka some special casio function
        pass

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node, str):
            return b'"' + str(node.value).encode() + b'"'
        else:  # a number
            # python's floating point max is around 1.7e308. casio's is this
            CASIO_MAX = 9.999999999e99
            node.value = min(max(node.value, -CASIO_MAX), CASIO_MAX)
            return str(node.value).encode().replace(b"e", B.EXP)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left, op, right = node.left, node.op, node.right
        left_eval = self.check_eval(left)
        right_eval = self.check_eval(right)

        def simple_bin(operator: bytes):
            return left_eval + operator + right_eval

        if isinstance(op, ast.Mult):
            return simple_bin(B.MULTIPLY)
        elif isinstance(op, ast.Add):
            return simple_bin(B.ADD)
        elif isinstance(op, ast.Sub):
            return simple_bin(B.SUBTRACT)
        elif isinstance(op, ast.Div):
            return simple_bin(B.DIVIDE)
        elif isinstance(op, ast.Eq):
            return simple_bin(b"=")
        elif isinstance(op, ast.NotEq):
            return simple_bin(B.NOT_EQUAL)
        elif isinstance(op, ast.And):
            return simple_bin(B.AND)
        elif isinstance(op, ast.Or):
            return simple_bin(B.OR)
        elif isinstance(op, ast.BitXor):
            return simple_bin(B.XOR)
        elif isinstance(op, ast.Pow):
            return simple_bin(B.POWER)
        elif isinstance(op, ast.FloorDiv):
            return B.FLOOR + b"(" + simple_bin(B.DIVIDE) + b")"
        # TODO: and more
        pass

    def visit_Assign(self, node: ast.Assign) -> Any:
        left = node.targets
        right = node.value
        right_eval = self.check_eval(right)
        for left_sym in left:
            if isinstance(left_sym, ast.Name):
                self.ctx.symbols[left_sym.id] = right_eval
                self.ctx.code.append(right_eval + B.ASSIGN + b"X")
            else:
                raise CasioAssignmentError(self.ctx, left_sym,
                                           "Can't assign to this symbol")


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
