import re
from parser import Kernel, Param, scanning, Parser

class Thread:
    pass

class Warp:
    pass

Dim3 = tuple[int, int, int]

class Emu:
    def _init_param_space(self, params:list[Param])->bytearray:
        nbytes = int( sum([int(re.search("\d+", p.type).group()) for p in params]) / 8)
        return bytearray(nbytes)

    def __call__(self, kernel:Kernel, gridDim:Dim3, blockDim:Dim3, params:list[bytes]):
        param_space = self._init_param_space(kernel.params)

if __name__=="__main__":
    stmnts = scanning("./matAdd.ptx")
    parser = Parser(stmnts)
    [kernel] = parser.parse()
    emu = Emu()
    emu(kernel, None, None, None)
        
