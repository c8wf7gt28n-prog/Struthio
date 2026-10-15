/* ARC-1 Compact R8.5-C -- RGMII job link + resident FIR service tests with failure injection.
 * Each case prints "FIT <id> <name> | <expected> | <observed> | PASS/FAIL" (docs/FAILURE_INJECTION_R85.md).
 * HOST_TESTED against tests/ecp5_mock.c + tests/emac_mock.c (behavioural models, virtual time). */
#include "accel_service.h"
#include "check.h"
#include "crc32.h"
#include "emac_mock.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *g_file;
static size_t g_file_len;
static uint32_t g_bit_crc;
static ecp5_mock M;
static emac_mock E;
static accel_service S;
static const uint8_t HOST_MAC[6] = { 0x02, 0x00, 0x00, 0xF1, 0x33, 0x44 };

static void make_image(void)
{
    static const uint8_t head[] = { 0xFF, 0x00, 'P', 'a', 'r', 't', ':', ' ', 'L', 'F', 'E', '5', 'U', '-', '4', '5', 'F',
                                    0x00, 0xFF, 0xFF, 0xFF, 0xBD, 0xB3, 0xFF, 0xFF, 0xFF, 0xFF, 0x3B, 0, 0, 0,
                                    0xE2, 0, 0, 0, 0x41, 0x11, 0x20, 0x43 };
    uint32_t i, x = 777, n = 65536u;
    uint8_t *bit = malloc(n);
    memcpy(bit, head, sizeof head);
    for (i = sizeof head; i < n; i++) { x = x * 1103515245u + 12345u; bit[i] = (uint8_t)(x >> 16); }
    g_bit_crc = arc1_crc32(0, bit, n);
    g_file = malloc(n + ACFG_HDR);
    g_file_len = ecp5_image_build(g_file, n + ACFG_HDR, bit, n, 3, 0, 0);
    free(bit);
}

static void fresh(int attach)
{
    ecp5_gpio_hal io = mock_gpio;
    arc1_spi_hal spi = mock_spi;
    arc1_eth_hal eh = emac_mock_hal;
    mock_init(&M, g_bit_crc);
    emac_mock_init(&E, &M);
    io.ctx = &M; spi.ctx = &M; eh.ctx = &E;
    svc_init(&S, &io, &spi, 20000);
    if (attach) svc_attach_eth(&S, &eh, HOST_MAC, 2000);
}

static void fit(const char *id, const char *name, const char *expect, int ok, const char *o)
{
    printf("FIT %s %s | %s | %s | %s\n", id, name, expect, o, ok ? "PASS" : "FAIL");
    g_checks++;
    if (!ok) g_fail++;
}

static arc1_transform_job jobs[AJOB_MAXCOUNT];
static arc1_transform_result out[AJOB_MAXCOUNT], ref[AJOB_MAXCOUNT];
static void make_jobs(uint16_t n, int salt)
{
    uint16_t i;
    for (i = 0; i < n; i++) {
        arc1_transform_job j = { (int32_t)i * 65536 + salt, -(int32_t)i * 4096, (int32_t)i * 65536 + 20 * 65536, 12 * 65536,
                                 46341, -46341, (int32_t)(i % 5) * 65536, 46341, 46341, salt * 16, 320, 240,
                                 0x200u + i + (uint32_t)salt };
        jobs[i] = j;
        arc1_transform_rectangle(&jobs[i], &ref[i]);
    }
}
static int results_ok(uint16_t n) { return memcmp(out, ref, sizeof(arc1_transform_result) * n) == 0; }

