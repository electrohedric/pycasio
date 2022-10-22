import os.path
import sys
from . import compiler
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser("pycasio.compile", description="Compile a .py file into a .G1M file for casio",
                                     epilog="Note that casio inputs for name and password "
                                            "are limited to 8 characters and must be: "
                                            "A-Z 0-9 <space> . [ ] { } ' \" ~ + - * / r @")
    parser.add_argument("pyfile", action="store", help="python file to compile")
    parser.add_argument("-n", "--name", dest="name", action="store", default="",
                        help="name to give the casio program, 1-8 chars (defaults to pyfile)")
    parser.add_argument("-o", "--out", dest="out", action="store", default="",
                        help="Output file name, .G1M extension is added if needed (defaults to name)")
    parser.add_argument("-p", "--pass", dest="pswd", action="store", default="",
                        help="Password to lock source code with, 1-8 chars (default is no password)")
    args = parser.parse_args()
    in_file = args.pyfile
    if not os.path.exists(in_file):
        print(f"File {in_file} does not exist")
        exit()
    # either they gave us a name or we'll have to try to make a valid one with the file name
    name = args.name or args.pyfile.lower().removesuffix(".py").replace("_", "").upper()[:8]
    out = args.out or name
    # add .G1M to given out file if it doesn't have it
    # always add .G1M if they didn't give us an out file
    if not args.out or not out.upper().endswith(".G1M"):
        out += ".G1M"
    password = args.pswd
    context = compiler.compile_file(in_file)
    with open(out, 'wb') as f:
        f.write(context.export(name, password))
