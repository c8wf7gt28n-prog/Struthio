# ARC-1 R10 -- F133 <-> D213 graphics command link (USB bulk transport, protocol layer only). HOST_TESTED.
CC   ?= cc
OUT  ?= build
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
INC   = -Iinclude
SRC   = src/gfx_link.c
TSRC  = tests/test_gfx.c
.PHONY: all test sanitize freestanding mutants clean
all: test sanitize freestanding mutants
$(OUT):
	mkdir -p $(OUT)
test: | $(OUT)
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(TSRC) -o $(OUT)/test_gfx
	$(abspath $(OUT))/test_gfx
sanitize: | $(OUT)
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer \
	  $(SRC) $(TSRC) -o $(OUT)/test_gfx_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_gfx_san | tail -1
freestanding: | $(OUT)
	$(CC) -c -O2 $(WARN) -ffreestanding $(INC) $(SRC) -o $(OUT)/gfx_link.o
	@echo "freestanding object compile OK (not a link, not an F133/D213 image)"
MUTANTS = MUTANT_GL_NO_CRC MUTANT_GL_NO_SEQ_MATCH MUTANT_GL_NO_DEDUP MUTANT_GL_NO_BOOTID MUTANT_GL_NO_ORDER \
          MUTANT_GL_NO_WATCHDOG MUTANT_GL_NO_REPROBE
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(CC) -O1 $(WARN) -Wno-unused-function $(INC) -D$$m $(SRC) $(TSRC) -o $(OUT)/mut_$$m || exit 1; \
	  if timeout 60 $(abspath $(OUT))/mut_$$m > $(OUT)/mut_$$m.log 2>&1; then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m ($$(grep -c '^FAIL' $(OUT)/mut_$$m.log) failing checks)"; fi; done
clean:
	rm -rf $(OUT)
