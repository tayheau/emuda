#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef uint8_t u8;
typedef _Float16 f16;

__global__ void matAdd(u8*A, u8*B, u8*C, u8 N){
	u8 col = blockIdx.x * blockDim.x + threadIdx.x;
	u8 row = blockIdx.y * blockDim.y + threadIdx.y;
	C[N*col + row] = A[N*col+row] + B[N*col+row];
}

// int main(int argc, char* argv[]) {
// 	u8 N = 16;
// 	size_t bytes = N * N * sizeof(f16);
// 	u8 *A, *B, *C, *dA, *dB, *dC;
// 	A = (u8*)malloc(bytes);
// 	B = (u8*)malloc(bytes);
// 	C = (u8*)calloc(bytes, sizeof(f16));
// 	memset(A, 0x01, bytes);
// 	memset(B, 0x02, bytes);
// 	// printf("%zu\n", sizeof(f16));
// 	// return 0;
// 	cudaMalloc((void**)&dA, bytes);
// 	cudaMalloc((void**)&dB, bytes);
// 	cudaMalloc((void**)&dC, bytes);
//
// 	cudaMemcpy(dA, A, bytes, cudaMemcpyHostToDevice);
// 	cudaMemcpy(dB, B, bytes, cudaMemcpyHostToDevice);
//
// 	dim3 block(8, 4);
// 	dim3 grid(2, 4);
// 	matAdd<<<grid, block>>>(dA, dB, dC, N);
// 	cudaMemcpy(C, dC, bytes, cudaMemcpyDeviceToHost);
// 	free(A); free(B); free(C);
// 	cudaFree(dA); cudaFree(dB); cudaFree(dC);
// 	return 0;
// }
