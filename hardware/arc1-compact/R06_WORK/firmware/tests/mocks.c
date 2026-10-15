#include "mocks.h"

#include <string.h>

#include "arc1_transform.h"

/* ============================ BT820 ============================ */
static void fnv(uint32_t *h, uint8_t b) { *h = (*h ^ b) * 16777619u; }

void mbt_init(mock_bt820 *m) {
    memset(m, 0, sizeof(*m));
    m->trace_hash = 2166136261u;
}

static uint8_t mbt_read_byte(mock_bt820 *m) {
    uint32_t a = m->addr + (uint32_t)m->rd_pos;
    uint8_t v;
    /* mock choice: everything outside the 1 MiB window is "illegal" */
    if (a >= MBT_RAM_BYTES) {
        static const uint8_t ill[4] = {0xBA, 0xAB, 0xAD, 0xDE};   /* 0xDEADABBA little endian */
        v = ill[a & 3u];
    } else {
        v = m->ram[a];
    }
    m->rd_pos++;
    return v;
}

static void mbt_select(void *ctx, int asserted) {
    mock_bt820 *m = (mock_bt820 *)ctx;
    if (asserted && !m->cs) {
        m->cs = 1; m->nbytes = 0; m->is_write = m->is_read = 0; m->wn = 0;
        m->sent_valid = 0; m->rd_pos = 0;
    } else if (!asserted && m->cs) {
        m->cs = 0;
        if (m->nbytes == 5 && !m->hdr[0] && !m->hdr[1] && !m->hdr[2] && !m->hdr[3] && !m->hdr[4]) {
            m->n_active++;
            fnv(&m->trace_hash, 0xAC);
        }
        if (m->is_write && m->wn) m->n_partial_words++;   /* incomplete word discarded */
        m->now_us += 1;                                   /* CS# high gap */
    }
}

static int mbt_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    mock_bt820 *m = (mock_bt820 *)ctx;
    size_t i;
    if (!m->cs) return -1;
    for (i = 0; i < n; i++) {
        uint8_t t = tx ? tx[i] : 0u, r = 0u;
        size_t k = m->nbytes++;
        m->now_us += 1;
        if (k < 5) m->hdr[k] = t;
        if (k == 3 && m->hdr[0] != 0xFFu) {
            memcpy(m->last_hdr, m->hdr, 4);
            m->addr = ((uint32_t)(m->hdr[0] & 0x7Fu) << 24) | ((uint32_t)m->hdr[1] << 16) |
                      ((uint32_t)m->hdr[2] << 8) | m->hdr[3];
            if (m->hdr[0] & 0x80u) { m->is_write = 1; m->n_writes++; }
            else { m->is_read = 1; m->n_reads++; m->rd_poll_left = m->poll_latency; }
        } else if (k == 4 && m->hdr[0] == 0xFFu) {
            m->last_cmd[0] = m->hdr[1]; m->last_cmd[1] = m->hdr[2]; m->last_cmd[2] = m->hdr[3];
            m->n_cmds++;
            fnv(&m->trace_hash, 0xFF); fnv(&m->trace_hash, m->hdr[1]); fnv(&m->trace_hash, m->hdr[2]);
        } else if (k >= 4 && m->is_write) {
            m->wword[m->wn++] = t;
            if (m->wn == 4) {
                uint32_t a = m->addr;
                size_t j;
                if (a < MBT_RAM_BYTES - 3u) memcpy(&m->ram[a], m->wword, 4);
                fnv(&m->trace_hash, 0x57);
                for (j = 0; j < 4; j++) { fnv(&m->trace_hash, (uint8_t)(a >> (8 * j))); fnv(&m->trace_hash, m->wword[j]); }
                m->addr += 4; m->wn = 0;
            }
        } else if (k >= 4 && m->is_read) {
            if (!m->sent_valid) {
                if (m->never_valid || m->rd_poll_left) { r = 0x00u; if (m->rd_poll_left) m->rd_poll_left--; }
                else { r = 0x01u; m->sent_valid = 1; }
            } else {
                r = mbt_read_byte(m);
            }
        }
        if (rx) rx[i] = r;
    }
    return 0;
}

static uint64_t mbt_now(void *ctx) { return ((mock_bt820 *)ctx)->now_us; }

arc1_spi_hal mbt_hal(mock_bt820 *m) {
    arc1_spi_hal h;
    h.ctx = m; h.select = mbt_select; h.transfer = mbt_transfer; h.now_us = mbt_now;
    return h;
}

