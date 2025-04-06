scopes = [dict()]
filename = ''
lines = []


class ProcDec:
    def __init__(self, name, args, type, body, lineno, col):
        self.name = name
        self.args = args
        self.type = type
        self.body = body
        self.lineno = lineno
        self.col = col

    def type_check(self):
        scopes.append(self.type)
        scopes.append(dict())
        for arg in self.args:
            if arg.name in scopes[-1]:
                print(f'File "{filename}", line {arg.lineno}')
                print(f'Error: Argument "{arg.name}" already given within the procdure {self.name}')
                sys.exit(1)
            else:
                scopes[-1][arg.name] = (arg.type, arg.lineno)

        has_return = self.body.type_check()
        scopes.pop()
        scopes.pop()

        if self.type != 'void' and not has_return:
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Function {self.name} does not return value on every possible code path')
            sys.exit(1)

    def to_tac(self):
        result = {"proc": self.name, "args": list(self.args), "body": []}
        for i in self.body:
            result["body"].append(i.to_tac())
        return result


class Statment:
    pass


class StatementBlock(Statment):
    def __init__(self, body, lineno, col):
        self.body = body
        self.lineno = lineno
        self.col = col

    def type_check(self):
        scopes.append(dict())
        has_return = False

        for stmt in self.body:
            if not isinstance(stmt, Statment):
                for s in stmt:
                    has_return = max(s.type_check(), has_return)
            else:
                has_return = max(stmt.type_check(), has_return)

        scopes.pop()

        return has_return


class StatementVarDecl(Statment):
    def __init__(self, name, initial, type, lineno, col):
        self.name = name
        self.initial = initial
        self.type = type
        self.lineno = lineno
        self.col = col

    def type_check(self):
        if self.name in scopes[-1]:
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Redecalred variable "{self.name}" within the scope')
            sys.exit(1)

        self.initial.type_check()

        if self.type == 'void':
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Variable "{self.name}" cannot be declared as VOID')
            sys.exit(1)

        elif self.initial.type == 'void':
            print(f'File "{filename}", line {self.initial.lineno}')
            print(f'Error: Variable "{self.name}" cannot be initialized with expression of type VOID')
            sys.exit(1)

        if self.initial.type != self.type:
            print(f'File "{filename}", line {self.initial.lineno}')
            print(f'Error: Variable "{self.name}" of type "{self.type}" initialized with expression of different type "{self.initial.type}"')
            sys.exit(1)

        scopes[-1][self.name] = (self.initial.type, self.lineno)

        return False

    def to_tac(self):
        return {"var": self.name, "init": self.initial}


class StatementAssign(Statment):
    def __init__(self, target, expr, lineno, col):
        self.target = target
        self.expr = expr
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.target.type_check()
        self.expr.type_check()
        self.type = self.target.type

        if self.expr.type == 'void':
            print(f'File "{filename}", line {self.expr.lineno}')
            print(f'Error: Variable "{self.target.name}" cannot be assigned with expression of type VOID')
            sys.exit(1)

        if self.type != self.expr.type:
            print(f'File "{filename}", line {self.expr.lineno}')
            print(f'Error: Variable "{self.target.name}" of type "{self.type}" assigned with expression of different type "{self.expr.type}"')
            sys.exit(1)

        return False


class StatementWhile(Statment):
    def __init__(self, condition, instructions, lineno, col):
        self.condition = condition
        self.instructions = instructions
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.condition.type_check()
        if self.condition.type != 'bool':
            print(f'File "{filename}", line {self.condition.lineno}')
            print(f'Error: Condition in WHILE has to be of "bool" type, "{self.condition.type}" given')
            sys.exit(1)

        self.instructions.type_check()
        return False


class StatementIf(Statment):
    def __init__(self, condition, instructions, else_case, lineno, col):
        self.condition = condition
        self.instructions = instructions
        self.else_case = else_case
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.condition.type_check()
        if self.condition.type != 'bool':
            print(f'File "{filename}", line {self.condition.lineno}')
            print(f'Error: Condition in IF has to be of "bool" type, "{self.condition.type}" given')
            sys.exit(1)

        has_return_if = self.instructions.type_check()
        has_return_else = False
        if self.else_case is not None:
            has_return_else = self.else_case.type_check()

        return has_return_if and has_return_else


class StatementEval(Statment):
    def __init__(self, expr, lineno, col):
        self.expr = expr
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.expr.type_check()
        self.type = self.expr.type
        return False


class StructuredJump(Statment):
    def __init__(self, jump_type, lineno, col):
        self.jump_type = jump_type
        self.lineno = lineno
        self.col = col

    def type_check(self):
        return False


class StatementReturn(Statment):
    def __init__(self, expr, lineno, col):
        self.expr = expr
        self.lineno = lineno
        self.col = col

    def type_check(self):
        if self.expr is not None:
            self.expr.type_check()
            self.type = self.expr.type

            if self.expr.type != scopes[1]:
                print(f'File "{filename}", line {self.expr.lineno}')
                print(f'Error: Cannot return expression of type "{self.expr.type}"')
                sys.exit(1)
        else:
            self.type = "void"
            if scopes[1] != 'void':
                print(f'File "{filename}", line {self.expr.lineno}')
                print(f'Error: Cannot return expression void type when function requires "{scopes[1]}"')
                sys.exit(1)

        return True


class Expression:
    pass


