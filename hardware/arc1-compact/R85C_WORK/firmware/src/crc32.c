#include "crc32.h"
uint32_t arc1_crc32(uint32_t crc, const void *p, size_t n)
{
    const uint8_t *b = (const uint8_t *)p;
    crc = ~crc;
    while (n--) {
        int k;
        crc ^= *b++;
        for (k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}
