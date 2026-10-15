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

/* R8.5-C: PG0..PG12 back to GPIO inputs; called before every FPGA power-down / unconfigure */
static void mux_off(accel_service *s)
{
    if (s->eth_attached) s->eth.hal.set_mux(s->eth.hal.ctx, 0);
    s->mux_on = 0;
    s->transport = SVC_TR_SPI;
    s->fir_sync = 0;
}

static void fault(accel_service *s, svc_err e)
{
    s->last_err = e;
    s->faults++;
    go(s, SVC_P6_FAULT);
    mux_off(s);
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
    s->transport = SVC_TR_SPI;
    ajob_fir_init(&s->fir);
    ecp5_safe(&s->cfg, 1);                       /* a crashed previous run may have left the FPGA half-configured */
    go(s, SVC_P1_LAUNCHER);
}

/* one known-answer job through the real engine: signature + datapath self-test before any game work */
static const arc1_transform_job kat_job = { -65536, -131072, 196608, 262144, 46341, -46341, 655360, 46341, 46341,
                                            -327680, 320, 240, 0x4B415401u };

/* one request/response on the current transport; EL_* and FL_* share TIMEOUT/IO/PROTOCOL/ARG codes */
static int xfer(accel_service *s, size_t ql, size_t *rl)
{
    if (s->transport == SVC_TR_ETH) return el_exchange(&s->eth, s->req, ql, s->resp, sizeof s->resp, rl);
    return fl_exchange(&s->link, s->req, ql, s->resp, sizeof s->resp, rl);
}

static int exchange(accel_service *s, const arc1_transform_job *jobs, uint16_t n, arc1_transform_result *out, int *job_err)
{
    size_t ql, rl = 0;
    int rc;
    uint32_t seq = s->seq++;
    ql = ajob_build(s->req, sizeof s->req, seq, jobs, n);
    if (!ql) { *job_err = AJOB_HOST_ARGS; return FL_ARG; }
    rc = xfer(s, ql, &rl);
    if (rc) { *job_err = -1; return rc; }
    *job_err = ajob_parse(s->resp, rl, seq, n, out);
    (void)fl_read32(&s->link, FL_REG_PERF_CYCLES, &s->last_cycles);
    return FL_OK;
}

void svc_attach_eth(accel_service *s, const arc1_eth_hal *eth, const uint8_t host_mac[6], uint32_t timeout_us)
{
    el_init(&s->eth, eth, host_mac, timeout_us);
    s->eth_attached = 1;
    mux_off(s);
}

