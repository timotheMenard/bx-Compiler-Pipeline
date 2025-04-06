import sys
import getopt
import json
from json_to_stat import ProcDec, StatementVarDecl

"""
.
The tac2x64 function is the main entry point that takes a JSON file containing TAC instructions and produces x64 assembly code. 
This completes the compilation pipeline: BX source → AST → TAC → x64 Assembly.
"""


class Instr:
    def __init__(self, opcode, arg1, arg2, dest):
        self.opcode = opcode
        self.arg1 = arg1
        self.arg2 = arg2
        self.dest = dest

    def __str__(self):
        return (f"opcode : {self.opcode}, arg1 : {self.arg1}, arg2 : {self.arg2}, dest : {self.dest}")

    def to_tac(self):
        if self.arg2 == None:
            return {"opcode": self.opcode, "args": [self.arg1], "result": self.dest}
        return {"opcode": self.opcode, "args": [self.arg1, self.arg2], "result": self.dest}


class Create_x64:
    def __init__(self, global_var, name, args):
        self.stack = {}
        self.global_var = global_var
        self.name = name
        self.args = args
        self.strs = []
        self.stack_pos = 0
        self.tmp_var_regester = ['', '%rdi', '%rsi', '%rdx', '%rcx', '%r8', '%r9']
        self.binop = {'add': 'addq', 'sub': 'subq', 'mul': 'imulq',
                      'and': 'andq', 'or': 'orq', 'xor': 'xorq'}
        self.unop = {'not': 'notq', 'neg': 'negq'}
        self.shiftop = {'shl': 'salq', 'shr': 'sarq'}
        self.div = {'div': '%rax', 'mod': '%rdx'}
        self.condition = ['je', 'jz', 'jne', 'jnz', 'jl',
                          'jnge', 'jle', 'jng', 'jg', 'jnle', 'jge', 'jnl']

        for i in range(min(len(self.args), 6)):
            self.strs.append('\tmovq {}, {}'.format(self.tmp_var_regester[i + 1], self.get_pos(args[i])))

    # Determines where a variable is stored
    def get_pos(self, var):
        if var in self.global_var:
            return "{}(%rbp)".format(var[1:])
        if var in self.args:
            if self.args.index(var) >= 6:
                return "{}(%rbp)".format((16 + 8 * (len(self.args) - self.args.index(var) - 1)))
        if var in self.stack.keys():
            return "{}(%rbp)".format(-8 * self.stack[var])
        else:
            self.stack_pos += 1
            self.stack[var] = self.stack_pos
            return "{}(%rbp)".format(-8 * self.stack_pos)

    # Converts each TAC instruction to assembly instructions
    def to_str(self, tac_expr):
        op = tac_expr.opcode
        dest = tac_expr.dest
        arg1 = tac_expr.arg1
        arg2 = tac_expr.arg2

        if (op == 'const'):
            self.strs.append("\tmovabsq ${}, %r10".format(arg1))
            self.strs.append("\tmovq %r10, {}".format(self.get_pos(dest)))

        elif (op == 'copy'):
            self.strs.append("\tmovq {}, %r10".format(self.get_pos(arg1)))
            self.strs.append("\tmovq %r10, {}".format(self.get_pos(dest)))

        elif op == 'label':
            self.strs.append(".main{}:".format(arg1[1:]))

        elif op == 'jmp':
            self.strs.append("\tjmp .main{}".format(arg1[1:]))

        elif op in self.binop.keys():
            self.strs.append("\tmovq {}, %r10".format(self.get_pos(arg1)))
            self.strs.append("\t{} {}, %r10".format(self.binop[op], self.get_pos(arg2)))
            self.strs.append("\tmovq %r10, {}".format(self.get_pos(dest)))

        elif op in self.unop.keys():
            self.strs.append("\tmovq {}, %r10".format(self.get_pos(arg1)))
            self.strs.append("\t{} %r10".format(self.unop[op]))
            self.strs.append("\tmovq %r10, {}".format(self.get_pos(dest)))

        elif op in self.shiftop.keys():
            self.strs.append("\tmovq {}, %r10".format(self.get_pos(arg1)))
            self.strs.append("\tmovq {}, %rcx".format(self.get_pos(arg2)))
            self.strs.append("\t{} %cl, %r10".format(self.shiftop[op]))
            self.strs.append("\tmovq %r10, {}".format(self.get_pos(dest)))

        elif op in self.div.keys():
            self.strs.append("\tmovq {}, %rax".format(self.get_pos(arg1)))
            self.strs.append("\tcqto")
            self.strs.append("\tidivq {}".format(self.get_pos(arg2)))
            self.strs.append("\tmovq {}, {}".format(self.div[op], self.get_pos(dest)))

        elif op in self.condition:
            self.strs.append("\tmovq {}, %r10".format(self.get_pos(arg1)))
            self.strs.append("\tcmpq $0, %r10")
            self.strs.append("\t{} {}".format(op, arg2[1:]))

        elif op == 'param':
            if arg1 <= 6:
                self.strs.append("\tmovq {}, {}".format(self.get_pos(arg2), self.tmp_var_regester[arg1]))
            else:
                self.strs.append("\tpushq {}".format(self.get_pos(arg2)))
        
        elif op == 'call':
            self.strs.append("\tcallq {}".format(arg1[1:]))
            if dest != None:
                self.strs.append("\tmovq %rax, {}".format(self.get_pos(dest)))

        elif op == 'ret':
            if arg1 == None:
                self.strs.append("\txorq %rax, %rax")
                self.strs.append("\tjmp .Lend_{}".format(self.name[1:]))
            else:
                self.strs.append("\tmovq {}, %rax".format(self.get_pos(arg1)))
                self.strs.append("\tjmp .Lend_{}".format(self.name[1:]))
        
        else:
            print("Unknown Opcode")
            sys.exit(1)

    def main(self, tac_file):
        for line in tac_file:
            self.to_str(line)
        head = [f'\t.globl {self.name[1:]}', '\t.text', f'{self.name[1:]}:', '\tpushq %rbp', '\tmovq %rsp, %rbp', f'\tsubq ${8 * len(self.stack)}, %rsp']
        if self.name[1:] == 'main':
            tail = [f'.Lend_{self.name[1:]}:', '\tmovq %rbp, %rsp ', '\tpopq %rbp ', '\txorq %rax, %rax', '\tretq', '']
        else:
            tail = [f'.Lend_{self.name[1:]}:', '\tmovq %rbp, %rsp ', '\tpopq %rbp ', '\tretq', '']
        return head + self.strs + tail

