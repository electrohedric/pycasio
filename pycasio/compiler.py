import ast
import os.path
import warnings
from typing import Any
from enum import IntFlag

from . import module_helper as mh
from .exceptions import *
from .bytecode import Bytecode as B
from .context import CasioContext, CasioType, CompilerFlags


def resolve_attr(attr: ast.Attribute) -> list[str]:
    if isinstance(attr.value, ast.Attribute):
        return resolve_attr(attr.value) + [attr.attr]
    elif isinstance(attr.value, ast.Name):
        return [attr.value.id, attr.attr]
    print("UNKNOWN SUB-ATTRIBUTE", attr.value)
    return []


def get_type(o):
    t = type(o)
    if t is float or t is int or t is complex:
        return CasioType.NUMBER
    elif t is str:
        return CasioType.STRING
    return CasioType.NULL


def node_between(left: SupportsAST, right: SupportsAST) -> SupportsAST:
    sa = ast.AST()
    sa.lineno = left.lineno
    sa.col_offset = left.end_col_offset
    sa.end_col_offset = right.col_offset
    return sa

class CodeFlags(IntFlag):
    NONE = 0
    PREVENT_EXPRESSION =    0b00001
    PREVENT_ASSIGNMENT =    0b00010
    PREVENT_ARGUMENT =      0b00100
    HAS_SIDE_EFFECTS =      0b01000
    IS_BOOLEAN =            0b10000

    def debug_msg(self):
        can_expr = not (self & CodeFlags.PREVENT_EXPRESSION)
        can_assign = not (self & CodeFlags.PREVENT_ASSIGNMENT)
        can_arg = not (self & CodeFlags.PREVENT_ARGUMENT)

        # common combinations and their meanings
        if can_expr and not can_assign and not can_arg:
            return "This expression must be used like a statement"
        if not can_expr and can_assign and not can_arg:
            return "This expression must be used in an assignment"
        return ""


class Code:
    def __init__(self, raw_code: bytes, expr_type: CasioType, flags=CodeFlags.NONE):
        self.bytes = raw_code
        self.type = expr_type
        self.flags = flags
        if self.type == CasioType.NULL:
            self.flags |= CodeFlags.PREVENT_ASSIGNMENT | CodeFlags.PREVENT_ARGUMENT


