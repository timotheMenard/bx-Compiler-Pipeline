import sys
import getopt

from json_to_stat import *
from parser import Parser


"""
.
The bx2front function takes source code and an optional filename and performs the following steps:

It creates a Parser object and calls its parse() method to transform the source code into an Abstract Syntax Tree (AST).
It analyzes the top-level declarations (functions and global variables):

Function Declarations Check:
Verifies there are no duplicate function declarations
Checks if a main() function exists and is of type void
Records function signatures (return type, line number, parameter types) in the global scope

Global Variable Declarations Check:
Verifies there are no duplicate global variable declarations
Validates that global int variables are initialised with number literals
Validates that global bool variables are initialised with boolean literals
Records variable types and line numbers in the global scope

Type Checking: Calls type_check() on each function declaration, which recursively type-checks statements and expressions within the function body.
Scope Management: At the end, it pops the current scope and creates a new empty scope.

Has error handling
"""


def bx2front(code, filename=""):
    main_found = False
    parser = Parser(code, filename)

    instructions = parser.parse()
    for instruction in instructions:
        if isinstance(instruction, ProcDec):
            if instruction.name in scopes[0]:
                print(f'File "{filename}", line {instruction.lineno}')
                print('Error: Redecalred procedure "{instruction.name}" within the scope'.format(instruction.name))
                print(f':line {scopes[0][instruction.name][1]}:Info:Declartion of "{instruction.name}"')
                sys.exit(1)

            if instruction.name == "main":
                if instruction.type != "void":
                    print(f'File "{filename}", line {instruction.lineno}')
                    print(f'Error: main() procedure has to be of type "void"')
                    sys.exit(1)
                main_found = True

            scopes[0][instruction.name] = (instruction.type, instruction.lineno, [arg.type for arg in instruction.args])
        else:
            for var in instruction:
                if var.name in scopes[0]:
                    print(f'File "{filename}", line {instruction.lineno}')
                    print(f'Error: Redecalred global variable "{var.name}" within the scope')
                    print(f':line {scopes[0][var.name][1]}:Info:Declartion of "{var.name}"')
                    sys.exit(1)

                if var.type == 'int' and not isinstance(var.initial, Number):
                    print(f'File "{filename}", line {var.initial.lineno}')
                    print(f'Error: Global variable "{var.name}" of type int decalred with a non-number value "{var.initial}"')
                    sys.exit(1)

                if var.type == 'bool' and not isinstance(var.initial, Bool):
                    print(f'File "{filename}", line {var.initial.lineno}')
                    print(f'Error: Global variable "{var.name}" of type bool decalred with a non-bool value "{var.initial}"')
                    sys.exit(1)

                scopes[0][var.name] = (var.type, var.lineno)

    if not main_found:
        print(f'File "{filename}"')
        print('Error: Program does not contain a main() procedure')
        sys.exit(1)

    for instruction in instructions:
        if isinstance(instruction, ProcDec):
            instruction.type_check()

    scopes.pop()
    scopes.append(dict())
    return instructions


if __name__ == '__main__':
    opts, args = getopt.getopt(sys.argv[1:], '', [])
    filename = args[0]

    if not filename.endswith('.bx'):
        print(filename, 'Wrong file extention')
        sys.exit(1)

    with open(filename, 'r') as file:
        code = file.read()

    print(bx2front(code, filename))
    print(scopes)
