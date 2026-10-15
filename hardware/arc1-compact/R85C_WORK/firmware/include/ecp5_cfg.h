/* ARC-1 Compact R8.5 -- F133 loader for the LFE5U-45F over sysCONFIG slave SPI (CFG[2:0] = 001).
 *
 * CONFIGURATION interface (this file): F133 SPI0 -> U21..U24 isolation buffers -> CCLK/D0(MOSI)/D1(MISO)/SN,
 * plus PROGRAMN (F133 PE8, open-drain use), INITN (PD0), DONE (PE9). Opcodes and flow: Lattice FPGA-TN-02039
 * (sysCONFIG) and the Linux lattice-sysconfig driver (independent reference implementation, CO [S8]).
 * The OPERATIONAL interface (AMBX mailbox, fpga_link.h) uses the same balls only after DONE, when the
 * slave-SPI port is disabled (SLAVE_SPI_PORT=DISABLE) and the user design owns them.
 * Evidence: HOST_TESTED against a behavioural sysCONFIG model (tests/ecp5_mock.c). Not run on silicon. */
#ifndef ECP5_CFG_H
#define ECP5_CFG_H
#include <stddef.h>
#include <stdint.h>
#include "arc1_hal.h"

#define ECP5_IDCODE_LFE5U_45 0x41112043u          /* bitstream VERIFY_ID, Lattice ECP5 family IDCODE list */

/* sysCONFIG commands (TN-02039 Table 6.x; 8-bit opcode + 24-bit operand) */
#define ECP5_CMD_READ_ID          0xE0u
#define ECP5_CMD_LSC_READ_STATUS  0x3Cu
#define ECP5_CMD_LSC_REFRESH      0x79u
#define ECP5_CMD_ISC_ENABLE       0xC6u
#define ECP5_CMD_ISC_ERASE        0x0Eu
#define ECP5_CMD_LSC_INIT_ADDRESS 0x46u
#define ECP5_CMD_LSC_BITSTREAM_BURST 0x7Au
#define ECP5_CMD_ISC_DISABLE      0x26u
#define ECP5_CMD_ISC_NOOP         0xFFu
/* status register bits (Linux lattice-sysconfig.h; TN-02039 status register) -- bench-verify */
#define ECP5_ST_DONE  (1u << 8)
#define ECP5_ST_BUSY  (1u << 12)
#define ECP5_ST_FAIL  (1u << 13)
#define ECP5_ST_ERR_MASK (7u << 23)                 /* BSE error code: 0 = none */

typedef enum {
    ECP5_PIN_PWR_EN = 0,     /* out: FPGA_PWR_EN_F (PE0) */
    ECP5_PIN_VCC_PG,         /* in : FPGA_VCC_PG (PD1) */
    ECP5_PIN_BUS_EN_N,       /* out: FPGA_BUS_EN_N (PE6), 0 = isolation buffers on */
    ECP5_PIN_PROGRAMN,       /* od : FPGA_PROGRAMN_F (PE8): set 0 = drive low, 1 = release (input); get = level */
    ECP5_PIN_INITN,          /* in : FPGA_INITN (PD0) */
    ECP5_PIN_DONE,           /* in : FPGA_DONE (PE9) */
    ECP5_PIN_PSRAM_REQ,      /* out: PSRAM_PWR_REQ (PE7) */
    ECP5_PIN_COUNT
} ecp5_pin;

typedef struct ecp5_gpio_hal {
    void *ctx;
    void (*set)(void *ctx, ecp5_pin pin, int level);
    int (*get)(void *ctx, ecp5_pin pin);
    void (*delay_us)(void *ctx, uint32_t us);
} ecp5_gpio_hal;

typedef enum {
    ECP5_OK = 0,
    ECP5_E_ARG,
    ECP5_E_IMAGE_HEADER,     /* container magic/format/header CRC */
    ECP5_E_IMAGE_TRUNCATED,  /* file shorter than declared (bad microSD read) */
    ECP5_E_IMAGE_CRC,        /* bitstream CRC32 mismatch */
    ECP5_E_IMAGE_DEVICE,     /* bitstream not for LFE5U-45 / no preamble / VERIFY_ID */
    ECP5_E_IMAGE_ABI,        /* container ABI major != firmware */
    ECP5_E_POWER,            /* VCC power-good never seen (rail fault) */
    ECP5_E_INITN_TIMEOUT,    /* INITN never high: POR (VCCAUX/VCCIO8) or init failed */
    ECP5_E_PROGRAMN_HELD,    /* PROGRAMN does not return high (held / shorted) */
    ECP5_E_IDCODE,           /* READ_ID mismatch: absent / wrong device / bus fault */
    ECP5_E_BUSY_TIMEOUT,     /* status BUSY never clears */
    ECP5_E_CONFIG_STATUS,    /* FAIL bit or BSE error after the burst (configuration CRC fault) */
    ECP5_E_DONE_TIMEOUT,     /* DONE never high after ISC_DISABLE */
    ECP5_E_INITN_ERROR,      /* INITN low after configuration: device-signalled error */
    ECP5_E_IO,               /* SPI HAL error */
    ECP5_E_COUNT
} ecp5_err;

