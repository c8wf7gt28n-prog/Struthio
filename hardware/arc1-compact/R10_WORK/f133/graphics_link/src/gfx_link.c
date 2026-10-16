/* ARC-1 R10 -- F133 host side of the graphics command link (see include/gfx_link.h). HOST_TESTED only. */
#include <string.h>
#include "gfx_link.h"

#define GL_ATTEMPTS   3u                            /* transfers per exchange (same seq) */
#define GL_MAX_STRAY  8u                            /* unmatched responses read per attempt before retrying */

uint32_t gl_crc32(uint32_t crc, const uint8_t *p, size_t n)
{
    crc = ~crc;
    while (n--) {
        crc ^= *p++;
        for (int k = 0; k < 8; k++) crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return ~crc;
}

static void wr16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void wr32(uint8_t *p, uint32_t v) { wr16(p, v); wr16(p + 2, v >> 16); }
static uint32_t rd16(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8; }
static uint32_t rd32(const uint8_t *p) { return rd16(p) | rd16(p + 2) << 16; }

size_t gl_build(uint8_t *out, size_t cap, const char magic[4], uint8_t type, uint32_t seq, const uint8_t *pl, size_t n)
{
    if (n > 0xFFFFu || GL_HDR + n > cap || (n && !pl)) return 0;
    memcpy(out, magic, 4);
    out[4] = GL_VERSION; out[5] = type; wr16(out + 6, (uint32_t)n); wr32(out + 8, seq);
    if (n) memmove(out + GL_HDR, pl, n);
    wr32(out + 12, gl_crc32(gl_crc32(0, out, 12), out + GL_HDR, n));
    return GL_HDR + n;
}

long gl_parse(const uint8_t *pkt, size_t len, const char magic[4], uint8_t *type, uint32_t *seq, uint8_t *version,
              const uint8_t **pl)
{
    if (len < GL_HDR || memcmp(pkt, magic, 4) != 0) return -1;
    size_t n = rd16(pkt + 6);
    if (GL_HDR + n != len) return -1;
#ifndef MUTANT_GL_NO_CRC
    if (gl_crc32(gl_crc32(0, pkt, 12), pkt + GL_HDR, n) != rd32(pkt + 12)) return -1;
#endif
    *type = pkt[5]; *seq = rd32(pkt + 8); *version = pkt[4]; *pl = pkt + GL_HDR;
    return (long)n;
}

void gl_host_init(gl_host *h, const gl_hal *hal, uint32_t timeout_us, unsigned max_fail, unsigned reprobe)
{
    memset(h, 0, sizeof *h);
    h->hal = *hal; h->timeout_us = timeout_us;
    h->max_fail = max_fail ? max_fail : 1; h->reprobe = reprobe ? reprobe : 1;
}

/* one request/response with retries of the same seq; rsp receives the 16-byte response payload */
static int exchange(gl_host *h, uint8_t type, const uint8_t *pl, size_t n, uint8_t rsp[GL_RSP_LEN])
{
    uint32_t seq = ++h->seq;
    size_t len = gl_build(h->tx, sizeof h->tx, "GCMD", type, seq, pl, n);
    if (!len) return GL_ARG;
    for (unsigned attempt = 0; attempt < GL_ATTEMPTS; attempt++) {
        if (attempt) h->retries++;
        h->exchanges++;
        if (h->hal.bulk_out(h->hal.ctx, h->tx, len, h->timeout_us) < 0) continue;
        for (unsigned k = 0; k < GL_MAX_STRAY; k++) {
            size_t got = 0;
            if (h->hal.bulk_in(h->hal.ctx, h->rx, sizeof h->rx, &got, h->timeout_us) != 0) break;
            uint8_t t, v; uint32_t s; const uint8_t *p;
            long m = gl_parse(h->rx, got, "GRSP", &t, &s, &v, &p);
            if (m < 0) { h->corrupt++; break; }     /* resend: the device replays its cached response */
#ifndef MUTANT_GL_NO_SEQ_MATCH
            if (s != seq || t != type || v != GL_VERSION || m != (long)GL_RSP_LEN) { h->stray++; continue; }
#else
            (void)s; (void)t; (void)v;
#endif
            if (p[0] == GL_S_BAD_CRC) break;        /* our request arrived damaged */
            memcpy(rsp, p, GL_RSP_LEN);
            return GL_OK;
        }
    }
    return GL_TIMEOUT;
}

static void failed(gl_host *h)
{
    if (++h->fails >= h->max_fail) h->up = 0;
}

int gl_hello(gl_host *h)
{
    uint8_t rsp[GL_RSP_LEN];
    int r = exchange(h, GL_T_HELLO, NULL, 0, rsp);
    if (r != GL_OK) { failed(h); return r; }
    if (rsp[0] != GL_S_OK) { h->up = 0; return GL_PROTOCOL; }
    h->boot_id = rd32(rsp + 8); h->caps = rd32(rsp + 12); h->dev_last_frame = rd32(rsp + 4);
    h->up = 1; h->fails = 0; h->since_probe = 0;
    return GL_OK;
}

int gl_submit_frame(gl_host *h, uint32_t frame_no, const uint8_t *cmds, size_t len)
{
    if ((len && !cmds) || len > GL_MAX_FRAME) return GL_ARG;
    if (!h->up) {
#ifndef MUTANT_GL_NO_REPROBE
        if (++h->since_probe >= h->reprobe) { h->since_probe = 0; (void)gl_hello(h); }
#endif
        if (!h->up) { h->dropped_frames++; return GL_FALLBACK; }
    }
    uint32_t nch = len ? (uint32_t)((len + GL_CHUNK - 1) / GL_CHUNK) : 1u;
    for (int pass = 0; pass < 2; pass++) {
        int restart = 0;
        uint8_t rsp[GL_RSP_LEN];
        for (uint32_t c = 0; c < nch && !restart; c++) {
            size_t off = (size_t)c * GL_CHUNK, n = len - off < GL_CHUNK ? len - off : GL_CHUNK;
            if (!len) n = 0;
            wr32(h->pl, frame_no); wr16(h->pl + 4, c); wr16(h->pl + 6, nch);
            if (n) memcpy(h->pl + GL_FRAME_HDR, cmds + off, n);
            int r = exchange(h, GL_T_FRAME, h->pl, GL_FRAME_HDR + n, rsp);
            if (r != GL_OK) { failed(h); h->dropped_frames++; return GL_FALLBACK; }
            h->fails = 0;
#ifndef MUTANT_GL_NO_BOOTID
            if (rd32(rsp + 8) != h->boot_id) {      /* device restarted: its assembly state is gone */
                h->resyncs++;
                if (gl_hello(h) != GL_OK) { h->dropped_frames++; return GL_FALLBACK; }
                restart = 1; break;
            }
#endif
            if (rsp[0] == GL_S_ORDER) { h->resyncs++; restart = 1; break; }
            if (rsp[0] != GL_S_OK) { h->dropped_frames++; return GL_FALLBACK; }
        }
        if (!restart) { h->dev_last_frame = rd32(rsp + 4); return GL_OK; }
    }
    h->dropped_frames++;
    return GL_FALLBACK;
}

int gl_send_fpga(gl_host *h, uint32_t total, gl_read_fn read, void *ctx, uint8_t *status, uint16_t *detail)
{
    uint8_t rsp[GL_RSP_LEN];
    if (!read || !status || !detail || total == 0) return GL_ARG;
    *status = 0xFF; *detail = 0;
    if (!h->up && gl_hello(h) != GL_OK) return GL_FALLBACK;
    for (int pass = 0; pass < 2; pass++) {
        int restart = 0;
        for (uint32_t off = 0; off < total && !restart; ) {
            uint32_t n = total - off < GL_CHUNK ? total - off : GL_CHUNK;
            wr32(h->pl, off); wr32(h->pl + 4, total);
            if (read(ctx, off, h->pl + 8, n) != 0) return GL_IO;
            if (exchange(h, GL_T_FPGA, h->pl, 8u + n, rsp) != GL_OK) { failed(h); return GL_FALLBACK; }
            h->fails = 0;
            if (rd32(rsp + 8) != h->boot_id || rsp[0] == GL_S_ORDER) {     /* device restarted / lost the stream */
                h->resyncs++;
                if (rd32(rsp + 8) != h->boot_id && gl_hello(h) != GL_OK) return GL_FALLBACK;
                restart = 1; break;
            }
            off += n;
            if (off < total && rsp[0] != GL_S_OK) { *status = rsp[0]; *detail = (uint16_t)rd16(rsp + 2); return GL_OK; }
            if (off == total) { *status = rsp[0]; *detail = (uint16_t)rd16(rsp + 2); return GL_OK; }
        }
        if (!restart) break;
    }
    return GL_FALLBACK;
}

/* ---------------- device side ---------------- */
void gl_dev_init(gl_dev *d, uint32_t boot_id, uint32_t caps)
{
    memset(d, 0, offsetof(gl_dev, asm_buf));
    d->boot_id = boot_id; d->caps = caps;
}

static size_t respond(gl_dev *d, uint8_t *rsp, size_t cap, uint8_t type, uint32_t seq, uint8_t status)
{
    uint8_t p[GL_RSP_LEN];
    memset(p, 0, sizeof p);
    p[0] = status; p[1] = type; p[2] = (uint8_t)d->detail; p[3] = (uint8_t)(d->detail >> 8); d->detail = 0;
    wr32(p + 4, d->last_frame); wr32(p + 8, d->boot_id); wr32(p + 12, type == GL_T_HELLO ? d->caps : 0u);
    return gl_build(rsp, cap, "GRSP", type, seq, p, sizeof p);
}

size_t gl_dev_rx(gl_dev *d, const uint8_t *pkt, size_t len, uint8_t *rsp, size_t cap, uint64_t now_us)
{
    uint8_t type, ver; uint32_t seq; const uint8_t *p;
    long n = gl_parse(pkt, len, "GCMD", &type, &seq, &ver, &p);
    if (n < 0) {
        if (len < GL_HDR || memcmp(pkt, "GCMD", 4) != 0) return 0;
        d->bad++;
        return respond(d, rsp, cap, pkt[5], rd32(pkt + 8), GL_S_BAD_CRC);  /* not cached */
    }
#ifndef MUTANT_GL_NO_DEDUP
    if (d->have_last && seq == d->last_seq && d->last_rsp_len <= cap) {
        d->replays++;
        memcpy(rsp, d->last_rsp, d->last_rsp_len);
        return d->last_rsp_len;
    }
#endif
    uint8_t st = GL_S_OK;
    if (ver != GL_VERSION) st = GL_S_BAD_VERSION;
    else if (type == GL_T_HELLO) { d->nchunks = 0; d->next_chunk = 0; d->asm_len = 0; }
    else if (type == GL_T_PING) { }
    else if (type == GL_T_FPGA) {
        uint32_t off = n >= 8 ? rd32(p) : 0xFFFFFFFFu, tot = n >= 8 ? rd32(p + 4) : 0;
        uint32_t m = n >= 8 ? (uint32_t)n - 8u : 0;
        if (n < 8) st = GL_S_BAD_TYPE;
        else if (!d->fpga_buf || !d->fpga_load || tot == 0 || tot > d->fpga_cap) st = GL_S_FPGA_NOBUF;
        else {
            if (off == 0) { d->fpga_rx = 0; d->fpga_total = tot; }
            if (off != d->fpga_rx || tot != d->fpga_total || off + m > tot) st = GL_S_ORDER;
            else {
                memcpy(d->fpga_buf + off, p + 8, m);
                d->fpga_rx += m;
                if (d->fpga_rx == tot) {
                    d->fpga_loads++;
                    st = d->fpga_load(d->ctx, d->fpga_buf, tot, &d->detail);
                    d->fpga_rx = 0; d->fpga_total = 0;
                }
            }
        }
    }
    else if (type != GL_T_FRAME || n < (long)GL_FRAME_HDR) st = GL_S_BAD_TYPE;
    else {
        uint32_t fno = rd32(p), c = rd16(p + 4), nch = rd16(p + 6);
        size_t m = (size_t)n - GL_FRAME_HDR;
        if (c == 0 && nch != 0) { d->cur_frame = fno; d->nchunks = nch; d->next_chunk = 0; d->asm_len = 0; }
#ifndef MUTANT_GL_NO_ORDER
        if (nch == 0 || d->nchunks == 0 || fno != d->cur_frame || c != d->next_chunk || nch != d->nchunks)
            st = GL_S_ORDER;
        else
#endif
        if (d->asm_len + m > GL_MAX_FRAME) { st = GL_S_TOO_BIG; d->nchunks = 0; }
        else {
            memcpy(d->asm_buf + d->asm_len, p + GL_FRAME_HDR, m);
            d->asm_len += m;
            if (++d->next_chunk == d->nchunks) {
                if (d->execute) d->execute(d->ctx, fno, d->asm_buf, d->asm_len);
                d->executed++; d->last_frame = fno; d->last_ok_us = now_us; d->lost_signalled = 0;
                d->nchunks = 0; d->next_chunk = 0; d->asm_len = 0;
            }
        }
    }
    size_t r = respond(d, rsp, cap, type, seq, st);
    if (r && r <= sizeof d->last_rsp) { memcpy(d->last_rsp, rsp, r); d->last_rsp_len = r; d->last_seq = seq; d->have_last = 1; }
    return r;
}

void gl_dev_tick(gl_dev *d, uint64_t now_us, uint64_t watchdog_us)
{
#ifndef MUTANT_GL_NO_WATCHDOG
    if (d->executed && !d->lost_signalled && now_us - d->last_ok_us > watchdog_us) {
        d->lost_signalled = 1;
        if (d->link_lost) d->link_lost(d->ctx);
    }
#else
    (void)d; (void)now_us; (void)watchdog_us;
#endif
}
