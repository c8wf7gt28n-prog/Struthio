/* ARC-1 Compact R8.5 -- accelerator service state machine (see header). HOST_TESTED with mocks only. */
#include "accel_service.h"
#include <string.h>

#define AMBX_ABI_MAJOR 3u

static void go(accel_service *s, svc_state st)
{
    s->state = st;
    if (s->ntrace < SVC_TRACE) s->trace[s->ntrace++] = st;
}

const char *svc_state_name(svc_state st)
{
    static const char *const n[] = { "P0_RESET", "P1_LAUNCHER", "P2_SELECT", "P3_CONFIGURE", "P4_HANDSHAKE", "P5_PLAY",
                                     "P6_FAULT" };
    return (unsigned)st <= SVC_P6_FAULT ? n[st] : "?";
}

static void fault(accel_service *s, svc_err e)
{
    s->last_err = e;
    s->faults++;
    go(s, SVC_P6_FAULT);
#ifndef MUTANT_SVC_NO_SAFE_ON_FAULT
    ecp5_safe(&s->cfg, 1);                       /* PSRAM off, buffers off, FPGA rails off */
#endif
    s->psram_ok = 0;
    s->consecutive_errors = 0;
    go(s, SVC_P1_LAUNCHER);
}

void svc_init(accel_service *s, const ecp5_gpio_hal *io, const arc1_spi_hal *spi, uint32_t job_timeout_us)
{
    memset(s, 0, sizeof *s);
    go(s, SVC_P0_RESET);
    ecp5_cfg_init(&s->cfg, io, spi);
    (void)fl_init(&s->link, spi, job_timeout_us ? job_timeout_us : 20000u);
    s->max_consecutive_errors = 3;
    s->seq = 1;
    ecp5_safe(&s->cfg, 1);                       /* a crashed previous run may have left the FPGA half-configured */
    go(s, SVC_P1_LAUNCHER);
}

/* one known-answer job through the real engine: signature + datapath self-test before any game work */
static const arc1_transform_job kat_job = { -65536, -131072, 196608, 262144, 46341, -46341, 655360, 46341, 46341,
                                            -327680, 320, 240, 0x4B415401u };

static int exchange(accel_service *s, const arc1_transform_job *jobs, uint16_t n, arc1_transform_result *out, int *job_err)
{
    size_t ql, rl = 0;
    int rc;
    uint32_t seq = s->seq++;
    ql = ajob_build(s->req, sizeof s->req, seq, jobs, n);
    if (!ql) { *job_err = AJOB_HOST_ARGS; return FL_ARG; }
    rc = fl_exchange(&s->link, s->req, ql, s->resp, sizeof s->resp, &rl);
    if (rc) { *job_err = -1; return rc; }
    *job_err = ajob_parse(s->resp, rl, seq, n, out);
    (void)fl_read32(&s->link, FL_REG_PERF_CYCLES, &s->last_cycles);
    return FL_OK;
}

