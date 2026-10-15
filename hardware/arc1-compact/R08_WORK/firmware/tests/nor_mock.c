#include "nor_mock.h"
#include <stdlib.h>
#include <string.h>

void nor_mock_init(nor_mock *m, uint32_t size, uint8_t mfr, uint8_t d1, uint8_t d2)
{
    memset(m, 0, sizeof *m);
    m->mem = (uint8_t *)malloc(size);
    memset(m->mem, 0xFF, size);
    m->size = size;
    m->jedec[0] = mfr; m->jedec[1] = d1; m->jedec[2] = d2;
    m->has_4b_opcodes = 1;
    m->sfdp_present = 1;
    m->sfdp_density_bits = size * 8u;
    m->sfdp_addr_bytes = size > 0x01000000u ? 1 : 0;
    m->miso_stuck = -1;
}

void nor_mock_free(nor_mock *m) { free(m->mem); m->mem = NULL; }

static uint8_t sfdp_byte(const nor_mock *m, uint32_t a)
{
    /* header at 0: "SFDP", rev 1.6, 1 parameter header; BFPT at 0x30 */
    static const uint8_t hdr[16] = { 'S','F','D','P', 0x06, 0x01, 0x00, 0xFF,
                                     0x00, 0x06, 0x01, 0x10, 0x30, 0x00, 0x00, 0xFF };
    uint32_t dw1, dw2;
    if (!m->sfdp_present) return 0xFF;
    if (a < 16) return hdr[a];
    dw1 = 0xFFF920E5u & ~(3u << 17);
    dw1 |= ((uint32_t)m->sfdp_addr_bytes & 3u) << 17;
    dw2 = m->sfdp_density_bits - 1u;
    if (a >= 0x30 && a < 0x34) return (uint8_t)(dw1 >> (8 * (a - 0x30)));
    if (a >= 0x34 && a < 0x38) return (uint8_t)(dw2 >> (8 * (a - 0x34)));
    return 0xFF;
}

/* number of address bytes for an opcode in the current mode */
static int addr_len(const nor_mock *m, uint8_t op)
{
    switch (op) {
    case 0x13: case 0x12: case 0x21: case 0xDC: case 0x0C:
        return m->has_4b_opcodes ? 4 : -1;
    case 0x03: case 0x02: case 0x20: case 0xD8: case 0x0B:
        return m->four_byte_mode ? 4 : 3;
    case 0x5A: return 3;
    default: return 0;
    }
}

static uint32_t eff_addr(const nor_mock *m, const uint8_t *a, int al)
{
    uint32_t x;
    if (al == 4) x = ((uint32_t)a[0] << 24) | ((uint32_t)a[1] << 16) | ((uint32_t)a[2] << 8) | a[3];
    else x = ((uint32_t)m->ear << 24) | ((uint32_t)a[0] << 16) | ((uint32_t)a[1] << 8) | a[2];
    return x & (m->size - 1u);    /* the device wraps at its capacity */
}

static uint8_t sr1(nor_mock *m)
{
    uint8_t s = 0;
    if (m->stuck_busy || m->busy_polls > 0) { s |= 1; if (m->busy_polls > 0) m->busy_polls--; }
    if (m->wel) s |= 2;
    return s;
}

/* byte-by-byte response for reads issued inside the transaction */
static uint8_t out_byte(nor_mock *m, size_t idx)
{
    uint8_t op = m->buf[0];
    int al;
    if (m->miso_stuck >= 0) return (uint8_t)m->miso_stuck;
    if (idx == 0) return 0xFF;
    switch (op) {
    case 0x9F: return idx <= 3 ? m->jedec[idx - 1] : 0xFF;
    case 0x05: return sr1(m);
    case 0x35: return 0x00;
    case 0x15: return (uint8_t)((m->four_byte_mode ? 1 : 0) | (m->adp ? 2 : 0));
    case 0xC8: return m->ear;
    case 0x5A:
        if (idx < 5) return 0xFF;
        return sfdp_byte(m, ((((uint32_t)m->buf[1] << 16) | ((uint32_t)m->buf[2] << 8) | m->buf[3]) + (uint32_t)(idx - 5)));
    case 0x03: case 0x13: case 0x0B: case 0x0C: {
        int dummy = (op == 0x0B || op == 0x0C) ? 1 : 0;
        al = addr_len(m, op);
        if (al < 0 || idx < (size_t)(1 + al + dummy)) return 0xFF;
        {
            uint32_t a = eff_addr(m, &m->buf[1], al) + (uint32_t)(idx - (size_t)(1 + al + dummy));
            a &= m->size - 1u;
            if (a >= 0x01000000u) m->upper_half_touched = 1;
            return m->mem[a];
        }
    }
    default: return 0xFF;
    }
}

