/* ARC-1 Compact R08 -- SPI NOR driver for the 32 MiB boot flash on F133 SPI0.
 *
 * Evidence: HOST_TESTED against tests/nor_mock.c only. Never run on silicon.
 * Opcodes and status bits follow the Winbond W25Q256JV datasheet (see
 * docs/NOR_BOOT_AND_FLASH.md for the exact revision and section refs).
 *
 * Addressing policy (corrective handoff v1.0 "ADDRESSING TRAP"):
 *   The device powers up in 3-byte mode (ADP = 0 assumed; read back at init)
 *   and the F133 boot ROM reads boot0 with 3-byte addressing from offset 0.
 *   This driver NEVER switches the device into 4-byte mode. It reaches the
 *   whole 32 MiB with the dedicated 4-byte-address opcodes (13h/0Ch/12h/21h/
 *   DCh), which ignore the current address mode. So a CPU reset or watchdog at
 *   any point leaves the flash in the state the boot ROM expects.
 *   For parts without dedicated 4-byte opcodes a fallback uses the Extended
 *   Address Register (C5h/C8h) and restores it to 0 after every operation.
 *   nor_init() repairs a device found in 4-byte mode or with EAR != 0
 *   (E9h exit, EAR := 0), and nor_prepare_reboot() re-checks it.
 */
#ifndef SPI_NOR_H
#define SPI_NOR_H
#include <stddef.h>
#include <stdint.h>
#include "arc1_hal.h"

enum nor_err {
    NOR_OK = 0,
    NOR_ERR_IO = 1,        /* HAL transfer failed */
    NOR_ERR_ID = 2,        /* JEDEC / SFDP missing, unknown, or inconsistent */
    NOR_ERR_RANGE = 3,     /* access beyond the device */
    NOR_ERR_ALIGN = 4,     /* erase address not sector aligned */
    NOR_ERR_TIMEOUT = 5,   /* busy (WIP) never cleared */
    NOR_ERR_VERIFY = 6,    /* readback differs from what was programmed */
    NOR_ERR_STATE = 7,     /* not initialised, or address mode could not be repaired */
    NOR_ERR_PROTECTED = 8  /* write enable latch did not set (WP#/protection) */
};

enum nor_addr_strategy { NOR_ADDR_3B_ONLY = 0, NOR_ADDR_4B_OPCODES = 1, NOR_ADDR_EAR = 2 };

typedef struct nor_info {
    uint8_t  mfr;
    uint16_t dev;
    uint32_t size_bytes;
    uint32_t sector_bytes;          /* smallest erase unit used (4 KiB) */
    uint32_t page_bytes;            /* program page (256 B) */
    int      sfdp_ok;
    uint32_t sfdp_density_bits;     /* from BFPT DWORD 2 */
    int      sfdp_addr_bytes;       /* BFPT DWORD 1 [18:17]: 0 = 3B only, 1 = 3B/4B, 2 = 4B only */
    enum nor_addr_strategy strategy;
    int      found_in_4b_mode;      /* repaired at init (diagnostic) */
    int      found_ear_nonzero;     /* repaired at init (diagnostic) */
} nor_info;

typedef struct nor_dev {
    const arc1_spi_hal *hal;
    nor_info info;
    uint32_t prog_timeout_us;
    uint32_t erase_timeout_us;
    int      ready;
    /* 0 = automatic (known-part table + SFDP); otherwise forced (bring-up / tests) */
    enum nor_addr_strategy force_strategy;
    int      force_set;
} nor_dev;

/* Opcodes (W25Q256JV instruction set; names as in the datasheet). */
#define NOR_OP_WREN        0x06u
#define NOR_OP_RDSR1       0x05u
#define NOR_OP_RDSR2       0x35u
#define NOR_OP_RDSR3       0x15u
#define NOR_OP_WRSR1       0x01u
#define NOR_OP_WRSR3       0x11u
#define NOR_OP_JEDEC_ID    0x9Fu
#define NOR_OP_SFDP        0x5Au
#define NOR_OP_READ3       0x03u
#define NOR_OP_READ4       0x13u
#define NOR_OP_PP3         0x02u
#define NOR_OP_PP4         0x12u
#define NOR_OP_SE3         0x20u
#define NOR_OP_SE4         0x21u
#define NOR_OP_EN4B        0xB7u
#define NOR_OP_EX4B        0xE9u
#define NOR_OP_WREAR       0xC5u
#define NOR_OP_RDEAR       0xC8u
#define NOR_OP_RSTEN       0x66u
#define NOR_OP_RST         0x99u
#define NOR_SR1_WIP        0x01u
#define NOR_SR1_WEL        0x02u
#define NOR_SR3_ADS        0x01u   /* current address mode: 1 = 4-byte */
#define NOR_SR3_ADP        0x02u   /* power-up address mode (non-volatile) */

int nor_init(nor_dev *d, const arc1_spi_hal *hal);
int nor_read(nor_dev *d, uint32_t addr, void *buf, size_t n);
int nor_erase_sector(nor_dev *d, uint32_t addr);
int nor_program(nor_dev *d, uint32_t addr, const void *buf, size_t n);
/* erase the covering sectors, program, read back and compare */
int nor_write_verified(nor_dev *d, uint32_t addr, const void *buf, size_t n);
/* make sure the boot ROM will find the device in 3-byte mode with EAR = 0 */
int nor_prepare_reboot(nor_dev *d);
/* read SR3 (diagnostics / tests) */
int nor_read_sr3(nor_dev *d, uint8_t *sr3);
#endif
