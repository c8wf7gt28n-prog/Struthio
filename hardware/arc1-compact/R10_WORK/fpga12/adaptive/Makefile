CC ?= cc
OUT ?= build
WARN = -std=c11 -Wall -Wextra -Werror -Wshadow -Iinclude
.PHONY: all test sanitize freestanding mutants clean
all: test sanitize freestanding mutants
test:
	mkdir -p $(OUT)
	$(CC) -O2 $(WARN) src/arc1_mechanics.c tests/test_mechanics.c -o $(OUT)/test_mechanics
	$(abspath $(OUT))/test_mechanics
sanitize:
	mkdir -p $(OUT)
	$(CC) -O1 -g $(WARN) -fsanitize=address,undefined src/arc1_mechanics.c tests/test_mechanics.c -o $(OUT)/test_mechanics_san
	ASAN_OPTIONS=detect_leaks=0 $(abspath $(OUT))/test_mechanics_san
freestanding:
	mkdir -p $(OUT)
	$(CC) -O2 $(WARN) -ffreestanding -fno-builtin -c src/arc1_mechanics.c -o $(OUT)/arc1_mechanics.o
mutants:
	mkdir -p $(OUT)
	$(CC) -O2 $(WARN) -DARC1_MECH_MUTANT_INCLUSIVE src/arc1_mechanics.c tests/test_mechanics.c -o $(OUT)/mut_inclusive
	@if $(abspath $(OUT))/mut_inclusive > $(OUT)/mut_inclusive.log; then echo "MUTANT_SURVIVED inclusive edges"; exit 1; \
	else echo "MUTANT_KILLED inclusive edges ($$(grep -c '^FAIL' $(OUT)/mut_inclusive.log) failing checks)"; fi
clean:
	rm -rf $(OUT)
