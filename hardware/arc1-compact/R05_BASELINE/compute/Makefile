CC ?= cc
PYTHON ?= python3
IVERILOG ?= iverilog
VVP ?= vvp
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Werror -Wconversion -Wshadow -pedantic

.PHONY: all check check-c check-hdl clean
all: build/libarc1_transform.so build/vector_check

build:
	mkdir -p build

build/libarc1_transform.so: arc1_transform.c arc1_transform.h | build
	$(CC) $(CFLAGS) -fPIC -shared -I. arc1_transform.c -o $@

build/vector_check: arc1_transform.c arc1_transform.h tests/vector_check.c | build
	$(CC) $(CFLAGS) -fsanitize=undefined -fno-sanitize-recover=all -I. arc1_transform.c tests/vector_check.c -o $@

build/vectors.hex: tests/generate_vectors.py | build
	$(PYTHON) tests/generate_vectors.py $@

check-c: all build/vectors.hex
	./build/vector_check build/vectors.hex
	$(PYTHON) tests/test_reference.py build/libarc1_transform.so

build/transform_tb: rtl/arc1_transform.sv tests/transform_tb.sv | build
	$(IVERILOG) -g2012 -Wall -s transform_tb -o $@ $^

check-hdl: build/transform_tb build/vectors.hex
	$(VVP) build/transform_tb +VECTORS=build/vectors.hex

check: check-c check-hdl

clean:
	rm -rf build __pycache__ tests/__pycache__