class ExpressionVar(Expression):
    def __init__(self, name, lineno, col, type=None):
        self.name = name
        self.lineno = lineno
        self.type = type
        self.col = col

    def type_check(self):
        for scope in reversed(scopes):
            if self.name in scope:
                if self.type is None:
                    self.type = scope[self.name][0]

                elif self.type != scopes[self.name][0]:
                    print(f'File "{filename}", line {self.lineno}')
                    print(f'Error: Variable "{self.name}" of type {self.type} has been declared with type "{scopes[self.name][0]}"')
                    sys.exit(1)

                return
        else:
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Undeclared variable "{self.name}"')
            sys.exit(1)


class ExpressionInt(Expression):
    def __init__(self, value, lineno, col):
        self.value = value
        self.lineno = lineno
        self.type = 'int'
        self.col = col

    def type_check(self):
        return


class ExpressionBool(Expression):
    def __init__(self, value, lineno, col):
        self.value = value
        self.lineno = lineno
        self.type = 'bool'
        self.col = col

    def type_check(self):
        return


class ExpressionUniOp(Expression):
    def __init__(self, op, arg, lineno, col):
        self.op = op
        self.arg = arg
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.arg.type_check()
        if self.op in ['not', 'sub', 'neg']:
            if self.arg.type == 'int':
                self.type = 'int'
            else:
                print(f'File "{filename}", line {self.arg.lineno}')
                print(f"Error: Operation and argumet's type '{self.arg.type}' not compatible")
                sys.exit(1)

        elif self.op == 'NOT':
            if self.arg.type == 'bool':
                self.type = 'bool'
            else:
                print(f'File "{filename}", line {self.arg.lineno}')
                print(f'Error: Operation and argumet type "{self.arg.type}" not compatible')
                sys.exit(1)
        else:
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Unknown operation "{self.op}"')
            sys.exit(1)


class ExpressionBinOp(Expression):
    def __init__(self, arg_left, op, arg_right, lineno, col):
        self.arg_left = arg_left
        self.arg_right = arg_right
        self.op = op
        self.lineno = lineno
        self.col = col

    def type_check(self):
        self.arg_left.type_check()
        self.arg_right.type_check()
        if self.op in ['add', 'sub', 'mul', 'div', 'mod', 'shr',
                       'shl', 'xor', 'or', 'and']:
            if self.arg_left.type == 'int' and self.arg_right.type == 'int':
                self.type = 'int'
            else:
                print(f'File "{filename}", line {self.arg_right.lineno}')
                print(f"Error: Operation and argument types not compatible")
                sys.exit(1)

        elif self.op in ['AND', 'OR']:
            if self.arg_left.type == 'bool' and self.arg_right.type == 'bool':
                self.type = 'bool'
            else:
                print(f'File "{filename}", line {self.arg_right.lineno}')
                print(f"Error: Operation and argument types not compatible")
                sys.exit(1)
        
        elif self.op in ['jz', 'jnz']:
            if (self.arg_left.type == 'int' and self.arg_right.type == 'int') or (self.arg_left.type == 'bool' and self.arg_right.type == 'bool'):
                self.type = 'bool'
            else:
                print(f'File "{filename}", line {self.arg_right.lineno}')
                print(f"Error: Operation and argument types not compatible")
                sys.exit(1)

        elif self.op in ['jl', 'jnle', 'jle', 'jnl']:
            if self.arg_left.type == 'int' and self.arg_right.type == 'int':
                self.type = 'bool'
            else:
                print(f'File "{filename}", line {self.arg_right.lineno}')
                print(f"Error: Operation and argument types not compatible")
                sys.exit(1)
        else:
            print(f'File "{filename}", line {self.lineno}')
            print(f"Error: Unknown operation '{self.op}'")
            sys.exit(1)


class ExpressionCall(Expression):
    def __init__(self, function, args, lineno, col):
        self.function = function
        self.args = args
        self.lineno = lineno
        self.col = col

    def type_check(self):
        if self.function == 'print':
            self.type = "void"
            if len(self.args) != 1:
                print(f'File "{filename}", line {self.lineno}')
                print(f'Error: Function "print" can only have one argument, {len(self.args)} given')
                sys.exit(1)

            self.args[0].type_check()
            if self.args[0].type == "int":
                self.function = '__bx_print_int'
            elif self.args[0].type == "bool":
                self.function = '__bx_print_bool'
            else:
                print(f'File "{filename}", line {self.args[0].lineno}')
                print(f'Error: Cannot print() expression of type "{self.args[0].type}"')
                sys.exit(1)

        elif self.function in scopes[0]:
            self.type, lineno, args_types = scopes[0][self.function]

            if len(self.args) != len(args_types):
                print(f'File "{filename}", line {self.lineno}')
                print(f'Error: Function "{self.function}" has requires {len(args_types)} arguments, {len(self.args)} given')
                sys.exit(1)

            for i in range(len(self.args)):
                self.args[i].type_check()
                if self.args[i].type != args_types[i]:
                    print(f'File "{filename}", line {self.args[i].lineno}')
                    print(f'Error: Argument of number {i + 1} is of wrong type "{self.args[i].type}"')
                    sys.exit(1)
        else:
            print(f'File "{filename}", line {self.lineno}')
            print(f'Error: Undeclared procedure "{self.function}"')
            sys.exit(1)

        return
