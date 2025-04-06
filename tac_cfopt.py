import sys
import getopt
import json
from json_to_stat import ProcDec, StatementVarDecl
from tac2x64 import Instr


class Instructions:
    def __init__(self, instruction):
        self.instruction = instruction
        self.id = id(instruction)
        self.child = []

    def check(self, tmp):
        return (tmp != None) and (isinstance(tmp, str)) and (tmp[0] == '%')

    def __str__(self):
        return f'opcode : {self.instruction.opcode}, arg : {[self.instruction.arg1, self.instruction.arg2]}, dest : {self.instruction.dest}'


class BasicBlock:
    def __init__(self, instructions):
        self.label = instructions[0].instruction.arg1
        self.instructions = instructions
        self.child = []
        self.father = []

    def add_father(self, father):
        self.father.append(father)

    def add_child(self, child):
        self.child.append(child)

    def union(self, tmp):
        self.instructions += tmp.instructions
        for child_lbl in tmp.child:
            self.child.append(child_lbl)


class ControlFlowGraph:
    def __init__(self, tac_file, proc_name):
        self.visited_str = []
        self.cjmp = {'jz', 'jnz', 'jl', 'jle', 'jnl', 'jnle'}
        self.name = proc_name[1:]
        self.build(tac_file)
        

    def build(self, tac_file):
        self.block = {}
        self.instrcutions = {}
        self.tac_id = []

        if (tac_file[0].opcode != 'label'):
            tmp = ".Lentry_" + self.name
            tac_file.insert(0, Instr('label', tmp, None, None))
            self.entry_label = tmp
        else:
            self.entry_label = tac_file[0].arg1

        i, count = 0, 0
        while (i < len(tac_file)):
            if (tac_file[i].opcode == 'jmp') and (i < len(tac_file) - 1) and (tac_file[i + 1].opcode != 'label'):
                tmp = Instr('label', f'.Ljmp_{self.name}_{count}', None, None)
                count += 1
                tac_file.insert(i + 1, tmp)

            elif (i >= 1) and (tac_file[i].opcode == 'label') and (tac_file[i - 1].opcode != 'jmp'):
                if (tac_file[i - 1].opcode == 'ret'):
                    tac_file.insert(i, Instr('jmp', tac_file[i].arg1, None, 'tmp'))
                else:
                    tac_file.insert(i, Instr('jmp', tac_file[i].arg1, None, None))

            tmp = Instructions(tac_file[i])
            self.instrcutions[tmp.id] = tmp
            self.tac_id.append(tmp.id)
            i += 1

        self.block[tac_file[0].arg1] = BasicBlock([self.instrcutions[self.tac_id[0]]])
        prev = tac_file[0].arg1

        edge = []

        for i in range(1, len(tac_file)):
            now = tac_file[i]
            if now.opcode == 'label':
                self.block[now.arg1] = BasicBlock([self.instrcutions[self.tac_id[i]]])
                prev = now.arg1
            else:
                self.block[prev].instructions.append(self.instrcutions[self.tac_id[i]])

            if now.opcode in self.cjmp:
                edge.append((prev, now.arg2))
            if now.opcode == 'jmp':
                edge.append((prev, now.arg1))

        for i in range(1, len(tac_file)):
            if tac_file[i].opcode == 'label':
                continue

            if tac_file[i].opcode in self.cjmp:
                if len(self.block[tac_file[i].arg2].instructions) > 1:
                    self.instrcutions[self.tac_id[i]].child.append(self.block[tac_file[i].arg2].instructions[1].id)
            if tac_file[i].opcode == 'jmp':
                if len(self.block[tac_file[i].arg1].instructions) > 1:
                    self.instrcutions[self.tac_id[i]].child.append(self.block[tac_file[i].arg1].instructions[1].id)
                continue

            if (i < len(tac_file) - 1):
                if (self.instrcutions[self.tac_id[i + 1]].instruction.opcode != 'label'):
                    self.instrcutions[self.tac_id[i]].child.append(self.tac_id[i + 1])

        for (father, child) in edge:
            self.block[father].add_child(child)
            self.block[child].add_father(father)

    def rec_linear2(self, now, visted):
        if (len(now.child) == 1):
            child_lbl = list(now.child)[0]
            block = self.block[child_lbl]
            if (len(block.father) == 1):
                visted += [child_lbl]
                return self.rec_linear2(block, visted)
        return visted
    
    def jump_thread(self):
        noNeedBlock = set()

        for label, block in self.block.items():
            linl = self.rec_linear2(block, [label])[:-1]

            if len(linl) > 1:
                f = True

                for i in range(1, len(linl) - 1):
                    if len(linl[i]) > 2:
                        f = False
                        break
                if f:
                    head = self.block[linl[0]]
                    head.instructions[-1].instruction.arg1 = linl[-1]
                    for i in linl[1:-1]:
                        head.union(self.block[i])
                        noNeedBlock.add(i)

            for child_lbl in block.child:
                con_variable, con_jmp_used = None, None  
                for instr in block.instructions:
                    if (instr.instruction.arg2 == child_lbl) and (instr.instruction.opcode in self.cjmp):
                        con_variable = instr.instruction.arg1
                        con_jmp_used = instr.instruction.opcode

                if not con_variable:
                    continue

                f = False
                child = self.block[child_lbl]
                for instr in child.instructions:
                    if instr.instruction.dest == con_variable:
                        f = True
                        break
                if f:
                    continue

                f = False
                for i in range(len(child.instructions) - 1):
                    now = child.instructions[i].instruction
                    if len(child.father) != 1:
                        break
                    if (now.opcode == con_jmp_used) and (now.arg1 == con_variable):
                        next_label = now.arg2
                        child.instructions[i].instruction.opcode = 'nop'
                        if child.instructions[i + 1].instruction.opcode == 'jmp':
                            child.instructions[i + 1].instruction.arg1 = next_label
                        f = True

        for i in noNeedBlock:
            self.block.pop(i, None)
            self.remove(i)


    def rec_linear1(self, now, visited_lbl):
        if (now.instructions[-1].instruction.opcode == 'jmp'):
            if (now.instructions[-1].instruction.arg1 not in visited_lbl):
                child = self.block[now.instructions[-1].instruction.arg1]
                visited_lbl.add(now.instructions[-1].instruction.arg1)

                if (child.instructions[-1].instruction.opcode != 'jmp') and (child.instructions[-1].instruction.opcode != 'ret'):
                    child.instructions += [Instructions(Instr('ret', None, None, None))]
                self.visited_str.extend(child.instructions)
                self.rec_linear1(child, visited_lbl)

        for child_lbl in now.child:
            if child_lbl in visited_lbl:
                continue
            child = self.block[child_lbl]
            visited_lbl.add(child_lbl)

            if (child.instructions[-1].instruction.opcode != 'jmp') and (child.instructions[-1].instruction.opcode != 'ret'):
                child.instructions += [Instructions(Instr('ret', None, None, None))]
            self.visited_str.extend(child.instructions)
            self.rec_linear1(child, visited_lbl)


    
    def cleaned(self, flag=True):
        entry = self.block[self.entry_label]
        self.visited_str = list(entry.instructions)
        self.rec_linear1(entry, set([self.entry_label]))

        for str in self.visited_str:
            f = True
            if (str.instruction.opcode == 'jmp') and (str.instruction.dest == 'tmp'):
                str.instruction.opcode = 'nop'
                continue
            if str.instruction.opcode != 'label':
                continue
            for i in self.visited_str:
                if ((i.instruction.opcode in self.cjmp) and (str.instruction.arg1 == i.instruction.arg2)) or \
                    ((i.instruction.opcode == 'jmp') and (str.instruction.arg1 == i.instruction.arg1)):
                    f = False
                    break
            if f:
                str.instruction.opcode = 'nop'

        if flag:
            tac = []
            count = 0
            for i in self.visited_str:
                tac.append(i.instruction)
            
            for i in range(len(tac) - 1):
                j = i - count
                if (tac[j].opcode == 'jmp') and (tac[j + 1].opcode == 'label') and (tac[j + 1].arg1 == tac[j].arg1):
                    tac.pop(j)
                    count += 1
            
            count = 0
            for i in range(len(tac) - 1):
                j = i - count
                now = tac[j]
                if now.opcode == 'ret':
                    if now.arg1 == None:
                        if (tac[j + 1].opcode == 'ret'):
                            tac.pop(j)
                            count += 1
                    else:
                        if (tac[j + 1].opcode == 'ret'):
                            tac.pop(j + 1)
                            count += 1
        else:
            tac = [i.instruction for i in self.visited_str]

        return list(filter(lambda instr: instr.opcode != 'nop', tac))

    def clean_dead_code(self):
        ns = self.cleaned(False)
        self.build(ns)

    def remove(self, block_label):
        for block in self.block.values():
            if block_label in block.child:
                block.child.remove(block_label)
            if block_label in block.father:
                block.father.remove(block_label)

    def coaleasce_blocks(self):
        for block in self.block.values():
            if len(block.child) == 1:
                childlbl = list(block.child)[0]
                child = self.block[childlbl]
                if (len(child.father) != 1) or (childlbl == self.entry_label):
                    continue
                if block.instructions[-1].instruction.opcode == 'jmp':
                    block.instructions[-1].instruction.opcode = 'nop'
                    block.union(child)
                    self.block.pop(childlbl)
                    self.remove(childlbl)
                    return (block.label, childlbl)
        return False

    def coaleasce(self):
        cset = set()
        while True:
            cblocks = self.coaleasce_blocks()
            self.clean_dead_code()
            if cblocks and (cblocks not in cset):
                cset.add(cblocks)
            else:
                break

    def optimize(self):
        self.jump_thread()
        self.clean_dead_code()
        self.coaleasce()

