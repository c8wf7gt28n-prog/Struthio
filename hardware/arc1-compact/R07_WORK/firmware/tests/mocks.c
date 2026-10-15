#include "mocks.h"

#include <string.h>

#include "arc1_transform.h"

/* ============================ BT820 ============================ */
static void fnv(uint32_t *h, uint8_t b) { *h = (*h ^ b) * 16777619u; }

static void mbt_violation(mock_bt820 *m, const char *what) {
    m->n_violations++;
    strncpy(m->last_violation, what, sizeof m->last_violation - 1u);
}

void mbt_init(mock_bt820 *m) {
    memset(m, 0, sizeof(*m));
    m->trace_hash = 2166136261u;
    m->boot_polls_needed = 3;
    m->regs_r1[0] = 0x7Cu;                          /* REG_ID */
}

/* register file lookup for a word-aligned address; NULL = not modelled */
static uint32_t *mbt_reg(mock_bt820 *m, uint32_t a) {
    if (a >= 0x7F006000u && a < 0x7F007000u) return &m->regs_r1[(a - 0x7F006000u) / 4u];
    if (a >= 0x7F800400u && a < 0x7F800500u) return &m->regs_sys[(a - 0x7F800400u) / 4u];
    if (a >= 0x7F800300u && a < 0x7F800400u) return &m->regs_lvdstx[(a - 0x7F800300u) / 4u];
    return NULL;
}
static int mbt_mapped(uint32_t a) {           /* AN086 Table 2 (+ REG_CMDB_WRITE) */
    return a < MBT_RAM_BYTES || (a >= 0x7F000000u && a < 0x7F004880u) || (a >= 0x7F006000u && a < 0x7F00C000u) ||
           (a >= 0x7F010000u && a < 0x7F010004u) || (a >= 0x7F800300u && a < 0x7F800600u) ||
           (a >= 0x7F800800u && a < 0x7F800900u);
}

static uint32_t mbt_read_word(mock_bt820 *m, uint32_t a) {
    uint32_t *r;
    if (!mbt_mapped(a)) return 0xDEADABBAu;
    if (a < MBT_RAM_BYTES) return (uint32_t)m->ram[a] | ((uint32_t)m->ram[a + 1] << 8) | ((uint32_t)m->ram[a + 2] << 16) | ((uint32_t)m->ram[a + 3] << 24);
    if (a >= 0x7F000000u && a < 0x7F004000u) { uint32_t o = a - 0x7F000000u;
        return (uint32_t)m->ram_cmd[o] | ((uint32_t)m->ram_cmd[o + 1] << 8) | ((uint32_t)m->ram_cmd[o + 2] << 16) | ((uint32_t)m->ram_cmd[o + 3] << 24); }
    if (a == 0x7F80044Cu) {                        /* REG_BOOT_STATUS */
        if (!m->power_active || m->never_boots) return 0u;
        if (++m->boot_reads < m->boot_polls_needed) return 0u;
        return 0x522E2E2Eu;
    }
    if (a == 0x7F800448u) return m->wrong_chip_id ? 0x08150100u : 0x08200100u;
    r = mbt_reg(m, a);
    return r ? *r : 0u;
}

/* coprocessor: execute RAM_CMD from REG_CMD_READ up to the new REG_CMD_WRITE */
static void mbt_copro(mock_bt820 *m) {
    uint32_t *rp = &m->regs_r1[0x14C / 4], wp = m->regs_r1[0x150 / 4] & 0x3FFFu;
    if (m->copro_stall || *rp == 0x3FFFu) return;
    while (*rp != wp) {
        uint32_t o = *rp, w = (uint32_t)m->ram_cmd[o] | ((uint32_t)m->ram_cmd[o + 1] << 8) |
                             ((uint32_t)m->ram_cmd[o + 2] << 16) | ((uint32_t)m->ram_cmd[o + 3] << 24);
        uint32_t adv = 4u;
        if (w == 0xFFFFFF00u) m->dl_len = 0;                     /* CMD_DLSTART */
        else if (w == 0xFFFFFF01u) {                             /* CMD_SWAP */
            if (m->copro_fault_on_swap) { *rp = 0x3FFFu; return; }
            m->swaps++;
            m->last_dl_len = m->dl_len < 16u ? m->dl_len : 16u;
            memcpy(m->last_dl, m->dl, m->last_dl_len * 4u);
        } else if (w == 0xFFFFFF6Bu) m->finishes++;              /* CMD_GRAPHICSFINISH */
        else if (w == 0xFFFFFF8Du) {                              /* CMD_RENDERTARGET + 3 words */
            if (((wp - o) & 0x3FFFu) < 16u) return;               /* wait for the whole command */
            m->rendertargets++; adv = 16u;
        }
        else if ((w & 0xFFFFFF00u) == 0xFFFFFF00u) { *rp = 0x3FFFu; return; }   /* unknown command: fault */
        else if (m->dl_len < 4096u) m->dl[m->dl_len++] = w;      /* display-list word */
        *rp = (o + adv) & 0x3FFFu;
    }
}

