/* ARC-1 Compact R8.5 -- AJOB/ARES framing (HOST_TESTED). */
#include "accel_job.h"
#include "crc32.h"
#include <string.h>

static void p32(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24); }
static uint32_t g32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }

static void ser_job(uint8_t *p, const arc1_transform_job *j)
{
    int32_t f[10] = { j->xmin, j->ymin, j->xmax, j->ymax, j->m00, j->m01, j->m02, j->m10, j->m11, j->m12 };
    int i;
    for (i = 0; i < 10; i++) p32(p + 4 * i, (uint32_t)f[i]);
    p[40] = (uint8_t)j->viewport_width; p[41] = (uint8_t)(j->viewport_width >> 8);
    p[42] = (uint8_t)j->viewport_height; p[43] = (uint8_t)(j->viewport_height >> 8);
    p32(p + 44, j->tag);
}

static void de_job(const uint8_t *p, arc1_transform_job *j)
{
    j->xmin = (int32_t)g32(p); j->ymin = (int32_t)g32(p + 4); j->xmax = (int32_t)g32(p + 8); j->ymax = (int32_t)g32(p + 12);
    j->m00 = (int32_t)g32(p + 16); j->m01 = (int32_t)g32(p + 20); j->m02 = (int32_t)g32(p + 24);
    j->m10 = (int32_t)g32(p + 28); j->m11 = (int32_t)g32(p + 32); j->m12 = (int32_t)g32(p + 36);
    j->viewport_width = (uint16_t)(p[40] | (p[41] << 8)); j->viewport_height = (uint16_t)(p[42] | (p[43] << 8));
    j->tag = g32(p + 44);
}

static void ser_res(uint8_t *p, const arc1_transform_result *r)
{
    p32(p, r->tag); p32(p + 4, (uint32_t)r->minx); p32(p + 8, (uint32_t)r->miny);
    p32(p + 12, (uint32_t)r->maxx); p32(p + 16, (uint32_t)r->maxy); p32(p + 20, r->flags);
}

size_t ajob_build(uint8_t *out, size_t cap, uint32_t seq, const arc1_transform_job *jobs, uint16_t count)
{
    size_t n = AJOB_HDR + (size_t)count * AJOB_JOB, i;
    if (count == 0 || count > AJOB_MAXCOUNT || cap < n) return 0;
    memcpy(out, "AJOB", 4);
    out[4] = 1; out[5] = AJOB_OP_TRANSFORM; out[6] = (uint8_t)count; out[7] = (uint8_t)(count >> 8);
    p32(out + 8, seq);
    for (i = 0; i < count; i++) ser_job(out + AJOB_HDR + i * AJOB_JOB, &jobs[i]);
    p32(out + 12, arc1_crc32(0, out + AJOB_HDR, (size_t)count * AJOB_JOB));
    return n;
}

int ajob_parse(const uint8_t *r, size_t len, uint32_t seq, uint16_t count, arc1_transform_result *res)
{
    uint16_t n;
    size_t i;
    if (!r || len < AJOB_HDR) return AJOB_HOST_TRUNCATED;
    if (memcmp(r, "ARES", 4) != 0 || r[4] != 1) return AJOB_HOST_BAD_MAGIC;
    if (g32(r + 8) != seq) return AJOB_HOST_SEQ;               /* stale or foreign response */
    if (r[5] != AJOB_OK) return r[5];
    n = (uint16_t)(r[6] | (r[7] << 8));
    if (n != count) return AJOB_HOST_COUNT;
    if (len != AJOB_HDR + (size_t)n * AJOB_RES) return AJOB_HOST_TRUNCATED;
    if (arc1_crc32(0, r + AJOB_HDR, (size_t)n * AJOB_RES) != g32(r + 12)) return AJOB_HOST_RESULT_CRC;
    for (i = 0; i < n; i++) {
        const uint8_t *p = r + AJOB_HDR + i * AJOB_RES;
        res[i].tag = g32(p); res[i].minx = (int32_t)g32(p + 4); res[i].miny = (int32_t)g32(p + 8);
        res[i].maxx = (int32_t)g32(p + 12); res[i].maxy = (int32_t)g32(p + 16); res[i].flags = g32(p + 20);
    }
    return AJOB_OK;
}

/* Mirrors accel_engine.sv exactly: used to produce the expected RESP bytes. */
size_t ajob_reference_response(uint8_t *o, size_t cap, const uint8_t *q, size_t qlen)
{
    uint8_t st = AJOB_OK;
    uint16_t count = 0, i;
    uint32_t seq = 0, crc = 0;
    if (cap < AJOB_HDR) return 0;
    if (qlen < AJOB_HDR || memcmp(q, "AJOB", 4) != 0) {      /* legacy loopback */
        if (cap < qlen) return 0;
        memcpy(o, q, qlen);
        return qlen;
    }
    count = (uint16_t)(q[6] | (q[7] << 8));
    seq = g32(q + 8);
    if (q[4] != 1) st = AJOB_BAD_VERSION;
    else if (q[5] != AJOB_OP_TRANSFORM) st = AJOB_BAD_OPCODE;
    else if (count == 0 || count > AJOB_MAXCOUNT || qlen != AJOB_HDR + (size_t)count * AJOB_JOB) st = AJOB_BAD_LENGTH;
    else if (arc1_crc32(0, q + AJOB_HDR, (size_t)count * AJOB_JOB) != g32(q + 12)) st = AJOB_PAYLOAD_CRC;
    if (st != AJOB_OK) count = 0;
    if (cap < AJOB_HDR + (size_t)count * AJOB_RES) return 0;
    for (i = 0; i < count; i++) {
        arc1_transform_job j;
        arc1_transform_result r;
        de_job(q + AJOB_HDR + (size_t)i * AJOB_JOB, &j);
        arc1_transform_rectangle(&j, &r);
        ser_res(o + AJOB_HDR + (size_t)i * AJOB_RES, &r);
    }
    if (count) crc = arc1_crc32(0, o + AJOB_HDR, (size_t)count * AJOB_RES);
    memcpy(o, "ARES", 4);
    o[4] = 1; o[5] = st; o[6] = (uint8_t)count; o[7] = (uint8_t)(count >> 8);
    p32(o + 8, seq); p32(o + 12, crc);
    return AJOB_HDR + (size_t)count * AJOB_RES;
}
