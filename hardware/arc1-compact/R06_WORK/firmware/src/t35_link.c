/* ARC-1 Compact R06 -- AMBX v1 mailbox client (see header). */
#include "t35_link.h"

#include <string.h>

int t35_init(t35_link *l, const arc1_spi_hal *hal, uint32_t timeout_us) {
    if (!l || !hal || !hal->select || !hal->transfer || !hal->now_us || timeout_us == 0u) return T35_ARG;
    memset(l, 0, sizeof(*l));
    l->hal = *hal;
    l->timeout_us = timeout_us;
    return T35_OK;
}

int t35_read(t35_link *l, uint16_t addr, uint8_t *data, size_t n) {
    uint8_t hdr[4];
    int rc;
    if (!l || !data || n == 0u) return T35_ARG;
    hdr[0] = 0x0Bu; hdr[1] = (uint8_t)(addr >> 8); hdr[2] = (uint8_t)(addr & 0xFFu); hdr[3] = 0u;
    l->hal.select(l->hal.ctx, 1);
    rc = l->hal.transfer(l->hal.ctx, hdr, NULL, sizeof hdr);
    if (!rc) rc = l->hal.transfer(l->hal.ctx, NULL, data, n);
    l->hal.select(l->hal.ctx, 0);
    return rc ? T35_IO : T35_OK;
}

int t35_write(t35_link *l, uint16_t addr, const uint8_t *data, size_t n) {
    uint8_t hdr[3];
    int rc;
    if (!l || !data || n == 0u) return T35_ARG;
    hdr[0] = 0x02u; hdr[1] = (uint8_t)(addr >> 8); hdr[2] = (uint8_t)(addr & 0xFFu);
    l->hal.select(l->hal.ctx, 1);
    rc = l->hal.transfer(l->hal.ctx, hdr, NULL, sizeof hdr);
    if (!rc) rc = l->hal.transfer(l->hal.ctx, data, NULL, n);
    l->hal.select(l->hal.ctx, 0);
    return rc ? T35_IO : T35_OK;
}

int t35_probe(t35_link *l) {
    uint8_t id[8];
    int rc = t35_read(l, T35_REG_MAGIC, id, sizeof id);
    if (rc) return rc;
    if (memcmp(id, "AMBX", 4) != 0 || id[4] != 1u || id[5] != 0u) return T35_NOT_READY;
    return T35_OK;
}

int t35_status(t35_link *l, uint16_t *status) {
    uint8_t b[2];
    int rc;
    if (!status) return T35_ARG;
    rc = t35_read(l, T35_REG_STATUS, b, sizeof b);
    if (rc) return rc;
    *status = (uint16_t)(b[0] | (b[1] << 8));
    /* an absent FPGA reads as 0xFFFF through the MISO pull-up */
    if ((*status & T35_ST_RESERVED) != 0u || (*status & T35_ST_FPGA_READY) == 0u) return T35_NOT_READY;
    return T35_OK;
}

static int ctl(t35_link *l, uint8_t v) { return t35_write(l, T35_REG_CONTROL, &v, 1); }

int t35_exchange(t35_link *l, const uint8_t *req, size_t req_len,
                 uint8_t *resp, size_t resp_cap, size_t *resp_len) {
    uint16_t st = 0, rl;
    uint8_t lenb[2];
    uint64_t t0;
    int rc;
    if (!l || !req || !resp || !resp_len || req_len == 0u || req_len > T35_BUF_BYTES) return T35_ARG;
    *resp_len = 0;
    rc = t35_status(l, &st);
    if (rc) return rc;
    if (st & T35_ST_RESP_READY) {           /* stale, unclaimed response: drop it */
        rc = ctl(l, T35_CTL_RESP_ACK);
        if (rc) return rc;
    }
    rc = t35_write(l, T35_REQ_BUF, req, req_len);
    lenb[0] = (uint8_t)(req_len & 0xFFu); lenb[1] = (uint8_t)(req_len >> 8);
    if (!rc) rc = t35_write(l, T35_REG_REQ_LEN, lenb, 2);
    if (!rc) rc = ctl(l, T35_CTL_DOORBELL);
    if (rc) return rc;
    l->exchanges++;
    t0 = l->hal.now_us(l->hal.ctx);
    for (;;) {
        rc = t35_status(l, &st);
        if (rc) return rc;                   /* includes FPGA vanished mid-job */
        if (st & T35_ST_OVERRUN) {
            (void)ctl(l, T35_CTL_CLEAR_OVERRUN);
            return T35_BUSY;
        }
        if (st & T35_ST_RESP_READY) break;
        if (l->hal.now_us(l->hal.ctx) - t0 > l->timeout_us) return T35_TIMEOUT;
    }
    rc = t35_read(l, T35_REG_RESP_LEN, lenb, 2);
    if (rc) return rc;
    rl = (uint16_t)(lenb[0] | (lenb[1] << 8));
    if (rl == 0u || rl > resp_cap || rl > T35_BUF_BYTES) {
        (void)ctl(l, T35_CTL_RESP_ACK);
        return T35_PROTOCOL;
    }
    rc = t35_read(l, T35_RESP_BUF, resp, rl);
    if (!rc) rc = ctl(l, T35_CTL_RESP_ACK);
    if (rc) return rc;
    *resp_len = rl;
    return T35_OK;
}

const char *t35_error_string(int err) {
    switch (err) {
    case T35_OK: return "ok";
    case T35_NOT_READY: return "FPGA not ready / absent";
    case T35_BUSY: return "doorbell refused (overrun)";
    case T35_TIMEOUT: return "timeout waiting for response";
    case T35_IO: return "SPI HAL transfer failed";
    case T35_PROTOCOL: return "response length out of range";
    case T35_ARG: return "invalid argument";
    default: return "unknown";
    }
}
