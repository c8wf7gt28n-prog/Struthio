/* ARC-1 Compact R8.5 -- AMBX v3 mailbox client (see header; derived from R06 t35_link.c). */
#include "fpga_link.h"

#include <string.h>

int fl_init(fpga_link *l, const arc1_spi_hal *hal, uint32_t timeout_us) {
    if (!l || !hal || !hal->select || !hal->transfer || !hal->now_us || timeout_us == 0u) return FL_ARG;
    memset(l, 0, sizeof(*l));
    l->hal = *hal;
    l->timeout_us = timeout_us;
    return FL_OK;
}

int fl_read(fpga_link *l, uint16_t addr, uint8_t *data, size_t n) {
    uint8_t hdr[4];
    int rc;
    if (!l || !data || n == 0u) return FL_ARG;
    hdr[0] = 0x0Bu; hdr[1] = (uint8_t)(addr >> 8); hdr[2] = (uint8_t)(addr & 0xFFu); hdr[3] = 0u;
    l->hal.select(l->hal.ctx, 1);
    rc = l->hal.transfer(l->hal.ctx, hdr, NULL, sizeof hdr);
    if (!rc) rc = l->hal.transfer(l->hal.ctx, NULL, data, n);
    l->hal.select(l->hal.ctx, 0);
    return rc ? FL_IO : FL_OK;
}

int fl_write(fpga_link *l, uint16_t addr, const uint8_t *data, size_t n) {
    uint8_t hdr[3];
    int rc;
    if (!l || !data || n == 0u) return FL_ARG;
    hdr[0] = 0x02u; hdr[1] = (uint8_t)(addr >> 8); hdr[2] = (uint8_t)(addr & 0xFFu);
    l->hal.select(l->hal.ctx, 1);
    rc = l->hal.transfer(l->hal.ctx, hdr, NULL, sizeof hdr);
    if (!rc) rc = l->hal.transfer(l->hal.ctx, data, NULL, n);
    l->hal.select(l->hal.ctx, 0);
    return rc ? FL_IO : FL_OK;
}

int fl_discover(fpga_link *l, uint16_t *version, uint16_t *caps) {
    uint8_t id[8];
    int rc = fl_read(l, FL_REG_MAGIC, id, sizeof id);
    if (rc) return rc;
    if (version) *version = (uint16_t)(id[4] | (id[5] << 8));
    if (caps) *caps = (uint16_t)(id[6] | (id[7] << 8));
    if (memcmp(id, "AMBX", 4) != 0) return FL_NOT_READY;      /* blank / absent FPGA reads 00 (MISO pull-down) */
    if (id[4] != FL_AMBX_VERSION || id[5] != 0u) return FL_VERSION;
    return FL_OK;
}

int fl_probe(fpga_link *l) { return fl_discover(l, NULL, NULL); }

int fl_read32(fpga_link *l, uint16_t addr, uint32_t *v) {
    uint8_t b[4];
    int rc;
    if (!v) return FL_ARG;
    rc = fl_read(l, addr, b, 4);
    if (!rc) *v = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    return rc;
}

int fl_status(fpga_link *l, uint16_t *status) {
    uint8_t b[2];
    int rc;
    if (!status) return FL_ARG;
    rc = fl_read(l, FL_REG_STATUS, b, sizeof b);
    if (rc) return rc;
    *status = (uint16_t)(b[0] | (b[1] << 8));
    /* an absent or unconfigured FPGA reads 0x0000 (3.3k BOOT-SEL1 pull-down on MISO): FPGA_READY = 0 */
    if ((*status & FL_ST_RESERVED) != 0u || (*status & FL_ST_FPGA_READY) == 0u) return FL_NOT_READY;
    return FL_OK;
}

static int ctl(fpga_link *l, uint8_t v) { return fl_write(l, FL_REG_CONTROL, &v, 1); }
int fl_control(fpga_link *l, uint8_t bits) { return ctl(l, bits); }

int fl_exchange(fpga_link *l, const uint8_t *req, size_t req_len,
                 uint8_t *resp, size_t resp_cap, size_t *resp_len) {
    uint16_t st = 0, rl;
    uint8_t lenb[2];
    uint64_t t0;
    int rc;
    if (!l || !req || !resp || !resp_len || req_len == 0u || req_len > FL_BUF_BYTES) return FL_ARG;
    *resp_len = 0;
    rc = fl_status(l, &st);
    if (rc) return rc;
    if (st & FL_ST_RESP_READY) {           /* stale, unclaimed response: drop it */
        rc = ctl(l, FL_CTL_RESP_ACK);
        if (rc) return rc;
    }
    rc = fl_write(l, FL_REQ_BUF, req, req_len);
    lenb[0] = (uint8_t)(req_len & 0xFFu); lenb[1] = (uint8_t)(req_len >> 8);
    if (!rc) rc = fl_write(l, FL_REG_REQ_LEN, lenb, 2);
    if (!rc) rc = ctl(l, FL_CTL_DOORBELL);
    if (rc) return rc;
    l->exchanges++;
    t0 = l->hal.now_us(l->hal.ctx);
    for (;;) {
        rc = fl_status(l, &st);
        if (rc) return rc;                   /* includes FPGA vanished mid-job */
        if (st & FL_ST_OVERRUN) {
            (void)ctl(l, FL_CTL_CLEAR_OVERRUN);
            return FL_BUSY;
        }
        if (st & FL_ST_RESP_READY) break;
        if (l->hal.now_us(l->hal.ctx) - t0 > l->timeout_us) return FL_TIMEOUT;
    }
    rc = fl_read(l, FL_REG_RESP_LEN, lenb, 2);
    if (rc) return rc;
    rl = (uint16_t)(lenb[0] | (lenb[1] << 8));
    if (rl == 0u || rl > resp_cap || rl > FL_BUF_BYTES) {
        (void)ctl(l, FL_CTL_RESP_ACK);
        return FL_PROTOCOL;
    }
    rc = fl_read(l, FL_RESP_BUF, resp, rl);
    if (!rc) rc = ctl(l, FL_CTL_RESP_ACK);
    if (rc) return rc;
    *resp_len = rl;
    return FL_OK;
}

const char *fl_error_string(int err) {
    switch (err) {
    case FL_OK: return "ok";
    case FL_NOT_READY: return "FPGA not ready / absent";
    case FL_BUSY: return "doorbell refused (overrun)";
    case FL_TIMEOUT: return "timeout waiting for response";
    case FL_IO: return "SPI HAL transfer failed";
    case FL_PROTOCOL: return "response length out of range";
    case FL_ARG: return "invalid argument";
    case FL_VERSION: return "AMBX protocol version mismatch";
    default: return "unknown";
    }
}
