/* ARC-1 Compact R06 -- host client for the T35 "AMBX" v1 SPI mailbox
 * (R06_WORK/fpga/mailbox/README.md). HOST_TESTED against a mock only. */
#ifndef T35_LINK_H
#define T35_LINK_H
#include "arc1_hal.h"

enum t35_error {
    T35_OK = 0,
    T35_NOT_READY = 1,   /* no/unknown FPGA: MAGIC/VERSION mismatch or reserved status bits set */
    T35_BUSY = 2,        /* doorbell refused (DOORBELL_OVERRUN) */
    T35_TIMEOUT = 3,
    T35_IO = 4,
    T35_PROTOCOL = 5,    /* response length out of range */
    T35_ARG = 6
};

#define T35_REG_MAGIC     0x0000u
#define T35_REG_VERSION   0x0004u
#define T35_REG_STATUS    0x0008u
#define T35_REG_CONTROL   0x000Cu
#define T35_REG_REQ_LEN   0x0010u
#define T35_REG_RESP_LEN  0x0014u
#define T35_REQ_BUF       0x2000u
#define T35_RESP_BUF      0x4000u
#define T35_BUF_BYTES     8192u

#define T35_ST_FPGA_READY   0x0001u
#define T35_ST_PSRAM_READY  0x0002u
#define T35_ST_RESP_READY   0x0010u
#define T35_ST_OVERRUN      0x0020u
#define T35_ST_RESERVED     0xF800u

#define T35_CTL_DOORBELL       0x01u
#define T35_CTL_RESP_ACK       0x02u
#define T35_CTL_CLEAR_OVERRUN  0x10u

typedef struct t35_link {
    arc1_spi_hal hal;
    uint32_t timeout_us;
    uint64_t exchanges;
} t35_link;

int t35_init(t35_link *l, const arc1_spi_hal *hal, uint32_t timeout_us);
int t35_read(t35_link *l, uint16_t addr, uint8_t *data, size_t n);
int t35_write(t35_link *l, uint16_t addr, const uint8_t *data, size_t n);
int t35_probe(t35_link *l);
int t35_status(t35_link *l, uint16_t *status);
/* One doorbell: write req, wait for RESP_READY, read the response, ack it. */
int t35_exchange(t35_link *l, const uint8_t *req, size_t req_len,
                 uint8_t *resp, size_t resp_cap, size_t *resp_len);
const char *t35_error_string(int err);

#endif
