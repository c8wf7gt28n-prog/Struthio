/* ARC-1 Compact R06 -- BT820 QSPI host-interface transaction layer.
 *
 * Implements only what BT820 datasheet v1.1 (BRT_000427) section 4.5 states:
 *   write : Addr3|0x80, Addr2, Addr1, Addr0, data...      (31-bit address)
 *   read  : Addr3 (MSB 0), Addr2, Addr1, Addr0, poll until 0x01, data...
 *   host command: 0xFF, cmd, param, 0x00, 0x00 (single channel mode only)
 *   ACTIVE: 0x00 x 5
 *   word based: 32-bit multiples, word-aligned addresses
 *   illegal addressing on burst read returns 0xDEADABBA
 * Only SINGLE channel mode is implemented (the power-on default). Dual/Quad
 * need F133 register-level confirmation (board plan risk F133_QUAD_IO_UNCONFIRMED).
 * The register map, host-command codes, display list encodings and the
 * byte order of 32-bit data are in BRT_AN_086, which R06 has NOT reviewed:
 * bt820_write32/bt820_read32 serialise little-endian as an ASSUMPTION.
 * Evidence level: HOST_TESTED against a mock, never against silicon. */
#ifndef BT820_HOST_H
#define BT820_HOST_H
#include "arc1_hal.h"

enum bt820_error {
    BT820_OK = 0,
    BT820_ERR_ARG = 1,
    BT820_ERR_IO = 2,
    BT820_ERR_TIMEOUT = 3,      /* no 0x01 data-valid byte within poll_limit */
    BT820_ERR_MODE = 4,         /* host command outside single channel mode */
    BT820_ERR_ILLEGAL_ADDR = 5  /* 32-bit read returned 0xDEADABBA */
};

typedef enum { BT820_BUS_SINGLE = 0, BT820_BUS_DUAL = 1, BT820_BUS_QUAD = 2 } bt820_bus_mode;

#define BT820_ADDR_LIMIT 0x80000000u
#define BT820_ILLEGAL_WORD 0xDEADABBAu
#define BT820_WRITE_LIMIT  0x7F000000u   /* writes at/above would begin with 0xFF */

typedef struct bt820_dev {
    arc1_spi_hal hal;
    bt820_bus_mode mode;
    uint32_t poll_limit;        /* max bytes clocked while waiting for 0x01 */
    uint32_t last_poll_bytes;
    uint64_t transactions;
} bt820_dev;

int bt820_init(bt820_dev *dev, const arc1_spi_hal *hal, uint32_t poll_limit);
int bt820_write(bt820_dev *dev, uint32_t addr, const uint8_t *data, size_t n);
int bt820_read(bt820_dev *dev, uint32_t addr, uint8_t *data, size_t n);
int bt820_write32(bt820_dev *dev, uint32_t addr, const uint32_t *words, size_t count);
int bt820_read32(bt820_dev *dev, uint32_t addr, uint32_t *value);
int bt820_host_command(bt820_dev *dev, uint8_t cmd, uint8_t param);
int bt820_host_active(bt820_dev *dev);
const char *bt820_error_string(int err);

#endif
