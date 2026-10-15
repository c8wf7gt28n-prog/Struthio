# ARC-1 Compact R06 host firmware layer: HOST_TESTED with mocks only.
# Builds against the UNMODIFIED R05 protocol and compute C sources.
# This is not an F133 build: no cross-compiler, BSP, or boot image (PASS 7).
CC   ?= cc
R05  ?= ../../R05_BASELINE
OUT  ?= build
WARN  = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
INC   = -Iinclude -Itests -I$(R05)/protocol/include -I$(R05)/compute
SRC   = src/bt820_host.c src/t35_link.c src/accel_dispatch.c \
        $(R05)/protocol/src/arc1_protocol.c $(R05)/compute/arc1_transform.c
TSRC  = tests/mocks.c tests/test_firmware.c

.PHONY: all test sanitize freestanding clean
all: test sanitize freestanding

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
	for f in src/bt820_host.c src/t35_link.c src/accel_dispatch.c; do \
	  $(CC) -c -O2 $(WARN) -ffreestanding $(INC) $$f -o $(OUT)/$$(basename $$f .c).o || exit 1; done
	@echo "freestanding object compile OK (not a link, not an F133 image)"

clean:
	rm -rf $(OUT)