class CasioNodeVisitor(ast.NodeVisitor):
    # some attributes do not directly translate to casio code
    # so the convention is as follows:
    # if a node translates to a line of code, it will append casio bytes to the context's lines
    # if a node does not translate to a line of code, it will return a special object
    # if a node translates to code (but not a line,) it will return casio bytes and set last_eval_type

    def __init__(self, context: CasioContext):
        self.ctx = context

    def warning(self, w):
        if self.ctx.flags & CompilerFlags.IGNORE_WARNINGS:
            return
        warnings.warn(w)

    def check_eval(self, node) -> Code:
        # evaluate the value of the node by executing visit_<NodeType>
        node_eval = self.visit(node)
        if not isinstance(node_eval, Code):
            # TODO: convert to assert. more of a check for me since unknown visit calls will return None
            # but for now the exact location printout is very nice
            raise CasioAssignmentError(self.ctx, node,
                                       f"{type(node).__name__} produced {type(node_eval).__name__} which is NOT Code")
        return node_eval

    def visit_Import(self, node: ast.Import) -> None:
        POSSIBLE_MODULES = mh.get_pycasio_modules()

        # import pycasio, pycasio.casio, abc
        for name in node.names:
            if name.name in POSSIBLE_MODULES:
                # import pycasio, pycasio.casio
                self.ctx.symbols.new(CasioType.NULL, name.asname or name.name, mh.ModulePath(name.name))
            elif mh.PACKAGE.is_child(name.name):
                # import pycasio.invalid
                raise CasioImportError(self.ctx, name,
                                           f"{name.name} is not a {__package__} module",
                                           f"Possible modules: {list(sorted(str(x) for x in POSSIBLE_MODULES))}")

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        POSSIBLE_MODULES = mh.get_pycasio_modules()
        POSSIBLE_FUNCTIONS = mh.get_pycasio_functions()

        # could be literally any 'from' import
        mod = mh.ModulePath(node.module)
        if mod not in mh.PACKAGE:
            return  # completely ignore other packages

        # from pycasio.? import ?
        if mod not in POSSIBLE_MODULES:
            raise CasioImportError(self.ctx, node,
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
                    children = mod.get_direct_children(POSSIBLE_MODULES)
                    raise CasioImportError(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} module",
                                               f"Possible modules: {list(sorted(str(x) for x in children))}")
                # from pycasio import casio
                # from pycasio.casio import lib_name
            else:
                # from pycasio.casio.lib_name import func_name, invalid
                valid_func_names = POSSIBLE_FUNCTIONS[mod]

                if name.name not in valid_func_names:
                    # from pycasio.casio.lib_name import invalid
                    raise CasioImportError(self.ctx, name,
                                               f"{name.name} is not a valid {node.module} function",
                                               f"Possible functions: {list(sorted(valid_func_names))}")
                # from pycasio.casio.lib_name import func_name

            self.ctx.symbols.new(CasioType.NULL, name.asname or name.name, full_name)

    def visit_Name(self, node: ast.Name) -> Code:
        # variable_name
        name = node.id
        if sym := self.ctx.symbols.get(name):
            return Code(sym.var, sym.type)
        else:
            raise CasioNameError(self.ctx, node,
                                 f"{name} is not defined")

    def visit_Attribute(self, node: ast.Attribute) -> mh.ModulePath:
        # module.path.attribute
        value = ".".join(resolve_attr(node))
        full_ref = self.ctx.lookup_casio_ref(value)
        if full_ref:
            # is a casio alias
            return full_ref
        else:
            raise CasioImportError(self.ctx, node,
                                       f"{value} is not a valid casio reference")

    def visit_Expr(self, node: ast.Expr) -> Any:
        # code that is not an assignment or control flow
        # ex + pr
        # print()
        # module.func()
        exp = node.value
        exp_eval = self.check_eval(exp)
        if isinstance(exp, ast.Call):
            if exp_eval.flags & CodeFlags.PREVENT_EXPRESSION:
                raise CasioOperationError(self.ctx, exp, f"This call cannot be used as a statement",
                                          helptxt=exp_eval.flags.debug_msg())
            if exp_eval.flags & CodeFlags.HAS_SIDE_EFFECTS:
                self.ctx.code.append(exp_eval.bytes)
            else:
                self.warning(CasioNoStatementWarning(self.ctx, node,
                                                     "Call has no side effects and will not be included"))
        else:
            self.warning(CasioNoStatementWarning(self.ctx, node,
                                                 "Statement has no effect and will not be included"))
        return exp_eval

    def visit_Call(self, node: ast.Call) -> Code:
        # print()
        # module.func() aka some special casio function
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        else:
            raise CasioNotImplementedException(self.ctx, node, "Dynamic function naming is not supported")

        def check_args(count):
            if len(node.args) > count:
                raise CasioOperationError(self.ctx, node,
                                          f"Too many arguments for {func_name} call, "
                                          f"expected {count}, got {len(node.args)}")

        last_arg: SupportsAST|None = None
        last_code: Code|None = None

        def check_type(expected):
            if last_code.type != expected:
                raise CasioTypeError(self.ctx, last_arg, f"{func_name} expects {expected}, not {last_code.type}")

        def eval_arg(i) -> Code:
            nonlocal last_arg, last_code
            if len(node.args) <= i:
                raise CasioOperationError(self.ctx, node,
                                          f"Not enough arguments for {func_name} call, expected arg {i}")
            arg = node.args[i]
            last_arg = arg
            last_code = self.check_eval(arg)
            if last_code.type == CasioType.NULL:
                raise CasioTypeError(self.ctx, arg, f"This expression does not return a value",
                                     helptxt=last_code.flags.debug_msg())
            if last_code.flags & CodeFlags.PREVENT_ARGUMENT:
                raise CasioOperationError(self.ctx, arg, f"This expression cannot be used as an argument",
                                          helptxt=last_code.flags.debug_msg())
            return last_code

        # check supported built-in functions first, everything else is unsupported
        if func_name == "abs":
            check_args(1)
            n = eval_arg(0)
            check_type(CasioType.NUMBER)
            return Code(B.ABSOLUTE + b"(" + n.bytes + b")", CasioType.NUMBER)
        elif func_name == "complex":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "input":
            check_args(1)
            if len(node.args) == 0:
                r = b"?"
            else:  # 1
                s = eval_arg(0)
                check_type(CasioType.STRING)
                r = s.bytes + b"?"
            return Code(r, CasioType.STRING,
                        CodeFlags.PREVENT_ARGUMENT | CodeFlags.PREVENT_EXPRESSION | CodeFlags.HAS_SIDE_EFFECTS)
        elif func_name == "int":
            check_args(1)
            n = eval_arg(0)
            check_type(CasioType.NUMBER)
            return Code(B.INT + b"(" + n + b")", CasioType.NUMBER)
        elif func_name == "bool":
            check_args(1)
            n = eval_arg(0)
            check_type(CasioType.NUMBER)
            # python needs operands specifically turned into bools to do xor properly but not casio
            return Code(n.bytes, n.type, CodeFlags.IS_BOOLEAN)
        elif func_name == "len":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "list":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "max":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "min":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "print":
            if len(node.args) == 0:
                # skip empty prints
                return Code(b"", CasioType.NULL, CodeFlags.HAS_SIDE_EFFECTS)
            elif len(node.args) == 1:
                u = eval_arg(0)
                return Code(u.bytes + B.DISP, CasioType.NULL, CodeFlags.HAS_SIDE_EFFECTS)
        elif func_name == "range":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "round":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        elif func_name == "sum":
            raise CasioNotImplementedException(self.ctx, node, f"{func_name} not implemented yet")
        else:
            raise CasioNotSupportedError(self.ctx, node, f"{func_name} built-in function is not supported",
                                         "The most likely reason is that this function is too complex. "
                                         "Try checking the casio library for similar functions.")

        # raise CasioNotImplementedException(self.ctx, node, "Call not supported yet")

    def visit_Constant(self, node: ast.Constant) -> Code:
        if isinstance(node.value, str):
            return Code(b'"' + str(node.value).encode() + b'"', CasioType.STRING)
        elif isinstance(node.value, int) or isinstance(node.value, float):  # a number
            # python's floating point max is around 1.7e308. casio's is this
            CASIO_MAX = 9.999999999e99
            node.value = min(max(node.value, -CASIO_MAX), CASIO_MAX)
            return Code(str(node.value).encode().replace(b"e", B.EXP), CasioType.NUMBER)
        else:
            raise CasioNotSupportedError(self.ctx, node, f"{type(node.value).__name__} type not supported")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Code:
        expr, op = node.operand, node.op
        expr_eval = self.check_eval(expr)
        if expr_eval.type != CasioType.NUMBER:
            raise CasioTypeError(self.ctx, node, "Unary operations only supported with numbers")

        if isinstance(op, ast.USub):  # negative sign
            return Code(B.NEGATIVE + expr_eval.bytes, expr_eval.type, expr_eval.flags)
        elif isinstance(op, ast.UAdd):  # positive sign
            return expr_eval  # nothing needs to be changed
        elif isinstance(op, ast.Not):
            return Code(B.NOT + expr_eval.bytes, expr_eval.type, CodeFlags.IS_BOOLEAN)
        # TODO: and more
        raise CasioNotSupportedError(self.ctx, op, "This operation is not supported by Casio",
                                     helptxt="Bitwise operators are unsupported")

    def visit_BinOp(self, node: ast.BinOp) -> Code:
        left, op, right = node.left, node.op, node.right
        left_eval = self.check_eval(left)
        right_eval = self.check_eval(right)
        if left_eval.type != right_eval.type:
            raise CasioTypeError(self.ctx, node,
                                 f"Types are not compatible: {left_eval.type} and {right_eval.type}")
        if left_eval.type != CasioType.NUMBER:
            # TODO: implement string ops too
            raise CasioTypeError(self.ctx, node, "Binary operations only supported with numbers")
        flags = left_eval.flags & right_eval.flags

        def simple_bin(operator: bytes):
            # TODO: don't need to add parenthesis if the prescendance of the outside operator
            #       is less than or equal to our operator
            return Code(b"(" + left_eval.bytes + operator + right_eval.bytes + b")", left_eval.type, flags)

        if isinstance(op, ast.Mult):
            return simple_bin(B.MULTIPLY)
        elif isinstance(op, ast.Add):
            return simple_bin(B.ADD)
        elif isinstance(op, ast.Sub):
            return simple_bin(B.SUBTRACT)
        elif isinstance(op, ast.Div):
            return simple_bin(B.DIVIDE)
        elif isinstance(op, ast.Pow):
            return simple_bin(B.POWER)
        elif isinstance(op, ast.Mod):
            return Code(B.MOD + left_eval.bytes + b"," + right_eval.bytes + b")", CasioType.NUMBER, flags)
        elif isinstance(op, ast.FloorDiv):
            return Code(B.FLOOR + b"(" + left_eval.bytes + B.DIVIDE + right_eval.bytes + b")", CasioType.NUMBER, flags)
        elif isinstance(op, ast.BitXor):
            if flags & CodeFlags.IS_BOOLEAN:
                return simple_bin(B.XOR)
            raise CasioNotSupportedError(self.ctx, node_between(left, right), "Bitwise XOR is not supported by Casio",
                                         helptxt="You can wrap each operand in bool() to use logical XOR instead")
        # TODO: and more?
        raise CasioNotSupportedError(self.ctx, node_between(left, right),
                                     f"{op} binary operation is not supported by Casio")

    def visit_Compare(self, node: ast.Compare) -> Any:
        ops = (*node.ops, None)
        comparators = (node.left, *node.comparators, None)
        code_bytes = b"("
        # zip operation uses shortest tuple: limited by ops
        for left, op, right in zip(comparators, ops, comparators[1:]):  # type: ast.expr, ast.operator, ast.expr
            # first add the bytes for the left side
            left_eval = self.check_eval(left)
            if left_eval.type != CasioType.NUMBER:
                # TODO: support comparison between strings
                raise CasioTypeError(self.ctx, node, f"Comparison must be between numbers, not {left_eval.type}")
            code_bytes += left_eval.bytes

            # no op means end
            if op is None:
                break

            # then add the bytes for the operator
            if isinstance(op, ast.Eq):
                code_bytes += b"="
            elif isinstance(op, ast.Lt):
                code_bytes += b"<"
            elif isinstance(op, ast.Gt):
                code_bytes += b">"
            elif isinstance(op, ast.LtE):
                code_bytes += B.LT_EQUAL
            elif isinstance(op, ast.GtE):
                code_bytes += B.GT_EQUAL
            elif isinstance(op, ast.NotEq):
                code_bytes += B.NOT_EQUAL
            else:
                raise CasioNotSupportedError(self.ctx, node_between(left, right),
                                             f"{op} comparison operator is not supported by Casio")
        code_bytes += b")"
        return Code(code_bytes, CasioType.NUMBER, CodeFlags.IS_BOOLEAN)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        op = node.op
        eval_values = []

        for value in node.values:
            eval_value = self.check_eval(value)
            if eval_value.type != CasioType.NUMBER:
                raise CasioTypeError(self.ctx, value,
                                     f"Boolean operator must be between numbers, not {eval_value.type}")
            eval_values.append(eval_value)

        def bool_op(operator: bytes):
            return Code(b"(" + operator.join([v.bytes for v in eval_values]) + b")",
                        CasioType.NUMBER, CodeFlags.IS_BOOLEAN)

        if isinstance(op, ast.And):
            return bool_op(B.AND)
        elif isinstance(op, ast.Or):
            return bool_op(B.OR)
        raise CasioNotSupportedError(self.ctx, node_between(node.values[0], node.values[1]),
                                     f"{op} boolean operation is not supported by Casio")

    def visit_Assign(self, node: ast.Assign) -> None:
        left = node.targets
        right = node.value  # type: ast.AST|ast.expr
        right_eval = self.visit(right)
        for left_sym in left:
            if isinstance(left_sym, ast.Name):
                if isinstance(right_eval, Code):
                    if right_eval.type == CasioType.NULL:
                        raise CasioTypeError(self.ctx, right, "This expression does not return a value",
                                             helptxt=right_eval.flags.debug_msg())
                    if right_eval.flags & CodeFlags.PREVENT_ASSIGNMENT:
                        raise CasioOperationError(self.ctx, right, "This expression cannot be used in an assignment",
                                                  helptxt=right_eval.flags.debug_msg())
                    sym = self.ctx.symbols.new(right_eval.type, left_sym.id, right_eval.bytes)
                    # only add code if it makes sense
                    # it's allowed for the programmer to make assignments to things that aren't relevant to casio
                    # such as modules, or references to matrices
                    self.ctx.code.append(right_eval.bytes + B.ASSIGN + sym.var)
                elif isinstance(right_eval, mh.ModulePath):
                    self.ctx.symbols.new(CasioType.NULL, left_sym.id, right_eval)
                else:
                    raise CasioAssignmentError(self.ctx, right,
                                               f"Can't assign to this expression "
                                               f"(couldn't parse {right.__class__.__name__})")
            else:
                raise CasioAssignmentError(self.ctx, left_sym, "Can't assign to this symbol")


DEBUG = False


def compile_source(filename: str, src: str) -> CasioContext:
    """
    Compile source code using the filename as reference

    :param filename: name of file, used in exception output
    :param src: source code of said file
    """
    node = ast.parse(src)
    if DEBUG:
        print(ast.dump(node, indent=2))
    context = CasioContext(filename, src, node)
    visitor = CasioNodeVisitor(context)
    visitor.visit(node)
    return context


def compile_file(file: str) -> CasioContext:
    """
    Load and compile a file

    :param file: path to file
    """
    with open(file) as f:
        src = f.read()
    return compile_source(os.path.basename(file), src)
