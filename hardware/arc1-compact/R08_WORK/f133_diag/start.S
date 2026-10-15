/* ARC-1 Compact R08 (copied unchanged from R07_WORK/f133_boot) F133 bring-up image entry. The BROM loads the eGON image
 * at 0x00020000 (SRAM A1, 32 KiB); mkimage prepends a 0x60-byte header whose
 * first word jumps here (0x00020060). BUILD-ONLY: never executed on silicon. */
    .section .text.start
    .globl _start
_start:
    la   sp, __stack_top
    la   t0, __bss_start
    la   t1, __bss_end
1:  bgeu t0, t1, 2f
    sd   zero, 0(t0)
    addi t0, t0, 8
    j    1b
2:  call main
3:  wfi
    j    3b
