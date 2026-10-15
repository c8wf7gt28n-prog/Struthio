/* ARC-1 Compact R8.5 -- behavioural board/ECP5 model (see header). */
#include "ecp5_mock.h"
#include "accel_job.h"
#include "crc32.h"
#include <string.h>

void mock_init(ecp5_mock *m, uint32_t good_crc)
{
    memset(m, 0, sizeof *m);
    m->good_crc = good_crc;
    m->idcode = ECP5_IDCODE_LFE5U_45;
    m->sck_hz = 25e6;
    m->cs_overhead_ns = 2000;
    m->bus_en_n = 1;
    m->ss = 0;
    m->ambx_version = 3;
}

static int powered(ecp5_mock *m) { return m->pwr_en && !m->no_vcc_pg && m->t_us >= m->t_pwr_on + 1000u; }
static int por_done(ecp5_mock *m) { return powered(m) && !m->no_initn && m->t_us >= m->t_pwr_on + 6000u; }

static void unconfigure(ecp5_mock *m)
{
    m->configured = 0; m->isc_enabled = 0; m->burst = 0; m->done = 0; m->cfg_fail = 0;
    m->resp_ready = 0; m->job_pending = 0; m->psram_ready = 0; m->bist_state = 0;
    ajob_fir_init(&m->fir);
}

void mock_f133_reset(ecp5_mock *m)
{
    m->pwr_en = 0;                     /* 100k pull-down on FPGA_PWR_EN: rails collapse */
    m->bus_en_n = 1; m->ss = 0; m->programn_drv_low = 0; m->psram_req = 0;
    unconfigure(m);
}

static void mset(void *ctx, ecp5_pin p, int v)
{
    ecp5_mock *m = ctx;
    switch (p) {
    case ECP5_PIN_PWR_EN:
        if (v && !m->pwr_en) m->t_pwr_on = m->t_us;
        if (!v) unconfigure(m);
        m->pwr_en = v;
        break;
    case ECP5_PIN_BUS_EN_N: m->bus_en_n = v; break;
    case ECP5_PIN_PROGRAMN:
        if (!v && powered(m)) unconfigure(m);           /* falling PROGRAMN: config memory cleared, INITN/DONE low */
        if (v && m->programn_drv_low) m->t_programn_release = m->t_us;
        m->programn_drv_low = !v;
        break;
    case ECP5_PIN_PSRAM_REQ: m->psram_req = v; break;
    default: break;
    }
}

static int mget(void *ctx, ecp5_pin p)
{
    ecp5_mock *m = ctx;
    switch (p) {
    case ECP5_PIN_VCC_PG: return powered(m);
    case ECP5_PIN_PROGRAMN: return powered(m) && !m->programn_drv_low && !m->programn_held;
    case ECP5_PIN_INITN:
        if (!powered(m)) return 0;                       /* 4.7k pull-up to an unpowered VCCIO8 */
        if (m->absent) return 1;                         /* pull-up only, no device */
        if (!por_done(m) || m->programn_drv_low || m->programn_held) return 0;
        if (m->t_us < m->t_programn_release + 50u) return 0;
        if (m->initn_fault) return 0;
        return 1;
    case ECP5_PIN_DONE:
        if (!powered(m)) return 0;
        if (m->absent) return 1;                         /* pull-up only: DONE alone must never be trusted */
        return m->done;
    default: return 0;
    }
}

static void mdelay(void *ctx, uint32_t us) { ((ecp5_mock *)ctx)->t_us += us; }

const ecp5_gpio_hal mock_gpio = { NULL, mset, mget, mdelay };

/* ---------------------------------------------------------------- SPI */
static uint64_t now(void *ctx) { return ((ecp5_mock *)ctx)->t_us; }

static void put_rx32(ecp5_mock *m, uint32_t v)
{
    m->rxq[0] = (uint8_t)(v >> 24); m->rxq[1] = (uint8_t)(v >> 16); m->rxq[2] = (uint8_t)(v >> 8); m->rxq[3] = (uint8_t)v;
    m->rxn = 4; m->rxi = 0;
}

static uint16_t mbx_status(ecp5_mock *m)
{
    uint16_t s = 0x0001u;
    if (m->psram_req && !m->psram_missing && !m->psram_ce_stuck) { s |= 0x0800u; m->psram_ready = 1; }
    if (m->psram_ready && m->psram_req) s |= 0x0002u;
    if (m->psram_ce_stuck && m->psram_req) s |= 0x0004u;
    if (m->job_pending) s |= 0x0008u;
    if (m->resp_ready && m->t_us >= m->engine_busy_until) s |= 0x0010u;
    if (m->resp_ready && m->t_us < m->engine_busy_until) s |= 0x0008u;
    if (m->bist_state == 1) s |= 0x0080u;
    if (m->bist_state == 2) s |= 0x0100u;
    return s;
}

