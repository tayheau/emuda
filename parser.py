"""
PTX Grammar

ptx -> statement*
statement -> directive | instruction | label
directive -> kernel | other
other -> directive_name directive_flags";"
directive_name -> "."KW 
directive_flags -> KW+

kernel -> [".visible"] ".entry" KW [( param-list )] "{"kernel_body"}"
param_list -> param+
param -> ".param" "."KW KW
kernel_body -> other | instruction
instruction -> [predicate] opcode (specifier)* operands";"
opcode -> KW
specifier -> "."KW
operands -> [[KW ","]* KW]


"""
from typing import Literal
from dataclasses import dataclass
from pathlib import Path
import re

@dataclass
class Statement:
    tokens: list[str]

@dataclass
class Instruction:
    opcode: str
    operands: list[str] 
    specifiers: list[str] | None = None
    predicate: str | None = None

#.param .type .ptr .space .align N varname
#.param .type .ptr        .align N varname
#.space = { .const, .global, .local, .shared }
@dataclass
class Param:
    type: str
    varname: str

@dataclass
class Kernel:
    name: str
    params: list[Param] 
    instructions: list[Instruction] 
    registers: list[tuple[str, str, int]]

def scanning(src:str|Path) -> list[Statement]:
    return [Statement(splitted) for splitted in map(str.split, open(src, "r"))
            if (len(splitted) > 0 and splitted[0] != "//")]

class Parser:
    def __init__(self, stmnt: list[Statement]):
        self.stmnts = stmnt; self.i = 0
    def _is_kernel(self, stmnt: Statement)->bool: return ".entry" in stmnt.tokens
    def _current(self)->Statement: return self.stmnts[self.i]
    def _is_eof(self)->bool: return self.i >= len(self.stmnts)
    def _next(self, i:int=1)->Statement: self.i += i; return self._current() if not self._is_eof() else Statement(["EOF"])
    def parse(self) -> list[Kernel]:
        print(len(self.stmnts))
        kernels  = []
        while not self._is_eof():
            if self._is_kernel(self._current()): kernels.append(self.parse_kernel())
            else : self._next()
        return kernels
    def parse_kernel(self):
        name = self._current().tokens[-1][:-1]
        params = []; instructions = []; registers = []
        while (c:=self._next()).tokens != [")"]:
            params.append(self._parse_param(c))
        self._next()
        while(c:=self._next()).tokens != ["}"]:
            if not c.tokens[0].startswith("."): instructions.append(self._parse_instruction(c))
            elif c.tokens[0]==".reg": registers.append(self._parse_register(c))
        return Kernel(name, params, instructions, registers)
    def _parse_instruction(self, stmnt:Statement)->Instruction:
        tokens=stmnt.tokens
        predicate = tokens.pop(0) if tokens[0].startswith("@") else None
        opcode, *specifiers = tokens[0].rstrip(";").split(".")
        operands = [t.rstrip(";").rstrip(",") for t in tokens[1:]] if len(tokens)>1 else []
        return Instruction(opcode, operands, specifiers, predicate)
    def _parse_param(self, stmnt:Statement)->Param:
        tokens=stmnt.tokens[1:]
        type = tokens.pop(0).lstrip(".")
        varname = tokens.pop().rstrip(",")
        return Param(type, varname)
    def _parse_register(self, stmnt:Statement)->tuple[str, str, int]:
        tokens=stmnt.tokens
        type = tokens[1].lstrip(".")
        name, n = re.fullmatch(r"(%\w+)<(\d+)>;", tokens[-1]).groups()
        return (type, name, int(n))


if __name__=="__main__":
    stmnts = scanning("./matAdd.ptx")
    parser = Parser(stmnts)
    [kernel] = parser.parse()
    print(kernel.instructions)
