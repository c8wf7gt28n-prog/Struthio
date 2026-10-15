# ARC-1 Compact R8.5 host firmware: NOR boot flash driver, flash layout / A/B journal, microSD game library (R08,
# unchanged) + ECP5 sysCONFIG loader, AMBX v3 link, AJOB framing, accelerator service P0..P6 (R8.5).
# HOST_TESTED with mocks only (not silicon).
CC   ?= cc
OUT  ?= build
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
R05  ?= ../../R05_BASELINE/compute
INC   = -Iinclude -Itests -I$(R05)
SRC   = src/spi_nor.c src/flash_layout.c src/game_lib.c src/crc32.c src/ecp5_cfg.c src/fpga_link.c src/accel_job.c src/accel_service.c
REFC  = $(R05)/arc1_transform.c
TSRC  = tests/nor_mock.c tests/test_nor.c tests/test_layout.c tests/test_library.c tests/ecp5_mock.c tests/test_ecp5.c tests/test_main.c

.PHONY: all test sanitize freestanding mutants clean
all: test sanitize freestanding mutants
$(OUT):
	mkdir -p $(OUT)
$(OUT)/test_r85: $(SRC) $(TSRC) | $(OUT)
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(REFC) $(TSRC) -o $@
test: $(OUT)/test_r85
	$(abspath $(OUT))/test_r85
sanitize: | $(OUT)
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all \
	  -fno-omit-frame-pointer $(SRC) $(REFC) $(TSRC) -o $(OUT)/test_r85_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_r85_san
freestanding: | $(OUT)
	for f in $(SRC); do $(CC) -c -O2 $(WARN) -ffreestanding $(INC) $$f -o $(OUT)/$$(basename $$f .c).o || exit 1; done
	@echo "freestanding object compile OK (not a link, not an F133 image)"
MUTANTS = MUTANT_NOR_3B_UPPER MUTANT_NOR_ENTER_4B MUTANT_NOR_NO_WIP_POLL MUTANT_NOR_NO_EAR_RESTORE \
          MUTANT_ECP5_NO_IMAGE_CRC MUTANT_ECP5_NO_IDCODE MUTANT_ECP5_NO_STATUS_CHECK MUTANT_SVC_NO_SAFE_ON_FAULT \
          MUTANT_SVC_NO_KAT MUTANT_SVC_NO_ABORT
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(CC) -O1 $(WARN) $(INC) -D$$m $(SRC) $(REFC) $(TSRC) -o $(OUT)/mut_$$m || exit 1; \
	  if timeout 120 $(abspath $(OUT))/mut_$$m > $(OUT)/mut_$$m.log 2>&1; then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m ($$(grep -cE '^FAIL|[|] FAIL$$' $(OUT)/mut_$$m.log) failing checks)"; fi; done
clean:
	rm -rf $(OUT)
