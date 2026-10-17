# ARC-1 R10 -- F133 bootloader core for the single 64 MiB NOR (ARC1_MEMORY_R10 s7.3 item 4). HOST_TESTED with mocks.
# Reuses R85C_WORK/firmware sources by path (unchanged) except the R10 copies src/spi_nor.c (W25Q512JV) and
# src/ecp5_cfg.c (LFE5U-12 + LFE5U-45 containers); each copy lists its changes in its first comment.
CC   ?= cc
OUT  ?= build
R85C ?= ../../../R85C_WORK/firmware
R05  ?= ../../../R05_BASELINE/compute
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
GL    = ../../f133/graphics_link
D45   = ../../d213/fpga45_loader
INC   = -Iinclude -I$(R85C)/include -I$(R85C)/tests -I$(R05) -I$(GL)/include -I$(D45)/include
SRC   = src/r10_boot.c src/r10_fpga45.c src/spi_nor.c src/ecp5_cfg.c $(GL)/src/gfx_link.c $(D45)/src/d213_fpga45.c $(R85C)/src/crc32.c $(R85C)/src/flash_layout.c
MOCKS = $(R85C)/tests/nor_mock.c $(R85C)/tests/ecp5_mock.c $(R85C)/src/accel_job.c $(R85C)/src/fpga_link.c $(R05)/arc1_transform.c
TSRC  = tests/test_boot.c
PSRC  = tests/test_fpga45_path.c
.PHONY: all layout test sanitize freestanding mutants clean
all: layout test sanitize freestanding mutants
$(OUT):
	mkdir -p $(OUT)
layout:
	python3 -I ../../memory/gen_nor_partition.py
	git diff --exit-code -- include/r10_nor_layout.h ../../memory/R10_nor_partition.csv
test: | $(OUT)
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(MOCKS) tests/test_power_loss.c -o $(OUT)/test_power_loss
	$(abspath $(OUT))/test_power_loss
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(MOCKS) $(TSRC) -o $(OUT)/test_boot
	$(abspath $(OUT))/test_boot
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(MOCKS) $(PSRC) -o $(OUT)/test_fpga45_path
	$(abspath $(OUT))/test_fpga45_path
sanitize: | $(OUT)
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all $(SRC) $(MOCKS) tests/test_power_loss.c -o $(OUT)/test_power_loss_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_power_loss_san
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
	  $(SRC) $(MOCKS) $(TSRC) -o $(OUT)/test_boot_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_boot_san | tail -2
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
	  $(SRC) $(MOCKS) $(PSRC) -o $(OUT)/test_fpga45_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_fpga45_san | tail -2
freestanding: | $(OUT)
	for f in src/r10_boot.c src/r10_fpga45.c src/spi_nor.c src/ecp5_cfg.c $(D45)/src/d213_fpga45.c; do $(CC) -c -O2 $(WARN) -ffreestanding $(INC) $$f -o $(OUT)/$$(basename $$f .c).o || exit 1; done
	@echo "freestanding object compile OK (not a link, not an F133 image)"
MUTANTS = MUTANT_BOOT_NO_LOCK MUTANT_BOOT_NO_GEN MUTANT_BOOT_SAME_COPY MUTANT_BOOT_NO_TRIAL_CONSUME \
          MUTANT_BOOT_NO_GOLDEN MUTANT_BOOT_NO_DISARM MUTANT_GL_NO_DEDUP MUTANT_D213_NO_IDCODE
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(CC) -O1 $(WARN) -Wno-unused-parameter $(INC) -D$$m $(SRC) $(MOCKS) $(TSRC) -o $(OUT)/mut_$$m || exit 1; \
	  $(CC) -O1 $(WARN) -Wno-unused-parameter $(INC) -D$$m $(SRC) $(MOCKS) $(PSRC) -o $(OUT)/mutp_$$m || exit 1; \
	  if timeout 120 $(abspath $(OUT))/mut_$$m > $(OUT)/mut_$$m.log 2>&1 && timeout 120 $(abspath $(OUT))/mutp_$$m >> $(OUT)/mut_$$m.log 2>&1; \
	  then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m ($$(grep -c '^FAIL' $(OUT)/mut_$$m.log) failing checks)"; fi; done
clean:
	rm -rf $(OUT)
