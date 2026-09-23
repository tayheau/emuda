from typing import Literal
import math
import struct
import re
from itertools import accumulate, product
from parser import Kernel, Param, scanning, Parser


Dim3 = tuple[int, int, int]
ptx_types = {"s8":"b", "s16":"h", "s32":"i", "s64":"q",
             "u8":"B", "u16":"H", "u32":"I", "u64":"Q",
             "f16":"e", "f32":"f", "f64":"d", "pred":"?"}
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
    def memcpy(self, ptr:int, value:bytearray, method:Literal["HtD", "DtH"]):
        if method == "HtD": self.arena[ptr:ptr+len(value)] = value
        elif method == "DtH": value[:] = self.arena[ptr:ptr+len(value)]

class CTA:
    def __init__(self, nwarps:int):
        self.warps = [Warp() for _ in range(nwarps)]
        self.shared = Arena(Ki(48))

class Warp:
    # def 
    pass


class Emu:
    def __init__(self): 
        self.global_state = Arena()
    def malloc(self, size:int, alignment:int=1): return self.global_state.malloc(size, alignment)
    def memcpy(self, ptr:int, value:bytearray, method:Literal["HtD", "DtH"]): self.global_state.memcpy(ptr, value, method)

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
    def _init_param_space(kernel:Kernel)->tuple[bytearray, list[int]]:
        nbytes = [Emu._get_type_size(p.type, byte=True) for p in kernel.params]
        offsets = [0, *accumulate(nbytes[:-1])]
        return bytearray(sum(nbytes)), offsets
    
    @staticmethod
    def _load_param_space(param_space:bytearray, offsets:list[int], kernel:Kernel, paramValues:list[Type]):
        for offset, param, value in zip(offsets, kernel.params, paramValues):
            encoded_value = Emu.encode(param.type, value)
            memoryview(param_space)[offset:offset+len(encoded_value)]=encoded_value
    #############################

    def __call__(self, kernel:Kernel, gridDim:Dim3, blockDim:Dim3, paramValues:list[Type]):
        state_space = {self.global_state}
        param_space, offsets = Emu._init_param_space(kernel)
        Emu._load_param_space(param_space, offsets, kernel, paramValues)
        #init const_space, global_space, shared_space globally
        #init sreg per CTA : %tid, %ntid, %ctaid, and %nctaid x y z
        #init reg per thread
        #reg & sreg non adressable : no bytearray
        # 32 threads per warps, (blockDim.x * blockDim.y * blockDim.z) 
        warps_per_cta = math.ceil(blockDim[0]*blockDim[1]*blockDim[2]/32)

        CTAs = [CTA(warps_per_cta) for _ in product(range(gridDim[0]), range(gridDim[1]), range(gridDim[2]))]




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
    print(kernel)
    # print(Emu.encode("u16", 12))