/* Per-game FPGA configuration container on microSD (little endian):
 *  0 "ACFG"  4 u16 format = 1   6 u16 abi_major   8 u16 abi_minor   10 u16 flags
 * 12 u32 idcode   16 u32 bit_len   20 u32 bit_crc32   24 u32 caps_required   28 u32 header_crc32 (bytes 0..27)
 * 32 bitstream (ecppack .bit, complete file incl. its comment header) */
#define ACFG_HDR 32u
typedef struct ecp5_image {
    const uint8_t *bit;
    uint32_t bit_len;
    uint16_t abi_major, abi_minor;
    uint32_t idcode, caps_required;
} ecp5_image;

typedef struct ecp5_cfg {
    ecp5_gpio_hal io;
    arc1_spi_hal spi;            /* SPI0 with CS = FPGA SN (PE4); NOR CS# held high by the binding */
    uint32_t chunk;              /* burst chunk size (bytes per HAL transfer) */
    uint32_t last_status;        /* last LSC_READ_STATUS value */
    uint32_t last_idcode;
    uint32_t pg_timeout_ms, initn_timeout_ms, done_timeout_ms, busy_timeout_ms;
} ecp5_cfg;

void ecp5_cfg_init(ecp5_cfg *c, const ecp5_gpio_hal *io, const arc1_spi_hal *spi);
/* streaming source: returns a pointer to n bytes at offset off (scratch may be used), NULL on read error */
typedef const uint8_t *(*ecp5_read_fn)(void *ctx, uint32_t off, uint32_t n, uint8_t *scratch);
typedef struct ecp5_source {
    ecp5_read_fn read;
    void *ctx;
    uint8_t *scratch;            /* >= chunk bytes when read copies (NOR); unused for memory */
} ecp5_source;

/* P2: validate a container read from microSD; fills img on success */
ecp5_err ecp5_image_check(const uint8_t *file, size_t len, uint16_t abi_major, ecp5_image *img);
/* builds a container around an ecppack .bit (host tool / tests) */
size_t ecp5_image_build(uint8_t *out, size_t cap, const uint8_t *bit, uint32_t bit_len, uint16_t abi_major,
                        uint16_t abi_minor, uint32_t caps_required);
/* header-only check (first 32 bytes) for streamed containers; fills img except img->bit */
ecp5_err ecp5_header_check(const uint8_t hdr[ACFG_HDR], uint16_t abi_major, ecp5_image *img, uint32_t *bit_crc);
/* bitstream head check (comment header, preamble, VERIFY_ID == idcode) on the first <= 4 KiB */
ecp5_err ecp5_bit_head_check(const uint8_t *b, uint32_t n, uint32_t idcode);
/* configure from a streamed source (bit_len bytes, offsets relative to the bitstream start).
 * The source must NOT be on SPI0: SN has to stay low for the whole LSC_BITSTREAM_BURST, so the shared SPI0 bus
 * cannot read the boot NOR in between. Stage NOR-resident images in DRAM first; microSD (SMHC0) is a separate bus. */
ecp5_err ecp5_configure_stream(ecp5_cfg *c, const ecp5_image *img, const ecp5_source *src);
/* rails on + POR complete (INITN high); safe to call repeatedly */
ecp5_err ecp5_power_up(ecp5_cfg *c);
/* P3: PROGRAMN pulse, READ_ID, ISC_ENABLE/ERASE/INIT_ADDRESS, burst, status, ISC_DISABLE, DONE */
ecp5_err ecp5_configure(ecp5_cfg *c, const ecp5_image *img);
/* first-article probe without a bitstream: rails, POR/INITN, PROGRAMN pulse, READ_ID, status; leaves the FPGA
 * powered and held unconfigured (PROGRAMN low) on success, powered off on failure */
ecp5_err ecp5_probe(ecp5_cfg *c, uint32_t *idcode, uint32_t *status);
/* P6/P2: hold the FPGA unconfigured (PROGRAMN low) and isolate the bus; power_off also drops the rails */
void ecp5_safe(ecp5_cfg *c, int power_off);
const char *ecp5_err_string(ecp5_err e);
#endif
