/* ARC-1 R10 -- host tests of the F133 <-> D213 graphics command link: F133 host code and D213 device code joined by
 * an in-memory USB bulk-pipe mock with fault injection. HOST_TESTED; no USB stack, no silicon. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gfx_link.h"

static int checks, fails;
#define CHECK(c) do { checks++; if (!(c)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

/* ---------------- USB bulk pipe mock ---------------- */
#define QN 8
typedef struct mock {
    gl_dev dev;
    uint8_t q[QN][GL_HDR + GL_RSP_LEN]; size_t qlen[QN]; unsigned qh, qt;
    uint64_t now;
    unsigned drop_out, drop_in, corrupt_out, corrupt_in, out_err, reset_at_out, lose_asm_at_out, dead, stale;
    unsigned outs, ins;
    uint32_t boot;
    /* execution record */
    unsigned exec_count[64]; uint32_t exec_crc[64]; size_t exec_len[64]; unsigned lost_calls;
} mock;
static mock M;
static uint8_t scratch[GL_MAX_PKT];

static void on_exec(void *ctx, uint32_t f, const uint8_t *c, size_t n)
{
    mock *m = ctx; f &= 63u;
    m->exec_count[f]++; m->exec_len[f] = n; m->exec_crc[f] = gl_crc32(0, c, n);
}
static void on_lost(void *ctx) { ((mock *)ctx)->lost_calls++; }
static void dev_boot(mock *m)
{
    gl_dev_init(&m->dev, ++m->boot * 0x1000193u, GL_CAP_2D | GL_CAP_3D);
    m->dev.execute = on_exec; m->dev.link_lost = on_lost; m->dev.ctx = m;
}
static void push(mock *m, const uint8_t *p, size_t n)
{
    if (m->qt - m->qh < QN) { memcpy(m->q[m->qt % QN], p, n); m->qlen[m->qt % QN] = n; m->qt++; }
}
static int m_out(void *ctx, const uint8_t *buf, size_t len, uint32_t to)
{
    mock *m = ctx; (void)to;
    m->outs++; m->now += 1 + len / 40;                       /* ~40 MB/s, a planning figure only */
    if (m->out_err) { m->out_err--; return -1; }
    if (m->dead || (m->drop_out && m->drop_out--)) return 0;
    if (m->reset_at_out && --m->reset_at_out == 0) dev_boot(m);
    if (m->lose_asm_at_out && --m->lose_asm_at_out == 0) m->dev.nchunks = 0;
    memcpy(scratch, buf, len);
    if (m->corrupt_out) { m->corrupt_out--; scratch[len - 1] ^= 0x10; }
    uint8_t rsp[GL_HDR + GL_RSP_LEN];
    if (m->stale && m->dev.have_last) { m->stale = 0; push(m, m->dev.last_rsp, m->dev.last_rsp_len); }
    size_t r = gl_dev_rx(&m->dev, scratch, len, rsp, sizeof rsp, m->now);
    if (!r) return 0;
    if (m->drop_in) { m->drop_in--; return 0; }
    if (m->corrupt_in) { m->corrupt_in--; rsp[20] ^= 0x01; }
    push(m, rsp, r);
    return 0;
}
static int m_in(void *ctx, uint8_t *buf, size_t cap, size_t *len, uint32_t to)
{
    mock *m = ctx;
    m->ins++;
    if (m->qh == m->qt) { m->now += to; return 1; }
    size_t n = m->qlen[m->qh % QN];
    if (n > cap) return -1;
    memcpy(buf, m->q[m->qh % QN], n); *len = n; m->qh++;
    return 0;
}

static gl_host H;
static void setup(void)
{
    memset(&M, 0, sizeof M);
    dev_boot(&M);
    gl_hal hal = { &M, m_out, m_in };
    gl_host_init(&H, &hal, 2000, 3, 4);
}
static uint8_t big[4 * GL_CHUNK];
static void fill(uint8_t *p, size_t n, uint32_t s) { for (size_t i = 0; i < n; i++) { s = s * 1103515245u + 12345u; p[i] = (uint8_t)(s >> 16); } }