svc_err svc_load(accel_service *s, const uint8_t *file, size_t len, int run_bist)
{
    ecp5_image img;
    arc1_transform_result r, ref;
    int rc, je = 0;
    uint16_t st = 0;
    unsigned t;
    if (s->state != SVC_P1_LAUNCHER && s->state != SVC_P5_PLAY) return SVC_E_STATE;
    if (s->state == SVC_P5_PLAY) svc_unload(s);
    go(s, SVC_P2_SELECT);
    s->last_cfg_err = ecp5_image_check(file, len, AMBX_ABI_MAJOR, &img);
    if (s->last_cfg_err) {                        /* bad/absent bitstream: FPGA stays off, nothing else changes */
        s->last_err = SVC_E_IMAGE;
        go(s, SVC_P1_LAUNCHER);
        return SVC_E_IMAGE;
    }
    s->caps_required = img.caps_required;
    go(s, SVC_P3_CONFIGURE);
    s->configs++;
    s->last_cfg_err = ecp5_configure(&s->cfg, &img);
    if (s->last_cfg_err == ECP5_E_CONFIG_STATUS) {     /* one retry on a configuration CRC/status fault */
        s->retries++;
        s->last_cfg_err = ecp5_configure(&s->cfg, &img);
    }
    if (s->last_cfg_err) { fault(s, SVC_E_CONFIG); return SVC_E_CONFIG; }
    go(s, SVC_P4_HANDSHAKE);
    rc = fl_discover(&s->link, &s->version, &s->caps);
    s->last_link_err = rc;
    if (rc == FL_VERSION) { fault(s, SVC_E_ABI); return SVC_E_ABI; }
    if (rc) { fault(s, SVC_E_DISCOVER); return SVC_E_DISCOVER; }
    if (!(s->caps & FL_CAP_AJOB) || (s->caps & img.caps_required) != img.caps_required) {
        fault(s, SVC_E_CAPS);
        return SVC_E_CAPS;
    }
    rc = exchange(s, &kat_job, 1, &r, &je);
    arc1_transform_rectangle(&kat_job, &ref);
#ifdef MUTANT_SVC_NO_KAT
    if (rc || je != AJOB_OK) {
#else
    if (rc || je != AJOB_OK || memcmp(&r, &ref, sizeof r) != 0) {
#endif
        s->last_link_err = rc; s->last_job_err = je;
        fault(s, SVC_E_SELFTEST);
        return SVC_E_SELFTEST;
    }
    /* PSRAM: power request (EN = REQ & DONE_DLY), then READY and optional BIST */
    s->cfg.io.set(s->cfg.io.ctx, ECP5_PIN_PSRAM_REQ, 1);
    s->psram_ok = 0;
    for (t = 0; t < 50u; t++) {
        s->cfg.io.delay_us(s->cfg.io.ctx, 100);
        if (fl_status(&s->link, &st) == FL_OK && (st & FL_ST_PSRAM_READY)) { s->psram_ok = 1; break; }
    }
    if (s->psram_ok && run_bist) {
        (void)fl_control(&s->link, FL_CTL_BIST_START);
        for (t = 0; t < 2000u; t++) {
            s->cfg.io.delay_us(s->cfg.io.ctx, 1000);
            if (fl_status(&s->link, &st) != FL_OK) break;
            if (!(st & FL_ST_BIST_BUSY) && (st & (FL_ST_BIST_PASS | FL_ST_BIST_FAIL))) break;
        }
        if (!(st & FL_ST_BIST_PASS) || (st & FL_ST_BIST_FAIL)) s->psram_ok = 0;
    }
    if (!s->psram_ok) {
        s->cfg.io.set(s->cfg.io.ctx, ECP5_PIN_PSRAM_REQ, 0);    /* degraded: no PSRAM, register-only jobs */
        if (img.caps_required & FL_CAP_PSRAM) { fault(s, SVC_E_PSRAM); return SVC_E_PSRAM; }
    }
    s->consecutive_errors = 0;
    go(s, SVC_P5_PLAY);
    return SVC_OK;
}

static svc_fallback cpu(accel_service *s, const arc1_transform_job *jobs, uint16_t n, arc1_transform_result *out, svc_fallback why)
{
    uint16_t i;
    for (i = 0; i < n; i++) arc1_transform_rectangle(&jobs[i], &out[i]);
    s->cpu_batches++;
    s->fallback[why]++;
    return why;
}

svc_fallback svc_transform(accel_service *s, const arc1_transform_job *jobs, uint16_t n, arc1_transform_result *out)
{
    int attempt, rc = 0, je = 0;
    svc_fallback why = SVC_FB_LINK;
    if (!jobs || !out || n == 0 || n > AJOB_MAXCOUNT) {
        if (jobs && out && n) return cpu(s, jobs, n, out, SVC_FB_COUNT_ARG);
        return SVC_FB_COUNT_ARG;
    }
    if (s->state != SVC_P5_PLAY) return cpu(s, jobs, n, out, SVC_FB_NOT_PLAYING);
    for (attempt = 0; attempt < 2; attempt++) {
        rc = exchange(s, jobs, n, out, &je);
        s->last_link_err = rc;
        s->last_job_err = je;
        if (rc == FL_OK && je == AJOB_OK) {
            s->consecutive_errors = 0;
            s->fpga_batches++;
            return SVC_FB_NONE;
        }
#ifndef MUTANT_SVC_NO_ABORT
        if (rc == FL_TIMEOUT) {                    /* stuck engine: ABORT, drain its ARES(ABORTED), no stale result */
            uint8_t dummy[AJOB_HDR];
            size_t dl = 0;
            uint16_t st = 0;
            s->aborts++;
            (void)fl_control(&s->link, FL_CTL_ABORT);
            if (fl_status(&s->link, &st) == FL_OK && (st & FL_ST_RESP_READY)) {
                (void)fl_read(&s->link, FL_RESP_BUF, dummy, sizeof dummy);
                (void)fl_control(&s->link, FL_CTL_RESP_ACK);
            }
            (void)dl;
            why = SVC_FB_TIMEOUT;
            break;                                 /* do not retry a timed-out batch inside the frame budget */
        }
#endif
        if (rc == FL_NOT_READY || rc == FL_IO || rc == FL_BUSY || rc == FL_PROTOCOL) { why = SVC_FB_LINK; break; }
        why = SVC_FB_FRAME;                        /* CRC / sequence / status: retry once */
        s->retries++;
    }
    s->consecutive_errors++;
    if (rc == FL_NOT_READY || s->consecutive_errors >= s->max_consecutive_errors ||
        !s->cfg.io.get(s->cfg.io.ctx, ECP5_PIN_DONE)) {
        fault(s, SVC_E_LINK);
    }
    return cpu(s, jobs, n, out, why);
}

void svc_unload(accel_service *s)
{
    if (s->state == SVC_P5_PLAY) {
        go(s, SVC_P2_SELECT);                      /* quiesce: no stale FPGA operation survives a game swap */
        (void)fl_control(&s->link, FL_CTL_ABORT);
    }
    ecp5_safe(&s->cfg, 1);
    s->psram_ok = 0;
    go(s, SVC_P1_LAUNCHER);
}
