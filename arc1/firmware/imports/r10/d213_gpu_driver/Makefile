# ARC-1 R10 -- D213-side GPU driver core, tested against the bit-exact 45F GPU model. HOST_TESTED.
CC  ?= cc
OUT ?= build
F45 ?= ../../fpga45
WARN = -std=c11 -Wall -Wextra -Werror -Wshadow
.PHONY: all test mutants clean
all: test mutants
test:
	mkdir -p $(OUT)
	$(CC) -O2 $(WARN) -Wno-unused-function -DGPU_REF_LIB -c $(F45)/tools/gpu_ref.c -o $(OUT)/gpu_ref_lib.o
	$(CC) -O2 $(WARN) -Iinclude -I$(F45)/abi src/r10_gpu.c tests/test_gpu_driver.c $(OUT)/gpu_ref_lib.o -lm -o $(OUT)/test_gpu_driver
	$(abspath $(OUT))/test_gpu_driver
mutants: test
	$(CC) -O2 $(WARN) -Iinclude -I$(F45)/abi -DGPU_W_RATIO=1e9f src/r10_gpu.c tests/test_gpu_driver.c $(OUT)/gpu_ref_lib.o -lm -o $(OUT)/mut_nosplit
	if $(abspath $(OUT))/mut_nosplit > $(OUT)/mut_nosplit.log; then echo "MUTANT_SURVIVED no w-ratio split"; exit 1; \
	  else echo "MUTANT_KILLED no w-ratio split ($$(grep -c '^FAIL' $(OUT)/mut_nosplit.log) failing checks)"; fi
clean:
	rm -rf $(OUT)
