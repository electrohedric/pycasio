from . import module_helper as mh
import ast


def get_casio_ref_type(ref: mh.ModulePath):
    # just a plain old module reference
    POSSIBLE_MODULES = mh.get_pycasio_modules()
    if ref in POSSIBLE_MODULES:
        return "mod", ref

    # must be a function reference
    # this must be a valid function module
    POSSIBLE_FUNCTIONS = mh.get_pycasio_functions()
    lib = ref[:-1]
    if lib not in POSSIBLE_FUNCTIONS:
        return None, ''

    # the function must exist inside its function module
    functions = POSSIBLE_FUNCTIONS[lib]
    func = ref[-1]
    if func not in functions:
        return None
    return "func", (lib, func)


class CasioContext:
    def __init__(self, filename: str, source: str, ast_node: ast.AST):
        self.filename = filename
        self.source = source
        self.ast = ast_node
        self.casio: dict[str, mh.ModulePath] = {}  # casio package aliases
        self.symbols = {}
        self.lines = []

    def dump_ast(self):
        print(ast.dump(self.ast, indent=2))

    def lookup_casio_ref(self, symbol: str):
        mod = mh.ModulePath(symbol)
        for i in range(len(mod)):
            mod_alias = mod[:i+1]
            if mod_alias in self.casio:
                # fix alias with real path
                mod = self.casio[mod_alias] + mod[i+1:]
                ref_type, ref = get_casio_ref_type(mod)
                if ref_type is not None:
                    return mod
                break
        # no reference to casio
        return None