import math
import struct
import re
from itertools import accumulate
from parser import Kernel, Param, scanning, Parser

class CTA:
    def __init__(self, nwarps:int):
        self.warps = [Warp() for _ in range(nwarps)]
        self.shared = bytearray(48_000)

class Warp:
    pass

Dim3 = tuple[int, int, int]
ptx_types = {"s8":"b", "s16":"h", "s32":"i", "s64":"q",
             "u8":"B", "u16":"H", "u32":"I", "u64":"Q",
             "f16":"e", "f32":"f", "f64":"d", "pred":"?"}
Type = float | int | bytes

class Emu:
    @staticmethod
    def encode(type:str, value:Type)->bytes:
        if type.startswith("b"): return Emu._encode_bits(type, value)
        return Emu._encode_type(type, value)

    @staticmethod
    def _encode_type(type:str, value:int|float)->bytes:
        return struct.pack(f"<{ptx_types[type]}", value)

    @staticmethod
    def  _encode_bits(type:str, value:bytes)->bytes:
        size = Emu._get_type_size(type, byte=True)
        return value.ljust(size, bytes.fromhex("00")) #since nvidia is small-endian

    @staticmethod
    def _get_type_size(type:str, byte:bool=False)->int: return int(re.search("\d+", type).group()) // (8 if byte else 1)


    @staticmethod
    def _init_param_space(kernel:Kernel)->tuple[bytearray, list[int]]:
        nbytes = [Emu._get_type_size(p.type, byte=True) for p in kernel.params]
        offsets = [0, *accumulate(nbytes[:-1])]
        return bytearray(sum(nbytes)), offsets
    
    @staticmethod
    def _load_param_space(param_space:bytearray, offsets:list[int], kernel:Kernel, paramValues:list[bytes]):
        for offset, param, value in zip(offsets, kernel.params, paramValues):
            encoded_value = Emu.encode(param.type, value)
            memoryview(param_space)[offset:offset+len(encoded_value)]=encoded_value
        
    def __call__(self, kernel:Kernel, gridDim:Dim3, blockDim:Dim3, paramValues:list[bytes]):
        param_space, offets = Emu._init_param_space(kernel)
        Emu._load_param_space(param_space, offets, kernel, paramValues)
        #init const_space, global_space, shared_space globally
        #init sreg per CTA : %tid, %ntid, %ctaid, and %nctaid x y z
        #init reg per thread
        # 32 threads per warps, (blockDim.x * blockDim.y * blockDim.z) 
        warps_per_cta = math.ceil(blockDim[0]*blockDim[1]*blockDim[2]/32)

        #below is wrong since need to send %ctaid x y z => itertools.product
        # CTAs = [CTA(warps_per_cta) for _ in range(gridDim[0] * gridDim[1] * gridDim[2])]



if __name__=="__main__":
    stmnts = scanning("./matAdd.ptx")
    parser = Parser(stmnts)
    [kernel] = parser.parse()
    emu = Emu()
    emu(kernel, None, None, None)
    print(Emu.encode("u16", 12))
