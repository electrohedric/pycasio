import os

import pycasio.compiler


# pycasio.compiler.DEBUG = True
context = pycasio.compiler.compile_file("super_basic.py")
print("="*100)
context.dump_ast()
print(context.symbols)
print("== EXE ==")
for line in context.code:
    print(line)

if not os.path.exists("bin"):
    os.mkdir("bin")

with open("bin/superbasic.G1M",'wb') as f:
    f.write(context.export("BASIC"))
