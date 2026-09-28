CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
all: test_input

test_input: test_input.c ../main/struthio_input.c ../main/struthio_input.h
	$(CC) $(CFLAGS) -I../main test_input.c ../main/struthio_input.c -o $@

run: test_input
	./test_input

clean:
	rm -f test_input
