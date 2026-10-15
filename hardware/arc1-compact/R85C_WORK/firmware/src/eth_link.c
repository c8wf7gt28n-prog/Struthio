/* ARC-1 Compact R8.5-C -- RGMII job link, F133 side (see header). HOST_TESTED with tests/emac_mock.c only. */
#include "eth_link.h"
#include <string.h>

const uint8_t el_fpga_mac[6] = { 0x02, 0xA1, 0xC1, 0x00, 0x00, 0x01 };

void el_init(eth_link *l, const arc1_eth_hal *hal, const uint8_t host_mac[6], uint32_t timeout_us)
{
    memset(l, 0, sizeof *l);
    l->hal = *hal;
    memcpy(l->host_mac, host_mac, 6);
    l->timeout_us = timeout_us ? timeout_us : 20000u;
}

size_t el_build(uint8_t *out, size_t cap, const uint8_t dst[6], const uint8_t src[6], const uint8_t *payload, size_t n)
{
    size_t len = EL_HDR + n;
    if (n > EL_MAX_PAYLOAD || (!payload && n)) return 0;
    if (len < EL_MIN_FRAME) len = EL_MIN_FRAME;
    if (cap < len) return 0;
    memcpy(out, dst, 6);
    memcpy(out + 6, src, 6);
    out[12] = (uint8_t)(EL_ETHERTYPE >> 8); out[13] = (uint8_t)EL_ETHERTYPE;
    out[14] = (uint8_t)n; out[15] = (uint8_t)(n >> 8);
    if (n) memcpy(out + EL_HDR, payload, n);
    memset(out + EL_HDR + n, 0, len - EL_HDR - n);
    return len;
}

long el_parse(const uint8_t *frame, size_t len, const uint8_t dst[6], const uint8_t src[6], const uint8_t **payload)
{
    size_t n;
    if (len < EL_HDR || len > EL_MAX_FRAME) return -1;
    if (memcmp(frame, dst, 6) != 0 || memcmp(frame + 6, src, 6) != 0) return -1;
    if (frame[12] != (uint8_t)(EL_ETHERTYPE >> 8) || frame[13] != (uint8_t)EL_ETHERTYPE) return -1;
    n = (size_t)frame[14] | ((size_t)frame[15] << 8);
    if (n > EL_MAX_PAYLOAD || EL_HDR + n > len) return -1;
    *payload = frame + EL_HDR;
    return (long)n;
}

static int is_ajob(const uint8_t *req, size_t len) { return len >= 16 && memcmp(req, "AJOB", 4) == 0; }

int el_exchange(eth_link *l, const uint8_t *req, size_t req_len, uint8_t *resp, size_t cap, size_t *resp_len)
{
    size_t fl, rl = 0;
    uint64_t t0;
    int rc, match_seq = is_ajob(req, req_len);
#ifdef MUTANT_ETH_NO_SEQ_MATCH
    match_seq = 0;
#endif
    if (!req || !resp || !resp_len || req_len == 0 || req_len > EL_MAX_PAYLOAD) return EL_ARG;
    /* drain anything already queued (stale replies to an exchange that timed out) */
    while ((rc = l->hal.recv(l->hal.ctx, l->frame, sizeof l->frame, &rl)) == 0) l->stray++;
    if (rc < 0) return EL_IO;
    fl = el_build(l->frame, sizeof l->frame, el_fpga_mac, l->host_mac, req, req_len);
    if (!fl || l->hal.send(l->hal.ctx, l->frame, fl) != 0) return EL_IO;
    l->sent++;
    t0 = l->hal.now_us(l->hal.ctx);
    for (;;) {
        const uint8_t *p;
        long n;
        rc = l->hal.recv(l->hal.ctx, l->frame, sizeof l->frame, &rl);
        if (rc < 0) return EL_IO;
        if (rc == 0) {
            n = el_parse(l->frame, rl, l->host_mac, el_fpga_mac, &p);
            if (n < 0 || (match_seq && (n < 16 || memcmp(p, "ARES", 4) != 0 || memcmp(p + 8, req + 8, 4) != 0))) {
                l->stray++;                       /* other traffic or a stale response: discard, keep waiting */
                continue;
            }
            if ((size_t)n > cap) return EL_PROTOCOL;
            memcpy(resp, p, (size_t)n);
            *resp_len = (size_t)n;
            l->received++;
            return EL_OK;
        }
        if (l->hal.now_us(l->hal.ctx) - t0 > l->timeout_us) { l->timeouts++; return EL_TIMEOUT; }
    }
}

/* loopback probe: a legacy (non-AJOB) payload comes back unchanged from the engine */
static unsigned probe(eth_link *l, unsigned frames)
{
    uint8_t req[256], resp[256];
    unsigned f, bad = 0, i;
    size_t rl;
    for (f = 0; f < frames; f++) {
        for (i = 0; i < sizeof req; i++) req[i] = (uint8_t)(i * 37u + f * 101u + 0x5Au);   /* toggling data pattern */
        req[0] = 'L';                                                                    /* never "AJOB" */
        if (el_exchange(l, req, sizeof req, resp, sizeof resp, &rl) != EL_OK || rl != sizeof req ||
            memcmp(req, resp, sizeof req) != 0)
            bad++;
    }
    return bad;
}

static int centre(const unsigned char *ok, unsigned steps, unsigned *pick, unsigned *width)
{
    unsigned i, best = 0, best_at = 0, run = 0;
    for (i = 0; i <= steps; i++) {
        if (i < steps && ok[i]) { run++; continue; }
        if (run > best) { best = run; best_at = i - run; }
        run = 0;
    }
    if (!best) return -1;
    *pick = best_at + (best - 1u) / 2u;
    if (width) *width = best;
    return 0;
}

int el_calibrate(eth_link *l, unsigned steps_tx, unsigned steps_rx, unsigned frames, unsigned *tx_step, unsigned *rx_step,
                 unsigned *win_tx, unsigned *win_rx)
{
    unsigned char ok[64];
    unsigned s, t, rx = 0, tx = 0;
    uint32_t keep = l->timeout_us;
    if (!steps_tx || !steps_rx || steps_tx > sizeof ok || steps_rx > sizeof ok || !frames || !l->hal.set_delay) return -1;
    if (l->timeout_us > 2000u) l->timeout_us = 2000u;             /* a failing setting must not stall the sweep */
    /* rx sweep at the current tx; if nothing passes (tx itself outside its eye) try the other tx steps in turn */
    for (t = 0; t < steps_tx; t++) {
        tx = (*tx_step + t) % steps_tx;
        for (s = 0; s < steps_rx; s++) { l->hal.set_delay(l->hal.ctx, tx, s); ok[s] = probe(l, frames) == 0; }
        if (centre(ok, steps_rx, &rx, win_rx) == 0) break;
    }
    if (t == steps_tx) { l->timeout_us = keep; return -1; }
    for (s = 0; s < steps_tx; s++) { l->hal.set_delay(l->hal.ctx, s, rx); ok[s] = probe(l, frames) == 0; }
    if (centre(ok, steps_tx, &tx, win_tx)) { l->timeout_us = keep; return -1; }
    l->hal.set_delay(l->hal.ctx, tx, rx);
    l->timeout_us = keep;
    *tx_step = tx; *rx_step = rx;
    return 0;
}
