/* ARC-1 Compact R08 -- SPI NOR driver (see include/spi_nor.h). HOST_TESTED only.
 * R10 copy of R85C_WORK/firmware/src/spi_nor.c. Changes: (1) two W25Q512JV rows in k_known; (2) capacity code 0x20
 * decoded as 64 MiB (the R08 `1u << code` was undefined for codes >= 0x20; harmless for the R08 32 MiB part). */
#include "spi_nor.h"
#include <string.h>

#define NOR_16M 0x01000000u

typedef struct { uint8_t mfr; uint16_t dev; uint32_t size; enum nor_addr_strategy strat; } nor_known;
/* Only parts whose datasheet was read for this driver. */
static const nor_known k_known[] = {
    { 0xEFu, 0x4019u, 0x02000000u, NOR_ADDR_4B_OPCODES },   /* W25Q256JV (standard SPI ID) */
    { 0xEFu, 0x7019u, 0x02000000u, NOR_ADDR_4B_OPCODES },   /* W25Q256JV (-IM/-JM ID variant) */
    /* R10 (ARC1_MEMORY_R10 s3.2): W25Q512JV, 512 Mbit. DOCUMENTED (Winbond W25Q512JV Rev I 2026-05-05 s8.1.1 / s8.1.2,
     * W25Q512JV-DTR Rev D s8.1.1): JEDEC EF 40 20 (-IQ/-IN), EF 70 20 (-IM); power-up 3-byte mode (ADP = 0 factory);
     * dedicated 4-byte opcodes 13h/0Ch/12h/21h/DCh; EAR C5h/C8h volatile. tPP <= 3.5 ms, tSE <= 400 ms (s9.6). */
    { 0xEFu, 0x4020u, 0x04000000u, NOR_ADDR_4B_OPCODES },
    { 0xEFu, 0x7020u, 0x04000000u, NOR_ADDR_4B_OPCODES },
};

static int xfer(nor_dev *d, const uint8_t *hdr, size_t nh, const uint8_t *tx, uint8_t *rx, size_t n)
{
    const arc1_spi_hal *h = d->hal;
    int rc = 0;
    h->select(h->ctx, 1);
    if (nh) rc = h->transfer(h->ctx, hdr, NULL, nh);
    if (rc == 0 && n) rc = h->transfer(h->ctx, tx, rx, n);
    h->select(h->ctx, 0);
    return rc ? NOR_ERR_IO : NOR_OK;
}

static int simple(nor_dev *d, uint8_t op) { return xfer(d, &op, 1, NULL, NULL, 0); }

static int rdreg(nor_dev *d, uint8_t op, uint8_t *v)
{
    return xfer(d, &op, 1, NULL, v, 1);
}

static int wrreg(nor_dev *d, uint8_t op, uint8_t v)
{
    uint8_t b[2] = { op, v };
    return xfer(d, b, 2, NULL, NULL, 0);
}

static int wait_idle(nor_dev *d, uint32_t timeout_us)
{
    const arc1_spi_hal *h = d->hal;
    uint64_t t0 = h->now_us(h->ctx);
    for (;;) {
        uint8_t sr = 0xFF;
        int rc = rdreg(d, NOR_OP_RDSR1, &sr);
        if (rc) return rc;
#ifdef MUTANT_NOR_NO_WIP_POLL
        sr = 0;
#endif
        if (!(sr & NOR_SR1_WIP)) return NOR_OK;
        if (h->now_us(h->ctx) - t0 > timeout_us) return NOR_ERR_TIMEOUT;
    }
}

static int write_enable(nor_dev *d)
{
    uint8_t sr = 0;
    int rc = simple(d, NOR_OP_WREN);
    if (rc) return rc;
    rc = rdreg(d, NOR_OP_RDSR1, &sr);
    if (rc) return rc;
    return (sr & NOR_SR1_WEL) ? NOR_OK : NOR_ERR_PROTECTED;
}

static int set_ear(nor_dev *d, uint8_t ear)
{
    int rc = write_enable(d);
    if (rc) return rc;
    rc = wrreg(d, NOR_OP_WREAR, ear);
    if (rc) return rc;
    {
        uint8_t back = 0xFF;
        rc = rdreg(d, NOR_OP_RDEAR, &back);
        if (rc) return rc;
        if (back != ear) return NOR_ERR_STATE;
    }
    return NOR_OK;
}

