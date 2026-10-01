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
