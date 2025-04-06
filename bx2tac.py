import json
import sys
import getopt

from json_to_stat import *
from bx2front import bx2front

filename = ''
next_temorary = 0
next_label = 0
__break_stack = []
__continue_stack = []

"""
.
The main function bx2tac takes BX source code and a filename, runs it through the frontend (bx2front), 
and then converts the resulting AST into TAC (Three-Address Code), finally outputting it as JSON.

Has error checking
"""

# Handles expressions with no return value
def void_exp(expression, tac):
    global next_temorary
    global filename

    if expression.type != 'void':
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unexpected expression type "{expression.type}"')
        sys.exit(1)

    if isinstance(expression, ExpressionCall):
        for i, arg in enumerate(expression.args):
            result = '%' + str(next_temorary)
            next_temorary += 1

            if arg.type == 'int':
                op, args = expr_to_tac(arg, tac)
                tac["body"].append({"opcode": op, "args": args, "result": result})

            elif arg.type == 'bool':
                temp = evaluate_bool_expr(arg, tac)
                tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})
            else:
                print(f'File "{filename}", line {arg.lineno}')
                print(f'Error: Argument has unknown type "{arg.type}"')
                sys.exit(1)

            if i == 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

            if i >= 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 2, result], 'result': None})
            else:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

        return "call", ["@" + expression.function, len(expression.args)]

    else:
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unrecognized expression "{expression}"')
        sys.exit(1)

# Converts boolean expressions to integers (0/1)
def evaluate_bool_expr(expression, tac):
    global next_temorary
    global next_label

    temp = '%' + str(next_temorary)
    next_temorary += 1

    if isinstance(expression, ExpressionCall):
        expression.type = "int"
        op, args = expr_to_tac(expression, tac)
        tac["body"].append({'opcode': op, 'args': args, 'result': temp})
        expression = "bool"
    else:
        Lt = "%.L" + str(next_label)
        next_label += 1
        Lf = "%.L" + str(next_label)
        next_label += 1

        tac['body'].append({'opcode': 'const', 'args': [0], 'result': temp})
        bool_exp(expression, Lt, Lf, tac)
        tac['body'].append({'opcode': 'label', 'args': [Lt], 'result': None})
        tac['body'].append({'opcode': 'const', 'args': [1], 'result': temp})
        tac['body'].append({'opcode': 'label', 'args': [Lf], 'result': None})

    return temp

