# ARC-1 Compact R08 host firmware: NOR boot flash driver, flash layout / A/B
# journal, microSD game library. HOST_TESTED with mocks only (not silicon).
CC   ?= cc
OUT  ?= build
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
INC   = -Iinclude -Itests
SRC   = src/spi_nor.c src/flash_layout.c src/game_lib.c src/crc32.c
TSRC  = tests/nor_mock.c tests/test_nor.c tests/test_layout.c tests/test_library.c tests/test_main.c

.PHONY: all test sanitize freestanding mutants clean
all: test sanitize freestanding mutants
$(OUT):
	mkdir -p $(OUT)
$(OUT)/test_r08: $(SRC) $(TSRC) | $(OUT)
	$(CC) -O2 $(WARN) $(INC) $(SRC) $(TSRC) -o $@
test: $(OUT)/test_r08
	$(abspath $(OUT))/test_r08
sanitize: | $(OUT)
	$(CC) -O1 -g $(WARN) $(INC) -fsanitize=address,undefined -fno-sanitize-recover=all \
	  -fno-omit-frame-pointer $(SRC) $(TSRC) -o $(OUT)/test_r08_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_r08_san
freestanding: | $(OUT)
	for f in $(SRC); do $(CC) -c -O2 $(WARN) -ffreestanding $(INC) $$f -o $(OUT)/$$(basename $$f .c).o || exit 1; done
	@echo "freestanding object compile OK (not a link, not an F133 image)"
MUTANTS = MUTANT_NOR_3B_UPPER MUTANT_NOR_ENTER_4B MUTANT_NOR_NO_WIP_POLL MUTANT_NOR_NO_EAR_RESTORE
mutants: | $(OUT)
	@for m in $(MUTANTS); do \
	  $(CC) -O1 $(WARN) $(INC) -D$$m $(SRC) $(TSRC) -o $(OUT)/mut_$$m || exit 1; \
	  if timeout 120 $(abspath $(OUT))/mut_$$m > $(OUT)/mut_$$m.log 2>&1; then echo "MUTANT_SURVIVED $$m"; exit 1; \
	  else echo "MUTANT_KILLED $$m ($$(grep -c '^FAIL' $(OUT)/mut_$$m.log) failing checks)"; fi; done
clean:
	rm -rf $(OUT)
