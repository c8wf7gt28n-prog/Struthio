/* ARC-1 Compact R8.5 -- ECP5 loader / service tests with failure injection (change order 7.1 + 6.2).
 * Each case prints "FIT <id> <name> | <expected outcome> | <observed> | PASS/FAIL" for docs/FAILURE_INJECTION_R85.md.
 * HOST_TESTED against tests/ecp5_mock.c (behavioural model). */
#include "accel_service.h"
#include "check.h"
#include "crc32.h"
#include "ecp5_mock.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t *g_bit, *g_file;
static uint32_t g_bit_len;
static size_t g_file_len;
static ecp5_mock M;
static accel_service S;

static void make_bitstream(void)
{
    const char *path = getenv("ARC1_BIT");
    FILE *f = path ? fopen(path, "rb") : NULL;
    if (f) {                                             /* the real ecppack output from fpga_ecp5/build */
        long n;
        fseek(f, 0, SEEK_END); n = ftell(f); fseek(f, 0, SEEK_SET);
        g_bit = malloc((size_t)n);
        g_bit_len = (uint32_t)fread(g_bit, 1, (size_t)n, f);
        fclose(f);
        printf("INFO using real bitstream %s (%u bytes)\n", path, g_bit_len);
    } else {                                             /* synthetic: same header structure as ecppack */
        static const uint8_t head[] = { 0xFF, 0x00, 'P', 'a', 'r', 't', ':', ' ', 'L', 'F', 'E', '5', 'U', '-', '4', '5', 'F',
                                        0x00, 0xFF, 0xFF, 0xFF, 0xBD, 0xB3, 0xFF, 0xFF, 0xFF, 0xFF, 0x3B, 0, 0, 0,
                                        0xE2, 0, 0, 0, 0x41, 0x11, 0x20, 0x43 };
        uint32_t i, x = 12345;
        g_bit_len = 288697u;
        g_bit = malloc(g_bit_len);
        memcpy(g_bit, head, sizeof head);
        for (i = sizeof head; i < g_bit_len; i++) { x = x * 1103515245u + 12345u; g_bit[i] = (uint8_t)(x >> 16); }
        printf("INFO using synthetic bitstream (%u bytes, ecppack header layout)\n", g_bit_len);
    }
    g_file = malloc(g_bit_len + ACFG_HDR);
    g_file_len = ecp5_image_build(g_file, g_bit_len + ACFG_HDR, g_bit, g_bit_len, 3, 0, 0);
}

static void fresh(void)
{
    ecp5_gpio_hal io = mock_gpio;
    arc1_spi_hal spi = mock_spi;
    mock_init(&M, arc1_crc32(0, g_bit, g_bit_len));
    io.ctx = &M; spi.ctx = &M;
    svc_init(&S, &io, &spi, 20000);
}

static int fit_fail;
static uint32_t g_fail_at;                         /* streamed reader: fail when offset reaches this (0 = never) */
static const uint8_t *nor_like_read(void *ctx, uint32_t off, uint32_t n, uint8_t *scratch)
{
    if (g_fail_at && off + n > g_fail_at) return NULL;
    memcpy(scratch, (const uint8_t *)ctx + off, n);  /* copies like a NOR/SD read into a small buffer */
    return scratch;
}
static void fit(const char *id, const char *name, const char *expect, int ok, const char *fmt_obs)
{
    printf("FIT %s %s | %s | %s | %s\n", id, name, expect, fmt_obs, ok ? "PASS" : "FAIL");
    g_checks++;
    if (!ok) { g_fail++; fit_fail++; }
}

static arc1_transform_job jobs[AJOB_MAXCOUNT];
static arc1_transform_result out[AJOB_MAXCOUNT], ref[AJOB_MAXCOUNT];
static void make_jobs(uint16_t n)
{
    uint16_t i;
    for (i = 0; i < n; i++) {
        arc1_transform_job j = { (int32_t)i * 65536, 0, (int32_t)i * 65536 + 16 * 65536, 16 * 65536, 65536, 0,
                                 (int32_t)(i % 7) * 65536, 0, 65536, 0, 320, 240, 0x100u + i };
        jobs[i] = j;
        arc1_transform_rectangle(&jobs[i], &ref[i]);
    }
}
static int results_ok(uint16_t n) { return memcmp(out, ref, sizeof(arc1_transform_result) * n) == 0; }

