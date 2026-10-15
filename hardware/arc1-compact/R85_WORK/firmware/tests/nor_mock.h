/* Behavioural SPI NOR model for host tests (W25Q256JV-like). NOT a device model
 * validated against silicon: it encodes the datasheet rules the driver relies on. */
#ifndef NOR_MOCK_H
#define NOR_MOCK_H
#include <stddef.h>
#include <stdint.h>
#include "arc1_hal.h"

typedef struct nor_mock {
    uint8_t *mem;
    uint32_t size;
    uint8_t  jedec[3];
    int      has_4b_opcodes;   /* 13h/12h/21h implemented */
    int      sfdp_present;
    uint32_t sfdp_density_bits;
    int      sfdp_addr_bytes;  /* 0 3B, 1 3B/4B, 2 4B */
    /* state */
    int      four_byte_mode;   /* ADS */
    int      adp;              /* power-up 4-byte mode bit */
    uint8_t  ear;
    int      wel;
    int      busy_polls;       /* WIP reads remaining */
    int      reset_enabled;
    /* transaction */
    int      cs;
    uint8_t  buf[4200];
    size_t   n;
    uint64_t t_us;
    /* fault injection */
    int      stuck_busy;
    int      wel_never_sets;   /* models WP#/protection */
    int      miso_stuck;       /* -1 off, else value returned for every byte */
    int      power_cut_after_bytes;  /* >0: next program stores only this many bytes */
    /* counters / observations */
    int      n_resets, n_programs, n_erases, n_ex4b, n_wrear;
    int      prog_while_busy, prog_without_wel, page_wrap;
    int      upper_half_touched;
} nor_mock;

void nor_mock_init(nor_mock *m, uint32_t size, uint8_t mfr, uint8_t d1, uint8_t d2);
void nor_mock_free(nor_mock *m);
void nor_mock_hal(nor_mock *m, arc1_spi_hal *hal);
/* what the F133 boot ROM would read from offset `a` using 03h + 3 address bytes
 * in the device's current mode (4-byte mode would consume a 4th address byte) */
int  nor_mock_brom_read_ok(const nor_mock *m);
#endif
