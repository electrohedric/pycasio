import pycasio.compiler


context = pycasio.compiler.compile_file("super_basic.py")
print("="*100)
context.dump_ast()
print(context.symbols)
print("== EXE ==")
print(b"\n".join(context.code))
