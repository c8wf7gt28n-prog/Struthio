/* ARC-1 Compact R8.5 -- host client for the ECP5 "AMBX" v3 SPI mailbox (OPERATIONAL interface).
 * Derived from R06/R07 t35_link.c (AMBX v1); register map: R85_WORK/fpga_ecp5/rtl/mbx_regs_r85.sv.
 * Valid only after DONE (the same SPI0 balls carry sysCONFIG before DONE, ecp5_cfg.h).
 * HOST_TESTED against a mock (tests/ecp5_mock.c) whose AJOB answers come from the RTL-verified reference. */
#ifndef FPGA_LINK_H
#define FPGA_LINK_H
#include "arc1_hal.h"

enum fl_error {
    FL_OK = 0,
    FL_NOT_READY = 1,   /* no/unknown FPGA: MAGIC/VERSION mismatch or reserved status bits set */
    FL_BUSY = 2,        /* doorbell refused (DOORBELL_OVERRUN) */
    FL_TIMEOUT = 3,
    FL_IO = 4,
    FL_PROTOCOL = 5,    /* response length out of range */
    FL_ARG = 6,
    FL_VERSION = 7       /* AMBX present but VERSION != 3: ABI mismatch, rejected safely */
};

#define FL_REG_MAGIC     0x0000u
#define FL_REG_VERSION   0x0004u
#define FL_REG_STATUS    0x0008u
#define FL_REG_CONTROL   0x000Cu
#define FL_REG_REQ_LEN   0x0010u
#define FL_REG_RESP_LEN  0x0014u
#define FL_REG_BIST_ERRS  0x001Cu
#define FL_REG_PERF_CYCLES 0x0024u
#define FL_REG_PERF_JOBS  0x0028u
#define FL_REG_PERF_ITEMS 0x002Cu
#define FL_REG_LAST_STATUS 0x0030u
#define FL_AMBX_VERSION   3u
#define FL_CAP_PSRAM      0x0001u
#define FL_CAP_BIST       0x0002u
#define FL_CAP_POWER_GUARD 0x0004u
#define FL_CAP_AJOB       0x0008u
#define FL_REQ_BUF       0x2000u
#define FL_RESP_BUF      0x4000u
#define FL_BUF_BYTES     8192u

#define FL_ST_FPGA_READY   0x0001u
#define FL_ST_PSRAM_READY  0x0002u
#define FL_ST_RESP_READY   0x0010u
#define FL_ST_OVERRUN      0x0020u
#define FL_ST_JOB_PENDING  0x0008u
#define FL_ST_PSRAM_ERROR  0x0004u
#define FL_ST_BIST_BUSY    0x0040u
#define FL_ST_BIST_PASS    0x0080u
#define FL_ST_BIST_FAIL    0x0100u
#define FL_ST_POWER_ON     0x0800u
#define FL_ST_POWER_LOST   0x1000u
#define FL_ST_RESERVED     0xE000u

#define FL_CTL_DOORBELL       0x01u
#define FL_CTL_RESP_ACK       0x02u
#define FL_CTL_PSRAM_RECOVER  0x04u
#define FL_CTL_BIST_START     0x08u
#define FL_CTL_CLEAR_OVERRUN  0x10u
#define FL_CTL_CLEAR_POWER_LOST 0x20u
#define FL_CTL_ABORT          0x40u

typedef struct fpga_link {
    arc1_spi_hal hal;
    uint32_t timeout_us;
    uint64_t exchanges;
} fpga_link;

int fl_init(fpga_link *l, const arc1_spi_hal *hal, uint32_t timeout_us);
int fl_read(fpga_link *l, uint16_t addr, uint8_t *data, size_t n);
int fl_write(fpga_link *l, uint16_t addr, const uint8_t *data, size_t n);
/* DISCOVER: AMBX magic + VERSION == 3; returns caps through *caps (may be NULL) */
int fl_probe(fpga_link *l);
int fl_discover(fpga_link *l, uint16_t *version, uint16_t *caps);
int fl_control(fpga_link *l, uint8_t bits);
int fl_read32(fpga_link *l, uint16_t addr, uint32_t *v);
int fl_status(fpga_link *l, uint16_t *status);
/* One doorbell: write req, wait for RESP_READY, read the response, ack it. */
int fl_exchange(fpga_link *l, const uint8_t *req, size_t req_len,
                 uint8_t *resp, size_t resp_cap, size_t *resp_len);
const char *fl_error_string(int err);

#endif