/* ============================ T35 ============================ */
void mt35_init(mock_t35 *m, mt35_engine e) {
    memset(m, 0, sizeof(*m));
    m->present = 1;
    m->engine = e;
    m->latency_us = 50;
    (void)arc1_session_init(&m->session, 8);
}

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)(v & 0xFFu); p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xFFu); p[1] = (uint8_t)((v >> 8) & 0xFFu);
    p[2] = (uint8_t)((v >> 16) & 0xFFu); p[3] = (uint8_t)(v >> 24);
}
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static int32_t s32(uint32_t v) { return (v & 0x80000000u) ? -(int32_t)(~v) - 1 : (int32_t)v; }

static size_t emit_status(const arc1_reply *r, uint8_t *out, size_t cap) {
    uint8_t pl[8];
    size_t w = 0;
    if (arc1_status_payload(r, pl) != ARC1_OK) return 0;
    if (arc1_encode(ARC1_STATUS, r->epoch, r->sequence, pl, 8, out, cap, &w) != ARC1_OK) return 0;
    return w;
}

/* R05-semantics accelerator in software: what the R07 RTL must eventually do */
static void sw_accel(mock_t35 *m) {
    static arc1_transform_job jobs[85];
    static arc1_transform_result res[85];
    static uint8_t pl[4096];
    arc1_packet pk;
    arc1_reply rep;
    size_t o = 0, w = 0, i, n = 0, pll;
    uint16_t st;
    uint16_t app = 0;
    m->resp_len = 0;
    if (arc1_decode(m->req, m->req_len, &pk) != ARC1_OK) return;   /* garbage: no reply */
    st = arc1_session_request(&m->session, &pk, &rep);
    o += emit_status(&rep, m->resp + o, sizeof m->resp - o);
    if (st == ARC1_STATUS_ACCEPTED) {
        const uint8_t *p = pk.payload;
        if (pk.payload_length < 8 || get16(p) != 1u) app = 2;
        else if (get16(p + 2) != 1u) app = 3;
        else {
            n = get16(p + 4);
            if (n == 0 || n > 85 || get16(p + 6) != 0 || pk.payload_length != 8u + 48u * n) app = 1;
        }
        if (!app) {
            for (i = 0; i < n; i++) {
                const uint8_t *r = p + 8 + 48 * i;
                jobs[i].xmin = s32(get32(r)); jobs[i].ymin = s32(get32(r + 4));
                jobs[i].xmax = s32(get32(r + 8)); jobs[i].ymax = s32(get32(r + 12));
                jobs[i].m00 = s32(get32(r + 16)); jobs[i].m01 = s32(get32(r + 20)); jobs[i].m02 = s32(get32(r + 24));
                jobs[i].m10 = s32(get32(r + 28)); jobs[i].m11 = s32(get32(r + 32)); jobs[i].m12 = s32(get32(r + 36));
                jobs[i].viewport_width = get16(r + 40); jobs[i].viewport_height = get16(r + 42);
                jobs[i].tag = get32(r + 44);
            }
            arc1_transform_batch(jobs, res, n);
            m->jobs_executed++;
        }
        if (m->engine == ENG_APP_ERROR) { app = 1; n = 0; }
        if (app) n = 0;
        put16(pl, 1); put16(pl + 2, 1); put16(pl + 4, (uint16_t)n); put16(pl + 6, app);
        for (i = 0; i < n; i++) {
            uint8_t *r = pl + 8 + 24 * i;
            uint32_t tag = res[i].tag;
            int32_t minx = res[i].minx;
            if (m->engine == ENG_WRONG_TAG && i == n / 2) tag ^= 0x100u;
            if (m->engine == ENG_WRONG_VALUE && i == n / 2) minx += 65536;
            put32(r, tag); put32(r + 4, (uint32_t)minx); put32(r + 8, (uint32_t)res[i].miny);
            put32(r + 12, (uint32_t)res[i].maxx); put32(r + 16, (uint32_t)res[i].maxy); put32(r + 20, res[i].flags);
        }
        pll = 8 + 24 * n;
        if (arc1_encode(ARC1_RESULT, pk.epoch, pk.sequence, pl, pll, m->resp + o, sizeof m->resp - o, &w) == ARC1_OK) {
            if (m->engine == ENG_CORRUPT_CRC) m->resp[o + w - 1] ^= 0x5Au;
            o += w;
        }
        if (arc1_session_complete(&m->session, pk.epoch, pk.sequence, &rep) == ARC1_STATUS_DONE &&
            m->engine != ENG_NO_DONE)
            o += emit_status(&rep, m->resp + o, sizeof m->resp - o);
    }
    m->resp_len = (uint16_t)o;
}

static void mt35_reset_state(mock_t35 *m) {
    m->job_pending = m->resp_ready = m->overrun = 0;
    m->req_len = m->resp_len = 0;
    m->doorbells = 0;
    (void)arc1_session_init(&m->session, 8);   /* receiver state is volatile (WIRE_ABI) */
}

