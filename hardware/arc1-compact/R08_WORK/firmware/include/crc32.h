#ifndef ARC1_CRC32_H
#define ARC1_CRC32_H
#include <stddef.h>
#include <stdint.h>
/* IEEE 802.3 CRC-32 (reflected, poly 0xEDB88320, init/xorout 0xFFFFFFFF) */
uint32_t arc1_crc32(uint32_t crc, const void *p, size_t n);
#endif
