/* ARC-1 Compact R8.5 -- AJOB cross-simulation vector generator (host C).
 * Builds request frames with the F133 driver code (src/accel_job.c) and the expected FPGA
 * responses with the R05 C reference (R05_BASELINE/compute/arc1_transform.c), and writes
 * them as $readmemh files + an SV include for fpga_ecp5/tb/tb_ecp5_top.sv.
 * The testbench compares the RTL response byte for byte and dumps what the RTL produced
 * (ajob_K_rtl.memh); "check" mode then feeds those RTL bytes to the F133 parser.
 * Usage: ajob_vectors OUTDIR | ajob_vectors check OUTDIR */
#include "accel_job.h"
#include "crc32.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint32_t rs = 0x2545F491u;
static uint32_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5; return rs; }
static int32_t rr(int32_t lo, int32_t hi) { return lo + (int32_t)(rnd() % (uint32_t)(hi - lo + 1)); }

static void job(arc1_transform_job *j, uint32_t tag, int kind)
{
    int32_t a, b;
    memset(j, 0, sizeof *j);
    a = rr(-200, 600) * 65536; b = rr(-200, 600) * 65536;
    j->xmin = a; j->xmax = a + rr(0, 200) * 65536 + rr(0, 65535);
    j->ymin = b; j->ymax = b + rr(0, 200) * 65536 + rr(0, 65535);
    j->m00 = rr(-131072, 131072); j->m01 = rr(-131072, 131072); j->m02 = rr(-300, 300) * 65536;
    j->m10 = rr(-131072, 131072); j->m11 = rr(-131072, 131072); j->m12 = rr(-300, 300) * 65536;
    j->viewport_width = 320; j->viewport_height = 240; j->tag = tag;
    if (kind == 1) { j->m00 = 0x7FFFFFFF; j->m01 = 0x7FFFFFFF; j->xmax = 0x7FFFFFFF; j->ymax = 0x7FFFFFFF; } /* saturation */
    if (kind == 2) { j->xmin = j->xmax + 1; }                                                                /* invalid */
    if (kind == 3) { j->viewport_width = 0; }                                                                /* invalid */
    if (kind == 4) { j->m00 = (int32_t)0x80000000; j->m11 = (int32_t)0x80000000; j->xmin = (int32_t)0x80000000; j->ymin = (int32_t)0x80000000; }
    if (kind == 5) { j->m00 = 65536; j->m01 = 0; j->m02 = 0; j->m10 = 0; j->m11 = 65536; j->m12 = 0; }      /* identity */
}

#define MAXF 8192
static uint8_t req[MAXF + 64], resp[MAXF + 64];
static arc1_transform_job jobs[AJOB_MAXCOUNT + 1];
static arc1_transform_result res[AJOB_MAXCOUNT + 1];

static void dump(const char *dir, const char *name, int k, const uint8_t *b, size_t n)
{
    char p[512];
    size_t i;
    FILE *f;
    snprintf(p, sizeof p, "%s/ajob_%d_%s.memh", dir, k, name);
    f = fopen(p, "w");
    if (!f) { perror(p); exit(2); }
    for (i = 0; i < n; i++) fprintf(f, "%02x\n", b[i]);
    if (n == 0) fprintf(f, "00\n");
    fclose(f);
}

static size_t load(const char *dir, const char *name, int k, uint8_t *b, size_t cap)
{
    char p[512];
    unsigned v;
    size_t n = 0;
    FILE *f;
    snprintf(p, sizeof p, "%s/ajob_%d_%s.memh", dir, k, name);
    f = fopen(p, "r");
    if (!f) return 0;
    while (n < cap && fscanf(f, "%x", &v) == 1) b[n++] = (uint8_t)v;
    fclose(f);
    return n;
}

static uint8_t rtl[MAXF + 64];
static ajob_fir_state fir_gen, fir_shadow;
static int16_t fin[AJOB_FIR_MAXBLK + 2], fout[AJOB_FIR_MAXBLK + 2], fexp[AJOB_FIR_MAXBLK + 2], taps[AJOB_FIR_TAPS];
#define NCASES 20

