/* ARC-1 Compact R07 -- BT820 QSPI host transaction layer (see header). */
#include "bt820_host.h"

#include <string.h>

#include "bt820_regs.h"

int bt820_init(bt820_dev *dev, const arc1_spi_hal *hal, uint32_t poll_limit, uint32_t ram_g_bytes) {
    if (!dev || !hal || !hal->select || !hal->transfer || poll_limit == 0u) return BT820_ERR_ARG;
    if (ram_g_bytes <= BT820_RAM_G_RESERVED_TOP || ram_g_bytes > BT820_RAM_G_END) return BT820_ERR_ARG;
    memset(dev, 0, sizeof(*dev));
    dev->hal = *hal;
    dev->mode = BT820_BUS_SINGLE;
    dev->power = BT820_PWR_SLEEP;      /* state after RST_N / power-up [AN086 2.3] */
    dev->poll_limit = poll_limit;
    dev->ram_g_bytes = ram_g_bytes;
    return BT820_OK;
}

/* Accessible regions [AN086 Table 2 + Reg. Def. 128]; note 1 says anything
 * else is reserved and shall not be read or written. */
typedef struct { uint32_t base, size; } region_t;
static const region_t k_regions[] = {
    {BT820_RAM_CMD, 0x4000u}, {BT820_REG_CORE_R2, 0x800u}, {BT820_RAM_REPORT, 0x80u},
    {BT820_REG_CORE_R1, 0x1000u}, {BT820_RAM_DL, 0x4000u}, {BT820_REG_CMDB_WRITE, 4u},
    {BT820_REG_LVDSTX, 0x100u}, {BT820_REG_SYS, 0x100u}, {BT820_REG_LVDSRX, 0x100u},
    {BT820_REG_I2S, 0x100u},
};

