import enum

from . import module_helper as mh
from .bytecode import Bytecode as B, Header
import ast


class CasioType(enum.Enum):
    NULL = "null"
    NUMBER = "num"
    STRING = "str"
    # LIST = "list"
    # MATRIX = "mat"


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


class Symbol:
    def __init__(self, name: str, value, var_type: CasioType):
        self.name = name  # actual name in the program
        self.value = value  # no idea
        self.type = var_type
        self.var: bytes|None = None  # casio var symbol

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if isinstance(other, Symbol):
            return self.name == other.name
        return False

    def __repr__(self):
        return f"Symbol{{{self.name} = {self.value} -> {self.var}}}"

    def __str__(self):
        return self.name


class SymbolTable(dict):
    def __init__(self):
        super().__init__()
        # X and Y are volatile because they get set automatically sometimes when doing graph operations
        # TODO: find out when and either avoid using those functions or report here that it's hopeless
        self.free_vars = {
            CasioType.NUMBER: [B.THETA, B.RADIUS] + [x.encode() for x in "ZWVUTSRQPONMLKJIHGFEDCBA"],
            CasioType.STRING: [B.STRING + str(x).encode() for x in range(1, 21)]
        }

    def get(self, __key: str) -> Symbol | None:
        return super().get(__key)

    def new(self, var_type: CasioType, name: str, value) -> Symbol:
        sym = Symbol(name, value, var_type)
        if var_type != CasioType.NULL:
            self.alloc(sym)
        self.add(sym)
        return sym

    def add(self, sym: Symbol):
        self[sym.name] = sym

    def alloc(self, sym: Symbol):
        assert sym.var is None, "double alloc!"
        assert sym.type != CasioType.NULL
        sym.var = self.free_vars[sym.type].pop()

    def free(self, sym: Symbol):
        if sym.var is not None:
            sym.var = self.free_vars[sym.type].append(sym.var)  # returns None


class CasioContext:
    def __init__(self, filename: str, source: str, ast_root: ast.AST):
        self.filename = filename
        self.source = source
        self.ast = ast_root
        self.symbols: SymbolTable[str, Symbol] = SymbolTable()
        self.code: list[bytes] = []

    def dump_ast(self):
        print(ast.dump(self.ast, indent=2))

    def lookup_casio_ref(self, symbol: str):
        mod = mh.ModulePath(symbol)
        # find the first matching prefix
        for i in range(len(mod)):
            mod_alias = mod[:i+1]
            if sym_ref := self.symbols.get(mod_alias):
                full_ref = sym_ref.value
                assert isinstance(full_ref, mh.ModulePath), f"symbol {symbol} = {full_ref} which is not a ModulePath"
                # fix alias with real path
                mod = full_ref + mod[i+1:]
                ref_type, ref = get_casio_ref_type(mod)
                if ref_type is not None:
                    return mod
                break
        # no reference to casio
        return None

    def export(self, program_name: str, password: str = "") -> bytes:
        """
        Export the program in a .G1M file as bytes.
        The filename doesn't matter, as long as the extension is **G1M**

        =============

        Input restrictions for program name and password:

        * A-Z
        * 0-9
        * <space> . [ ] { } ' " ~
        * "+" : + (plus)
        * "-" : - (minus)
        * "*" : × (multiplication)
        * "/" : ÷ (division)
        * "r" : r (radius)
        * "@" : θ (theta)
        =============

        :param program_name: name of the program the calculator will read. 1-8 chars. See input restrictions.
        :param password: password to edit the source code on the calculator. 0-8 chars. See input restrictions.
        :return: G1M file bytes
        """
        program = B.CARRIAGE.join(self.code)
        header = Header(len(program), program_name, password, base_mode=False)
        # program needs at least 1 null byte and also padded to 4-bytes
        null_bytes = header.pad_bytecount - header.actual_bytecount
        g1m = header.bytes + program + b"\x00" * null_bytes
        return g1m