def tac_cfopt(filename):
    gvars, procs = [], []
    name = filename[:-8]
    with open(filename, 'r') as fp:
        js_obj = json.load(fp)
    
    tac = []
    for obj in js_obj:
        if "proc" in obj.keys():
            taco = []
            for line in obj["body"]:
                arg1, arg2 = None, None
                args = line["args"]
                if len(args) == 1 or len(args) == 2:
                    arg1 = args[0]
                    if len(args) == 2:
                        arg2 = args[1]
                taco.append(Instr(line["opcode"], arg1, arg2, line["result"]))
            tac.append(ProcDec(obj["proc"], obj["args"], None, taco, None, None))
        elif "var" in obj:
            tac.append(StatementVarDecl(obj["var"], obj["init"], None, None, None))

    for decl in tac:
        if isinstance(decl, ProcDec):
            if decl.body == []:
                procs.append(ProcDec(decl.name, decl.args, None, [], None, None))
                continue
            
            cfg = ControlFlowGraph(decl.body, decl.name)
            cfg.optimize()
            proc_instrs = cfg.cleaned()
            procs.append(ProcDec(decl.name, decl.args, None, proc_instrs, None, None))

        elif isinstance(decl, StatementVarDecl):
            gvars.append(decl)

    with open(f'{name}tac_opt.json', 'w') as tac_file:
        tac = [i.to_tac() for i in gvars + procs]
        tac_file.write(json.dumps(tac))
