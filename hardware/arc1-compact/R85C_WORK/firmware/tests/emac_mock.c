/* ARC-1 Compact R8.5-C -- EMAC / RGMII / eth_link.sv behavioural model (see header). */
#include "emac_mock.h"
#include <string.h>

void emac_mock_init(emac_mock *e, ecp5_mock *m)
{
    memset(e, 0, sizeof *e);
    e->m = m;
    e->tx_lo = 2; e->tx_hi = 6;              /* planning eye: ETXDC 0..7 -> 2..6 pass; ERXDC 0..31 -> 10..20 pass */
    e->rx_lo = 10; e->rx_hi = 20;
    e->tx_step = 4; e->rx_step = 15;
}

static int fpga_up(const ecp5_mock *m) { return m->pwr_en && m->done; }

static void push(emac_mock *e, const uint8_t *f, size_t n)
{
    if (e->qn == EMOCK_Q) return;            /* EMAC RX ring full: frame lost */
    memcpy(e->q[e->qn], f, n);
    e->qlen[e->qn++] = n;
}

static void wire_time(emac_mock *e, size_t frame_len)
{
    /* preamble 8 + frame + FCS 4 + IFG 12 bytes at 125 MB/s, rounded up to whole microseconds */
    e->m->t_us += (frame_len + 24u + 124u) / 125u;
}

static int send(void *ctx, const uint8_t *frame, size_t len)
{
    emac_mock *e = ctx;
    ecp5_mock *m = e->m;
    uint8_t resp[EL_MAX_PAYLOAD], out[EL_MAX_FRAME];
    const uint8_t *p;
    size_t rl, ol;
    long n;
    uint16_t count;
    if (!e->mux) { e->mux_violations++; return 0; }       /* firmware sent with PG not in RGMII function */
    if (!fpga_up(m)) return 0;                              /* FPGA lost (power/configuration): frame lost */
    wire_time(e, len);
    if (e->link_down) { e->link_down--; return 0; }
    if (e->drop_req) { e->drop_req--; return 0; }
    if (e->tx_step < e->tx_lo || e->tx_step > e->tx_hi) { m->eth_cnt[1]++; return 0; }   /* FPGA sees a bad FCS */
    if (len < 14 || frame[12] != 0x88 || frame[13] != 0xB5) { m->eth_cnt[3]++; return 0; }
    if (len < EL_HDR) { m->eth_cnt[3]++; return 0; }
    n = (long)((size_t)frame[14] | ((size_t)frame[15] << 8));
    if (n > (long)EL_MAX_PAYLOAD || EL_HDR + (size_t)n > len) { m->eth_cnt[3]++; return 0; }
    p = frame + EL_HDR;
    m->eth_cnt[0]++;
    e->frames_to_fpga++;
    memcpy(e->last_host_mac, frame + 6, 6);
    if (e->engine_hang) return 0;
    if ((size_t)n >= 16 && memcmp(p, "AJOB", 4) == 0) {
        rl = ajob_reference_response(resp, sizeof resp, p, (size_t)n, &m->fir);
        count = (uint16_t)(p[6] | (p[7] << 8));
        /* engine time (RTL_SIMULATED, tb_ecp5_top): transform 39 + 96/job cycles; FIR block ~35.5 cycles/sample;
         * IR load ~1 cycle/byte; at 80 MHz */
        m->perf_cycles = p[5] == 1 ? 39u + 96u * count : p[5] == 3 ? 40u + (uint32_t)count * 355u / 10u : 40u + (uint32_t)n;
        m->t_us += m->perf_cycles / 80u;
    } else {
        memcpy(resp, p, (size_t)n);                  /* legacy transport loopback */
        rl = (size_t)n;
        m->t_us += 1;
    }
    m->perf_jobs++;
    ol = el_build(out, sizeof out, e->last_host_mac, el_fpga_mac, resp, rl);
    m->eth_cnt[4]++;
    wire_time(e, ol);
    if (e->rx_step < e->rx_lo || e->rx_step > e->rx_hi) { e->f133_rx_fcs_errors++; return 0; }
    if (e->drop_resp) { e->drop_resp--; return 0; }
    if (e->stray_before_resp) {
        uint8_t st[64], sf[EL_MAX_FRAME];
        size_t sl;
        e->stray_before_resp--;
        memset(st, 0, sizeof st);
        memcpy(st, "ARES", 4); st[4] = 1;
        st[8] = (uint8_t)(resp[8] ^ 0x5Au);           /* stale sequence number */
        sl = el_build(sf, sizeof sf, e->last_host_mac, el_fpga_mac, st, 16);
        push(e, sf, sl);
        sl = el_build(sf, sizeof sf, e->last_host_mac, el_fpga_mac, st, 16);
        sf[12] = 0x08; sf[13] = 0x00;                 /* an IPv4 frame on the wire */
        push(e, sf, sl);
    }
    push(e, out, ol);
    if (e->dup_resp) { e->dup_resp--; push(e, out, ol); }
    e->frames_from_fpga++;
    return 0;
}

static int recv(void *ctx, uint8_t *buf, size_t cap, size_t *len)
{
    emac_mock *e = ctx;
    unsigned i;
    if (!e->qn) { e->m->t_us += 1; return 1; }       /* polling advances virtual time */
    if (e->qlen[0] > cap) return -1;
    memcpy(buf, e->q[0], e->qlen[0]);
    *len = e->qlen[0];
    for (i = 1; i < e->qn; i++) { memcpy(e->q[i - 1], e->q[i], e->qlen[i]); e->qlen[i - 1] = e->qlen[i]; }
    e->qn--;
    return 0;
}

static void set_mux(void *ctx, int rgmii)
{
    emac_mock *e = ctx;
    if (rgmii && !fpga_up(e->m)) e->mux_violations++;
    e->mux = rgmii;
}

static void set_delay(void *ctx, unsigned tx, unsigned rx)
{
    emac_mock *e = ctx;
    e->tx_step = tx; e->rx_step = rx;
}

static uint64_t now(void *ctx) { return ((emac_mock *)ctx)->m->t_us; }

const arc1_eth_hal emac_mock_hal = { 0, send, recv, set_mux, set_delay, now };
