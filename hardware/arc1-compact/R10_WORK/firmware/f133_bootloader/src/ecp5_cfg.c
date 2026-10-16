/* ARC-1 Compact R8.5 -- ECP5 sysCONFIG slave-SPI loader (see header). HOST_TESTED with a model only. */
/* R10 copy of R85C_WORK/firmware/src/ecp5_cfg.c (two ECP5s in R10). Changes: the container checks accept exactly the
 * LFE5U-45 and LFE5U-12 IDCODEs (r10_idcode_ok; the bootloader enforces the right device per partition), and
 * ecp5_image_build_id() takes the IDCODE (ecp5_image_build() keeps the R8.5-C behaviour: LFE5U-45). */
#include "ecp5_cfg.h"
#include "r10_boot.h"
#include "crc32.h"
#include <string.h>

static uint32_t g32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static void p32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }

void ecp5_cfg_init(ecp5_cfg *c, const ecp5_gpio_hal *io, const arc1_spi_hal *spi)
{
    memset(c, 0, sizeof *c);
    c->io = *io;
    c->spi = *spi;
    c->chunk = 4096u;
    c->pg_timeout_ms = 20u;          /* buck soft-start ~1 ms (TLV62569) */
    c->initn_timeout_ms = 50u;       /* tICFG max 33 ms (DS Table 3.42) + margin */
    c->done_timeout_ms = 100u;
    c->busy_timeout_ms = 200u;       /* ISC_ERASE of SRAM */
}

/* ---------------------------------------------------------------- container + bitstream checks */
ecp5_err ecp5_bit_head_check(const uint8_t *b, uint32_t n, uint32_t idcode)
{
    uint32_t i = 2;
    if (n < 64u || b[0] != 0xFFu || b[1] != 0x00u) return ECP5_E_IMAGE_DEVICE;
    while (i + 1u < n && !(b[i] == 0x00u && b[i + 1u] == 0xFFu)) i++;          /* comment strings end with 00 FF */
    if (i + 1u >= n) return ECP5_E_IMAGE_DEVICE;
    for (i += 2u; i + 4u <= n && i < 4096u; i++) {
        if (b[i] == 0xFFu && b[i + 1u] == 0xFFu && b[i + 2u] == 0xBDu && b[i + 3u] == 0xB3u) break;   /* preamble */
    }
    if (i + 4u > n || i >= 4096u) return ECP5_E_IMAGE_DEVICE;
    for (i += 4u; i + 8u <= n && i < 4096u; i++) {
        if (b[i] == 0xE2u && b[i + 1u] == 0 && b[i + 2u] == 0 && b[i + 3u] == 0) {                   /* VERIFY_ID */
            uint32_t id = ((uint32_t)b[i + 4u] << 24) | ((uint32_t)b[i + 5u] << 16) | ((uint32_t)b[i + 6u] << 8) | b[i + 7u];
            return id == idcode ? ECP5_OK : ECP5_E_IMAGE_DEVICE;
        }
    }
    return ECP5_E_IMAGE_DEVICE;
}

ecp5_err ecp5_image_check(const uint8_t *f, size_t len, uint16_t abi_major, ecp5_image *img)
{
    uint32_t bl;
    ecp5_err e;
    if (!f || !img) return ECP5_E_ARG;
    if (len < ACFG_HDR) return ECP5_E_IMAGE_TRUNCATED;
    if (memcmp(f, "ACFG", 4) != 0 || f[4] != 1u || f[5] != 0u || arc1_crc32(0, f, 28) != g32(f + 28)) return ECP5_E_IMAGE_HEADER;
    bl = g32(f + 16);
    if (bl == 0u || bl > 16u * 1024u * 1024u) return ECP5_E_IMAGE_HEADER;
    if ((size_t)bl > len - ACFG_HDR) return ECP5_E_IMAGE_TRUNCATED;
#ifndef MUTANT_ECP5_NO_IMAGE_CRC
    if (arc1_crc32(0, f + ACFG_HDR, bl) != g32(f + 20)) return ECP5_E_IMAGE_CRC;
#endif
    if (!r10_idcode_ok(g32(f + 12))) return ECP5_E_IMAGE_DEVICE;             /* never silently accept 85F images */
    e = ecp5_bit_head_check(f + ACFG_HDR, bl, g32(f + 12));
    if (e) return e;
    if ((uint16_t)(f[6] | (f[7] << 8)) != abi_major) return ECP5_E_IMAGE_ABI;
    img->bit = f + ACFG_HDR;
    img->bit_len = bl;
    img->abi_major = (uint16_t)(f[6] | (f[7] << 8));
    img->abi_minor = (uint16_t)(f[8] | (f[9] << 8));
    img->idcode = g32(f + 12);
    img->caps_required = g32(f + 24);
    return ECP5_OK;
}

