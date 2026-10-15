/* ARC-1 Compact R06 -- BT820 QSPI host transaction layer (see header). */
#include "bt820_host.h"

#include <string.h>

int bt820_init(bt820_dev *dev, const arc1_spi_hal *hal, uint32_t poll_limit) {
    if (!dev || !hal || !hal->select || !hal->transfer || poll_limit == 0u) return BT820_ERR_ARG;
    memset(dev, 0, sizeof(*dev));
    dev->hal = *hal;
    dev->mode = BT820_BUS_SINGLE;
    dev->poll_limit = poll_limit;
    return BT820_OK;
}

static int check_span(uint32_t addr, size_t n) {
    if ((addr & 3u) != 0u || n == 0u || (n & 3u) != 0u) return BT820_ERR_ARG;
    if (addr >= BT820_ADDR_LIMIT || n > (size_t)(BT820_ADDR_LIMIT - addr)) return BT820_ERR_ARG;
    return BT820_OK;
}

static void addr_bytes(uint32_t addr, int write, uint8_t out[4]) {
    out[0] = (uint8_t)(((addr >> 24) & 0x7Fu) | (write ? 0x80u : 0x00u));
    out[1] = (uint8_t)((addr >> 16) & 0xFFu);
    out[2] = (uint8_t)((addr >> 8) & 0xFFu);
    out[3] = (uint8_t)(addr & 0xFFu);
}

int bt820_write(bt820_dev *dev, uint32_t addr, const uint8_t *data, size_t n) {
    uint8_t hdr[4];
    int rc;
    if (!dev || !data) return BT820_ERR_ARG;
    rc = check_span(addr, n);
    if (rc) return rc;
    /* A write to 0x7Fxxxxxx would start with 0xFF, the host-command prefix
     * (DS 4.5.2.3). The datasheet does not say how the BT820 disambiguates;
     * refuse until the BRT_AN_086 memory map is reviewed. */
    if (addr >= BT820_WRITE_LIMIT) return BT820_ERR_ARG;
    addr_bytes(addr, 1, hdr);
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, hdr, NULL, sizeof hdr);
    if (!rc) rc = dev->hal.transfer(dev->hal.ctx, data, NULL, n);
    dev->hal.select(dev->hal.ctx, 0);
    dev->transactions++;
    return rc ? BT820_ERR_IO : BT820_OK;
}

int bt820_read(bt820_dev *dev, uint32_t addr, uint8_t *data, size_t n) {
    uint8_t hdr[4], b = 0;
    uint32_t polled = 0;
    int rc;
    if (!dev || !data) return BT820_ERR_ARG;
    rc = check_span(addr, n);
    if (rc) return rc;
    addr_bytes(addr, 0, hdr);
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, hdr, NULL, sizeof hdr);
    /* poll for the 0x01 data-valid byte (BT820 DS 4.5.1) */
    while (!rc) {
        rc = dev->hal.transfer(dev->hal.ctx, NULL, &b, 1);
        if (rc) break;
        polled++;
        if (b == 0x01u) break;
        if (polled >= dev->poll_limit) {
            dev->hal.select(dev->hal.ctx, 0);
            dev->last_poll_bytes = polled;
            dev->transactions++;
            return BT820_ERR_TIMEOUT;
        }
    }
    if (!rc) rc = dev->hal.transfer(dev->hal.ctx, NULL, data, n);
    dev->hal.select(dev->hal.ctx, 0);
    dev->last_poll_bytes = polled;
    dev->transactions++;
    return rc ? BT820_ERR_IO : BT820_OK;
}

int bt820_write32(bt820_dev *dev, uint32_t addr, const uint32_t *words, size_t count) {
    uint8_t buf[64];
    size_t done = 0;
    if (!dev || !words || count == 0u || count > (SIZE_MAX / 4u)) return BT820_ERR_ARG;
    if (check_span(addr, count * 4u)) return BT820_ERR_ARG;
    while (done < count) {
        size_t k, chunk = count - done;
        int rc;
        if (chunk > sizeof buf / 4u) chunk = sizeof buf / 4u;
        for (k = 0; k < chunk; k++) {           /* little-endian: ASSUMPTION (BRT_AN_086) */
            uint32_t w = words[done + k];
            buf[4u * k + 0u] = (uint8_t)(w & 0xFFu);
            buf[4u * k + 1u] = (uint8_t)((w >> 8) & 0xFFu);
            buf[4u * k + 2u] = (uint8_t)((w >> 16) & 0xFFu);
            buf[4u * k + 3u] = (uint8_t)((w >> 24) & 0xFFu);
        }
        rc = bt820_write(dev, addr + (uint32_t)(4u * done), buf, 4u * chunk);
        if (rc) return rc;
        done += chunk;
    }
    return BT820_OK;
}

int bt820_read32(bt820_dev *dev, uint32_t addr, uint32_t *value) {
    uint8_t b[4];
    int rc;
    if (!value) return BT820_ERR_ARG;
    rc = bt820_read(dev, addr, b, 4);
    if (rc) return rc;
    *value = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return (*value == BT820_ILLEGAL_WORD) ? BT820_ERR_ILLEGAL_ADDR : BT820_OK;
}

int bt820_host_command(bt820_dev *dev, uint8_t cmd, uint8_t param) {
    uint8_t seq[5];
    int rc;
    if (!dev) return BT820_ERR_ARG;
    if (dev->mode != BT820_BUS_SINGLE) return BT820_ERR_MODE;
    seq[0] = 0xFFu; seq[1] = cmd; seq[2] = param; seq[3] = 0u; seq[4] = 0u;
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, seq, NULL, sizeof seq);
    dev->hal.select(dev->hal.ctx, 0);
    dev->transactions++;
    return rc ? BT820_ERR_IO : BT820_OK;
}

int bt820_host_active(bt820_dev *dev) {
    static const uint8_t seq[5] = {0, 0, 0, 0, 0};
    int rc;
    if (!dev) return BT820_ERR_ARG;
    if (dev->mode != BT820_BUS_SINGLE) return BT820_ERR_MODE;
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, seq, NULL, sizeof seq);
    dev->hal.select(dev->hal.ctx, 0);
    dev->transactions++;
    return rc ? BT820_ERR_IO : BT820_OK;
}

const char *bt820_error_string(int err) {
    switch (err) {
    case BT820_OK: return "ok";
    case BT820_ERR_ARG: return "invalid argument (alignment, length or 31-bit range)";
    case BT820_ERR_IO: return "SPI HAL transfer failed";
    case BT820_ERR_TIMEOUT: return "no 0x01 data-valid byte within poll limit";
    case BT820_ERR_MODE: return "host command needs single channel mode";
    case BT820_ERR_ILLEGAL_ADDR: return "BT820 returned 0xDEADABBA (illegal address)";
    default: return "unknown";
    }
}