int bt820_span_valid(const bt820_dev *dev, uint32_t addr, size_t n) {
    size_t i;
    uint64_t end = (uint64_t)addr + n;
    if (!dev || n == 0u || (addr & 3u) != 0u || (n & 3u) != 0u || end > BT820_ADDR_LIMIT) return 0;
#ifdef MUTANT_NO_MAP_CHECK
    return 1;                                                   /* verification mutant */
#endif
    if (end <= (uint64_t)(dev->ram_g_bytes - BT820_RAM_G_RESERVED_TOP)) return 1;   /* usable RAM_G */
    for (i = 0; i < sizeof k_regions / sizeof k_regions[0]; i++)
        if (addr >= k_regions[i].base && end <= (uint64_t)k_regions[i].base + k_regions[i].size) return 1;
    return 0;
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
    if (!dev || !data || !bt820_span_valid(dev, addr, n)) return BT820_ERR_ARG;
    addr_bytes(addr, 1, hdr);
    /* defence in depth: a write frame must never look like a host command */
    if (hdr[0] == 0xFFu && hdr[1] >= 0xE0u && hdr[1] <= 0xEFu) return BT820_ERR_ARG;
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
    if (!dev || !data || !bt820_span_valid(dev, addr, n)) return BT820_ERR_ARG;
    addr_bytes(addr, 0, hdr);
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, hdr, NULL, sizeof hdr);
    while (!rc) {                                   /* poll for 0x01 [DS 4.5.1] */
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
    uint8_t buf[256];
    size_t done = 0;
    if (!dev || !words || count == 0u || count > (SIZE_MAX / 4u)) return BT820_ERR_ARG;
    if (!bt820_span_valid(dev, addr, count * 4u)) return BT820_ERR_ARG;
    while (done < count) {
        size_t k, chunk = count - done;
        int rc;
        if (chunk > sizeof buf / 4u) chunk = sizeof buf / 4u;
        for (k = 0; k < chunk; k++) {            /* little endian (EveApps transfer32) */
            uint32_t w = words[done + k];
#ifdef MUTANT_BIG_ENDIAN
            w = (w >> 24) | ((w >> 8) & 0xFF00u) | ((w << 8) & 0xFF0000u) | (w << 24);   /* verification mutant */
#endif
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

int bt820_wr32(bt820_dev *dev, uint32_t addr, uint32_t value) { return bt820_write32(dev, addr, &value, 1); }

int bt820_read32(bt820_dev *dev, uint32_t addr, uint32_t *value) {
    uint8_t b[4];
    int rc;
    if (!value) return BT820_ERR_ARG;
    rc = bt820_read(dev, addr, b, 4);
    if (rc) return rc;
    *value = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return (*value == BT820_ILLEGAL_WORD) ? BT820_ERR_ILLEGAL_ADDR : BT820_OK;
}

static int send5(bt820_dev *dev, const uint8_t seq[5]) {
    int rc;
    dev->hal.select(dev->hal.ctx, 1);
    rc = dev->hal.transfer(dev->hal.ctx, seq, NULL, 5);
    dev->hal.select(dev->hal.ctx, 0);
    dev->transactions++;
    return rc ? BT820_ERR_IO : BT820_OK;
}

int bt820_host_command(bt820_dev *dev, uint8_t code, uint8_t param) {
    uint8_t seq[5];
    int cfg, rc;
    if (!dev) return BT820_ERR_ARG;
    switch (code) {
    case BT820_HC_STANDBY: case BT820_HC_SLEEP: case BT820_HC_POWERDOWN: case BT820_HC_RESET_PULSE:
        cfg = 0; break;
    case BT820_HC_SETPLLSP1: case BT820_HC_SETSYSCLKDIV: case BT820_HC_SETBOOTCFG:
    case BT820_HC_BOOTCFGEN: case BT820_HC_SETDDRTYPE:
        cfg = 1; break;
    default:
        return BT820_ERR_ARG;                       /* not in AN086 Table 3 */
    }
    if (!cfg && param != 0u) return BT820_ERR_ARG;  /* power commands carry 0x00 */
    if (dev->mode != BT820_BUS_SINGLE) return BT820_ERR_MODE;   /* ignored in dual/quad [AN086 2.3] */
#ifndef MUTANT_CFG_WHILE_ACTIVE
    if (cfg && dev->power == BT820_PWR_ACTIVE) return BT820_ERR_STATE;
#endif  /* "effective ONLY in low-power state" */
    seq[0] = 0xFFu; seq[1] = code; seq[2] = param; seq[3] = 0u; seq[4] = 0u;
    rc = send5(dev, seq);
    if (rc) return rc;
    if (code == BT820_HC_STANDBY) dev->power = BT820_PWR_STANDBY;
    else if (code == BT820_HC_SLEEP) dev->power = BT820_PWR_SLEEP;
    else if (code == BT820_HC_POWERDOWN) dev->power = BT820_PWR_POWERDOWN;
    /* RESET_PULSE: clocks stay active, no return to SLEEP [AN086 Table 3] */
    return BT820_OK;
}

int bt820_host_active(bt820_dev *dev) {
    static const uint8_t seq[5] = {0, 0, 0, 0, 0};
    int rc;
    if (!dev) return BT820_ERR_ARG;
    if (dev->mode != BT820_BUS_SINGLE) return BT820_ERR_MODE;
    rc = send5(dev, seq);
    if (!rc) dev->power = BT820_PWR_ACTIVE;
    return rc;
}

void bt820_note_hw_reset(bt820_dev *dev) {
    if (!dev) return;
    dev->power = BT820_PWR_SLEEP;
    dev->mode = BT820_BUS_SINGLE;                   /* SPI single channel after POR/RST_N */
}

const char *bt820_error_string(int err) {
    switch (err) {
    case BT820_OK: return "ok";
    case BT820_ERR_ARG: return "invalid argument (alignment, length, unmapped address or command code)";
    case BT820_ERR_IO: return "SPI HAL transfer failed";
    case BT820_ERR_TIMEOUT: return "no 0x01 data-valid byte within poll limit";
    case BT820_ERR_MODE: return "host command needs single channel mode";
    case BT820_ERR_ILLEGAL_ADDR: return "BT820 returned 0xDEADABBA (illegal address)";
    case BT820_ERR_STATE: return "configuration host command only allowed in a low-power state";
    default: return "unknown";
    }
}
