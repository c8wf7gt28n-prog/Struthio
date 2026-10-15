    .section .text.start
    .globl _start
_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    li sp, 0x00F00000
    call bench_main
    li a7, 93
    ecall
