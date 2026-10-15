/* ARC-1 Compact R06 -- optional accelerator dispatch with CPU fallback. */
#include "accel_dispatch.h"

#include <string.h>

#include "arc1_protocol.h"

static void put16(uint8_t *p, uint16_t v) { p[0] = (uint8_t)(v & 0xFFu); p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)(v & 0xFFu); p[1] = (uint8_t)((v >> 8) & 0xFFu);
    p[2] = (uint8_t)((v >> 16) & 0xFFu); p[3] = (uint8_t)(v >> 24);
}
static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | (p[1] << 8)); }
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint32_t u(int32_t v) { return (uint32_t)v; }
static int32_t s(uint32_t v) { return (v & 0x80000000u) ? -(int32_t)(~v) - 1 : (int32_t)v; }

void accel_init(accel_ctx *a, t35_link *link, int enabled) {
    memset(a, 0, sizeof(*a));
    a->link = link;
    a->enabled = enabled;
}

size_t accel_pack_jobs(const arc1_transform_job *jobs, size_t n, uint8_t *out, size_t cap) {
    size_t i, need = 8u + 48u * n;
    if (n == 0u || n > ACCEL_MAX_BATCH || cap < need) return 0;
    put16(out, 1u); put16(out + 2, 1u); put16(out + 4, (uint16_t)n); put16(out + 6, 0u);
    for (i = 0; i < n; i++) {
        uint8_t *r = out + 8u + 48u * i;
        const arc1_transform_job *j = &jobs[i];
        put32(r + 0, u(j->xmin)); put32(r + 4, u(j->ymin)); put32(r + 8, u(j->xmax)); put32(r + 12, u(j->ymax));
        put32(r + 16, u(j->m00)); put32(r + 20, u(j->m01)); put32(r + 24, u(j->m02));
        put32(r + 28, u(j->m10)); put32(r + 32, u(j->m11)); put32(r + 36, u(j->m12));
        put16(r + 40, j->viewport_width); put16(r + 42, j->viewport_height); put32(r + 44, j->tag);
    }
    return need;
}

int accel_unpack_results(const uint8_t *p, size_t len, size_t expect, arc1_transform_result *out) {
    size_t i, count;
    if (len < 8u || get16(p) != 1u || get16(p + 2) != 1u) return -1;
    count = get16(p + 4);
    if (get16(p + 6) != 0u || count != expect || len != 8u + 24u * count) return -1;
    for (i = 0; i < count; i++) {
        const uint8_t *r = p + 8u + 24u * i;
        out[i].tag = get32(r);
        out[i].minx = s(get32(r + 4)); out[i].miny = s(get32(r + 8));
        out[i].maxx = s(get32(r + 12)); out[i].maxy = s(get32(r + 16));
        out[i].flags = get32(r + 20);
        if (out[i].flags & ~7u) return -1;
    }
    return 0;
}

/* collect up to 4 frames from one mailbox response */
typedef struct { size_t n; arc1_packet pk[4]; uint8_t store[4][ARC1_MAX_FRAME]; } frames_t;
static void on_frame(void *ctx, const arc1_packet *p) {
    frames_t *f = (frames_t *)ctx;
    if (f->n < 4u) {          /* the payload pointer is only valid in the callback: copy it */
        memcpy(f->store[f->n], p->payload, p->payload_length);
        f->pk[f->n] = *p;
        f->pk[f->n].payload = f->store[f->n];
    }
    f->n++;
}

static uint8_t g_req[ARC1_MAX_FRAME];
static uint8_t g_resp[T35_BUF_BYTES];
static uint8_t g_pay[ARC1_MAX_PAYLOAD];
static frames_t g_frames;
static arc1_parser g_parser;

static int map_link(int rc) {
    if (rc == T35_NOT_READY) return ACCEL_FB_NOT_READY;
    if (rc == T35_TIMEOUT) return ACCEL_FB_TIMEOUT;
    return ACCEL_FB_LINK;
}

static int exchange_frames(accel_ctx *a, uint8_t type, uint32_t seq, const uint8_t *pl, size_t pll) {
    size_t wlen = 0, rlen = 0;
    int rc;
    if (arc1_encode(type, a->epoch, seq, pl, pll, g_req, sizeof g_req, &wlen) != ARC1_OK) return ACCEL_FB_FRAME;
    rc = t35_exchange(a->link, g_req, wlen, g_resp, sizeof g_resp, &rlen);
    if (rc) return map_link(rc);
    memset(&g_frames, 0, sizeof g_frames);
    arc1_parser_init(&g_parser);
    (void)arc1_parser_feed(&g_parser, g_resp, rlen, on_frame, &g_frames);
    /* the mailbox response is a known transaction boundary */
    if (arc1_parser_finish(&g_parser) != 0u || g_parser.rejected != 0u || g_frames.n == 0u || g_frames.n > 4u)
        return ACCEL_FB_FRAME;
    return ACCEL_FB_NONE;
}