ecp5_err ecp5_header_check(const uint8_t f[ACFG_HDR], uint16_t abi_major, ecp5_image *img, uint32_t *bit_crc)
{
    if (!f || !img || !bit_crc) return ECP5_E_ARG;
    if (memcmp(f, "ACFG", 4) != 0 || f[4] != 1u || f[5] != 0u || arc1_crc32(0, f, 28) != g32(f + 28)) return ECP5_E_IMAGE_HEADER;
    if (g32(f + 16) == 0u || g32(f + 16) > 16u * 1024u * 1024u) return ECP5_E_IMAGE_HEADER;
    if (!r10_idcode_ok(g32(f + 12))) return ECP5_E_IMAGE_DEVICE;
    if ((uint16_t)(f[6] | (f[7] << 8)) != abi_major) return ECP5_E_IMAGE_ABI;
    img->bit = NULL;
    img->bit_len = g32(f + 16);
    img->abi_major = abi_major;
    img->abi_minor = (uint16_t)(f[8] | (f[9] << 8));
    img->idcode = g32(f + 12);
    img->caps_required = g32(f + 24);
    *bit_crc = g32(f + 20);
    return ECP5_OK;
}

size_t ecp5_image_build(uint8_t *o, size_t cap, const uint8_t *bit, uint32_t bl, uint16_t maj, uint16_t min, uint32_t caps)
{
    return ecp5_image_build_id(o, cap, bit, bl, maj, min, caps, ECP5_IDCODE_LFE5U_45);
}

size_t ecp5_image_build_id(uint8_t *o, size_t cap, const uint8_t *bit, uint32_t bl, uint16_t maj, uint16_t min, uint32_t caps,
                           uint32_t idcode)
{
    if (!o || !bit || cap < ACFG_HDR + (size_t)bl || !r10_idcode_ok(idcode)) return 0;
    memset(o, 0, ACFG_HDR);
    memcpy(o, "ACFG", 4);
    o[4] = 1; o[6] = (uint8_t)maj; o[7] = (uint8_t)(maj >> 8); o[8] = (uint8_t)min; o[9] = (uint8_t)(min >> 8);
    p32(o + 12, idcode);
    p32(o + 16, bl);
    p32(o + 20, arc1_crc32(0, bit, bl));
    p32(o + 24, caps);
    p32(o + 28, arc1_crc32(0, o, 28));
    memmove(o + ACFG_HDR, bit, bl);
    return ACFG_HDR + (size_t)bl;
}

/* ---------------------------------------------------------------- sysCONFIG primitives */
static int cmd(ecp5_cfg *c, uint8_t op, uint32_t operand, uint8_t *rx, size_t rxn)
{
    uint8_t h[4];
    int rc;
    h[0] = op; h[1] = (uint8_t)(operand >> 16); h[2] = (uint8_t)(operand >> 8); h[3] = (uint8_t)operand;
    c->spi.select(c->spi.ctx, 1);
    rc = c->spi.transfer(c->spi.ctx, h, NULL, 4);
    if (!rc && rxn) rc = c->spi.transfer(c->spi.ctx, NULL, rx, rxn);
    c->spi.select(c->spi.ctx, 0);
    return rc;
}

static int read_status(ecp5_cfg *c, uint32_t *st)
{
    uint8_t b[4];
    int rc = cmd(c, ECP5_CMD_LSC_READ_STATUS, 0, b, 4);
    if (rc) return rc;
    *st = ((uint32_t)b[0] << 24) | ((uint32_t)b[1] << 16) | ((uint32_t)b[2] << 8) | b[3];
    c->last_status = *st;
    return 0;
}

static ecp5_err wait_not_busy(ecp5_cfg *c)
{
    uint32_t st = 0, t;
    for (t = 0; t <= c->busy_timeout_ms * 10u; t++) {
        if (read_status(c, &st)) return ECP5_E_IO;
        if (!(st & ECP5_ST_BUSY)) return ECP5_OK;
        c->io.delay_us(c->io.ctx, 100);
    }
    return ECP5_E_BUSY_TIMEOUT;
}

