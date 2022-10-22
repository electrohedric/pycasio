import os.path
from . import compiler
from . import bytecode
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser("python -m pycasio.compile",
                                     description="Compile a .py file into a .G1M file for casio",
                                     epilog="Note that casio inputs for name and password "
                                            "are limited to 8 characters and must be: "
                                            "A-Z 0-9 <space> . [ ] { } ' \" ~ + - * /")
    parser.add_argument("pyfile", action="store", help="python file to compile")
    parser.add_argument("-n", "--name", dest="name", action="store", default="",
                        help="name to give the casio program, 1-8 chars (defaults to pyfile)")
    parser.add_argument("-o", "--out", dest="out", action="store", default="",
                        help="Output file name, .G1M extension is added if needed (defaults to name)")
    parser.add_argument("-p", "--pass", dest="pswd", action="store", default="",
                        help="Password to lock source code with, 1-8 chars (default is no password.) "
                             "Setting a password only prevents you from looking at the source code on the calculator "
                             "and is not recommended, as it makes debugging on the calculator near impossible.")
    args = parser.parse_args()
    in_file = args.pyfile
    if not os.path.exists(in_file):
        print(f"File {in_file} does not exist")
        exit(1)
    # either they gave us a name or we'll have to try to make a valid one with the file name
    # I'm taking r and theta out of the docs because it's confusing. everything will be uppercased by default
    name = args.name or os.path.basename(args.pyfile).lower().removesuffix(".py").replace("_", "")[:8]
    name = name.upper()
    if not bytecode.Header.verify_program_name(name):
        print(f"{name} is not a valid program name")
        exit(1)
    print(f"Program name is set to: {name}")
    password = args.pswd.upper()
    if not bytecode.Header.verify_password(password):
        print(f"{password} is not a valid password")
        exit(1)
    if password:
        print(f"Password is set to: {password}")
    out = args.out or name
    # add .G1M to given out file if it doesn't have it
    # always add .G1M if they didn't give us an out file
    if not args.out or not out.upper().endswith(".G1M"):
        out += ".G1M"
    print(f"Compiling {in_file}...")
    context = compiler.compile_file(in_file)
    print(f"Casio code is {len(context.code)} lines")
    with open(out, 'wb') as f:
        count = f.write(context.export(name, password))
    print(f"Wrote {count} bytes to {out}")
