from unittest import TestCase
from . import compiler
from .exceptions import CasioImportException
import os
from functools import cache
import inspect
import re


class TestCompiler(TestCase):
    pass


FIND_TEST_PATTERN = re.compile(r"#.*@test\s+([a-z0-9_\s-]+)")

class AbstractTest:
    def __init__(self, path: str, test_name: str):
        self.filename = os.path.basename(path)
        with open(path) as f:
            self.source = f.read()
        self.test_name = test_name
        self.tester: TestCase = None

    def generate_tests(self, cls: type):
        test_map = get_test_map()

        test_count = 0
        for match in FIND_TEST_PATTERN.finditer(self.source.lower()):
            method_name, *args = match.group(1).strip().split()
            if method_name not in test_map:
                print(f"[Test Loader] Unknown test '{method_name}' in {self.filename}")
                continue
            test_method = test_map[method_name]
            def some_func(fake_self):
                self.tester = fake_self
                test_method(self)

            # this is basically taken from https://stackoverflow.com/a/2799009
            # update class of interest with new test method
            some_func.__name__ = f"test_{method_name}"
            setattr(cls, some_func.__name__, some_func)
            test_count += 1
        return test_count

    def compile(self):
        compiler.compile_source(self.source)

    def test_compiles(self):
        self.compile()

    def test_ex_import(self):
        self.tester.assertRaises(CasioImportException, self.compile)


@cache
def get_test_map() -> dict[str, callable]:
    d = {}
    for name, member in inspect.getmembers(AbstractTest):
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
        tester = AbstractTest(test_file, f"test_compiler_{test_py[:-3]}")  # cut off .py
        tests_generated = tester.generate_tests(TestCompiler)
        if tests_generated == 0:
            print(f"[Test Loader] No tests found in file {test_py}")
        else:
            file_count += 1
            test_count += tests_generated

    print(f"[Test Loader] Loaded {test_count} tests from {file_count} files")


load_compiler_tests()
