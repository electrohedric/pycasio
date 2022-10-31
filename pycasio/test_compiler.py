import inspect
import os
import re
import sys
from functools import cache
from unittest import TestCase

from . import compiler
from . import exceptions as cex
from . import module_helper as mh
from .context import CasioType
from .bytecode import Bytecode


class TestCompiler(TestCase):
    pass


FIND_TEST_PATTERN = re.compile(r"^[ \t]*#.*@test[ \t]+([a-z0-9_-]+)[ \t]?(.*)", re.IGNORECASE)
FIND_BYTE_REPL = re.compile(r"\{([A-Z_]+)}")  # TODO: allow {,} escape


class TestLoader:
    def __init__(self, path: str):
        self.path = path
        self.filename = os.path.basename(path)
        with open(path) as f:
            self.source = f.read()
        self.tester: TestCase|None = None
        self.line_no = 0
        self.lines = self.source.splitlines()

    def generate_tests(self, cls: type):
        test_map = get_test_map()

        test_count = 0
        for line_num, line in enumerate(self.lines, start=1):
            match = FIND_TEST_PATTERN.match(line)
            if not match:
                continue

            method_name = match.group(1)
            # TODO: allow spaces in arguments when enclosed in "
            #       like ``@test symbol var "hello world"`` would not work properly
            args = match.group(2).strip().split()
            method_name = method_name.replace("-", "_")
            if method_name not in test_map:
                print(f"[Test Loader] Unknown test '{method_name}' in {self.filename}", file=sys.stderr)
                continue

            test_method = test_map[method_name]

            # intermediate values for the function capture
            this_line_num = line_num
            this_line = line

            def some_func(tester_self):
                # called as if this function is a member in the tester class (TestCompiler->self == tester_self)
                self.tester = tester_self
                self.line_no = this_line_num
                vargs = [parse_value(v) for v in args]
                try:
                    test_method(self, *vargs)  # some method in TestLoader beginning with "test_"
                except TypeError as e:
                    print(f"[Test Loader] TESTER ERROR:{self.msg()}", file=sys.stderr)
                    print(this_line, file=sys.stderr)
                    print(f"Method name: test_{method_name}, Args parsed: {vargs}", file=sys.stderr)
                    raise e

            # this is basically taken from https://stackoverflow.com/a/2799009
            # update class of interest with new test method
            some_func.__name__ = f"test_{self.filename}"
            setattr(cls, some_func.__name__, some_func)
            test_count += 1
        return test_count

    def msg(self):
        return f"\nTest File \"{self.path}\", line {self.line_no}"

    def compile(self):
        return compiler.compile_source(self.filename, self.source)

    def test_compiles(self):
        """ test that the file compiles and return the context if it does """
        try:
            return self.compile()
        except cex.CasioException:
            self.tester.fail(f"Test expected file to compile: {self.msg()}")
        except Exception as e:
            self.tester.fail(f"Test expected file to compile: {self.msg()}")
            raise e

    def test_err(self, ename):
        """ test that a certain error occured while compiling the file """
        if ename[0].islower():
            ename = ename[0].upper() + ename[1:]
        etype = f"Casio{ename}Error"
        if not hasattr(cex, etype):
            self.tester.fail(f"{self.msg()}\n{etype} does not exist")
            return
        ex = getattr(cex, etype)
        if not issubclass(ex, cex.CasioException):
            self.tester.fail(f"{self.msg()}\n{etype} is not a casio exception")
            return
        with self.tester.assertRaises(ex, msg=self.msg()):
            self.compile()

    def test_import(self, name, module_path):
        """ test that a certain symbol contains the module path """
        context = self.test_compiles()
        self.tester.assertIn(name, context.symbols, self.msg())
        import_sym = context.symbols[name].value
        self.tester.assertIsInstance(import_sym, mh.ModulePath, self.msg())
        self.tester.assertEqual(import_sym, module_path, self.msg())

    def _test_symbol(self, type_: CasioType, bytes_: bytes, name):
        context = self.test_compiles()
        self.tester.assertIn(name, context.symbols, self.msg())
        sym = context.symbols[name]
        self.tester.assertEqual(type_, sym.type, self.msg())
        self.tester.assertEqual(bytes_, sym.value, self.msg())

    def test_symbol_str(self, name, value):
        """ test that a symbol contains a string value """
        self._test_symbol(CasioType.STRING, b'"' + str(value).encode() + b'"', name)

    def test_symbol_num(self, name, value):
        """ test that a symbol contains a number value """
        self._test_symbol(CasioType.NUMBER, str(value).encode(), name)

    def test_symbol_expr(self, name, value):
        """ test that a symbol contains a number with specific bytecode """
        new_value = str(value).encode()
        for byte_repl in FIND_BYTE_REPL.finditer(value):
            match = byte_repl.group(0)
            text = byte_repl.group(1)
            if not hasattr(Bytecode, text):
                self.tester.fail(f"{self.msg()}\n{text} bytecode does not exist")
                return
            casio_bytes = getattr(Bytecode, text)
            if not isinstance(casio_bytes, bytes):
                self.tester.fail(f"{self.msg()}\n{text} is not valid bytecode")
                return
            new_value = new_value.replace(match.encode(), casio_bytes, 1)

        self._test_symbol(CasioType.NUMBER, new_value, name)

@cache
def get_test_map() -> dict[str, callable]:
    d = {}
    for name, member in inspect.getmembers(TestLoader):
        if inspect.isfunction(member) and name.startswith("test_"):
            d[name[5:]] = member  # remove test_
    return d


def parse_value(v: str):
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    # else str
    # always remove quotes
    if v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v


def load_compiler_tests():
    file_count = 0
    test_count = 0
    parent_dir = os.path.dirname(__file__)
    test_dir = os.path.join(parent_dir, "test_data")
    for dir_path, dir_names, file_names in os.walk(test_dir):
        for test_py in file_names:
            if not test_py.endswith(".py"):
                print(f"[Test Loader] Skipping non-py file '{test_py}'")
                continue

            test_file = os.path.join(dir_path, test_py)
            tester = TestLoader(test_file)  # cut off .py
            tests_generated = tester.generate_tests(TestCompiler)
            if tests_generated == 0:
                print(f"[Test Loader] No tests found in file {test_py}", file=sys.stderr)  # TODO: use logging
            else:
                file_count += 1
                test_count += tests_generated

    print(f"[Test Loader] Loaded {test_count} tests from {file_count} files")


load_compiler_tests()