/* Build opcode + address for an access at `addr` and select EAR if needed. */
static int addr_hdr(nor_dev *d, uint8_t op3, uint8_t op4, uint32_t addr, uint8_t *hdr, size_t *nh, int *ear_used)
{
    *ear_used = 0;
#ifdef MUTANT_NOR_3B_UPPER
    (void)op4; (void)d;
    hdr[0] = op3; hdr[1] = (uint8_t)(addr >> 16); hdr[2] = (uint8_t)(addr >> 8); hdr[3] = (uint8_t)addr; *nh = 4;
    return NOR_OK;
#else
    if (d->info.strategy == NOR_ADDR_4B_OPCODES) {
        hdr[0] = op4;
        hdr[1] = (uint8_t)(addr >> 24); hdr[2] = (uint8_t)(addr >> 16);
        hdr[3] = (uint8_t)(addr >> 8);  hdr[4] = (uint8_t)addr;
        *nh = 5;
        return NOR_OK;
    }
    if (d->info.strategy == NOR_ADDR_EAR && addr >= NOR_16M) {
        int rc = set_ear(d, (uint8_t)(addr >> 24));
        if (rc) return rc;
        *ear_used = 1;
    } else if (addr >= NOR_16M) {
        return NOR_ERR_RANGE;
    }
    hdr[0] = op3; hdr[1] = (uint8_t)(addr >> 16); hdr[2] = (uint8_t)(addr >> 8); hdr[3] = (uint8_t)addr;
    *nh = 4;
    return NOR_OK;
#endif
}

static int ear_restore(nor_dev *d, int ear_used, int rc)
{
#ifdef MUTANT_NOR_NO_EAR_RESTORE
    (void)d; (void)ear_used;
    return rc;
#else
    if (ear_used) {
        int rc2 = set_ear(d, 0);
        if (rc == NOR_OK) rc = rc2;
    }
    return rc;
#endif
}

static int range_ok(const nor_dev *d, uint32_t addr, size_t n)
{
    return d->ready && (uint64_t)addr + n <= d->info.size_bytes;
}

static uint32_t rd_le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static int read_sfdp(nor_dev *d, uint32_t a, uint8_t *buf, size_t n)
{
    uint8_t hdr[5] = { NOR_OP_SFDP, (uint8_t)(a >> 16), (uint8_t)(a >> 8), (uint8_t)a, 0x00 /* dummy */ };
    return xfer(d, hdr, 5, NULL, buf, n);
}

int nor_read_sr3(nor_dev *d, uint8_t *sr3) { return rdreg(d, NOR_OP_RDSR3, sr3); }

/* Leave the device as the boot ROM expects it: 3-byte mode, EAR = 0. */
static int normalise_addr_mode(nor_dev *d, int record)
{
    uint8_t sr3 = 0, ear = 0;
    int rc = rdreg(d, NOR_OP_RDSR3, &sr3);
    if (rc) return rc;
    if (sr3 & NOR_SR3_ADS) {
        if (record) d->info.found_in_4b_mode = 1;
        rc = simple(d, NOR_OP_EX4B);
        if (rc) return rc;
        rc = rdreg(d, NOR_OP_RDSR3, &sr3);
        if (rc) return rc;
        if (sr3 & NOR_SR3_ADS) return NOR_ERR_STATE;
    }
    if (sr3 & NOR_SR3_ADP) return NOR_ERR_STATE;   /* would power up in 4-byte mode: boot ROM risk */
    rc = rdreg(d, NOR_OP_RDEAR, &ear);
    if (rc) return rc;
    if (ear != 0) {
        if (record) d->info.found_ear_nonzero = 1;
        rc = set_ear(d, 0);
        if (rc) return rc;
    }
    return NOR_OK;
}

