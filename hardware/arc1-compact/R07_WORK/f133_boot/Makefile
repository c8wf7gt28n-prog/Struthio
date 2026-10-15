# ARC-1 Compact R07 F133 bare-metal bring-up image. BUILD-ONLY evidence:
# compiled and packaged, never executed on silicon.
CROSS   ?= riscv64-unknown-elf-
CC       = $(CROSS)gcc
OBJCOPY  = $(CROSS)objcopy
OBJDUMP  = $(CROSS)objdump
SIZE     = $(CROSS)size
MKIMAGE ?= mkimage
OUT     ?= build
FW       = ../firmware
CFLAGS   = -march=rv64imac_zicsr -mabi=lp64 -mcmodel=medany -Os -ffreestanding -fno-builtin \
           -nostdlib -fno-pic -std=c11 -Wall -Wextra -Werror -Wconversion -I. -Ishim -I$(FW)/include
SRC      = start.S main.c $(FW)/src/bt820_host.c $(FW)/src/bt820_gfx.c

.PHONY: all check clean
all: $(OUT)/arc1_r07_f133.egon check

$(OUT):
	mkdir -p $(OUT)
$(OUT)/arc1_r07_f133.elf: $(SRC) link.ld f133_regs.h | $(OUT)
	$(CC) $(CFLAGS) -T link.ld -Wl,--gc-sections -Wl,-Map=$(OUT)/arc1_r07_f133.map $(SRC) -lgcc -o $@
$(OUT)/arc1_r07_f133.bin: $(OUT)/arc1_r07_f133.elf
	$(OBJCOPY) -O binary $< $@
$(OUT)/arc1_r07_f133.egon: $(OUT)/arc1_r07_f133.bin
	$(MKIMAGE) -T sunxi_egon -A riscv -d $< $@
check: $(OUT)/arc1_r07_f133.egon
	$(SIZE) $(OUT)/arc1_r07_f133.elf
	$(OBJDUMP) -d $(OUT)/arc1_r07_f133.elf | sed -n '1,12p'
	python3 -I egon_check.py $<
	sha256sum $(OUT)/arc1_r07_f133.egon $(OUT)/arc1_r07_f133.elf
	@echo "SD card placement: dd if=arc1_r07_f133.egon of=/dev/sdX bs=1024 seek=8  (sector 16, 8 KiB offset)"
clean:
	rm -rf $(OUT)
