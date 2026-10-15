/* Freestanding shim: the shared BT820 driver needs only these two; main.c defines them. */
#ifndef ARC1_SHIM_STRING_H
#define ARC1_SHIM_STRING_H
#include <stddef.h>
void *memset(void *d, int c, size_t n);
void *memcpy(void *d, const void *s, size_t n);
#endif