static void commit(nor_mock *m)
{
    uint8_t op;
    int al;
    if (m->n == 0) return;
    op = m->buf[0];
    if (op != 0x99) m->reset_enabled = (op == 0x66);
    switch (op) {
    case 0x06: if (!m->wel_never_sets) m->wel = 1; break;
    case 0x04: m->wel = 0; break;
    case 0x99:
        if (m->reset_enabled) { m->n_resets++; m->four_byte_mode = m->adp; m->ear = 0; m->wel = 0; m->busy_polls = 0; }
        m->reset_enabled = 0; break;
    case 0xB7: m->four_byte_mode = 1; break;
    case 0xE9: m->four_byte_mode = 0; m->n_ex4b++; break;
    case 0xC5: if (m->wel && m->n >= 2) { m->ear = m->buf[1] & 0x01; m->n_wrear++; } m->wel = 0; break;
    case 0x02: case 0x12:
        al = addr_len(m, op);
        if (al < 0 || m->n < (size_t)(1 + al)) break;
        if (m->busy_polls > 0 || m->stuck_busy) { m->prog_while_busy++; break; }
        if (!m->wel) { m->prog_without_wel++; break; }
        {
            uint32_t a = eff_addr(m, &m->buf[1], al);
            size_t k, nd = m->n - (size_t)(1 + al);
            if (m->power_cut_after_bytes > 0 && (size_t)m->power_cut_after_bytes < nd) { nd = (size_t)m->power_cut_after_bytes; m->power_cut_after_bytes = 0; }
            if ((a & 0xFFu) + nd > 256u) m->page_wrap++;
            for (k = 0; k < nd; k++) {
                uint32_t pa = (a & ~0xFFu) | ((a + (uint32_t)k) & 0xFFu);   /* wraps within the page */
                if (pa >= 0x01000000u) m->upper_half_touched = 1;
                m->mem[pa] &= m->buf[(size_t)(1 + al) + k];
            }
            m->n_programs++;
            m->busy_polls = 3;
        }
        m->wel = 0; break;
    case 0x20: case 0x21:
        al = addr_len(m, op);
        if (al < 0 || m->n < (size_t)(1 + al)) break;
        if (m->busy_polls > 0 || m->stuck_busy) { m->prog_while_busy++; break; }
        if (!m->wel) { m->prog_without_wel++; break; }
        {
            uint32_t a = eff_addr(m, &m->buf[1], al) & ~0xFFFu;
            if (a >= 0x01000000u) m->upper_half_touched = 1;
            memset(&m->mem[a], 0xFF, 4096);
            m->n_erases++;
            m->busy_polls = 5;
        }
        m->wel = 0; break;
    default: break;
    }
}

static void mk_select(void *ctx, int asserted)
{
    nor_mock *m = (nor_mock *)ctx;
    if (asserted && !m->cs) { m->cs = 1; m->n = 0; }
    else if (!asserted && m->cs) { m->cs = 0; commit(m); }
}

static int mk_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n)
{
    nor_mock *m = (nor_mock *)ctx;
    size_t i;
    if (!m->cs) return -1;
    for (i = 0; i < n; i++) {
        uint8_t b = tx ? tx[i] : 0x00;
        if (m->n < sizeof m->buf) m->buf[m->n] = b;
        if (rx) rx[i] = out_byte(m, m->n);
        m->n++;
    }
    m->t_us += n;
    return 0;
}

static uint64_t mk_now(void *ctx) { nor_mock *m = (nor_mock *)ctx; return m->t_us++; }

void nor_mock_hal(nor_mock *m, arc1_spi_hal *hal)
{
    hal->ctx = m; hal->select = mk_select; hal->transfer = mk_transfer; hal->now_us = mk_now;
}

int nor_mock_brom_read_ok(const nor_mock *m) { return !m->four_byte_mode && m->ear == 0 && !m->adp; }
