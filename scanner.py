import getopt
import sys
from py.ply import lex as lex

"""
The Lexer class defines the rules for tokenising source code.

It has,
Input handling: Methods to feed text to the lexer and retrieve tokens
Token definitions: Regular expressions that define the language's lexical elements
Error handling: Logic for handling illegal characters
Also has a test functionality 
"""


class Lexer(object):
    def __init__(self, filename="", **kwargs):
        self.filename = filename
        self.lexer = lex.lex(object=self, **kwargs)

    def input(self, text):
        self.code = text
        self.lexer.input(text)

    def reset_lineno(self):
        self.lexer.lineno = 1

    def token(self):
        self.last_token = self.lexer.token()
        return self.last_token

    def find_tok_column(self, token, n=None):
        if n is None:
            last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos)
            return token.lexpos - last_cr
        else:
            last_cr = self.lexer.lexdata.rfind('\n', 0, token.lexpos(n))
            return token.lexpos(n) - last_cr

    def test(self, data):
        self.input(data)
        while True:
            tok = self.token()
            if tok:
                print(tok)
            else:
                break

    keywords = {'def': 'DEF',
                'var': 'VAR', 'bool': 'BOOL', 'int': 'INT',
                'if': 'IF', 'else': 'ELSE',
                'while': 'WHILE', 'return': 'RETURN',
                'break': 'BREAK', 'continue': 'CONTINUE',
                'true': 'TRUE', 'false': 'FALSE'}

    tokens = (
        'add', 'sub', 'SEMICOLON', 'LPAREN', 'RPAREN', 'IDENT', 'NUMBER',
        'LBRACE', 'RBRACE', 'COMMA',
        'shl', 'shr', 'xor', 'or', 'and',
        'mul', 'div', 'mod', 'neg', 'not',
        'ASSIGN', 'COLON', 'OR', 'AND', 'jz', 'jnz',
        'jl', 'jnle', 'jle', 'jnl', 'NOT',
    ) + tuple(keywords.values())

    t_DEF = r'def'
    t_LPAREN = r'\('
    t_RPAREN = r'\)'
    t_add = r'\+'
    t_sub = '-'
    t_SEMICOLON = ';'
    t_shr = r'\>\>'
    t_shl = r'\<\<'
    t_xor = r'\^'
    t_or = r'\|'
    t_and = r'\&'
    t_mul = r'\*'
    t_div = r'\/'
    t_mod = r'\%'
    t_not = r'\~'
    t_ASSIGN = r'\='
    t_COLON = ':'
    t_LBRACE = r'\{'
    t_RBRACE = r'\}'
    t_OR = r'\|\|'
    t_AND = r'\&\&'
    t_jz = r'\=\='
    t_jnz = r'\!\='
    t_jl = r'\<'
    t_jle = r'\<\='
    t_jnle = r'\>'
    t_jnl = r'\>\='
    t_NOT = r'\!'
    t_COMMA = r'\,'

    t_ignore = " \t\f\v\r"

    def t_IDENT(self, t):
        r'[A-Za-z_][A-Za-z0-9_]*'
        t.type = self.keywords.get(t.value, 'IDENT')
        return t

    def t_NUMBER(self, t):
        r'0|-?[1-9][0-9]*'
        t.value = int(t.value)

        if t.value < -(1 << 63) or t.value >= (1 << 63):
            print(f'File "{self.filename}", line {t.lexer.lineno}')
            print(f':Error: Wrong integer "{t.value}" - out of accpeted range')
            sys.exit(1)

        return t

    def t_COMMENTS(self, t):
        r'//.*\n?'
        t.lexer.lineno += 1

    def t_newline(self, t):
        r'\n'
        t.lexer.lineno += 1

    def t_error(self, t):
        print(f'File "{self.filename}", line {t.lexer.lineno}')
        print(f"Error: Illegal character '{t.value[0]}'")
        sys.exit(1)
