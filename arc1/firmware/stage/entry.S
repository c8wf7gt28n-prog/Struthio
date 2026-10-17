/* ARC-1 Stage R04 linker smoke image, NOT a silicon-ready reset handler. */
.section .text.entry,"ax",@progbits
.global _start
.type _start,@function
_start:
  la sp, __stack_top
  la t0, __bss_start
  la t1, __bss_end
1:
  bgeu t0, t1, 2f
  sd zero, 0(t0)
  addi t0, t0, 8
  j 1b
2:
  call arc1_stage_main
3:
  wfi
  j 3b