# Parses the JSON TAC representation
def load_tac(js_obj):    
    var = []
    proc = []
    for obj in js_obj:
        if "proc" in obj.keys():
            tac = []
            for line in obj["body"]:
                arg1, arg2 = None, None
                args = line["args"]
                if len(args) == 1:
                    arg1 = args[0]
                    if (isinstance(arg1, str)) and (arg1[:3] == '%.L'):
                        arg1 = arg1 + "_" + obj["proc"][1:]
                elif len(args) == 2:
                    arg1 = args[0]
                    arg2 = args[1]
                    if (isinstance(arg1, str)) and (arg1[:3] == '%.L'):
                        arg1 = arg1 + "_" + obj["proc"][1:]
                    if (isinstance(arg2, str)) and (arg2[:3] == '%.L'):
                        arg2 = arg2 + "_" + obj["proc"][1:]
                tac.append(Instr(line["opcode"], arg1, arg2, line["result"]))
            proc.append(ProcDec(obj["proc"], obj["args"], None, tac, None, None))
        elif "var" in obj:
            var.append(StatementVarDecl(obj["var"], obj["init"], None, None, None))
    return var, proc

"""
The tac2x64 function:
Loads TAC from JSON
Outputs global variable definitions
Generates assembly for each procedure
Returns the complete assembly as a list of strings
"""
def tac2x64(file_name):
    with open(file_name, 'r') as fp:
        js_obj = json.load(fp)
        var, proc = load_tac(js_obj)

    out = []
    global_var = []
    for v in var:
        global_var.append(v.name)
        out = out + [f'\t.globl {v.name[1:]}', '\t.data', f'{v.name[1:]}:  .quad {v.initial}', '']

    for p in proc:
        now = Create_x64(global_var, p.name, p.args)
        now_x86 = now.main(p.body)
        out += now_x86

    return out