/* FIR: independent reference state, driven exactly like the service's caller */
static ajob_fir_state R;
static int16_t taps[AJOB_FIR_TAPS], blk[AJOB_FIR_MAXBLK], y[AJOB_FIR_MAXBLK], yref[AJOB_FIR_MAXBLK];
static uint32_t rng = 99;
static int16_t rnd16(void) { rng = rng * 1664525u + 1013904223u; return (int16_t)(rng >> 16); }
static void make_taps(void)
{
    unsigned i;
    for (i = 0; i < AJOB_FIR_TAPS; i++) taps[i] = (int16_t)(rnd16() / (int16_t)(8 + (i / 64)));
    ajob_fir_init(&R);
    memcpy(R.ir, taps, sizeof taps);
    R.ir_valid = 1;
}
/* run one block through the service and the reference; returns 1 if bit-exact */
static int fir_step(uint16_t n, svc_fallback *fb)
{
    uint16_t i;
    for (i = 0; i < n; i++) blk[i] = rnd16();
    *fb = svc_fir_block(&S, blk, n, y);
    ajob_fir_run(&R, blk, n, yref);
    return memcmp(y, yref, sizeof(int16_t) * n) == 0;
}

static int safe_off(void) { return S.state == SVC_P1_LAUNCHER && !M.pwr_en && !E.mux && E.mux_violations == 0; }

