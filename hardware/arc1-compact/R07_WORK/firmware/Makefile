# ARC-1 Compact R07 host firmware layer: HOST_TESTED with mocks only.
# Builds against the UNMODIFIED R05 protocol and compute C sources.
# This is not an F133 build: no cross-compiler, BSP, or boot image (PASS 7).
CC   ?= cc
R05  ?= ../../R05_BASELINE
OUT  ?= build
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
INC   = -Iinclude -Itests -I$(R05)/protocol/include -I$(R05)/compute
SRC   = src/bt820_host.c src/bt820_gfx.c src/t35_link.c src/accel_dispatch.c \
        $(R05)/protocol/src/arc1_protocol.c $(R05)/compute/arc1_transform.c
TSRC  = tests/mocks.c tests/test_bt820.c tests/test_firmware.c

.PHONY: all test sanitize freestanding mutants r06-probe clean
all: test sanitize freestanding mutants r06-probe

$(OUT):
	mkdir -p $(OUT)

$(OUT)/test_firmware: $(SRC) $(TSRC) | $(OUT)
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(TSRC) -o $@

test: $(OUT)/test_firmware
	$(abspath $(OUT))/test_firmware

# AddressSanitizer + UBSan (leak detection disabled like R05: ptrace may be blocked)
sanitize: | $(OUT)
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all \
	  -fno-omit-frame-pointer $(SRC) $(TSRC) -o $(OUT)/test_firmware_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_firmware_san

# Driver sources must compile without a hosted libc beyond string.h/stdint.h.
freestanding: | $(OUT)
	for f in src/bt820_host.c src/bt820_gfx.c src/t35_link.c src/accel_dispatch.c; do \
	  $(CC) -c -O2 $(WARN) -ffreestanding $(INC) $$f -o $(OUT)/$$(basename $$f .c).o || exit 1; done
	@echo "freestanding object compile OK (not a link, not an F133 image)"

# Mutation checks: each broken driver variant must FAIL the test suite.
MUTANTS = MUTANT_NO_MAP_CHECK MUTANT_BIG_ENDIAN MUTANT_CFG_WHILE_ACTIVE MUTANT_NO_WRAP
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(CC) -O1 $(WARN) $(INC) -D$$m $(SRC) $(TSRC) -o $(OUT)/mut_$$m || exit 1; \
	  if timeout 120 $(abspath $(OUT))/mut_$$m > $(OUT)/mut_$$m.log 2>&1; then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m ($$(grep -c '^FAIL' $(OUT)/mut_$$m.log) failing checks)"; fi; done

# Regression probe against the frozen R06 driver: must reproduce the R06 defect.
R06FW ?= ../../R06_WORK/firmware
r06-probe: | $(OUT)
	$(CC) -O1 -std=c11 -I$(R06FW)/include -I$(R06FW)/tests -I$(R05)/protocol/include -I$(R05)/compute \
	  $(R06FW)/src/bt820_host.c $(R06FW)/tests/mocks.c $(R05)/protocol/src/arc1_protocol.c \
	  $(R05)/compute/arc1_transform.c tests/r06_regression_probe.c -o $(OUT)/r06_probe
	@if $(abspath $(OUT))/r06_probe; then echo "UNEXPECTED: R06 accepted the write"; exit 1; \
	  else echo "R06 defect reproduced; R07 suite covers it"; fi

clean:
	rm -rf $(OUT)