# Handles boolean expressions with control flow
def bool_exp(expression, Lt, Lf, tac):
    global next_temorary
    global next_label
    global filename

    if expression.type != 'bool':
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unexpected expression type "{expression.type}"')
        sys.exit(1)

    if isinstance(expression, ExpressionBool):
        if expression.value == 'true':
            tac['body'].append({"opcode": "jmp", "args": [Lt], "result": None})
        elif expression.value == 'false':
            tac['body'].append({"opcode": "jmp", "args": [Lf], "result": None})
        else:
            print(f'File "{filename}", line {expression.lineno}')
            print(f'Error: Unknown bool value "{expression.value}"')
            sys.exit(1)

    elif isinstance(expression, ExpressionVar):
        for scope in reversed(scopes):
            if expression.name in scope:
                value = scope[expression.name][0]
                tac['body'].append({'opcode': 'jz', 'args': [value, Lf], 'result': None})
                tac['body'].append({'opcode': 'jmp', 'args': [Lt], 'result': None})
                break

    elif isinstance(expression, ExpressionUniOp):
        if expression.arg.type == 'bool':
            bool_exp(expression.arg, Lf, Lt, tac)
        elif expression.arg.type == 'int':
            arg = '%' + str(next_temorary)
            next_temorary += 1

            op, args = expr_to_tac(expression.arg, tac)
            tac["body"].append({"opcode": op, "args": args, "result": arg})

            tac["body"].append({"opcode": 'jz', 'args': [arg, Lt], 'result': None})
            tac['body'].append({"opcode": "jmp", 'args': [Lf], 'result': None})

    elif isinstance(expression, ExpressionBinOp):
        if expression.op in ['jz', 'jnz', 'jl', 'jle', 'jnle', 'jnl']:
            arg1 = '%' + str(next_temorary)
            next_temorary += 1

            if expression.arg_left.type == 'int':
                op, args = expr_to_tac(expression.arg_left, tac)
                tac["body"].append({"opcode": op, "args": args, "result": arg1})

            elif expression.arg_left.type == 'bool':
                temp = evaluate_bool_expr(expression.arg_left, tac)
                tac["body"].append({"opcode": 'copy', 'args': [temp], "result": arg1})

            arg2 = '%' + str(next_temorary)
            next_temorary += 1

            if expression.arg_right.type == 'int':
                op, args = expr_to_tac(expression.arg_right, tac)
                tac["body"].append({"opcode": op, "args": args, "result": arg2})

            elif expression.arg_right.type == 'bool':
                temp = evaluate_bool_expr(expression.arg_right, tac)
                tac["body"].append({"opcode": 'copy', 'args': [temp], "result": arg2})

            tac["body"].append({'opcode': "sub", 'args': [arg1, arg2], "result": arg1})
            tac["body"].append({"opcode": expression.op, 'args': [arg1, Lt], 'result': None})
            tac['body'].append({"opcode": "jmp", 'args': [Lf], 'result': None})

        elif expression.op == 'AND':
            Li = "%.L" + str(next_label)
            next_label += 1

            bool_exp(expression.arg_left, Li, Lf, tac)
            tac['body'].append({"opcode": 'label',  'args': [Li], 'result': None})
            bool_exp(expression.arg_right, Lt, Lf, tac)

        elif expression.op == 'OR':
            Li = "%.L" + str(next_label)
            next_label += 1

            bool_exp(expression.arg_left, Lt, Li, tac)
            tac['body'].append({"opcode": 'label',  'args': [Li], 'result': None})
            bool_exp(expression.arg_right, Lt, Lf, tac)

        else:
            print(f'File "{filename}", line {expression.lineno}')
            print(f'Error: Unknown binary opperation "{expression.op}"')
            sys.exit(1)

    elif isinstance(expression, ExpressionCall):
        temp = '%' + str(next_temorary)
        next_temorary += 1

        for i, arg in enumerate(expression.args):
            result = '%' + str(next_temorary)
            next_temorary += 1

            if arg.type == 'int':
                op, args = expr_to_tac(arg, tac)
                tac["body"].append({"opcode": op, "args": args, "result": result})

            elif arg.type == 'bool':
                temp = evaluate_bool_expr(arg, tac)
                tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})

            if i == 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

            if i >= 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 2, result], 'result': None})
            else:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

        tac["body"].append({"opcode": "call", 'args': ["@" + expression.function, len(expression.args)], 'result': temp})
        tac['body'].append({'opcode': 'jz', 'args': [temp, Lf], 'result': None})
        tac['body'].append({'opcode': 'jmp', 'args': [Lt], 'result': None})

    else:
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unrecognized expression "{expression}"')
        sys.exit(1)

