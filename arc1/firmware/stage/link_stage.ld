/* UNQUALIFIED hypothetical memory layout. 0x20000 is a linker-test address, NOT a D213 load address. */
OUTPUT_ARCH(riscv)
ENTRY(_start)
MEMORY { STAGE_RAM (rwx) : ORIGIN = 0x00020000, LENGTH = 0x00020000 }
SECTIONS {
  . = ORIGIN(STAGE_RAM);
  .text : { KEEP(*(.text.entry)) *(.text .text.*) } > STAGE_RAM
  .rodata : { *(.rodata .rodata.*) KEEP(*(.arc1.stage)) } > STAGE_RAM
  .data : { *(.sdata .sdata.*) *(.data .data.*) } > STAGE_RAM
  .bss (NOLOAD) : {
    . = ALIGN(8); __bss_start = .;
    *(.sbss .sbss.*) *(.bss .bss.*) *(COMMON)
    . = ALIGN(8); __bss_end = .;
  } > STAGE_RAM
  . = ALIGN(16);
  __stack_top = ORIGIN(STAGE_RAM) + LENGTH(STAGE_RAM);
  ASSERT(__bss_end + 4096 <= __stack_top, "No room for 4KiB stack")
}