static int wait_pin(ecp5_cfg *c, ecp5_pin p, int level, uint32_t ms)
{
    uint32_t t;
    for (t = 0; t <= ms * 10u; t++) {
        if (c->io.get(c->io.ctx, p) == level) return 1;
        c->io.delay_us(c->io.ctx, 100);
    }
    return 0;
}

ecp5_err ecp5_power_up(ecp5_cfg *c)
{
    if (!c) return ECP5_E_ARG;
    c->io.set(c->io.ctx, ECP5_PIN_PSRAM_REQ, 0);
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, 1);
    c->io.set(c->io.ctx, ECP5_PIN_PWR_EN, 1);
    if (!wait_pin(c, ECP5_PIN_VCC_PG, 1, c->pg_timeout_ms)) {
        c->io.set(c->io.ctx, ECP5_PIN_PWR_EN, 0);
        return ECP5_E_POWER;
    }
    if (!wait_pin(c, ECP5_PIN_INITN, 1, c->initn_timeout_ms)) {
        /* PROGRAMN held low externally keeps the device in initialisation: tell it apart from a rail fault */
        ecp5_err e = c->io.get(c->io.ctx, ECP5_PIN_PROGRAMN) ? ECP5_E_INITN_TIMEOUT : ECP5_E_PROGRAMN_HELD;
        c->io.set(c->io.ctx, ECP5_PIN_PWR_EN, 0);      /* VCCAUX / VCCIO8 missing or POR never released */
        return e;
    }
    return ECP5_OK;
}

static const uint8_t *mem_read(void *ctx, uint32_t off, uint32_t n, uint8_t *scratch)
{
    (void)n; (void)scratch;
    return (const uint8_t *)ctx + off;
}

ecp5_err ecp5_configure(ecp5_cfg *c, const ecp5_image *img)
{
    ecp5_source src;
    if (!c || !img || !img->bit || !img->bit_len) return ECP5_E_ARG;
    src.read = mem_read;
    src.ctx = (void *)(uintptr_t)img->bit;
    src.scratch = NULL;
    return ecp5_configure_stream(c, img, &src);
}

ecp5_err ecp5_configure_stream(ecp5_cfg *c, const ecp5_image *img, const ecp5_source *src)
{
    uint8_t id[4];
    uint32_t st = 0, off;
    ecp5_err e;
    int rc;
    if (!c || !img || !img->bit_len || !src || !src->read) return ECP5_E_ARG;
    e = ecp5_power_up(c);
    if (e) return e;
    c->io.set(c->io.ctx, ECP5_PIN_PSRAM_REQ, 0);              /* quiesce PSRAM before the user design disappears */
    c->io.set(c->io.ctx, ECP5_PIN_BUS_EN_N, 0);
    /* PROGRAMN pulse: tPRGM >= 110 ns accepted, <= 50 ns rejected (DS Table 3.42) */
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, 0);
    c->io.delay_us(c->io.ctx, 2);
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, 1);
    if (!wait_pin(c, ECP5_PIN_PROGRAMN, 1, 1)) { e = ECP5_E_PROGRAMN_HELD; goto fail; }
    if (!wait_pin(c, ECP5_PIN_INITN, 1, c->initn_timeout_ms)) { e = ECP5_E_INITN_TIMEOUT; goto fail; }
    if (cmd(c, ECP5_CMD_READ_ID, 0, id, 4)) { e = ECP5_E_IO; goto fail; }
    c->last_idcode = ((uint32_t)id[0] << 24) | ((uint32_t)id[1] << 16) | ((uint32_t)id[2] << 8) | id[3];
#ifndef MUTANT_ECP5_NO_IDCODE
    if (c->last_idcode != img->idcode) { e = ECP5_E_IDCODE; goto fail; }
