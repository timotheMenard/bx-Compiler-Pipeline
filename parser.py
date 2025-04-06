import getopt
import sys
from py.ply import yacc as yacc
from scanner import Lexer
import json_to_stat as jts

"""
The Parser class defines the grammar rules and actions for parsing the language.

Parsing method: The parse() method that processes the input code
Precedence rules: Defines operator precedence and associativity
Production rules: Functions prefixed with p_ define grammar productions and actions

This parser supports:
Types: int and bool with explicit type annotations
Control flow: if-else statements and while loops
Functions: With parameters, return types, and return statements
Variables: Declaration, initialisation, and assignment
Expressions: Operators with proper precedence
Structured jumps: break and continue statements

"""


class Parser(object):
    def __init__(self, code, filename=""):
        self.lex = Lexer(filename=filename)
        self.tokens = self.lex.tokens
        self.parser = yacc.yacc(module=self, start='program')
        self.filename = filename
        self.code = code

    # Parse the input code and returns the AST
    def parse(self):
        return self.parser.parse(input=self.code, lexer=self.lex)

    #  Defines operator precedence (lowest to highest) and associativity
    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'or'),
        ('left', 'xor'),
        ('left', 'and'),
        ('nonassoc', 'jz', 'jnz'),
        ('nonassoc', 'jl', 'jnle', 'jle', 'jnl'),
        ('left', 'shl', 'shr'),
        ('left', 'add', 'sub'),
        ('left', 'mul', 'div', 'mod'),
        ('right', 'neg', 'NOT'),
        ('right', 'not'))

    # Handles parsing errors, reporting the filename, line number, and the unexpected token, then exits the program
    def p_error(self, p):
        if not p:
            print(f'Error: Invalid program')
        else:
            print(f'File "{self.filename}", line {p.lineno}')
            print(f'Error: Unexpected sign "{p.value}"')
        sys.exit(1)

    # All the set of rules
    
    def p_expr_ident(self, p):
        """expr : IDENT"""
        p[0] = jts.ExpressionVar(p[1], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_expr_number(self, p):
        """expr : NUMBER"""
        p[0] = jts.ExpressionInt(p[1], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_expr_bool(self, p):
        """expr : TRUE
                | FALSE"""
        p[0] = jts.ExpressionBool(p[1], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_expr_binop(self, p):
        '''expr : expr add expr
                | expr sub expr
                | expr mul expr
                | expr div expr
                | expr mod expr
                | expr shr expr
                | expr shl expr
                | expr xor expr
                | expr or expr
                | expr and expr
                | expr OR expr
                | expr AND expr
                | expr jz expr
                | expr jnz expr
                | expr jl expr
                | expr jnle expr
                | expr jle expr
                | expr jnl expr'''

        to_name = {'+': 'add', '-': 'sub', '*': 'mul',
                   '/': 'div', '%': 'mod', '>>': 'shr', '<<': 'shl',
                   '^': 'xor', '|': 'or', '&': 'and', '||': 'OR',
                   '&&': 'AND', '==': 'jz', '!=': 'jnz', '<': 'jl',
                   '>': 'jnle', '<=': 'jle', '>=': 'jnl'}

        p[0] = jts.ExpressionBinOp(p[1], to_name[p[2]], p[3], p.lineno(2), self.lex.find_tok_column(p, 2))

    def p_expr_unop(self, p):
        '''expr : not expr
                | sub expr %prec neg
                | neg expr
                | NOT expr'''

        to_name = {'-': 'neg', '~': 'not', '!': 'NOT'}
        p[0] = jts.ExpressionUniOp(to_name[p[1]], p[2], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_expr_parens(self, p):
        '''expr : LPAREN expr RPAREN'''
        p[0] = p[2]

    def p_expr_seq(self, p):
        '''expr_seq : expr COMMA expr_seq
                    | expr'''
        p[0] = [p[1]] + (p[3] if len(p) > 2 else [])

    def p_exprs(self, p):
        '''exprs : expr COMMA expr_seq
                | expr
                |'''
        if len(p) == 1:
            p[0] = []
        elif len(p) == 2:
            p[0] = [p[1]]
        else:
            p[0] = [p[1]] + p[3]

    def p_expr_proc_call(self, p):
        '''expr : IDENT LPAREN exprs RPAREN'''
        p[0] = jts.ExpressionCall(p[1], p[3], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_type(self, p):
        '''type : INT
                | BOOL'''
        p[0] = p[1].lower()

    def p_varinits(self, p):
        '''varinits : IDENT ASSIGN expr COMMA varinits
                    | IDENT ASSIGN expr'''
        p[0] = [(p[1], p[3], p.lineno(1), self.lex.find_tok_column(p, 1))] + (p[5] if len(p) > 4 else [])

    def p_vardecl(self, p):
        '''vardecl : VAR varinits COLON type SEMICOLON'''
        p[0] = [jts.StatementVarDecl(var[0], var[1], p[4], var[2], var[3]) for var in p[2]]

    def p_assign(self, p):
        '''assign : IDENT ASSIGN expr SEMICOLON'''
        p[0] = jts.StatementAssign(jts.ExpressionVar(p[1], p.lineno(1), self.lex.find_tok_column(p, 1)), p[3], p.lineno(3), self.lex.find_tok_column(p, 3))

    def p_return(self, p):
        '''return : RETURN SEMICOLON
                | RETURN expr SEMICOLON'''
        p[0] = jts.StatementReturn(expr=p[2] if len(p) > 3 else None, lineno=p.lineno(1), col=self.lex.find_tok_column(p, 1))

    def p_jump(self, p):
        '''jump : CONTINUE SEMICOLON
                | BREAK SEMICOLON'''
        p[0] = jts.StructuredJump(jump_type=p[1], lineno=p.lineno(1), col=self.lex.find_tok_column(p, 1))

    def p_print(self, p):
        '''eval : expr SEMICOLON'''
        p[0] = jts.StatementEval(p[1], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_ifelse(self, p):
        '''ifelse : IF LPAREN expr RPAREN block ifrest'''
        p[0] = jts.StatementIf(p[3], p[5], p[6], lineno=p.lineno(1), col=self.lex.find_tok_column(p, 1))

    def p_ifrest(self, p):
        '''ifrest : ELSE ifelse
                | ELSE block
                |'''
        if len(p) == 1:
            p[0] = None
        else:
            p[0] = p[2]

    def p_while(self, p):
        '''while : WHILE LPAREN expr RPAREN block'''
        p[0] = jts.StatementWhile(p[3], p[5], lineno=p.lineno(1), col=self.lex.find_tok_column(p, 1))

    def p_stmt(self, p):
        '''stmts : vardecl stmts
                | block stmts
                | assign stmts
                | eval stmts
                | while stmts
                | ifelse stmts
                | jump stmts
                | return stmts
                |'''
        p[0] = [p[1]] + p[2] if len(p) > 1 else []

    def p_block(self, p):
        '''block : LBRACE stmts RBRACE'''
        p[0] = jts.StatementBlock(p[2], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_idents(self, p):
        '''idents : IDENT COMMA idents
                | IDENT'''
        p[0] = [(p[1], p.lineno(1), self.lex.find_tok_column(p, 1))] + (p[3] if len(p) > 2 else [])

    def p_param(self, p):
        '''param : idents COLON type'''
        p[0] = [jts.ExpressionVar(var[0], var[1], var[2], p[3]) for var in p[1]]

    def p_params_arr(self, p):
        '''params_arr : param COMMA params_arr
                    | param'''
        p[0] = p[1] + (p[3] if len(p) > 2 else [])

    def p_params(self, p):
        '''params : param COMMA params_arr
                | param
                |'''
        if len(p) > 2:
            p[0] = p[1] + p[3]
        elif len(p) == 2:
            p[0] = p[1]
        else:
            p[0] = []

    def p_proctype(self, p):
        '''proctype : COLON type
                    |'''
        p[0] = p[2] if len(p) > 1 else "void"

    def p_proc(self, p):
        '''procdecl : DEF IDENT LPAREN params RPAREN proctype block'''
        p[0] = jts.ProcDec(p[2], p[4], p[6], p[7], p.lineno(1), self.lex.find_tok_column(p, 1))

    def p_decl(self, p):
        '''decl : vardecl
                | procdecl'''
        p[0] = p[1]

    def p_decls(self, p):
        '''decls : decl decls
                |'''
        p[0] = [p[1]] + p[2] if len(p) > 1 else []

    def p_program(self, p):
        '''program : decls'''
        p[0] = p[1]