static uint8_t mbx_rd(ecp5_mock *m, uint32_t a)
{
    static const uint8_t id[4] = { 'A', 'M', 'B', 'X' };
    uint16_t st;
    if (a < 4) return id[a];
    if (a == 4) return (uint8_t)m->ambx_version;
    if (a == 5) return 0;
    if (a == 6) return 0x0F;
    if (a == 7) return 0;
    if (a == 8 || a == 9) { st = mbx_status(m); return (uint8_t)(a == 8 ? st : st >> 8); }
    if (a == 0x14 || a == 0x15) return (uint8_t)(a == 0x14 ? m->resp_len : m->resp_len >> 8);
    if (a >= 0x24 && a < 0x28) return (uint8_t)(m->perf_cycles >> (8 * (a - 0x24)));
    if (a >= 0x28 && a < 0x2C) return (uint8_t)(m->perf_jobs >> (8 * (a - 0x28)));
    if (a >= 0x4000 && a < 0x6000) return m->resp[a - 0x4000];
    if (a >= 0x2000 && a < 0x4000) return m->req[a - 0x2000];
    return 0;
}

static void doorbell(ecp5_mock *m)
{
    size_t rl;
    if (m->req_len == 0 || m->job_pending || m->resp_ready) return;
    m->doorbells++;
    if (m->lose_fpga_after_jobs && m->jobs_done >= m->jobs_before_loss) { unconfigure(m); return; }
    if (m->mbx_stuck_busy) { m->job_pending = 1; return; }
    if (m->mbx_corrupt_req_once) { m->req[16] ^= 0x10; m->mbx_corrupt_req_once = 0; }
    rl = ajob_reference_response(m->resp, sizeof m->resp, m->req, m->req_len, &m->fir);
    if (m->mbx_wrong_result && rl >= 40) {         /* plausible, well-framed but numerically wrong engine output */
        uint32_t c;
        m->resp[20] ^= 0x01;
        c = arc1_crc32(0, m->resp + 16, rl - 16);
        m->resp[12] = (uint8_t)c; m->resp[13] = (uint8_t)(c >> 8); m->resp[14] = (uint8_t)(c >> 16); m->resp[15] = (uint8_t)(c >> 24);
    }
    if (m->mbx_corrupt_resp_once && rl > 20) { m->resp[20] ^= 0x01; m->mbx_corrupt_resp_once = 0; }
    m->resp_len = (uint16_t)rl;
    m->resp_ready = 1;
    m->perf_jobs++;
    m->jobs_done++;
    /* engine time: linear fit to tb_ecp5_top PERF_LAST_CYCLES (RTL_SIMULATED): n=1 135, n=8 771, n=16 1575, n=170 16359 */
    m->perf_cycles = 39u + 96u * ((uint32_t)m->req[6] | ((uint32_t)m->req[7] << 8));
    if (m->engine_hz) m->engine_busy_until = m->t_us + (uint64_t)m->perf_cycles * 1000000u / m->engine_hz;
}

static void mbx_wr(ecp5_mock *m, uint32_t a, uint8_t v)
{
    if (a >= 0x2000 && a < 0x4000) { m->req[a - 0x2000] = v; return; }
    if (a == 0x10) { m->req_len = (uint16_t)((m->req_len & 0xFF00u) | (unsigned)v); return; }
    if (a == 0x11) { m->req_len = (uint16_t)((m->req_len & 0x00FFu) | ((unsigned)v << 8)); return; }
    if (a == 0x0C) {
        if (v & 0x02) { m->resp_ready = 0; }
        if (v & 0x40 && m->job_pending) {              /* ABORT: post ARES status 5, count 0, seq echoed */
            memset(m->resp, 0, 16);
            memcpy(m->resp, "ARES", 4);
            m->resp[4] = 1; m->resp[5] = AJOB_ABORTED;
            memcpy(m->resp + 8, m->req + 8, 4);
            m->resp_len = 16; m->job_pending = 0; m->resp_ready = 1;
        }
        if (v & 0x08) m->bist_state = (m->bist_fail || m->psram_ce_stuck) ? 2 : 1;
        if (v & 0x01) doorbell(m);
    }
}