/* Second pass: the bytes the RTL actually produced go through the F133 driver parser. */
static int check_rtl(const char *dir)
{
    int k, fails = 0;
    for (k = 0; k < NCASES; k++) {
        size_t ql = load(dir, "req", k, req, sizeof req), el = load(dir, "resp", k, resp, sizeof resp);
        size_t rl = load(dir, "rtl", k, rtl, sizeof rtl);
        uint16_t n, i;
        uint32_t seq;
        int pr;
        if (!ql || !el || rl < el) { printf("FAIL case %d: missing RTL dump\n", k); fails++; continue; }
        rl = el;                                    /* the dump is padded to the expected length */
        if (memcmp(rtl, resp, el) != 0) { printf("FAIL case %d: RTL bytes differ from reference\n", k); fails++; continue; }
        if (k == 9) { printf("CHECK %d legacy loopback identical\n", k); continue; }
        n = (uint16_t)(req[6] | (req[7] << 8));
        seq = (uint32_t)req[8] | ((uint32_t)req[9] << 8) | ((uint32_t)req[10] << 16) | ((uint32_t)req[11] << 24);
        if (req[5] != AJOB_OP_TRANSFORM) {                       /* FIR cases: host FIR parser on the RTL bytes */
            pr = ajob_parse_fir(rtl, rl, seq, req[5], n, fout);
            printf("CHECK %d fir op %u parser=%d (RTL status byte %u)\n", k, req[5], pr, rtl[5]);
            if ((rtl[5] == 0) != (pr == AJOB_OK)) { printf("FAIL case %d: parser disagrees with status\n", k); fails++; }
            continue;
        }
        pr = ajob_parse(rtl, rl, seq, n, res);
        /* results equal the reference bytes, which gen mode verified against arc1_transform_rectangle */
        for (i = 0; pr == AJOB_OK && i < n; i++)
            if (res[i].tag != ((uint32_t)req[AJOB_HDR + i * AJOB_JOB + 44] | ((uint32_t)req[AJOB_HDR + i * AJOB_JOB + 45] << 8) |
                               ((uint32_t)req[AJOB_HDR + i * AJOB_JOB + 46] << 16) | ((uint32_t)req[AJOB_HDR + i * AJOB_JOB + 47] << 24))) {
                printf("FAIL case %d job %u tag order\n", k, i); fails++;
            }
        printf("CHECK %d parser=%d (RTL status byte %u)\n", k, pr, rtl[5]);
        if ((rtl[5] == 0) != (pr == AJOB_OK)) { printf("FAIL case %d: parser disagrees with status\n", k); fails++; }
    }
    printf("%s\n", fails ? "AJOB_RTL_CHECK_FAIL" : "AJOB_RTL_CHECK_PASS");
    return fails ? 1 : 0;
}