int nor_init(nor_dev *d, const arc1_spi_hal *hal)
{
    uint8_t id[3] = { 0, 0, 0 };
    uint8_t sf[16];
    uint8_t bfpt[8];
    int rc;
    size_t i;
    enum nor_addr_strategy forced = d->force_strategy;
    int force_set = d->force_set;

    memset(d, 0, sizeof *d);
    d->hal = hal;
    d->force_strategy = forced;
    d->force_set = force_set;
    d->prog_timeout_us = 5000u;      /* page program max 3 ms (W25Q256JV tPP) + margin */
    d->erase_timeout_us = 500000u;   /* 4 KiB sector erase max 400 ms (tSE) + margin */

    /* Software reset: abort any operation interrupted by a CPU reset. */
    if ((rc = simple(d, NOR_OP_RSTEN)) != NOR_OK) return rc;
    if ((rc = simple(d, NOR_OP_RST)) != NOR_OK) return rc;
    {   /* tRST 30 us */
        uint64_t t0 = hal->now_us(hal->ctx);
        while (hal->now_us(hal->ctx) - t0 < 40u) { }
    }
    {
        uint8_t op = NOR_OP_JEDEC_ID;
        if ((rc = xfer(d, &op, 1, NULL, id, 3)) != NOR_OK) return rc;
    }
    d->info.mfr = id[0];
    d->info.dev = (uint16_t)((id[1] << 8) | id[2]);
    if (id[0] == 0x00 || id[0] == 0xFF) return NOR_ERR_ID;          /* no device / MISO stuck */
    if (id[2] < 0x10 || id[2] > 0x20) return NOR_ERR_ID;             /* capacity code out of range */

    /* SFDP (JESD216): header, first parameter header, BFPT DWORDs 1-2 */
    if ((rc = read_sfdp(d, 0, sf, 16)) != NOR_OK) return rc;
    if (sf[0] == 'S' && sf[1] == 'F' && sf[2] == 'D' && sf[3] == 'P') {
        uint32_t ptp = (uint32_t)sf[12] | ((uint32_t)sf[13] << 8) | ((uint32_t)sf[14] << 16);
        if ((rc = read_sfdp(d, ptp, bfpt, 8)) != NOR_OK) return rc;
        {
            uint32_t dw1 = rd_le32(bfpt), dw2 = rd_le32(bfpt + 4);
            d->info.sfdp_ok = 1;
            d->info.sfdp_addr_bytes = (int)((dw1 >> 17) & 3u);
            d->info.sfdp_density_bits = (dw2 & 0x80000000u) ? 0u : dw2 + 1u;
        }
    }
    /* JEDEC capacity codes run 0x10..0x19 (2^code bytes) and then continue at 0x20 = 512 Mbit (64 MiB): the R08
     * expression 1u << id[2] shifts by 32 for a W25Q512JV (R10 fix, found by f133_bootloader/tests/test_boot.c) */
    d->info.size_bytes = id[2] <= 0x19u ? 1u << id[2] : (id[2] == 0x20u ? 0x04000000u : 0u);
    if (d->info.size_bytes == 0) return NOR_ERR_ID;
    d->info.sector_bytes = 4096u;
    d->info.page_bytes = 256u;
    if (d->info.sfdp_ok && d->info.sfdp_density_bits != 0 &&
        d->info.sfdp_density_bits / 8u != d->info.size_bytes) return NOR_ERR_ID;   /* JEDEC vs SFDP mismatch */

    d->info.strategy = NOR_ADDR_3B_ONLY;
    if (d->info.size_bytes > NOR_16M) {
        int known = 0;
        for (i = 0; i < sizeof k_known / sizeof k_known[0]; i++)
            if (k_known[i].mfr == d->info.mfr && k_known[i].dev == d->info.dev &&
                k_known[i].size == d->info.size_bytes) { d->info.strategy = k_known[i].strat; known = 1; }
        if (!known) return NOR_ERR_ID;     /* unknown > 16 MiB part: refuse rather than guess */
        if (!d->info.sfdp_ok || d->info.sfdp_addr_bytes != 1) return NOR_ERR_ID;  /* expect 3B/4B capable */
    }
    if (d->force_set) d->info.strategy = d->force_strategy;

    d->ready = 1;
    if ((rc = normalise_addr_mode(d, 1)) != NOR_OK) { d->ready = 0; return rc; }
#ifdef MUTANT_NOR_ENTER_4B
    simple(d, NOR_OP_EN4B);
#endif
    return NOR_OK;
}