static void mt35_tick(mock_t35 *m) {
    if (!m->present && m->absent_until_us && m->now_us >= m->absent_until_us) {
        m->present = 1; m->absent_until_us = 0; mt35_reset_state(m);
    }
    if (m->job_pending && m->ready_at_us && m->now_us >= m->ready_at_us) {
        m->job_pending = 0; m->resp_ready = 1; m->ready_at_us = 0;
    }
}

static void doorbell(mock_t35 *m) {
    if (m->job_pending || m->resp_ready || m->req_len == 0 || m->req_len > 8192) { m->overrun = 1; return; }
    m->job_pending = 1; m->doorbells++;
    if (m->engine == ENG_RESET_ON_JOB && m->req_len > 32) {         /* FPGA lost mid-job */
        m->present = 0; m->absent_until_us = m->now_us + 2000; return;
    }
    if (m->engine == ENG_LOOPBACK) { memcpy(m->resp, m->req, m->req_len); m->resp_len = m->req_len; }
    else sw_accel(m);
    if (m->engine == ENG_DROP && m->req_len > 32) { m->ready_at_us = 0; return; }   /* never answers */
    m->ready_at_us = m->now_us + ((m->engine == ENG_SLOW && m->req_len > 32) ? 10u * 1000u * 1000u : m->latency_us);
    if (m->resp_len == 0) m->ready_at_us = 0;                        /* nothing to say */
}

static uint8_t reg_read(mock_t35 *m, uint16_t a) {
    uint16_t st = (uint16_t)(1u | (m->job_pending ? 8u : 0u) | (m->resp_ready ? 16u : 0u) | (m->overrun ? 32u : 0u) | 2u);
    if (a >= 0x2000 && a < 0x4000) return m->req[a - 0x2000];
    if (a >= 0x4000 && a < 0x6000) return m->resp[a - 0x4000];
    switch (a) {
    case 0: return 'A'; case 1: return 'M'; case 2: return 'B'; case 3: return 'X';
    case 4: return 1; case 6: return 3;
    case 8: return (uint8_t)(st & 0xFFu); case 9: return (uint8_t)(st >> 8);
    case 0x10: return (uint8_t)(m->req_len & 0xFFu); case 0x11: return (uint8_t)(m->req_len >> 8);
    case 0x14: return (uint8_t)(m->resp_len & 0xFFu); case 0x15: return (uint8_t)(m->resp_len >> 8);
    default: return 0;
    }
}

static void reg_write(mock_t35 *m, uint16_t a, uint8_t v) {
    if (a >= 0x2000 && a < 0x4000) { m->req[a - 0x2000] = v; return; }
    if (a == 0x10) m->req_len = (uint16_t)(((unsigned)m->req_len & 0xFF00u) | (unsigned)v);
    else if (a == 0x11) m->req_len = (uint16_t)(((unsigned)m->req_len & 0x00FFu) | ((unsigned)v << 8));
    else if (a == 0x0C) {
        if (v & 0x01u) doorbell(m);
        if (v & 0x02u) m->resp_ready = 0;
        if (v & 0x10u) m->overrun = 0;
    }
}

static void mt35_select(void *ctx, int asserted) {
    mock_t35 *m = (mock_t35 *)ctx;
    m->cs = asserted; m->nbytes = 0;
    m->now_us += 1;
    mt35_tick(m);
}

static int mt35_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    mock_t35 *m = (mock_t35 *)ctx;
    size_t i;
    if (!m->cs) return -1;
    for (i = 0; i < n; i++) {
        uint8_t t = tx ? tx[i] : 0u, r = 0xFFu;      /* absent FPGA: MISO pull-up */
        size_t k = m->nbytes++;
        m->now_us += 1;                               /* ~8 Mbit/s mock clock */
        mt35_tick(m);
        if (m->present) {
            r = 0x00u;
            if (k == 0) m->cmd = t;
            else if (k == 1) m->addr = (uint16_t)(t << 8);
            else if (k == 2) m->addr = (uint16_t)(m->addr | t);
            else if (m->cmd == 0x02u) { reg_write(m, m->addr, t); m->addr++; }
            else if (m->cmd == 0x0Bu && k >= 4) { r = reg_read(m, m->addr); m->addr++; }
        }
        if (rx) rx[i] = r;
    }
    return 0;
}

static uint64_t mt35_now(void *ctx) { mock_t35 *m = (mock_t35 *)ctx; m->now_us += 1; mt35_tick(m); return m->now_us; }

arc1_spi_hal mt35_hal(mock_t35 *m) {
    arc1_spi_hal h;
    h.ctx = m; h.select = mt35_select; h.transfer = mt35_transfer; h.now_us = mt35_now;
    return h;
}