int main(int argc, char **argv)
{
    static const char *names[] = { "one_job", "eight_mixed", "max_170", "bad_crc", "bad_version", "bad_opcode",
                                   "bad_length", "count_zero", "count_171", "legacy_frame", "identity_16",
                                   "fir_before_ir", "fir_set_ir", "fir_735_a", "fir_735_b", "fir_bad_crc", "fir_33",
                                   "fir_ir_1023", "fir_1025", "fir_1024" };
    enum { NC = NCASES };
    size_t qlen[NC], rlen[NC];
    int st[NC], k, fails = 0;
    FILE *sv;
    char p[512];
    if (argc == 3 && strcmp(argv[1], "check") == 0) return check_rtl(argv[2]);
    if (argc != 2) { fprintf(stderr, "usage: %s OUTDIR\n", argv[0]); return 2; }
    if (arc1_crc32(0, "123456789", 9) != 0xCBF43926u) { puts("FAIL crc32 check value"); return 1; }
    ajob_fir_init(&fir_gen);
    ajob_fir_init(&fir_shadow);
    for (k = 0; k < NC; k++) {
        uint16_t n = 1, i;
        if (k >= 11) {                                     /* ---- resident FIR cases, state carried in order ---- */
            uint32_t sq = 0x2000u + (uint32_t)k;
            uint16_t nb = (k == 13 || k == 14 || k == 15) ? 735 : (k == 16 ? 33 : (k == 18 ? 1025 : (k == 19 ? 1024 : 64)));
            int want, pr;
            uint8_t op = (k == 12 || k == 17) ? AJOB_OP_FIR_SET_IR : AJOB_OP_FIR_BLOCK;
            for (i = 0; i < AJOB_FIR_MAXBLK + 1; i++) fin[i] = (int16_t)(uint16_t)rnd();
            for (i = 0; i < AJOB_FIR_TAPS; i++) taps[i] = (int16_t)((int32_t)(rnd() % 65536u) - 32768) / (int16_t)(1 + (i >> 7));
            if (op == AJOB_OP_FIR_SET_IR) {
                qlen[k] = ajob_build_fir_ir(req, sizeof req, sq, taps);
                if (k == 17) { qlen[k] -= 2; req[6] = 0xFF; req[7] = 0x03;          /* 1023 taps: bad length */
                               { uint32_t c = arc1_crc32(0, req + AJOB_HDR, 2046); req[12] = (uint8_t)c; req[13] = (uint8_t)(c >> 8); req[14] = (uint8_t)(c >> 16); req[15] = (uint8_t)(c >> 24); } }
            } else if (k == 18) {                          /* 1025 samples: hand-built, the builder refuses it */
                size_t q;
                memcpy(req, "AJOB", 4); req[4] = 1; req[5] = AJOB_OP_FIR_BLOCK; req[6] = 1; req[7] = 4;
                req[8] = (uint8_t)sq; req[9] = (uint8_t)(sq >> 8); req[10] = 0; req[11] = 0;
                for (q = 0; q < 1025; q++) { req[16 + 2 * q] = (uint8_t)(uint16_t)fin[q]; req[17 + 2 * q] = (uint8_t)((uint16_t)fin[q] >> 8); }
                { uint32_t c = arc1_crc32(0, req + 16, 2050); req[12] = (uint8_t)c; req[13] = (uint8_t)(c >> 8); req[14] = (uint8_t)(c >> 16); req[15] = (uint8_t)(c >> 24); }
                qlen[k] = 16 + 2050;
            } else {
                qlen[k] = ajob_build_fir_block(req, sizeof req, sq, fin, nb);
                if (k == 15) req[AJOB_HDR + 100] ^= 0x04;     /* corrupted in transit: PAYLOAD_CRC, history not advanced */
            }
            rlen[k] = ajob_reference_response(resp, sizeof resp, req, qlen[k], &fir_gen);
            st[k] = resp[5];
            want = (k == 11) ? AJOB_BAD_STATE : (k == 15) ? AJOB_PAYLOAD_CRC : (k == 17 || k == 18) ? AJOB_BAD_LENGTH : AJOB_OK;
            if (st[k] != want) { printf("FAIL fir case %d status %d != %d\n", k, st[k], want); fails++; }
            pr = ajob_parse_fir(resp, rlen[k], sq, op, nb, fout);
            if (pr != want) { printf("FAIL fir parse case %d: %d != %d\n", k, pr, want); fails++; }
            /* independent shadow: plain direct-form convolution over the accepted sample stream */
            if (op == AJOB_OP_FIR_SET_IR && want == AJOB_OK) { memcpy(fir_shadow.ir, taps, sizeof taps); fir_shadow.ir_valid = 1; }
            if (op == AJOB_OP_FIR_BLOCK && want == AJOB_OK) {
                uint16_t j, t;
                for (j = 0; j < nb; j++) fir_shadow.x[(fir_shadow.wp + j) & 2047u] = fin[j];
                for (j = 0; j < nb; j++) {
                    int64_t a = 0, sh;
                    for (t = 0; t < 1024; t++) a += (int64_t)fir_shadow.ir[t] * fir_shadow.x[(unsigned)(fir_shadow.wp + j - t) & 2047u];
                    sh = a >> 15;
                    fexp[j] = (int16_t)(sh > 32767 ? 32767 : sh < -32768 ? -32768 : sh);
                }
                fir_shadow.wp = (uint16_t)((fir_shadow.wp + nb) & 2047u);
                if (memcmp(fexp, fout, 2u * nb) != 0) { printf("FAIL fir case %d outputs differ from shadow\n", k); fails++; }
            }
            dump(argv[1], "req", k, req, qlen[k]);
            dump(argv[1], "resp", k, resp, rlen[k]);
            printf("CASE %d %-13s req=%zu resp=%zu status=%d\n", k, names[k], qlen[k], rlen[k], st[k]);
            continue;
        }
        uint32_t seq = 0x1000u + (uint32_t)k * 0x01010101u;
        if (k == 1) n = 8;
        if (k == 2) n = AJOB_MAXCOUNT;
        if (k == 10) n = 16;
        for (i = 0; i < n; i++) job(&jobs[i], 0xA0000000u | ((uint32_t)k << 16) | i,
                                    k == 1 ? (int)(i % 6) : (k == 10 ? 5 : 0));
        qlen[k] = ajob_build(req, sizeof req, seq, jobs, n);
        if (!qlen[k]) { printf("FAIL build case %d\n", k); return 1; }
        switch (k) {
        case 3: req[12] ^= 0x01; break;
        case 4: req[4] = 2; break;
        case 5: req[5] = 7; break;
        case 6: req[qlen[k]++] = 0x55; break;
        case 7: req[6] = 0; req[7] = 0; break;
        case 8: req[6] = 171; req[7] = 0; break;
        case 9: memcpy(req, "XJOB", 4); break;
        default: break;
        }
        rlen[k] = ajob_reference_response(resp, sizeof resp, req, qlen[k], &fir_gen);
        st[k] = (k == 9) ? -1 : resp[5];
        /* the F133 driver must accept exactly the good cases and report the FPGA status otherwise */
        if (k != 9) {
            int pr = ajob_parse(resp, rlen[k], seq, n, res);
            int want = (k <= 2 || k == 10) ? AJOB_OK : st[k];
            if (pr != want) { printf("FAIL parse case %d: %d != %d\n", k, pr, want); fails++; }
            if (pr == AJOB_OK) for (i = 0; i < n; i++) {
                arc1_transform_result r;
                arc1_transform_rectangle(&jobs[i], &r);
                if (memcmp(&r, &res[i], sizeof r) != 0) { printf("FAIL result %d/%u\n", k, i); fails++; }
            }
            /* corruptions the host must catch */
            if (pr == AJOB_OK) {
                resp[AJOB_HDR + 3] ^= 0x80;
                if (ajob_parse(resp, rlen[k], seq, n, res) != AJOB_HOST_RESULT_CRC) { printf("FAIL crc not caught %d\n", k); fails++; }
                resp[AJOB_HDR + 3] ^= 0x80;
                if (ajob_parse(resp, rlen[k], seq + 1, n, res) != AJOB_HOST_SEQ) { printf("FAIL seq not caught %d\n", k); fails++; }
                if (ajob_parse(resp, rlen[k] - 1, seq, n, res) != AJOB_HOST_TRUNCATED) { printf("FAIL trunc not caught %d\n", k); fails++; }
            }
        }
        dump(argv[1], "req", k, req, qlen[k]);
        dump(argv[1], "resp", k, resp, rlen[k]);
        printf("CASE %d %-13s req=%zu resp=%zu status=%d\n", k, names[k], qlen[k], rlen[k], st[k]);
    }
    snprintf(p, sizeof p, "%s/ajob_cases.svh", argv[1]);
    sv = fopen(p, "w");
    if (!sv) { perror(p); return 2; }
    fprintf(sv, "// generated by firmware/tools/ajob_vectors.c -- do not edit\nlocalparam integer NAJOB = %d;\n", NC);
    fprintf(sv, "function integer ajob_qlen(input integer k); case (k)\n");
    for (k = 0; k < NC; k++) fprintf(sv, "  %d: ajob_qlen = %zu;\n", k, qlen[k]);
    fprintf(sv, "  default: ajob_qlen = 0; endcase endfunction\nfunction integer ajob_rlen(input integer k); case (k)\n");
    for (k = 0; k < NC; k++) fprintf(sv, "  %d: ajob_rlen = %zu;\n", k, rlen[k]);
    fprintf(sv, "  default: ajob_rlen = 0; endcase endfunction\nfunction integer ajob_status(input integer k); case (k)\n");
    for (k = 0; k < NC; k++) fprintf(sv, "  %d: ajob_status = %d;\n", k, st[k]);
    fprintf(sv, "  default: ajob_status = -1; endcase endfunction\n");
    fclose(sv);
    printf("%s\n", fails ? "AJOB_VECTORS_FAIL" : "AJOB_VECTORS_PASS");
    return fails ? 1 : 0;
}