# Converts integer expressions to TAC
def expr_to_tac(expression, tac):
    global next_temorary
    global filename

    if expression.type != 'int':
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unexpected expression type "{expression.type}"')
        sys.exit(1)

    if isinstance(expression, ExpressionInt):
        return "const", [expression.value]

    elif isinstance(expression, ExpressionVar):
        for scope in reversed(scopes):
            if expression.name in scope:
                return "copy", [scope[expression.name][0]]

    elif isinstance(expression, ExpressionUniOp):
        arg1 = '%' + str(next_temorary)
        next_temorary += 1

        op, args = expr_to_tac(expression.arg, tac)
        tac["body"].append({"opcode": op, "args": args, "result": arg1})

        return expression.op, [arg1]

    elif isinstance(expression, ExpressionBinOp):
        arg1 = '%' + str(next_temorary)
        next_temorary += 1

        op, args = expr_to_tac(expression.arg_left, tac)
        tac["body"].append({"opcode": op, "args": args, "result": arg1})

        arg2 = '%' + str(next_temorary)
        next_temorary += 1

        op, args = expr_to_tac(expression.arg_right, tac)
        tac["body"].append({"opcode": op, "args": args, "result": arg2})

        return expression.op, [arg1, arg2]

    elif isinstance(expression, ExpressionCall):
        for i, arg in enumerate(expression.args):
            result = '%' + str(next_temorary)
            next_temorary += 1

            if arg.type == 'int':
                op, args = expr_to_tac(arg, tac)
                tac["body"].append({"opcode": op, "args": args, "result": result})

            elif arg.type == 'bool':
                temp = evaluate_bool_expr(arg, tac)
                tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})

            if i == 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

            if i >= 6 and len(expression.args) & 1:
                tac["body"].append({'opcode': 'param', "args": [i + 2, result], 'result': None})
            else:
                tac["body"].append({'opcode': 'param', "args": [i + 1, result], 'result': None})

        return "call", ["@" + expression.function, len(expression.args)]

    else:
        print(f'File "{filename}", line {expression.lineno}')
        print(f'Error: Unrecognized expression "{expression}"')
        sys.exit(1)

