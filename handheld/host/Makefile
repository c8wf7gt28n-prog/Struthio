# STRUTHIO HANDHELD · host builds and tests (no ESP-IDF needed).
#   make -C handheld/host test
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
CORE = ../core/struthio_sim.c ../core/struthio_tower.c ../core/struthio_digest.c ../core/struthio_input.c
HDRS = ../core/struthio_core.h ../core/struthio_input.h
BUILD = build

all: $(BUILD)/replay

$(BUILD)/replay: replay.c $(CORE) $(HDRS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core replay.c $(CORE) -o $@

test: $(BUILD)/replay
	./$(BUILD)/replay ../golden/*.trace

clean:
	rm -rf $(BUILD)
.PHONY: all test clean
