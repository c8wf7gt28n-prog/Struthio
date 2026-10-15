# ARC-1 Compact R8.5 F133 diagnostic image (R08 image with the ECP5 S4/S5 stages). BUILD-ONLY evidence: compiled and
# packaged, never executed on silicon. Reuses the R07 host-tested BT820 driver
# (R07_WORK/firmware, unchanged) and the R08 host-tested NOR/layout code.
CROSS   ?= riscv64-unknown-elf-
CC       = $(CROSS)gcc
OBJCOPY  = $(CROSS)objcopy
SIZE     = $(CROSS)size
MKIMAGE ?= mkimage
OUT     ?= build
FW7      = ../../R07_WORK/firmware
FW8      = ../firmware
CFLAGS   = -march=rv64imac_zicsr -mabi=lp64 -mcmodel=medany -Os -ffreestanding -fno-builtin \
           -nostdlib -fno-pic -std=c11 -Wall -Wextra -Werror -Wconversion -I. -Ishim -I$(FW8)/include -I$(FW7)/include
SRC      = start.S main.c $(FW7)/src/bt820_host.c $(FW7)/src/bt820_gfx.c \
           $(FW8)/src/spi_nor.c $(FW8)/src/flash_layout.c $(FW8)/src/crc32.c \
           $(FW8)/src/ecp5_cfg.c $(FW8)/src/fpga_link.c

.PHONY: all check clean
all: $(OUT)/arc1_r85_diag.egon check
$(OUT):
	mkdir -p $(OUT)
$(OUT)/arc1_r85_diag.elf: $(SRC) link.ld f133_regs.h $(FW8)/include/board_pins_r85.h | $(OUT)
	$(CC) $(CFLAGS) -T link.ld -Wl,--gc-sections -Wl,-Map=$(OUT)/arc1_r85_diag.map $(SRC) -lgcc -o $@
$(OUT)/arc1_r85_diag.bin: $(OUT)/arc1_r85_diag.elf
	$(OBJCOPY) -O binary $< $@
$(OUT)/arc1_r85_diag.egon: $(OUT)/arc1_r85_diag.bin
	$(MKIMAGE) -T sunxi_egon -A riscv -d $< $@
check: $(OUT)/arc1_r85_diag.egon
	$(SIZE) $(OUT)/arc1_r85_diag.elf
	python3 -I egon_check.py $<
	sha256sum $(OUT)/arc1_r85_diag.egon $(OUT)/arc1_r85_diag.elf
	@echo "Placement: NOR offset 0 (boot0). First-article / FEL procedure: docs/RECOVERY_DOSSIER.md"
clean:
	rm -rf $(OUT)
