/* ARC-1 Compact R07 -- BT820 QSPI host-interface transaction layer.
 *
 * R07 change (fixes R06 defect R06-BT-0x7F): writes to 0x7F000000 and above
 * are REQUIRED for normal operation (command FIFO, registers, display list:
 * AN086 Table 2). R06 refused them. R07 instead validates every access
 * against the documented memory map and the host-command table:
 *
 *   write frame : (A[30:24] | 0x80), A[23:16], A[15:8], A[7:0], data (LE words)
 *   read  frame : A[30:24], A[23:16], A[15:8], A[7:0], poll for 0x01, data
 *   host command: 0xFF, code, param, 0x00, 0x00  (exactly 5 bytes, single mode)
 *
 * A write into 0x7Fxxxxxx also starts with 0xFF. It cannot be confused with a
 * host command because (a) documented regions put A[23:16] in {0x00, 0x01,
 * 0x80} while host-command codes are 0xE0..0xEB (0x7FE0_0000..0x7FEB_FFFF is
 * not in the memory map and is refused here), and (b) every write carries at
 * least 4 data bytes after the 4 address bytes, so it is never a 5-byte
 * transaction. Bridgetek's own host driver (EveApps-BT82X, MIT, commit
 * 6b5a57eb, EVE_HalImpl_RP2040.c EVE_Hal_startTransfer) emits exactly this
 * framing. How the BT820 silicon decodes it is still to be confirmed by bench
 * capture (vendor question Q2 in R07_WORK/docs/VENDOR_QUESTIONS.md).
 *
 * Byte order of 32-bit data: little endian (EveApps EVE_Hal_transfer32).
 * Only SINGLE channel mode is implemented (board-plan risk
 * F133_QUAD_IO_UNCONFIRMED). Evidence: HOST_TESTED against a mock only. */
#ifndef BT820_HOST_H
#define BT820_HOST_H
#include "arc1_hal.h"

enum bt820_error {
    BT820_OK = 0,
    BT820_ERR_ARG = 1,          /* alignment, length, unmapped/reserved address, bad command code */
    BT820_ERR_IO = 2,
    BT820_ERR_TIMEOUT = 3,      /* no 0x01 data-valid byte within poll_limit */
    BT820_ERR_MODE = 4,         /* host command outside single channel mode */
    BT820_ERR_ILLEGAL_ADDR = 5, /* 32-bit read returned 0xDEADABBA */
    BT820_ERR_STATE = 6         /* configuration host command while ACTIVE */
};

typedef enum { BT820_BUS_SINGLE = 0, BT820_BUS_DUAL = 1, BT820_BUS_QUAD = 2 } bt820_bus_mode;
typedef enum { BT820_PWR_SLEEP = 0, BT820_PWR_STANDBY, BT820_PWR_POWERDOWN, BT820_PWR_ACTIVE } bt820_power;

#define BT820_ADDR_LIMIT   0x80000000u
#define BT820_ILLEGAL_WORD 0xDEADABBAu

typedef struct bt820_dev {
    arc1_spi_hal hal;
    bt820_bus_mode mode;
    bt820_power power;          /* host's model of the chip power state */
    uint32_t poll_limit;        /* max bytes clocked while waiting for 0x01 */
    uint32_t ram_g_bytes;       /* attached DDR (MN820: 128 MiB); top 2.5 MiB is reserved */
    uint32_t last_poll_bytes;
    uint64_t transactions;
} bt820_dev;

int bt820_init(bt820_dev *dev, const arc1_spi_hal *hal, uint32_t poll_limit, uint32_t ram_g_bytes);
/* 1 if [addr, addr+n) lies inside one documented, accessible region */
int bt820_span_valid(const bt820_dev *dev, uint32_t addr, size_t n);
int bt820_write(bt820_dev *dev, uint32_t addr, const uint8_t *data, size_t n);
int bt820_read(bt820_dev *dev, uint32_t addr, uint8_t *data, size_t n);
int bt820_write32(bt820_dev *dev, uint32_t addr, const uint32_t *words, size_t count);
int bt820_wr32(bt820_dev *dev, uint32_t addr, uint32_t value);
int bt820_read32(bt820_dev *dev, uint32_t addr, uint32_t *value);
/* code must be one of AN086 Table 3; config codes need a low-power state */
int bt820_host_command(bt820_dev *dev, uint8_t code, uint8_t param);
int bt820_host_active(bt820_dev *dev);
/* call after the RST_N pin was pulsed: the chip is in SLEEP [AN086 2.3] */
void bt820_note_hw_reset(bt820_dev *dev);
const char *bt820_error_string(int err);

#endif