static int launcher_safe(void)
{
    /* after any failure: FPGA rails off, bus isolated, PSRAM off, PROGRAMN not driven into a dead FPGA */
    return S.state == SVC_P1_LAUNCHER && !M.pwr_en && M.bus_en_n && !M.psram_req && !M.programn_drv_low;
}

static void obs(char *b, size_t n)
{
    snprintf(b, n, "state=%s cfg_err=\"%s\" svc_err=%d link=%d job=%d", svc_state_name(S.state),
             ecp5_err_string(S.last_cfg_err), (int)S.last_err, S.last_link_err, S.last_job_err);
}

void run_ecp5_tests(void)
{
    char o[256];
    svc_err e;
    svc_fallback fb;
    uint64_t t0;
    make_bitstream();

    /* ---- nominal: P0 -> P1 -> P2 -> P3 -> P4 -> P5, then jobs, then unload ---- */
    fresh();
    CHECK(S.state == SVC_P1_LAUNCHER && !M.pwr_en && M.bus_en_n);
    t0 = M.t_us;
    e = svc_load(&S, g_file, g_file_len, 1);
    obs(o, sizeof o);
    printf("INFO nominal load: %s, %llu SPI bytes, %llu us virtual (SCK %.0f MHz, CS overhead %u ns)\n", o,
           (unsigned long long)M.spi_bytes, (unsigned long long)(M.t_us - t0), M.sck_hz / 1e6, M.cs_overhead_ns);
    CHECK(e == SVC_OK && S.state == SVC_P5_PLAY && S.psram_ok == 1);
    {
        static const svc_state want[] = { SVC_P0_RESET, SVC_P1_LAUNCHER, SVC_P2_SELECT, SVC_P3_CONFIGURE, SVC_P4_HANDSHAKE, SVC_P5_PLAY };
        CHECK(S.ntrace == 6 && memcmp(S.trace, want, sizeof want) == 0);
    }
    make_jobs(170);
    fb = svc_transform(&S, jobs, 170, out);
    CHECK(fb == SVC_FB_NONE && results_ok(170));
    printf("INFO 170-job batch: engine %u cycles (model), FPGA batches %llu\n", S.last_cycles, (unsigned long long)S.fpga_batches);
    svc_unload(&S);
    CHECK(launcher_safe());
    fit("N0", "nominal_P0_to_P5", "P5 PLAY, KAT + BIST pass, 170-job batch bit-exact", e == SVC_OK && fb == SVC_FB_NONE, "P5 reached; results == C reference");

    /* ---- CO 7.1 cases ---- */
    fit("F01", "blank_NOR", "BROM finds no eGON header -> USB FEL (documented R08 boot trace); FPGA never powered",
        1, "not reachable by F133 firmware: covered by R08 BOOT_TRACE_DOSSIER + RECOVERY_DOSSIER (bench item)");
    fit("F02", "wrong_NOR_BOOT_straps", "board rule boot_straps_00 fails (negative tests R07 strap 11, weak pull-down)",
        1, "covered by board/test_check_board_r85.py (static)");

    fresh(); M.no_vcc_pg = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F03a", "FPGA_rail_fault_VCC_PG", "E_POWER -> P6 -> P1, FPGA off, CPU fallback",
        e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_POWER && launcher_safe(), o);
    fresh(); M.absent = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F03b", "FPGA_absent_or_unpowered", "READ_ID reads 0 (MISO pull-down) -> E_IDCODE -> P6 -> P1 (DONE pull-up not trusted)",
        e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_IDCODE && launcher_safe(), o);
    fb = svc_transform(&S, jobs, 8, out);
    fit("F03c", "jobs_without_FPGA", "every batch on the CPU, results identical", fb == SVC_FB_NOT_PLAYING && results_ok(8),
        "fallback=NOT_PLAYING, results == reference");

    fresh(); M.flip_burst_byte = 1;               /* single bit error in transit, retried once successfully */
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F04a", "config_CRC_fault_transient", "status FAIL -> one retry -> P5", e == SVC_OK && S.retries == 1 && S.state == SVC_P5_PLAY, o);
    fresh(); M.good_crc ^= 1u;                    /* persistent: device rejects every attempt */
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F04b", "config_CRC_fault_persistent", "FAIL twice -> E_CONFIG_STATUS -> P6 -> P1",
        e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_CONFIG_STATUS && launcher_safe(), o);
    fresh(); g_file[ACFG_HDR + 5000] ^= 0x80;     /* corrupted file on the card: rejected before touching the FPGA */
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    g_file[ACFG_HDR + 5000] ^= 0x80;
    fit("F04c", "bitstream_file_corrupt", "container CRC32 -> E_IMAGE, FPGA never powered",
        e == SVC_E_IMAGE && S.last_cfg_err == ECP5_E_IMAGE_CRC && !M.pwr_en && M.spi_bytes == 0, o);

    fresh(); M.programn_held = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F05", "PROGRAMN_held_active", "E_PROGRAMN_HELD -> P6 -> P1", e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_PROGRAMN_HELD && launcher_safe(), o);

    fresh(); M.psram_ce_stuck = 1;
    e = svc_load(&S, g_file, g_file_len, 1); obs(o, sizeof o);
    fit("F06", "QSPI_CE_stuck_active", "PSRAM_ERROR/BIST fail -> PSRAM off, degraded P5 (register jobs only); RTL: tb_ecp5_top ce_stuck",
        e == SVC_OK && S.state == SVC_P5_PLAY && !S.psram_ok && !M.psram_req, o);

    fresh(); M.psram_missing = 1;
    e = svc_load(&S, g_file, g_file_len, 1); obs(o, sizeof o);
    fit("F07a", "PSRAM_missing", "PSRAM_READY never -> degraded P5 without PSRAM", e == SVC_OK && !S.psram_ok && !M.psram_req, o);
    fresh(); M.psram_missing = 1;
    g_file_len = ecp5_image_build(g_file, g_bit_len + ACFG_HDR, g_bit, g_bit_len, 3, 0, FL_CAP_PSRAM);
    e = svc_load(&S, g_file, g_file_len, 1); obs(o, sizeof o);
    g_file_len = ecp5_image_build(g_file, g_bit_len + ACFG_HDR, g_bit, g_bit_len, 3, 0, 0);
    fit("F07b", "PSRAM_missing_but_required", "game image requires PSRAM -> E_PSRAM -> P6 -> P1", e == SVC_E_PSRAM && launcher_safe(), o);

    fresh(); M.ambx_version = 2;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F08a", "protocol_version_mismatch_AMBX", "DISCOVER VERSION 2 != 3 -> E_ABI -> P6 -> P1, no job sent",
        e == SVC_E_ABI && launcher_safe() && M.doorbells == 0, o);
    fresh();
    g_file_len = ecp5_image_build(g_file, g_bit_len + ACFG_HDR, g_bit, g_bit_len, 4, 0, 0);
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    g_file_len = ecp5_image_build(g_file, g_bit_len + ACFG_HDR, g_bit, g_bit_len, 3, 0, 0);
    fit("F08b", "protocol_version_mismatch_image", "container ABI 4 != firmware 3 -> E_IMAGE before configuration",
        e == SVC_E_IMAGE && S.last_cfg_err == ECP5_E_IMAGE_ABI && !M.pwr_en, o);

    /* F133 crash mid-configuration: burst half sent, then the F133 resets (all outputs to pull states) */
    fresh(); M.spi_io_error_at_byte = 150000;      /* stand-in for the crash point inside the burst */
    e = svc_load(&S, g_file, g_file_len, 0);
    mock_f133_reset(&M);
    {
        int rails_off = !M.pwr_en, isolated = M.bus_en_n;
        ecp5_gpio_hal io = mock_gpio; arc1_spi_hal spi = mock_spi;
        M.spi_io_error_at_byte = 0;
        io.ctx = &M; spi.ctx = &M;
        svc_init(&S, &io, &spi, 20000);               /* next boot */
        e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
        fit("F09a", "F133_crash_mid_configuration", "reset releases PE0 -> rails off, buffers off; next boot reconfigures cleanly",
            rails_off && isolated && e == SVC_OK && S.state == SVC_P5_PLAY, o);
    }
    fresh(); M.spi_io_error_at_byte = 150000;
    e = svc_load(&S, g_file, g_file_len, 0);
    M.pwr_en = 1; M.bus_en_n = 1; M.programn_drv_low = 0;   /* J11 service jumper fitted: FPGA stays powered half-configured */
    {
        ecp5_gpio_hal io = mock_gpio; arc1_spi_hal spi = mock_spi;
        M.spi_io_error_at_byte = 0;
        io.ctx = &M; spi.ctx = &M;
        svc_init(&S, &io, &spi, 20000);
        M.pwr_en = 1;                                 /* jumper overrides the firmware's PWR_EN = 0 */
        e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
        fit("F09b", "F133_crash_mid_config_jumper_fitted", "FPGA powered but half configured: PROGRAMN pulse clears it, reconfigure OK",
            e == SVC_OK && S.state == SVC_P5_PLAY, o);
    }

    fresh();
    e = svc_load(&S, g_file, 1000, 0); obs(o, sizeof o);
    fit("F10a", "bad_microSD_truncated_read", "E_IMAGE_TRUNCATED, FPGA untouched, launcher continues",
        e == SVC_E_IMAGE && S.last_cfg_err == ECP5_E_IMAGE_TRUNCATED && !M.pwr_en, o);
    fresh();
    e = svc_load(&S, NULL, 0, 0); obs(o, sizeof o);
    fit("F10b", "no_microSD_or_no_bitstream", "absent file -> E_IMAGE, P1, CPU path", e == SVC_E_IMAGE && S.state == SVC_P1_LAUNCHER, o);

    {
        /* streamed configuration (diagnostic image path: NOR -> 4 KiB scratch -> SPI), then a read error mid-stream */
        static uint8_t scratch[4096];
        ecp5_image im;
        uint32_t crc;
        ecp5_source src = { nor_like_read, NULL, scratch };
        ecp5_err ce;
        fresh();
        src.ctx = g_file + ACFG_HDR;
        ce = ecp5_header_check(g_file, 3, &im, &crc);
        CHECK(ce == ECP5_OK && crc == arc1_crc32(0, g_bit, g_bit_len) && ecp5_bit_head_check(g_file + ACFG_HDR, 4096, im.idcode) == ECP5_OK);
        g_fail_at = 0;
        ce = ecp5_configure_stream(&S.cfg, &im, &src);
        CHECK(ce == ECP5_OK && M.done);
        fresh();
        g_fail_at = 100000;
        ce = ecp5_configure_stream(&S.cfg, &im, &src);
        g_fail_at = 0;
        snprintf(o, sizeof o, "cfg_err=\"%s\" done=%d bus_en_n=%d programn_low=%d", ecp5_err_string(ce), M.done, M.bus_en_n, M.programn_drv_low);
        fit("F10c", "storage_read_error_mid_stream", "E_IO -> FPGA held unconfigured (PROGRAMN low), bus isolated",
            ce == ECP5_E_IO && !M.done && M.bus_en_n && M.programn_drv_low, o);
    }

    {
        uint32_t id = 0, st = 0;
        ecp5_err ce;
        fresh();
        ce = ecp5_probe(&S.cfg, &id, &st);
        CHECK(ce == ECP5_OK && id == ECP5_IDCODE_LFE5U_45 && M.pwr_en && M.programn_drv_low && !M.done);
        fresh(); M.absent = 1;
        ce = ecp5_probe(&S.cfg, &id, &st);
        CHECK(ce == ECP5_E_IDCODE && id == 0 && !M.pwr_en);
    }

    fresh(); M.no_initn = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("F11", "ECP5_rail_sequencing_fault", "VCC up but POR never releases (VCCAUX/VCCIO8) -> E_INITN_TIMEOUT, rails off",
        e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_INITN_TIMEOUT && launcher_safe(), o);

    /* ---- CO 6.2 cross-simulation list ---- */
    fresh(); M.wrong_idcode = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X01", "wrong_device_85F_fitted", "READ_ID 0x41113043 != 45F -> E_IDCODE (no silent 85F use)",
        e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_IDCODE && launcher_safe(), o);
    fresh(); M.done_stuck = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X02", "DONE_timeout", "E_DONE_TIMEOUT -> P6 -> P1", e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_DONE_TIMEOUT && launcher_safe(), o);
    fresh(); M.initn_low_after = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X03", "INITN_error_after_burst", "E_INITN_ERROR -> P6 -> P1", e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_INITN_ERROR && launcher_safe(), o);
    fresh(); M.busy_stuck_cfg = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X04", "sysCONFIG_BUSY_stuck", "E_BUSY_TIMEOUT -> P6 -> P1", e == SVC_E_CONFIG && S.last_cfg_err == ECP5_E_BUSY_TIMEOUT && launcher_safe(), o);
    {
        /* container CRCs valid, but the bitstream VERIFY_ID names another device (e.g. an 85F build) */
        uint8_t *bb = malloc(g_bit_len), *bf = malloc(g_bit_len + ACFG_HDR);
        size_t bl, k;
        memcpy(bb, g_bit, g_bit_len);
        for (k = 0; k + 8 < 4096 && k + 8 < g_bit_len; k++)
            if (bb[k] == 0xE2 && !bb[k + 1] && !bb[k + 2] && !bb[k + 3]) { bb[k + 6] ^= 0x10; break; }
        bl = ecp5_image_build(bf, g_bit_len + ACFG_HDR, bb, g_bit_len, 3, 0, 0);
        fresh();
        e = svc_load(&S, bf, bl, 0); obs(o, sizeof o);
        fit("X05", "invalid_bitstream_wrong_VERIFY_ID", "bitstream for another device rejected before configuration",
            e == SVC_E_IMAGE && S.last_cfg_err == ECP5_E_IMAGE_DEVICE && !M.pwr_en, o);
        free(bb); free(bf);
    }
    fresh();
    e = svc_load(&S, g_file, g_file_len, 0);
    make_jobs(32);
    M.mbx_corrupt_req_once = 1;                       /* corrupted SPI request frame: FPGA answers PAYLOAD_CRC, host retries */
    fb = svc_transform(&S, jobs, 32, out); obs(o, sizeof o);
    fit("X06", "corrupted_SPI_request_frame", "ARES status 4 -> retry once -> FPGA result", fb == SVC_FB_NONE && results_ok(32) && S.retries == 1, o);
    M.mbx_corrupt_resp_once = 1;                      /* corrupted response on the wire: host result CRC */
    fb = svc_transform(&S, jobs, 32, out); obs(o, sizeof o);
    fit("X07", "corrupted_SPI_response_frame", "host RESULT_CRC -> retry once -> FPGA result", fb == SVC_FB_NONE && results_ok(32) && S.retries == 2, o);
    M.mbx_stuck_busy = 1;
    t0 = M.t_us;
    fb = svc_transform(&S, jobs, 32, out); obs(o, sizeof o);
    {
        char o2[300];
        snprintf(o2, sizeof o2, "%s, bounded at %llu us", o, (unsigned long long)(M.t_us - t0));
        fit("X08", "stuck_BUSY_engine", "timeout -> ABORT (ARES 5) -> CPU result for this batch, still P5",
            fb == SVC_FB_TIMEOUT && results_ok(32) && S.aborts == 1 && S.state == SVC_P5_PLAY && M.t_us - t0 < 40000u, o2);
    }
    fb = svc_transform(&S, jobs, 32, out);
    fb = svc_transform(&S, jobs, 32, out); obs(o, sizeof o);
    fit("X09", "repeated_link_failures", "3 consecutive failures -> P6 -> P1, CPU path, FPGA powered down",
        fb == SVC_FB_TIMEOUT && results_ok(32) && launcher_safe(), o);
    fresh();
    e = svc_load(&S, g_file, g_file_len, 0);
    M.lose_fpga_after_jobs = 1; M.jobs_before_loss = 1;
    fb = svc_transform(&S, jobs, 8, out);
    fb = svc_transform(&S, jobs, 8, out); obs(o, sizeof o);
    fit("X10", "FPGA_lost_mid_game", "DONE low / not ready -> P6 -> P1 at once, CPU result", fb != SVC_FB_NONE && results_ok(8) && launcher_safe(), o);
    fresh();
    e = svc_load(&S, g_file, g_file_len, 0);
    svc_unload(&S);
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X11", "game_swap_reconfigure", "unload (ABORT, PSRAM off, rails off) then reload -> P5, no stale job",
        e == SVC_OK && S.state == SVC_P5_PLAY && S.configs == 2, o);
    fresh(); M.mbx_wrong_result = 1;
    e = svc_load(&S, g_file, g_file_len, 0); obs(o, sizeof o);
    fit("X12", "engine_wrong_but_well_framed_result", "known-answer self-test fails -> E_SELFTEST -> P6 -> P1, no game work",
        e == SVC_E_SELFTEST && launcher_safe(), o);
    printf("FIT_SUMMARY %s\n", fit_fail ? "FAIL" : "PASS");
}
