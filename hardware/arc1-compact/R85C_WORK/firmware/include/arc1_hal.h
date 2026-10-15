/* ARC-1 Compact R06 (copied unchanged into R08) -- minimal SPI HAL used by the host-side drivers.
 * HOST_TESTED with mocks only; no F133 BSP binding exists yet (PASS 7). */
#ifndef ARC1_HAL_H
#define ARC1_HAL_H
#include <stddef.h>
#include <stdint.h>

typedef struct arc1_spi_hal {
    void *ctx;
    /* asserted != 0 drives CS# low. The binding must keep CS# high for at
     * least the peripheral's minimum (BT820: 2 SCK cycles) between calls. */
    void (*select)(void *ctx, int asserted);
    /* Full-duplex single-line transfer of n bytes while CS# stays as is.
     * tx == NULL sends 0x00 bytes; rx == NULL discards. Returns 0 on success. */
    int (*transfer)(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n);
    /* Monotonic microseconds, used for timeouts. */
    uint64_t (*now_us)(void *ctx);
} arc1_spi_hal;

#endif
