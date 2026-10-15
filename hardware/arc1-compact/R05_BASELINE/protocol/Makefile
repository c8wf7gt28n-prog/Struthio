CC ?= cc
CFLAGS ?= -O2
WARN = -std=c11 -Wall -Wextra -Werror -Wpedantic -Wconversion -Wshadow
CPPFLAGS += -Iinclude
SANITIZER_OPTIONS ?= detect_leaks=0

.PHONY: all test sanitize clean
all: build/libarc1_protocol.so build/test_protocol

build:
	mkdir -p build

build/libarc1_protocol.so: src/arc1_protocol.c include/arc1_protocol.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) -fPIC -shared src/arc1_protocol.c -o $@

build/test_protocol: src/arc1_protocol.c tests/test_protocol.c include/arc1_protocol.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN) src/arc1_protocol.c tests/test_protocol.c -o $@

test: all
	./build/test_protocol
	python3 -m unittest discover -s tests -p 'test_reference.py' -v

sanitize: | build
	$(CC) $(CPPFLAGS) -O1 -g $(WARN) -fsanitize=address,undefined -fno-omit-frame-pointer src/arc1_protocol.c tests/test_protocol.c -o build/test_protocol_sanitize
	ASAN_OPTIONS="$(SANITIZER_OPTIONS)" ./build/test_protocol_sanitize

clean:
	rm -rf build