#endif
    if (cmd(c, ECP5_CMD_ISC_ENABLE, 0, NULL, 0)) { e = ECP5_E_IO; goto fail; }
    if ((e = wait_not_busy(c)) != ECP5_OK) goto fail;
    if (cmd(c, ECP5_CMD_ISC_ERASE, 0x010000u, NULL, 0)) { e = ECP5_E_IO; goto fail; }
    if ((e = wait_not_busy(c)) != ECP5_OK) goto fail;
    if (cmd(c, ECP5_CMD_LSC_INIT_ADDRESS, 0, NULL, 0)) { e = ECP5_E_IO; goto fail; }
    /* burst: opcode + whole .bit under one SN assertion */
    {
        uint8_t h[4] = { ECP5_CMD_LSC_BITSTREAM_BURST, 0, 0, 0 };
        c->spi.select(c->spi.ctx, 1);
        rc = c->spi.transfer(c->spi.ctx, h, NULL, 4);
        for (off = 0; !rc && off < img->bit_len; off += c->chunk) {
            uint32_t n = img->bit_len - off < c->chunk ? img->bit_len - off : c->chunk;
            const uint8_t *p = src->read(src->ctx, off, n, src->scratch);
            rc = p ? c->spi.transfer(c->spi.ctx, p, NULL, n) : -1;
        }
        c->spi.select(c->spi.ctx, 0);
        if (rc) { e = ECP5_E_IO; goto fail; }
    }
    if ((e = wait_not_busy(c)) != ECP5_OK) goto fail;
    st = c->last_status;
    (void)st;
#ifndef MUTANT_ECP5_NO_STATUS_CHECK
    if ((st & ECP5_ST_FAIL) || (st & ECP5_ST_ERR_MASK)) { e = ECP5_E_CONFIG_STATUS; goto fail; }
#endif
    if (cmd(c, ECP5_CMD_ISC_DISABLE, 0, NULL, 0)) { e = ECP5_E_IO; goto fail; }
    if (!wait_pin(c, ECP5_PIN_DONE, 1, c->done_timeout_ms)) {
        e = c->io.get(c->io.ctx, ECP5_PIN_INITN) ? ECP5_E_DONE_TIMEOUT : ECP5_E_INITN_ERROR;
        goto fail;
    }
    if (!c->io.get(c->io.ctx, ECP5_PIN_INITN)) { e = ECP5_E_INITN_ERROR; goto fail; }
    return ECP5_OK;                                              /* bus stays enabled for the mailbox */
fail:
    ecp5_safe(c, 0);
    return e;
}

ecp5_err ecp5_probe(ecp5_cfg *c, uint32_t *idcode, uint32_t *status)
{
    uint8_t id[4];
    ecp5_err e;
    if (!c || !idcode || !status) return ECP5_E_ARG;
    *idcode = 0; *status = 0;
    e = ecp5_power_up(c);
    if (e) return e;
    c->io.set(c->io.ctx, ECP5_PIN_BUS_EN_N, 0);
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, 0);
    c->io.delay_us(c->io.ctx, 2);
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, 1);
    if (!wait_pin(c, ECP5_PIN_PROGRAMN, 1, 1)) { e = ECP5_E_PROGRAMN_HELD; goto out; }
    if (!wait_pin(c, ECP5_PIN_INITN, 1, c->initn_timeout_ms)) { e = ECP5_E_INITN_TIMEOUT; goto out; }
    if (cmd(c, ECP5_CMD_READ_ID, 0, id, 4)) { e = ECP5_E_IO; goto out; }
    *idcode = ((uint32_t)id[0] << 24) | ((uint32_t)id[1] << 16) | ((uint32_t)id[2] << 8) | id[3];
    if (read_status(c, status)) { e = ECP5_E_IO; goto out; }
    e = *idcode == ECP5_IDCODE_LFE5U_45 ? ECP5_OK : ECP5_E_IDCODE;
out:
    ecp5_safe(c, e != ECP5_OK);
    return e;
}

void ecp5_safe(ecp5_cfg *c, int power_off)
{
    if (!c) return;
    c->io.set(c->io.ctx, ECP5_PIN_PSRAM_REQ, 0);
    c->io.set(c->io.ctx, ECP5_PIN_BUS_EN_N, 1);
    c->io.set(c->io.ctx, ECP5_PIN_PROGRAMN, power_off ? 1 : 0);   /* never drive PROGRAMN into an unpowered FPGA */
    if (power_off) c->io.set(c->io.ctx, ECP5_PIN_PWR_EN, 0);
}

const char *ecp5_err_string(ecp5_err e)
{
    static const char *const s[ECP5_E_COUNT] = {
        "ok", "bad argument", "container header", "container truncated (microSD read)", "bitstream CRC32",
        "bitstream not for LFE5U-45", "container ABI mismatch", "FPGA VCC power-good missing", "INITN timeout",
        "PROGRAMN held low", "READ_ID mismatch (absent/wrong FPGA)", "sysCONFIG busy timeout",
        "configuration status FAIL/CRC", "DONE timeout", "INITN low after configuration", "SPI I/O" };
    return (unsigned)e < ECP5_E_COUNT ? s[e] : "unknown";
}