static void end_txn(ecp5_mock *m)
{
    if (m->burst) {
        /* end of LSC_BITSTREAM_BURST: check preamble, VERIFY_ID and the frame CRC (modelled as CRC32 of the stream) */
        uint32_t i;
        int pre = 0, idok = 0;
        for (i = 0; i + 8 < sizeof m->burst_head && i + 8 < m->burst_len; i++) {
            if (!pre && m->burst_head[i] == 0xFF && m->burst_head[i + 1] == 0xFF && m->burst_head[i + 2] == 0xBD && m->burst_head[i + 3] == 0xB3) pre = 1;
            if (pre && m->burst_head[i] == 0xE2 && !m->burst_head[i + 1] && !m->burst_head[i + 2] && !m->burst_head[i + 3]) {
                uint32_t id = ((uint32_t)m->burst_head[i + 4] << 24) | ((uint32_t)m->burst_head[i + 5] << 16) |
                              ((uint32_t)m->burst_head[i + 6] << 8) | m->burst_head[i + 7];
                idok = id == m->idcode;
                break;
            }
        }
        m->cfg_fail = !(pre && idok && m->burst_crc == m->good_crc);
        m->burst = 0;
    }
    m->hn = 0; m->op = -1; m->rxn = 0;
}

static void msel(void *ctx, int asserted)
{
    ecp5_mock *m = ctx;
    m->t_us += m->cs_overhead_ns / 1000u;
    if (!asserted && m->ss) end_txn(m);
    m->ss = asserted;
    if (asserted) { m->hn = 0; m->op = -1; m->rxn = 0; }
}

static uint8_t byte(ecp5_mock *m, uint8_t tx)
{
    int reach = !m->bus_en_n && powered(m) && !m->absent;
    uint8_t rx = 0;                                      /* MISO strap pull-down */
    if (!reach) return 0;
    if (m->done) {                                       /* user mode: AMBX mailbox (opcode 02 write, 0B read) */
        if (m->hn < 3) {
            m->hdr[m->hn++] = tx;
            if (m->hn == 3) { m->op = m->hdr[0]; m->addr = ((uint32_t)m->hdr[1] << 8) | m->hdr[2]; }
            return 0;
        }
        if (m->op == 0x02) { mbx_wr(m, m->addr++, tx); return 0; }
        if (m->op == 0x0B) { if (m->hn == 3) { m->hn = 4; return 0; } return mbx_rd(m, m->addr++); }
        return 0;
    }
    if (m->burst) {
        if (m->flip_burst_byte && m->burst_len == 4000u) { tx ^= 0x01; m->flip_burst_byte = 0; }
        if (m->burst_len < sizeof m->burst_head) m->burst_head[m->burst_len] = tx;
        m->burst_crc = arc1_crc32(m->burst_crc, &tx, 1);
        m->burst_len++;
        return 0;
    }
    if (m->hn < 4) {
        m->hdr[m->hn++] = tx;
        if (m->hn == 4) {
            m->op = m->hdr[0];
            if (!por_done(m) || m->programn_drv_low) { m->op = -1; return 0; }
            switch (m->op) {
            case ECP5_CMD_READ_ID: put_rx32(m, m->wrong_idcode ? 0x41113043u : m->idcode); break;   /* 85F id if wrong */
            case ECP5_CMD_LSC_READ_STATUS: {
                uint32_t st = 0;
                if (m->busy_stuck_cfg) st |= ECP5_ST_BUSY;
                if (m->cfg_fail) st |= ECP5_ST_FAIL | (1u << 23);
                if (m->isc_enabled) st |= 1u << 9;
                put_rx32(m, st);
                break; }
            case ECP5_CMD_ISC_ENABLE: m->isc_enabled = 1; break;
            case ECP5_CMD_ISC_ERASE: m->cfg_fail = 0; break;
            case ECP5_CMD_LSC_INIT_ADDRESS: break;
            case ECP5_CMD_LSC_BITSTREAM_BURST:
                if (m->isc_enabled) { m->burst = 1; m->burst_len = 0; m->burst_crc = 0; }
                break;
            case ECP5_CMD_ISC_DISABLE:
                m->isc_enabled = 0;
                if (!m->cfg_fail && m->burst_len && !m->done_stuck) {
                    m->configured = 1;
                    m->done = 1;
                    if (m->initn_low_after) { m->done = 0; m->initn_fault = 1; }
                }
                break;
            default: break;
            }
        }
        return 0;
    }
    if (m->rxi < m->rxn) rx = m->rxq[m->rxi++];
    return rx;
}

static int mxfer(void *ctx, const uint8_t *tx, uint8_t *rx, size_t n)
{
    ecp5_mock *m = ctx;
    size_t i;
    double ns = 0;
    for (i = 0; i < n; i++) {
        uint8_t r;
        if (m->spi_io_error_at_byte && m->spi_bytes + 1 == (uint64_t)m->spi_io_error_at_byte) return -1;
        r = byte(m, tx ? tx[i] : 0);
        if (rx) rx[i] = r;
        m->spi_bytes++;
    }
    ns = (double)n * 8.0 * 1e9 / m->sck_hz;
    m->t_us += (uint64_t)(ns / 1000.0);
    return 0;
}

const arc1_spi_hal mock_spi = { NULL, msel, mxfer, now };