static void mbt_write_word(mock_bt820 *m, uint32_t a, const uint8_t *b) {
    uint32_t v = (uint32_t)b[0] | ((uint32_t)b[1] << 8) | ((uint32_t)b[2] << 16) | ((uint32_t)b[3] << 24);
    uint32_t *r;
    size_t j;
    if (!mbt_mapped(a)) { mbt_violation(m, "write to unmapped/reserved address"); return; }
    fnv(&m->trace_hash, 0x57);
    for (j = 0; j < 4; j++) { fnv(&m->trace_hash, (uint8_t)(a >> (8 * j))); fnv(&m->trace_hash, b[j]); }
    if (a < MBT_RAM_BYTES) { memcpy(&m->ram[a], b, 4); return; }
    if (a >= 0x7F000000u && a < 0x7F004000u) { memcpy(&m->ram_cmd[a - 0x7F000000u], b, 4); return; }
    if (a == 0x7F00614Cu) { mbt_violation(m, "host wrote REG_CMD_READ"); return; }
    if (a == 0x7F80044Cu) { mbt_violation(m, "host wrote REG_BOOT_STATUS"); return; }
    r = mbt_reg(m, a);
    if (r) *r = v;
    if (a == 0x7F006150u) mbt_copro(m);                    /* REG_CMD_WRITE kicks the coprocessor */
}

static void mbt_select(void *ctx, int asserted) {
    mock_bt820 *m = (mock_bt820 *)ctx;
    if (asserted && !m->cs) {
        m->cs = 1; m->nbytes = 0; m->is_read = 0; m->sent_valid = 0; m->rd_pos = 0;
        return;
    }
    if (asserted || !m->cs) return;
    m->cs = 0;
    m->now_us += 1;
    /* classify the finished transaction from its full byte content */
    if (m->nbytes == 5 && !m->tx[0] && !m->tx[1] && !m->tx[2] && !m->tx[3] && !m->tx[4]) {
        m->n_active++; m->power_active = 1; m->boot_reads = 0;
        fnv(&m->trace_hash, 0xAC);
        if (m->n_cmd_log < MBT_LOG_MAX) memcpy(m->cmd_log[m->n_cmd_log++], m->tx, 5);
        return;
    }
    if (m->nbytes == 5 && m->tx[0] == 0xFFu && m->tx[1] >= 0xE0u && m->tx[1] <= 0xEBu && !m->tx[3] && !m->tx[4]) {
        uint8_t c = m->tx[1];
        int cfg = (c == 0xE4u || c == 0xE6u || c == 0xE8u || c == 0xE9u || c == 0xEBu);
        m->n_cmds++;
        if (m->n_cmd_log < MBT_LOG_MAX) memcpy(m->cmd_log[m->n_cmd_log++], m->tx, 5);
        if (cfg && m->power_active) mbt_violation(m, "config host command while ACTIVE (ignored by chip)");
        if (c == 0xE0u || c == 0xE1u || c == 0xE2u) m->power_active = 0;
        fnv(&m->trace_hash, 0xFF); fnv(&m->trace_hash, m->tx[1]); fnv(&m->trace_hash, m->tx[2]);
        return;
    }
    if (m->is_read) {          /* a read of address 0 and ACTIVE differ only in length */
        m->n_reads++;
        if (!m->power_active) mbt_violation(m, "read before ACTIVE");
        return;
    }
    if (m->nbytes >= 4 && (m->tx[0] & 0x80u)) {
        size_t k, ndata = m->nbytes - 4;
        uint32_t a = ((uint32_t)(m->tx[0] & 0x7Fu) << 24) | ((uint32_t)m->tx[1] << 16) | ((uint32_t)m->tx[2] << 8) | m->tx[3];
        m->n_writes++;
        m->last_write.len = m->nbytes < 16 ? m->nbytes : 16;
        memcpy(m->last_write.bytes, m->tx, m->last_write.len);
        if (!m->power_active) mbt_violation(m, "memory write before ACTIVE");
        if (ndata == 0) mbt_violation(m, "write without data");
        if (ndata & 3u) m->n_partial_words++;                     /* incomplete word discarded */
        for (k = 0; k + 4 <= ndata; k += 4) mbt_write_word(m, a + (uint32_t)k, &m->tx[4 + k]);
        return;
    }
    if (m->nbytes) mbt_violation(m, "unrecognised transaction");
}

static int mbt_transfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n) {
    mock_bt820 *m = (mock_bt820 *)ctx;
    size_t i;
    if (!m->cs) return -1;
    for (i = 0; i < n; i++) {
        uint8_t t = tx ? tx[i] : 0u, r = 0u;
        size_t k = m->nbytes++;
        m->now_us += 1;
        if (k < MBT_TX_MAX) m->tx[k] = t;
        if (k == 3 && !(m->tx[0] & 0x80u)) {                 /* MSB 0: read (ACTIVE decided at CS# high) */
            m->is_read = 1;
            m->addr = ((uint32_t)m->tx[0] << 24) | ((uint32_t)m->tx[1] << 16) | ((uint32_t)m->tx[2] << 8) | m->tx[3];
            m->rd_poll_left = m->poll_latency;
        } else if (k >= 4 && m->is_read) {
            if (!m->sent_valid) {
                if (m->never_valid || m->rd_poll_left) { r = 0x00u; if (m->rd_poll_left) m->rd_poll_left--; }
                else { r = 0x01u; m->sent_valid = 1; }
            } else {
                if ((m->rd_pos & 3u) == 0u)            /* one register access per word */
                    m->rd_word = mbt_read_word(m, m->addr + (uint32_t)m->rd_pos);
                r = (uint8_t)(m->rd_word >> (8u * (m->rd_pos & 3u)));
                m->rd_pos++;
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
