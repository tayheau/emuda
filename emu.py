from __future__ import annotations
import copy
from dataclasses import dataclass
from matplotlib.pylab import isin
from typing import Literal, Self
import math
import struct
import re
from itertools import accumulate, product
from parser import Kernel, Param, scanning, Parser


@dataclass
class Registers:
    reg: dict[str, bytearray]; sreg: dict[str, int]
    def uar(self, values:dict[str, int|bytearray])->Registers: #update and return 
        for k, v in values.items():
            if k in self.reg and isinstance(v, bytearray): self.reg[k] = v
            elif k in self.sreg and isinstance(v, int): self.sreg[k] = v
            else: raise ValueError(f"issue updating {k} in registers")
        print(self)
        return self
    def copy_for_warp(self, warpid:int)->Registers:
        r = copy.deepcopy(self)
        r.sreg["%warpid"] = warpid
        return r
Dim3 = tuple[int, int, int]
def _dim3_names(n:str): return [f"{n}.{d}" for d in ["x", "y", "z"]]
ptx_types = {"s8":"b", "s16":"h", "s32":"i", "s64":"q",
             "u8":"B", "u16":"H", "u32":"I", "u64":"Q",
             "f16":"e", "f32":"f", "f64":"d", "pred":"?"}
sregsKeys = [*_dim3_names("%tid"), *_dim3_names("%ntid"),
             *_dim3_names("%ctaid"), *_dim3_names("%nctaid"),
             "%laneid", "%warpid", "%nwarpid", ]
Type = float | int | bytes
def Ki(a:int): return a << 10
def Mi(a:int): return a << 20
def Gi(a:int): return a << 30
def BIN_UP_MASK(a:int, b:int): return (a+b-1) & ~(b-1)

class Arena:
    def __init__(self, memsize:int=Ki(48)):
        self.arena = bytearray(memsize)
        self.current_position: int = 0
    def malloc(self, size:int, alignment:int=8)->int:
        pos_aligned = BIN_UP_MASK(self.current_position, alignment)
        if (np:=pos_aligned + size) >= len(self.arena): raise MemoryError("no more allocated memory")
        self.current_position = np
        return pos_aligned
    def memcpy(self, ptr:int, value:bytearray|bytes, method:Literal["HtD", "DtH"]): #byte case works only for HtD
        if method == "HtD": self.arena[ptr:ptr+len(value)] = value
        elif method == "DtH":
            if isinstance(value, bytes): raise ValueError(f"bytes are immutable")
            value[:] = self.arena[ptr:ptr+len(value)]

class CTA:
    def __init__(self, *, nctaid:Dim3, ctaid:Dim3, ntid:Dim3, state_space:list[Arena], registers_templates:Registers, kernel:Kernel,):
        state_space=state_space.copy(); state_space.append(Arena(Ki(48))) #"shared" state space
        registers_templates.sreg["%nwarpid"] = math.ceil((nctaid[0]or 1)*(nctaid[1]or 1)*(nctaid[2]or 1)/32) #null dim should init to 1
        cta_sreg = {"%nctaid":nctaid, "%ctaid":ctaid, "%ntid":ntid}
        for n, dim in cta_sreg.items(): registers_templates.sreg.update(zip(_dim3_names(n), dim))
        self.warps = [Warp(state_space, registers_templates.uar({"%warpid":warpid}),)
                      for warpid in range(registers_templates.sreg["%nwarpid"])]

class Warp:
    def __init__(self, state_space:list[Arena], registers_templates:Registers):
        self.pc=[]; self.initiated=[]; self.alive=[]; self.regs = []
        # for lane in range(32):
        #     l_id = registers_templates.sreg["%wid"]
        #     if (l_id:=registers_templates.sreg["%ntid.x"]
        #
        #
            # check if the thread is alive: linear_id < ntid.x * ntid.y * ntid.z 
            # init pc , pc thread_masking, overflow alive thread_masking 



        # regs = copy.deepcopy(registers_templates) #TODO per thread tid, laneid 
        # print(regs)
    #     for lane in range(32):
    #tid here 
    #linear_id = %warpid * 32 + lane
    # since linear_id = x + ctaid.x (y + ctaid.y z)
    # x = linear_id % ctaid.x
    # y = (linear_id // ctaid.x) % ctaid.y
    # z = linear_id // (ctaid.x * ctaid.y) 


    # pass


