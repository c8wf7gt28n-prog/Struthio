OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { SRAM (rwx) : ORIGIN = 0x00020060, LENGTH = 32K - 0x60 }
SECTIONS {
  .text : { KEEP(*(.text.start)) *(.text*) } > SRAM
  .rodata : { *(.rodata*) *(.srodata*) } > SRAM
  .data : { *(.data*) *(.sdata*) } > SRAM
  .bss (NOLOAD) : { . = ALIGN(8); __bss_start = .; *(.bss*) *(.sbss*) *(COMMON) . = ALIGN(8); __bss_end = .; } > SRAM
  __stack_top = ORIGIN(SRAM) + LENGTH(SRAM);
  /DISCARD/ : { *(.comment) *(.eh_frame*) *(.riscv.attributes) }
}