void run_eth_tests(void)
{
    char o[256];
    svc_err e;
    svc_fallback fb;
    int ok, i, okall;
    uint64_t t0, f0;
    make_image();

    /* ---- E00 nominal: KAT over SPI, then PG -> RGMII after DONE, KAT over RGMII, batches over RGMII ---- */
    fresh(1);
    CHECK(!E.mux && E.mux_violations == 0);
    e = svc_load(&S, g_file, g_file_len, 0);
    make_jobs(170, 1);
    f0 = E.frames_to_fpga;
    t0 = M.t_us;
    fb = svc_transform(&S, jobs, 170, out);
    snprintf(o, sizeof o, "load=%d transport=%d mux=%d doorbells=%u eth_frames=%llu fb=%d batch_us=%llu", (int)e,
             (int)S.transport, E.mux, M.doorbells, (unsigned long long)(E.frames_to_fpga - f0), (int)fb,
             (unsigned long long)(M.t_us - t0));
    ok = e == SVC_OK && S.transport == SVC_TR_ETH && E.mux && M.doorbells == 1 && E.frames_to_fpga - f0 == 1 &&
         fb == SVC_FB_NONE && results_ok(170) && E.mux_violations == 0;
    fit("E00", "rgmii_nominal", "P5 over RGMII after SPI KAT; 170-job batch bit-exact in one frame each way", ok, o);
    svc_unload(&S);
    CHECK(safe_off());

    /* ---- E01 bitstream without the RGMII capability: SPI transport, PG never switched ---- */
    fresh(1); M.no_rgmii = 1;
    e = svc_load(&S, g_file, g_file_len, 0);
    make_jobs(16, 2);
    fb = svc_transform(&S, jobs, 16, out);
    snprintf(o, sizeof o, "transport=%d mux=%d fb=%d", (int)S.transport, E.mux, (int)fb);
    fit("E01", "no_rgmii_caps", "SPI mailbox transport, PG0-PG12 stay GPIO inputs",
        e == SVC_OK && S.transport == SVC_TR_SPI && !E.mux && E.frames_to_fpga == 0 && fb == SVC_FB_NONE && results_ok(16), o);

    /* ---- E02 RGMII path dead (delay chain outside the eye): KAT over RGMII fails -> degraded to SPI, still P5 ---- */
    fresh(1); E.tx_step = 0;
    e = svc_load(&S, g_file, g_file_len, 0);
    make_jobs(8, 3);
    fb = svc_transform(&S, jobs, 8, out);
    snprintf(o, sizeof o, "state=%s transport=%d mux=%d eth_kat_fail=%llu fpga_fcs_err=%u fb=%d", svc_state_name(S.state),
             (int)S.transport, E.mux, (unsigned long long)S.eth_kat_failures, M.eth_cnt[1], (int)fb);
    fit("E02", "rgmii_kat_fails_degrade_spi", "RGMII KAT fails -> PG back to GPIO, SPI transport, jobs bit-exact",
        e == SVC_OK && S.state == SVC_P5_PLAY && S.transport == SVC_TR_SPI && !E.mux && S.eth_kat_failures == 1 &&
        fb == SVC_FB_NONE && results_ok(8), o);

    /* ---- E03/E04 lost request / lost response: timeout -> ABORT -> CPU result; next batch over RGMII ---- */
    for (i = 0; i < 2; i++) {
        svc_fallback fb2;
        fresh(1);
        (void)svc_load(&S, g_file, g_file_len, 0);
        if (i == 0) E.drop_req = 1; else E.drop_resp = 1;
        make_jobs(32, 4 + i);
        fb = svc_transform(&S, jobs, 32, out);
        ok = fb == SVC_FB_TIMEOUT && results_ok(32);
        make_jobs(32, 6 + i);
        fb2 = svc_transform(&S, jobs, 32, out);
        snprintf(o, sizeof o, "fb=%d then fb=%d transport=%d timeouts=%llu aborts=%llu", (int)fb, (int)fb2, (int)S.transport,
                 (unsigned long long)S.eth.timeouts, (unsigned long long)S.aborts);
        fit(i == 0 ? "E03" : "E04", i == 0 ? "rgmii_request_lost" : "rgmii_response_lost",
            "TIMEOUT -> ABORT -> CPU result (bit-exact); next batch over RGMII",
            ok && fb2 == SVC_FB_NONE && results_ok(32) && S.transport == SVC_TR_ETH, o);
    }

    /* ---- E05 stale ARES + foreign EtherType ahead of the answer: discarded, answer used ---- */
    fresh(1);
    (void)svc_load(&S, g_file, g_file_len, 0);
    E.stray_before_resp = 1;
    make_jobs(24, 8);
    f0 = S.eth.stray;
    {
        uint64_t r0 = S.retries, fr0 = E.frames_to_fpga;
        fb = svc_transform(&S, jobs, 24, out);
        snprintf(o, sizeof o, "fb=%d stray_discarded=%llu frames_to_fpga=%llu retries=%llu", (int)fb,
                 (unsigned long long)(S.eth.stray - f0), (unsigned long long)(E.frames_to_fpga - fr0),
                 (unsigned long long)(S.retries - r0));
        fit("E05", "rgmii_stale_and_foreign_frames",
            "stale ARES (old seq) and an IPv4 frame discarded by the link layer; answer used without a retry",
            fb == SVC_FB_NONE && results_ok(24) && S.eth.stray - f0 == 2 && E.frames_to_fpga - fr0 == 1 && S.retries == r0, o);
    }

    /* ---- E06 duplicated response: drained before the next exchange ---- */
    E.dup_resp = 1;
    make_jobs(10, 9);
    fb = svc_transform(&S, jobs, 10, out);
    ok = fb == SVC_FB_NONE && results_ok(10);
    make_jobs(10, 10);
    f0 = S.eth.stray;
    fb = svc_transform(&S, jobs, 10, out);
    snprintf(o, sizeof o, "fb=%d stray_drained=%llu", (int)fb, (unsigned long long)(S.eth.stray - f0));
    fit("E06", "rgmii_duplicate_response", "duplicate drained, never used as the next batch's answer",
        ok && fb == SVC_FB_NONE && results_ok(10) && S.eth.stray - f0 == 1, o);

    /* ---- E07 link down for 3 batches: CPU each time, then fault -> P1 with PG off before power-down ---- */
    fresh(1);
    (void)svc_load(&S, g_file, g_file_len, 0);
    E.link_down = 3;
    okall = 1;
    for (i = 0; i < 3; i++) { make_jobs(16, 11 + i); fb = svc_transform(&S, jobs, 16, out); okall &= results_ok(16) && fb != SVC_FB_NONE; }
    snprintf(o, sizeof o, "state=%s pwr_en=%d mux=%d mux_violations=%u faults=%llu", svc_state_name(S.state), M.pwr_en, E.mux,
             E.mux_violations, (unsigned long long)S.faults);
    fit("E07", "rgmii_link_down", "3 failed batches (CPU results bit-exact) -> P6 -> P1; PG to GPIO before rails off",
        okall && safe_off() && S.faults == 1, o);

    /* ---- E08 FPGA-side FCS errors are visible through the mailbox counters ---- */
    fresh(1);
    (void)svc_load(&S, g_file, g_file_len, 0);
    E.tx_step = 7;                                /* setting outside the (moved) eye */
    make_jobs(4, 15);
    fb = svc_transform(&S, jobs, 4, out);
    {
        uint8_t c[12];
        uint16_t fcs;
        (void)fl_read(&S.link, FL_REG_ETH_RX_OK, c, sizeof c);
        fcs = (uint16_t)(c[2] | (c[3] << 8));
        snprintf(o, sizeof o, "fb=%d rx_ok=%u rx_fcs=%u (mailbox 0x0034..)", (int)fb, c[0] | (c[1] << 8), fcs);
        fit("E08", "rgmii_fcs_errors_counted", "frames corrupted on the wire: CPU result, FCS count readable over SPI",
            fb == SVC_FB_TIMEOUT && results_ok(4) && fcs >= 1 && fcs == M.eth_cnt[1], o);
    }

    /* ---- E09 delay-chain calibration finds the centre of both eyes ---- */
    {
        unsigned tx = 0, rx = 0, wtx = 0, wrx = 0;
        int rc;
        fresh(1);
        (void)svc_load(&S, g_file, g_file_len, 0);
        rc = el_calibrate(&S.eth, 8, 32, 4, &tx, &rx, &wtx, &wrx);
        snprintf(o, sizeof o, "rc=%d ETXDC=%u (eye %u-%u, width %u) ERXDC=%u (eye %u-%u, width %u)", rc, tx, E.tx_lo, E.tx_hi,
                 wtx, rx, E.rx_lo, E.rx_hi, wrx);
        fit("E09", "rgmii_delay_calibration", "sweep from ETXDC=0 picks the centre of each eye (model: tx 2-6, rx 10-20)",
            rc == 0 && tx == 4 && rx == 15 && wtx == 5 && wrx == 11 && E.tx_step == 4 && E.rx_step == 15, o);
        E.tx_lo = 20; E.tx_hi = 30;                  /* no working setting */
        tx = 0; rx = 0;
        rc = el_calibrate(&S.eth, 8, 32, 2, &tx, &rx, NULL, NULL);
        CHECK(rc == -1);
    }

    /* ---- E10 resident FIR over RGMII: bit-exact with the reference, first block primes ---- */
    fresh(1);
    (void)svc_load(&S, g_file, g_file_len, 0);
    make_taps();
    fb = svc_fir_set_ir(&S, taps);
    okall = fb == SVC_FB_NONE;
    t0 = M.t_us;
    okall &= fir_step(735, &fb) && fb == SVC_FB_NONE;
    printf("INFO FIR 735-sample block incl. first-use resync over RGMII: %llu us virtual\n", (unsigned long long)(M.t_us - t0));
    t0 = M.t_us;
    okall &= fir_step(735, &fb) && fb == SVC_FB_NONE;
    printf("INFO FIR 735-sample block over RGMII (model: wire 1 Gb/s + RTL engine cycles): %llu us virtual\n",
           (unsigned long long)(M.t_us - t0));
    for (i = 0; i < 4; i++) okall &= fir_step((uint16_t)(1 + i * 300), &fb) && fb == SVC_FB_NONE;
    snprintf(o, sizeof o, "fpga_blocks=%llu cpu_blocks=%llu resyncs=%llu", (unsigned long long)S.fir_fpga_blocks,
             (unsigned long long)S.fir_cpu_blocks, (unsigned long long)S.fir_resyncs);
    fit("E10", "fir_resident_rgmii", "6 blocks (1..901 samples) bit-exact on the FPGA; one resync at first use",
        okall && S.fir_fpga_blocks == 6 && S.fir_cpu_blocks == 0 && S.fir_resyncs == 1, o);

    /* ---- E11 lost FIR request: FPGA did NOT append; CPU answers; resync keeps later FPGA blocks exact ---- */
    E.drop_req = 1;
    okall = fir_step(512, &fb) && fb == SVC_FB_TIMEOUT;
    for (i = 0; i < 3; i++) okall &= fir_step(700, &fb) && fb == SVC_FB_NONE;
    snprintf(o, sizeof o, "cpu_blocks=%llu resyncs=%llu all_exact=%d", (unsigned long long)S.fir_cpu_blocks,
             (unsigned long long)S.fir_resyncs, okall);
    fit("E11", "fir_request_lost_resync", "CPU block bit-exact; re-prime (IR + 1024 samples); next 3 FPGA blocks exact",
        okall && S.fir_cpu_blocks == 1 && S.fir_resyncs == 2, o);

    /* ---- E12 lost FIR response: FPGA DID append; resync makes the state certain again ---- */
    E.drop_resp = 1;
    okall = fir_step(333, &fb) && fb == SVC_FB_TIMEOUT;
    for (i = 0; i < 2; i++) okall &= fir_step(1024, &fb) && fb == SVC_FB_NONE;
    snprintf(o, sizeof o, "resyncs=%llu all_exact=%d", (unsigned long long)S.fir_resyncs, okall);
    fit("E12", "fir_response_lost_resync", "CPU block bit-exact; re-prime; later FPGA blocks exact", okall && S.fir_resyncs == 3, o);

    /* ---- E13 FIR continuity across unload (CPU) and a reload (fresh FPGA state) ---- */
    svc_unload(&S);
    okall = fir_step(400, &fb) && fb == SVC_FB_NOT_PLAYING;          /* game keeps running on the CPU */
    e = svc_load(&S, g_file, g_file_len, 0);
    okall &= e == SVC_OK;
    for (i = 0; i < 3; i++) okall &= fir_step(640, &fb) && fb == SVC_FB_NONE;
    snprintf(o, sizeof o, "load=%d resyncs=%llu all_exact=%d mux_violations=%u", (int)e, (unsigned long long)S.fir_resyncs,
             okall, E.mux_violations);
    fit("E13", "fir_across_reload", "CPU while unloaded; after reload the FPGA is re-primed and stays bit-exact",
        okall && S.fir_resyncs == 4 && E.mux_violations == 0, o);

    /* ---- E14 FIR over the SPI mailbox (no RGMII), and FIR before any IR ---- */
    fresh(0);
    (void)svc_load(&S, g_file, g_file_len, 0);
    fb = svc_fir_block(&S, blk, 16, y);
    ok = fb == SVC_FB_NO_IR;
    make_taps();
    (void)svc_fir_set_ir(&S, taps);
    okall = 1;
    for (i = 0; i < 3; i++) okall &= fir_step(735, &fb) && fb == SVC_FB_NONE;
    snprintf(o, sizeof o, "no_ir_fb=%d transport=%d all_exact=%d resyncs=%llu", (int)ok, (int)S.transport, okall,
             (unsigned long long)S.fir_resyncs);
    fit("E14", "fir_over_spi_and_no_ir", "SVC_FB_NO_IR before an IR; 3 SPI-mailbox FIR blocks bit-exact",
        ok && okall && S.transport == SVC_TR_SPI && S.fir_resyncs == 1, o);

    /* ---- E15 FPGA lost mid-game (configuration gone) during FIR: CPU, fault -> P1, PG off ---- */
    fresh(1);
    (void)svc_load(&S, g_file, g_file_len, 0);
    make_taps();
    (void)svc_fir_set_ir(&S, taps);
    okall = fir_step(256, &fb) && fb == SVC_FB_NONE;
    M.done = 0; M.configured = 0;                                     /* FPGA dropped out (e.g. PROGRAMN glitch) */
    for (i = 0; i < 3; i++) okall &= fir_step(256, &fb);
    snprintf(o, sizeof o, "state=%s pwr_en=%d mux=%d mux_violations=%u all_exact=%d", svc_state_name(S.state), M.pwr_en, E.mux,
             E.mux_violations, okall);
    fit("E15", "fpga_lost_during_fir", "every block bit-exact (CPU); fault -> P1; PG to GPIO before power-down",
        okall && safe_off(), o);
}
