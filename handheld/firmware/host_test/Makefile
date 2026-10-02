# STRUTHIO HANDHELD · firmware host tests (portable button layer).
#   make -C handheld/firmware/host_test run
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2 -D_GNU_SOURCE
SRC = test_buttons.c ../main/struthio_buttons.c ../../core/struthio_input.c
all: test_buttons
test_buttons: $(SRC) ../main/struthio_buttons.h ../../core/struthio_input.h
	$(CC) $(CFLAGS) -I../main -I../../core $(SRC) -o $@
run: test_buttons
	./test_buttons ../../golden/*.trace
clean:
	rm -f test_buttons
.PHONY: all run clean

# Type-check the hardware-independent firmware sources on the host against
# host_shim/ (a stand-in for the ESP-IDF headers). The board adapter
# (board_waveshare_35b.c, board_pmu.cpp) and everything else are checked
# against the REAL ESP-IDF headers by ../idf_check/idf_check.sh.
FW_SRC = ../main/main.c ../main/service.c ../main/selftest.c ../main/struthio_buttons.c
compile:
	@for f in $(FW_SRC); do $(CC) $(CFLAGS) -fsyntax-only -I../host_shim -I../main -I../../core -I../../render -I../../audio $$f || exit 1; done
	@echo "PASS: firmware sources type-check against host_shim (not a real idf.py build)"
.PHONY: compile