# Converts statements to TAC instructions
def statements_to_tac(instruction, tac):
    global next_temorary
    global next_label
    global filename

    if isinstance(instruction, StatementBlock):
        scopes.append(dict())
        for stmt in instruction.body:
            if not isinstance(stmt, Statment):
                for s in stmt:
                    statements_to_tac(s, tac)
            else:
                statements_to_tac(stmt, tac)
        scopes.pop()

    elif isinstance(instruction, StatementVarDecl):
        result = '%' + str(next_temorary)
        next_temorary += 1

        if instruction.type == 'int':
            op, args = expr_to_tac(instruction.initial, tac)
            tac["body"].append({"opcode": op, "args": args, "result": result})

        elif instruction.type == 'bool':
            temp = evaluate_bool_expr(instruction.initial, tac)
            tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})

        scopes[-1][instruction.name] = (result, instruction.lineno)

    elif isinstance(instruction, StatementAssign):
        for scope in reversed(scopes):
            if instruction.target.name in scope:

                result = scope[instruction.target.name][0]

                if instruction.type == 'int':
                    op, args = expr_to_tac(instruction.expr, tac)
                    tac["body"].append({"opcode": op, "args": args, "result": result})

                elif instruction.type == 'bool':
                    temp = evaluate_bool_expr(instruction.expr, tac)
                    tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})
                break

    elif isinstance(instruction, StatementIf):
        Lt = "%.L" + str(next_label)
        next_label += 1
        Lf = "%.L" + str(next_label)
        next_label += 1

        bool_exp(instruction.condition, Lt, Lf, tac)
        tac["body"].append({'opcode': 'label', 'args': [Lt], 'result': None})
        statements_to_tac(instruction.instructions, tac)

        if instruction.else_case is None:
            tac["body"].append({'opcode': 'label', 'args': [Lf], 'result': None})
        else:
            Lo = "%.L" + str(next_label)
            next_label += 1
            tac["body"].append({'opcode': 'jmp', 'args': [Lo], 'result': None})
            tac["body"].append({'opcode': 'label', 'args': [Lf], 'result': None})
            statements_to_tac(instruction.else_case, tac)
            tac["body"].append({'opcode': 'label', 'args': [Lo], 'result': None})

    elif isinstance(instruction, StatementWhile):
        Lhead = "%.L" + str(next_label)
        next_label += 1
        tac["body"].append({'opcode': 'label', 'args': [Lhead], 'result': None})

        Lbod = "%.L" + str(next_label)
        next_label += 1
        Lend = "%.L" + str(next_label)
        next_label += 1

        __break_stack.append(Lend)
        __continue_stack.append(Lhead)
        bool_exp(instruction.condition, Lbod, Lend, tac)
        tac["body"].append({'opcode': 'label', 'args': [Lbod], 'result': None})
        statements_to_tac(instruction.instructions, tac)
        tac["body"].append({'opcode': 'jmp', 'args': [Lhead], 'result': None})
        tac["body"].append({'opcode': 'label', 'args': [Lend], 'result': None})
        __continue_stack.pop()
        __break_stack.pop()

    elif isinstance(instruction, StructuredJump):
        if instruction.jump_type == 'break':
            if len(__break_stack) == 0:
                print(f'File "{filename}", line {instruction.lineno}')
                print(f'Error: Break instruction out of loop')
                sys.exit(1)

            tac['body'].append({'opcode': 'jmp', 'args': [__break_stack[-1]], 'result': None})

        elif instruction.jump_type == 'continue':
            if len(__continue_stack) == 0:
                print(f'File "{filename}", line {instruction.lineno}')
                print(f'Error: Continue instruction out of loop')
                sys.exit(1)

            tac['body'].append({'opcode': 'jmp', 'args': [__continue_stack[-1]], 'result': None})

    elif isinstance(instruction, StatementEval):
        if instruction.type == 'int':
            op, args = expr_to_tac(instruction.expr, tac)
            tac["body"].append({"opcode": op, "args": args, "result": None})
        elif instruction.type == 'bool':
            temp = evaluate_bool_expr(instruction.expr, tac)
            tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': None})
        elif instruction.type == "void":
            op, args = void_exp(instruction.expr, tac)
            tac["body"].append({"opcode": op, "args": args, "result": None})

    elif isinstance(instruction, StatementReturn):
        if instruction.type != "void":
            result = '%' + str(next_temorary)
            next_temorary += 1
            if instruction.type == 'int':
                op, args = expr_to_tac(instruction.expr, tac)
                tac["body"].append({"opcode": op, "args": args, "result": result})

            elif instruction.type == 'bool':
                temp = evaluate_bool_expr(instruction.expr, tac)
                tac['body'].append({'opcode': 'copy', 'args': [temp], 'result': result})

            tac["body"].append({"opcode": "ret", "args": [result], "result": None})
        else:
            tac["body"].append({"opcode": "ret", "args": [], "result": None})

    else:
        print(f'File "{filename}", line {instruction.lineno}')
        print(f'Error: Unrecognized statement "{instruction}"')
        sys.exit(1)

# Processes global declarations (variables and procedures)
def globs(instructions):
    tac = []
    index = []
    for instruction in instructions:
        if isinstance(instruction, ProcDec):
            index.append((len(tac), instruction))
            tac.append({"proc": "@" + instruction.name, "args": ["%" + arg.name for arg in instruction.args], "body": []})
            scopes[0][instruction.name] = ("@" + instruction.name, instruction.lineno)
        else:
            for var in instruction:
                if var.type == 'int':
                    tac.append({"var": "@" + var.name, "init": var.initial.value})
                else:
                    tac.append({"var": "@" + var.name, "init": 0 if var.initial.value == 'false' else 1})

                scopes[0][var.name] = ("@" + var.name, var.lineno)

    return tac, index

#  The entry point that processes source code into TAC
def bx2tac(code, file=""):
    global filename
    filename = file
    for line in code.split('\n'):
        lines.append(line)

    instructions = bx2front(code, filename)
    tac, index = globs(instructions)

    
    for i, instruction in index:
        if isinstance(instruction, ProcDec):
            scopes.append({arg.name: ("%" + arg.name, arg.lineno) for arg in instruction.args})
            statements_to_tac(instruction.body, tac[i])
            scopes.pop()

    tac_json = json.dumps(tac)

    return tac_json