class Emu:
    def __init__(self): 
        self.global_state = Arena()
    def malloc(self, size:int, alignment:int=1): return self.global_state.malloc(size, alignment)
    def memcpy(self, ptr:int, value:bytearray|bytes, method:Literal["HtD", "DtH"]): self.global_state.memcpy(ptr, value, method)

    @staticmethod
    def encode(type:str, value:Type)->bytes:
        size = Emu._get_type_size(type, byte=True)
        if type.startswith("b"): 
            if not isinstance(value, (bytes, bytearray)): raise TypeError(f"{type} expects bytes")
            return value.ljust(size, b"\x00")
        if type.startswith("f"): return struct.pack(f"<{ptx_types[type]}", float(value))
        if type == "pred": return struct.pack("<?", bool(value))
        else: return struct.pack(f"<{ptx_types[type]}", int(value))

    @staticmethod
    def decode(type:str, value:bytes)->int|float:
        return struct.unpack(f"<{ptx_types[type]}", value)[0]

    @staticmethod
    def _get_type_size(type:str, byte:bool=False)->int: return int(re.search("\d+", type).group()) // (8 if byte else 1)


    #switch param state to Arena##
    @staticmethod
    def _init_param_space(kernel:Kernel, paramValues:list[Type])->tuple[list[int], Arena]:
        if not len(paramValues) == len(kernel.params): raise ValueError(f"must enter correct number of params")
        param_stsp = Arena(Ki(4)); offsets = [] # CUDA12 param state was 4KiB
        for param, value in zip(kernel.params, paramValues): 
            encoded_value = Emu.encode(param.type, value)
            offsets.append(ptr := param_stsp.malloc(Emu._get_type_size(param.type, byte=True)))
            param_stsp.memcpy(ptr, encoded_value, method="HtD")
        return offsets, param_stsp

    @staticmethod
    def _gen_registers(kernel:Kernel)->Registers:
        return Registers({f"{n}{i}": bytearray(Emu._get_type_size(t, byte=True))
                for t, n, s in kernel.registers for i in range(1, s+1)},
                {name:0x0 for name in sregsKeys})

    def __call__(self, kernel:Kernel, gridDim:Dim3, blockDim:Dim3, paramValues:list[Type]):
        offsets, param_space = Emu._init_param_space(kernel, paramValues)
        registers_templates = Emu._gen_registers(kernel)
        state_space = [self.global_state, param_space]
        # Emu._load_param_space(param_space, offsets, kernel, paramValues)
        #init const_space, global_space, shared_space globally
        #init sreg per CTA : %tid, %ntid, %ctaid, and %nctaid x y z
        # sregsKeys = ["%tid", "%ntid", "%laneid", "%warpid", "%nwarpid", "%ctaid", "%nctaid",]
        #init reg per thread
        #reg & sreg non adressable : no bytearray
        # 32 threads per warps, (blockDim.x * blockDim.y * blockDim.z) 

        # print(registers_templates.sreg)
    
        # print(list( product(range(gridDim[0]), range(gridDim[1]), range(gridDim[2]))))
        CTAs = [CTA(nctaid=gridDim, ntid=blockDim, ctaid=(x,y,z), state_space=state_space, registers_templates=registers_templates, kernel=kernel)
                for x,y,z in product(range(gridDim[0])or[0], range(gridDim[1])or[0], range(gridDim[2])or[0])]
        # print(CTAs)




if __name__=="__main__":
    stmnts = scanning("./matAdd.ptx")
    parser = Parser(stmnts)
    [kernel] = parser.parse()
    emu = Emu()
    A = bytearray([1]*16); dA = emu.malloc(len(bytes(16)))
    B = bytearray([2]*16); dB = emu.malloc(len(bytes(16)))
    dC = emu.malloc(len(bytes(16)))

    emu.memcpy(dA, A, "HtD")
    emu.memcpy(dB, B, "HtD")


    emu(kernel, (2,2,0), (2,2,0), [dA, dB, dC, 16])
    # print(kernel)
    # print(Emu.encode("u16", 12))