int nor_read(nor_dev *d, uint32_t addr, void *buf, size_t n)
{
    uint8_t hdr[5];
    size_t nh;
    int ear, rc;
    if (!range_ok(d, addr, n)) return d->ready ? NOR_ERR_RANGE : NOR_ERR_STATE;
    if (n == 0) return NOR_OK;
    /* With the EAR fallback a read must not cross a 16 MiB bank. */
    if (d->info.strategy == NOR_ADDR_EAR && (addr >> 24) != (uint32_t)(((uint64_t)addr + n - 1) >> 24)) {
        size_t first = (size_t)(NOR_16M - (addr & (NOR_16M - 1u)));
        rc = nor_read(d, addr, buf, first);
        if (rc) return rc;
        return nor_read(d, addr + (uint32_t)first, (uint8_t *)buf + first, n - first);
    }
    rc = addr_hdr(d, NOR_OP_READ3, NOR_OP_READ4, addr, hdr, &nh, &ear);
    if (rc) return rc;
    rc = xfer(d, hdr, nh, NULL, (uint8_t *)buf, n);
    return ear_restore(d, ear, rc);
}

int nor_erase_sector(nor_dev *d, uint32_t addr)
{
    uint8_t hdr[5];
    size_t nh;
    int ear, rc;
    if (!range_ok(d, addr, 1)) return d->ready ? NOR_ERR_RANGE : NOR_ERR_STATE;
    if (addr % d->info.sector_bytes) return NOR_ERR_ALIGN;
    rc = addr_hdr(d, NOR_OP_SE3, NOR_OP_SE4, addr, hdr, &nh, &ear);
    if (rc) return rc;
    rc = write_enable(d);
    if (rc == NOR_OK) rc = xfer(d, hdr, nh, NULL, NULL, 0);
    if (rc == NOR_OK) rc = wait_idle(d, d->erase_timeout_us);
    return ear_restore(d, ear, rc);
}

int nor_program(nor_dev *d, uint32_t addr, const void *buf, size_t n)
{
    const uint8_t *p = (const uint8_t *)buf;
    if (!range_ok(d, addr, n)) return d->ready ? NOR_ERR_RANGE : NOR_ERR_STATE;
    while (n) {
        uint32_t room = d->info.page_bytes - (addr % d->info.page_bytes);   /* never wrap inside a page */
        size_t chunk = n < room ? n : room;
        uint8_t hdr[5];
        size_t nh;
        int ear, rc;
        rc = addr_hdr(d, NOR_OP_PP3, NOR_OP_PP4, addr, hdr, &nh, &ear);
        if (rc) return rc;
        rc = write_enable(d);
        if (rc == NOR_OK) rc = xfer(d, hdr, nh, p, NULL, chunk);
        if (rc == NOR_OK) rc = wait_idle(d, d->prog_timeout_us);
        rc = ear_restore(d, ear, rc);
        if (rc) return rc;
        addr += (uint32_t)chunk; p += chunk; n -= chunk;
    }
    return NOR_OK;
}

int nor_write_verified(nor_dev *d, uint32_t addr, const void *buf, size_t n)
{
    uint8_t tmp[256];
    uint32_t s, end;
    size_t off = 0;
    int rc;
    if (!range_ok(d, addr, n)) return d->ready ? NOR_ERR_RANGE : NOR_ERR_STATE;
    if (n == 0) return NOR_OK;
    if (addr % d->info.sector_bytes) return NOR_ERR_ALIGN;   /* whole sectors are rewritten */
    end = addr + (uint32_t)n;
    for (s = addr; s < end; s += d->info.sector_bytes)
        if ((rc = nor_erase_sector(d, s)) != NOR_OK) return rc;
    if ((rc = nor_program(d, addr, buf, n)) != NOR_OK) return rc;
    while (off < n) {
        size_t c = (n - off) < sizeof tmp ? (n - off) : sizeof tmp;
        if ((rc = nor_read(d, addr + (uint32_t)off, tmp, c)) != NOR_OK) return rc;
        if (memcmp(tmp, (const uint8_t *)buf + off, c) != 0) return NOR_ERR_VERIFY;
        off += c;
    }
    return NOR_OK;
}

int nor_prepare_reboot(nor_dev *d)
{
    if (!d->ready) return NOR_ERR_STATE;
    return normalise_addr_mode(d, 0);
}