static int status_is(const arc1_packet *p, uint16_t want, uint32_t epoch, uint32_t seq) {
    arc1_reply r;
    if (p->type != ARC1_STATUS || arc1_read_status(p, &r) != ARC1_OK) return 0;
    return r.status == want && r.epoch == epoch && r.sequence == seq;
}

static int hello(accel_ctx *a) {
    int rc;
    a->epoch++;                                   /* every new session uses a larger epoch */
    rc = exchange_frames(a, ARC1_HELLO, 0u, NULL, 0u);
    if (rc) return rc;
    if (g_frames.n != 1u || !status_is(&g_frames.pk[0], ARC1_STATUS_OK, a->epoch, 0u)) return ACCEL_FB_SESSION;
    a->session_ok = 1;
    a->next_sequence = 1u;
    return ACCEL_FB_NONE;
}

static int try_fpga(accel_ctx *a, const arc1_transform_job *jobs, size_t n, arc1_transform_result *out) {
    size_t pll, i;
    uint32_t seq;
    int rc;
    if (!a->link) return ACCEL_FB_NOT_READY;
    if (!a->session_ok) {
        rc = t35_probe(a->link);
        if (rc) return map_link(rc);
        rc = hello(a);
        if (rc) return rc;
    }
    pll = accel_pack_jobs(jobs, n, g_pay, sizeof g_pay);
    if (pll == 0u) return ACCEL_FB_RESULT;
    seq = a->next_sequence++;
    rc = exchange_frames(a, ARC1_JOB, seq, g_pay, pll);
    if (rc) return rc;
    /* expected: STATUS ACCEPTED, RESULT, STATUS DONE (same order as the R05 pipeline) */
    if (g_frames.n != 3u || !status_is(&g_frames.pk[0], ARC1_STATUS_ACCEPTED, a->epoch, seq) ||
        !status_is(&g_frames.pk[2], ARC1_STATUS_DONE, a->epoch, seq))
        return ACCEL_FB_SESSION;
    if (g_frames.pk[1].type != ARC1_RESULT || g_frames.pk[1].epoch != a->epoch || g_frames.pk[1].sequence != seq)
        return ACCEL_FB_FRAME;
    if (accel_unpack_results(g_frames.pk[1].payload, g_frames.pk[1].payload_length, n, out)) return ACCEL_FB_RESULT;
    for (i = 0; i < n; i++)
        if (out[i].tag != jobs[i].tag) return ACCEL_FB_RESULT;
    return ACCEL_FB_NONE;
}

accel_fallback accel_transform_batch(accel_ctx *a, const arc1_transform_job *jobs, size_t n,
                                     arc1_transform_result *out) {
    accel_fallback why;
    if (!a || !jobs || !out || n == 0u || n > ACCEL_MAX_BATCH) {
        if (jobs && out && n) arc1_transform_batch(jobs, out, n);
        return ACCEL_FB_DISABLED;
    }
    why = a->enabled ? (accel_fallback)try_fpga(a, jobs, n, out) : ACCEL_FB_DISABLED;
    if (why == ACCEL_FB_NONE && a->verify) {
        static arc1_transform_result ref[ACCEL_MAX_BATCH];
        arc1_transform_batch(jobs, ref, n);
        if (memcmp(ref, out, n * sizeof *out) != 0) why = ACCEL_FB_VERIFY;
    }
    if (why != ACCEL_FB_NONE) {
        if (why != ACCEL_FB_DISABLED) a->session_ok = 0;   /* next try: new HELLO, larger epoch */
        arc1_transform_batch(jobs, out, n);
        a->cpu_batches++;
    } else {
        a->fpga_batches++;
    }
    a->reasons[why]++;
    return why;
}

const char *accel_fallback_string(accel_fallback f) {
    static const char *names[ACCEL_FB_COUNT] = {"fpga", "disabled", "not_ready", "timeout", "link",
                                                "frame", "session", "result", "verify"};
    return ((unsigned)f < ACCEL_FB_COUNT) ? names[f] : "unknown";
}