int main(void)
{
    /* G01 framing */
    {
        uint8_t pkt[64], t, v; uint32_t s; const uint8_t *p;
        CHECK(gl_crc32(0, (const uint8_t *)"123456789", 9) == 0xCBF43926u);
        size_t n = gl_build(pkt, sizeof pkt, "GCMD", 2, 0x01020304u, (const uint8_t *)"abc", 3);
        CHECK(n == 19);
        CHECK(gl_parse(pkt, n, "GCMD", &t, &s, &v, &p) == 3 && t == 2 && s == 0x01020304u && v == 1 && memcmp(p, "abc", 3) == 0);
        CHECK(gl_parse(pkt, n, "GRSP", &t, &s, &v, &p) < 0);
        CHECK(gl_parse(pkt, n - 1, "GCMD", &t, &s, &v, &p) < 0);
        pkt[17] ^= 4; CHECK(gl_parse(pkt, n, "GCMD", &t, &s, &v, &p) < 0); pkt[17] ^= 4;
        pkt[9] ^= 1;  CHECK(gl_parse(pkt, n, "GCMD", &t, &s, &v, &p) < 0);   /* header covered by the CRC */
        CHECK(gl_build(pkt, 18, "GCMD", 2, 0, (const uint8_t *)"abc", 3) == 0);
    }
    /* G02 hello */
    setup();
    CHECK(gl_submit_frame(&H, 1, (const uint8_t *)"x", 1) == GL_FALLBACK);   /* not up before HELLO ... */
    CHECK(gl_hello(&H) == GL_OK && H.up && H.caps == (GL_CAP_2D | GL_CAP_3D) && H.boot_id == M.dev.boot_id);
    /* G03 small frame, G05 empty frame */
    CHECK(gl_submit_frame(&H, 3, (const uint8_t *)"draw", 4) == GL_OK);
    CHECK(M.exec_count[3] == 1 && M.exec_len[3] == 4 && M.exec_crc[3] == gl_crc32(0, (const uint8_t *)"draw", 4));
    CHECK(gl_submit_frame(&H, 5, NULL, 0) == GL_OK && M.exec_count[5] == 1 && M.exec_len[5] == 0);
    CHECK(H.dev_last_frame == 5);
    /* G04 multi-chunk frame (3.5 chunks) */
    fill(big, sizeof big, 7);
    size_t bl = 3 * GL_CHUNK + GL_CHUNK / 2;
    CHECK(gl_submit_frame(&H, 4, big, bl) == GL_OK && M.exec_count[4] == 1 && M.exec_len[4] == bl &&
          M.exec_crc[4] == gl_crc32(0, big, bl));
    printf("TEST gl_basic done fails=%d\n", fails);

    /* G06 lost response: retry same seq, device replays, executes once */
    setup(); gl_hello(&H);
    M.drop_in = 1;
    CHECK(gl_submit_frame(&H, 6, (const uint8_t *)"abc", 3) == GL_OK);
    CHECK(M.exec_count[6] == 1 && H.retries == 1 && M.dev.replays == 1);
    /* G07 corrupted request: BAD_CRC, resend, executes once */
    M.corrupt_out = 1;
    CHECK(gl_submit_frame(&H, 7, (const uint8_t *)"abcd", 4) == GL_OK && M.exec_count[7] == 1 && M.dev.bad == 1);
    CHECK(M.exec_crc[7] == gl_crc32(0, (const uint8_t *)"abcd", 4));
    /* G08 corrupted response: resend, replay, executes once */
    M.corrupt_in = 1;
    CHECK(gl_submit_frame(&H, 8, (const uint8_t *)"q", 1) == GL_OK && M.exec_count[8] == 1 && H.corrupt == 1);
    /* G09 stale response ahead of the real one is ignored */
    M.stale = 1;
    CHECK(gl_submit_frame(&H, 9, (const uint8_t *)"zz", 2) == GL_OK && H.stray >= 1 && M.exec_count[9] == 1);
    CHECK(H.dev_last_frame == 9);
    /* G16 bulk OUT error once */
    M.out_err = 1;
    CHECK(gl_submit_frame(&H, 16, (const uint8_t *)"e", 1) == GL_OK && M.exec_count[16] == 1);
    printf("TEST gl_faults done fails=%d\n", fails);

    /* G10 device restart between chunks: resync and complete the frame from chunk 0 */
    setup(); gl_hello(&H);
    uint32_t b0 = H.boot_id;
    M.reset_at_out = 2;                                        /* before the second chunk */
    fill(big, sizeof big, 10);
    CHECK(gl_submit_frame(&H, 10, big, 2 * GL_CHUNK) == GL_OK);
    CHECK(M.exec_count[10] == 1 && M.exec_len[10] == 2 * GL_CHUNK && M.exec_crc[10] == gl_crc32(0, big, 2 * GL_CHUNK));
    CHECK(H.boot_id != b0 && H.resyncs >= 1);
    /* G13 device lost its assembly state (no restart): ORDER, host restarts the frame */
    M.lose_asm_at_out = 2;
    CHECK(gl_submit_frame(&H, 13, big, 2 * GL_CHUNK) == GL_OK && M.exec_count[13] == 1 && M.exec_len[13] == 2 * GL_CHUNK);
    printf("TEST gl_resync done fails=%d\n", fails);

    /* G11 dead link -> fallback after max_fail frames; reprobe brings it back */
    setup(); gl_hello(&H);
    M.dead = 1;
    for (uint32_t f = 20; f < 23; f++) CHECK(gl_submit_frame(&H, f, (const uint8_t *)"d", 1) == GL_FALLBACK);
    CHECK(!H.up);
    unsigned outs = M.outs;
    CHECK(gl_submit_frame(&H, 23, (const uint8_t *)"d", 1) == GL_FALLBACK && M.outs == outs);  /* no transfer */
    M.dead = 0;
    int back = 0;
    for (uint32_t f = 24; f < 34 && !back; f++) back = gl_submit_frame(&H, f, (const uint8_t *)"r", 1) == GL_OK;
    CHECK(back && H.up && H.dropped_frames >= 4);
    printf("TEST gl_fallback done fails=%d\n", fails);

    /* G12 device watchdog: link_lost once, re-armed by the next frame */
    setup(); gl_hello(&H);
    gl_dev_tick(&M.dev, M.now + 1000000, 100000);
    CHECK(M.lost_calls == 0);                                  /* nothing executed yet: no alarm at boot */
    CHECK(gl_submit_frame(&H, 40, (const uint8_t *)"w", 1) == GL_OK);
    gl_dev_tick(&M.dev, M.now + 50000, 100000);  CHECK(M.lost_calls == 0);
    gl_dev_tick(&M.dev, M.now + 200000, 100000); CHECK(M.lost_calls == 1);
    gl_dev_tick(&M.dev, M.now + 300000, 100000); CHECK(M.lost_calls == 1);
    M.now += 300000;
    CHECK(gl_submit_frame(&H, 41, (const uint8_t *)"w", 1) == GL_OK);
    gl_dev_tick(&M.dev, M.now + 200000, 100000); CHECK(M.lost_calls == 2);
    /* G14 device rejects a wrong version and out-of-order chunks; G15 argument errors */
    {
        uint8_t pkt[64], rsp[64], t, v; uint32_t s; const uint8_t *p;
        uint8_t fp[GL_FRAME_HDR] = { 50, 0, 0, 0, 1, 0, 2, 0 };    /* frame 50, chunk 1 of 2, no chunk 0 */
        size_t n = gl_build(pkt, sizeof pkt, "GCMD", GL_T_FRAME, 900, fp, sizeof fp);
        size_t r = gl_dev_rx(&M.dev, pkt, n, rsp, sizeof rsp, 0);
        CHECK(gl_parse(rsp, r, "GRSP", &t, &s, &v, &p) == GL_RSP_LEN && s == 900 && p[0] == GL_S_ORDER);
        n = gl_build(pkt, sizeof pkt, "GCMD", GL_T_PING, 901, NULL, 0);
        pkt[4] = 2; { uint32_t c = gl_crc32(gl_crc32(0, pkt, 12), pkt + GL_HDR, 0);
                      pkt[12] = (uint8_t)c; pkt[13] = (uint8_t)(c >> 8); pkt[14] = (uint8_t)(c >> 16); pkt[15] = (uint8_t)(c >> 24); }
        r = gl_dev_rx(&M.dev, pkt, n, rsp, sizeof rsp, 0);
        CHECK(gl_parse(rsp, r, "GRSP", &t, &s, &v, &p) == GL_RSP_LEN && p[0] == GL_S_BAD_VERSION);
        CHECK(gl_dev_rx(&M.dev, (const uint8_t *)"HTTP/1.1 200 OK\r\n", 17, rsp, sizeof rsp, 0) == 0);
        CHECK(gl_submit_frame(&H, 1, NULL, 5) == GL_ARG);
        CHECK(gl_submit_frame(&H, 1, big, GL_MAX_FRAME + 1) == GL_ARG);
    }
    printf("TEST gl_device done fails=%d\n", fails);
    printf("%d checks, %d failed\n", checks, fails);
    if (fails) { printf("GFX_LINK_TEST_FAIL\n"); return 1; }
    printf("GFX_LINK_TEST_PASS\n");
    return 0;
}