/* P4, after DONE + DISCOVER: switch PG to RGMII and prove the path with the same known-answer job */
static void eth_bringup(accel_service *s)
{
    arc1_transform_result r, ref;
    int rc, je = 0;
    if (!s->eth_attached || !(s->caps & FL_CAP_RGMII)) return;
    s->eth.hal.set_mux(s->eth.hal.ctx, 1);
    s->mux_on = 1;
    s->transport = SVC_TR_ETH;
    rc = exchange(s, &kat_job, 1, &r, &je);
    arc1_transform_rectangle(&kat_job, &ref);
    if (rc || je != AJOB_OK || memcmp(&r, &ref, sizeof r) != 0) {   /* degraded: keep the SPI transport */
        s->eth_kat_failures++;
        s->last_link_err = rc; s->last_job_err = je;
        mux_off(s);
    }
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
#ifdef MUTANT_SVC_MUX_EARLY
    if (s->eth_attached) s->eth.hal.set_mux(s->eth.hal.ctx, 1);   /* RGMII drive into an unconfigured FPGA */
#endif
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
    eth_bringup(s);
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
    s->fir_sync = 0;                             /* fresh bitstream: FIR state zero; re-prime from the mirror on first use */
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
        if (rc == FL_TIMEOUT) {                    /* stuck engine: ABORT, drain its ARES(ABORTED), no stale result;
                                                      over RGMII the ABORTED frame is discarded by sequence number */
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
    mux_off(s);                                    /* PG back to GPIO inputs before the FPGA rails go off */
    ecp5_safe(&s->cfg, 1);
    s->psram_ok = 0;
    go(s, SVC_P1_LAUNCHER);
}

/* ------------------------------------------------------------------ R8.5-C resident FIR */
static void link_failure(accel_service *s, int rc)
{
    s->consecutive_errors++;
    if (rc == FL_NOT_READY || s->consecutive_errors >= s->max_consecutive_errors ||
        !s->cfg.io.get(s->cfg.io.ctx, ECP5_PIN_DONE))
        fault(s, SVC_E_LINK);
}

/* one FIR frame (op 2 or 3); y may be NULL (outputs discarded). Returns 0 only for a fully checked AJOB_OK. */
static int fir_exchange(accel_service *s, uint8_t op, const int16_t *v, uint16_t n, int16_t *y, int *rc_out)
{
    static int16_t discard[AJOB_FIR_MAXBLK];
    size_t ql, rl = 0;
    int rc, je;
    uint32_t seq = s->seq++;
    ql = op == AJOB_OP_FIR_SET_IR ? ajob_build_fir_ir(s->req, sizeof s->req, seq, v)
                                  : ajob_build_fir_block(s->req, sizeof s->req, seq, v, n);
    if (!ql) { *rc_out = FL_ARG; return -1; }
    rc = xfer(s, ql, &rl);
    *rc_out = rc;
    s->last_link_err = rc;
    if (rc) return -1;
    je = ajob_parse_fir(s->resp, rl, seq, op, op == AJOB_OP_FIR_SET_IR ? 0 : n, y ? y : discard);
    s->last_job_err = je;
    return je == AJOB_OK ? 0 : -1;
}

/* bring the FPGA FIR state to the mirror: IR, then the last 1024 mirrored samples (outputs discarded). Whatever
 * the FPGA history was (a block applied or not, a reconfiguration), its last 1023 samples now equal the mirror's. */
static int fir_resync(accel_service *s, int *rc)
{
    static int16_t prime[AJOB_FIR_MAXBLK];
    unsigned i;
    if (fir_exchange(s, AJOB_OP_FIR_SET_IR, s->fir.ir, AJOB_FIR_TAPS, NULL, rc)) return -1;
    for (i = 0; i < AJOB_FIR_MAXBLK; i++)
        prime[i] = s->fir.x[(unsigned)(s->fir.wp + AJOB_FIR_HIST - AJOB_FIR_MAXBLK + i) & (AJOB_FIR_HIST - 1u)];
    if (fir_exchange(s, AJOB_OP_FIR_BLOCK, prime, AJOB_FIR_MAXBLK, NULL, rc)) return -1;
    s->fir_resyncs++;
    s->fir_sync = 1;
    return 0;
}

svc_fallback svc_fir_set_ir(accel_service *s, const int16_t taps[AJOB_FIR_TAPS])
{
    int rc = 0;
    if (!taps) return SVC_FB_COUNT_ARG;
    memcpy(s->fir.ir, taps, sizeof s->fir.ir);
    s->fir.ir_valid = 1;
    if (s->state != SVC_P5_PLAY) { s->fir_sync = 0; return SVC_FB_NOT_PLAYING; }
    if (s->fir_sync && fir_exchange(s, AJOB_OP_FIR_SET_IR, taps, AJOB_FIR_TAPS, NULL, &rc) == 0) {
        s->consecutive_errors = 0;
        return SVC_FB_NONE;
    }
    s->fir_sync = 0;                               /* applied by the next block's resync (IR + history) */
    if (rc) { link_failure(s, rc); return rc == FL_TIMEOUT ? SVC_FB_TIMEOUT : SVC_FB_LINK; }
    return SVC_FB_NONE;
}

static svc_fallback fir_cpu(accel_service *s, const int16_t *in, uint16_t n, int16_t *out, svc_fallback why)
{
    ajob_fir_run(&s->fir, in, n, out);
    s->fir_cpu_blocks++;
    s->cpu_batches++;
    s->fallback[why]++;
    return why;
}

svc_fallback svc_fir_block(accel_service *s, const int16_t *in, uint16_t n, int16_t *out)
{
    int rc = 0;
    if (!in || !out || n == 0 || n > AJOB_FIR_MAXBLK) return SVC_FB_COUNT_ARG;
    if (!s->fir.ir_valid) { memset(out, 0, sizeof *out * n); s->fallback[SVC_FB_NO_IR]++; return SVC_FB_NO_IR; }
    if (s->state != SVC_P5_PLAY) return fir_cpu(s, in, n, out, SVC_FB_NOT_PLAYING);
#ifndef MUTANT_FIR_NO_RESYNC
    if (!s->fir_sync && fir_resync(s, &rc)) {
#else
    if (!s->fir_sync && ((void)fir_resync, s->fir_sync = 1, 0)) {      /* trusts the FPGA state blindly */
#endif
        link_failure(s, rc);
        return fir_cpu(s, in, n, out, rc == FL_TIMEOUT ? SVC_FB_TIMEOUT : rc ? SVC_FB_LINK : SVC_FB_FRAME);
    }
    if (fir_exchange(s, AJOB_OP_FIR_BLOCK, in, n, out, &rc) == 0) {
        ajob_fir_run(&s->fir, in, n, NULL);        /* mirror: history only, no arithmetic */
        s->consecutive_errors = 0;
        s->fir_fpga_blocks++;
        s->fpga_batches++;
        return SVC_FB_NONE;
    }
    /* outcome unknown (the FPGA may or may not have appended the block): CPU result now, re-prime before reuse */
    s->fir_sync = 0;
    if (rc == FL_TIMEOUT) { s->aborts++; (void)fl_control(&s->link, FL_CTL_ABORT); }
    link_failure(s, rc ? rc : FL_PROTOCOL);
    return fir_cpu(s, in, n, out, rc == FL_TIMEOUT ? SVC_FB_TIMEOUT : rc ? SVC_FB_LINK : SVC_FB_FRAME);
}
