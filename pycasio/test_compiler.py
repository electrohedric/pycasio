import inspect
import os
import re
import sys
from functools import cache
from unittest import TestCase

from . import compiler
from . import exceptions as cex


class TestCompiler(TestCase):
    pass


FIND_TEST_PATTERN = re.compile(r"^[ \t]*#.*@test[ \t]+([a-z0-9_. \t-]+)")

class TestLoader:
    def __init__(self, path: str):
        self.path = path
        self.filename = os.path.basename(path)
        with open(path) as f:
            self.source = f.read()
        self.tester: TestCase|None = None
        self.line_no = 0

    def generate_tests(self, cls: type):
        test_map = get_test_map()

        test_count = 0
        for line_num, line in enumerate(self.source.lower().splitlines(), start=1):
            match = FIND_TEST_PATTERN.match(line)
            if not match:
                continue

            method_name, *args = match.group(1).strip().split()
            if method_name not in test_map:
                print(f"[Test Loader] Unknown test '{method_name}' in {self.filename}", file=sys.stderr)
                continue

            test_method = test_map[method_name]
            def some_func(fake_self):
                self.tester = fake_self
                self.line_no = line_num
                test_method(self, *args)  # some method in this class beginning with "test_"

            # this is basically taken from https://stackoverflow.com/a/2799009
            # update class of interest with new test method
            some_func.__name__ = f"test_{self.filename}"
            setattr(cls, some_func.__name__, some_func)
            test_count += 1
        return test_count

    def msg(self):
        return f"Test File \"{self.path}\", line {self.line_no}"

    def compile(self):
        return compiler.compile_source(self.filename, self.source)

    def test_compiles(self):
        try:
            return self.compile()
        except cex.CasioException:
            self.tester.fail(f"Test expected file to compile: {self.msg()}")
        except Exception as e:
            self.tester.fail(f"Test expected file to compile: {self.msg()}")
            raise e

    def test_err_import(self):
        with self.tester.assertRaises(cex.CasioImportException, msg=self.msg()):
            self.compile()

    def test_import(self, name, module_path):
        context = self.test_compiles()
        self.tester.assertIn(name, context.symbols, self.msg())
        self.tester.assertEqual(context.symbols[name].value, module_path, self.msg())


@cache
def get_test_map() -> dict[str, callable]:
    d = {}
    for name, member in inspect.getmembers(TestLoader):
        if inspect.isfunction(member) and name.startswith("test_"):
            d[name[5:]] = member  # remove test_
    return d


def load_compiler_tests():
    file_count = 0
    test_count = 0
    parent_dir = os.path.dirname(__file__)
    test_dir = os.path.join(parent_dir, "test_data")
    for test_py in os.listdir(test_dir):
        if not test_py.endswith(".py"):
            print(f"[Test Loader] Skipping non-py file '{test_py}'")
            continue

        test_file = os.path.join(test_dir, test_py)
        tester = TestLoader(test_file)  # cut off .py
        tests_generated = tester.generate_tests(TestCompiler)
        if tests_generated == 0:
            print(f"[Test Loader] No tests found in file {test_py}", file=sys.stderr)  # TODO: use logging
        else:
            file_count += 1
            test_count += tests_generated

    print(f"[Test Loader] Loaded {test_count} tests from {file_count} files")


load_compiler_tests()
