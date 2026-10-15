/* ARC-1 Compact R8.5 -- host link cost of AJOB transform batches: the real F133 driver code (accel_service ->
 * fpga_link -> AJOB framing) against the board model at a given SPI0 clock, with engine time from the RTL
 * PERF counter fit. Output: one JSON line per batch size. MODEL: SPI bytes x 8 / f_sck + per-transaction overhead
 * (cs_overhead_ns, ASSUMPTION for the F133 driver), not a measurement on hardware.
 * Usage: bench_link SCK_HZ CS_OVERHEAD_NS */
#include "accel_service.h"
#include "crc32.h"
#include "ecp5_mock.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static ecp5_mock M;
static accel_service S;
static uint8_t bit[4096], file[4096 + ACFG_HDR];
static arc1_transform_job jobs[AJOB_MAXCOUNT];
static arc1_transform_result out[AJOB_MAXCOUNT], ref[AJOB_MAXCOUNT];

int main(int argc, char **argv)
{
    static const uint8_t head[] = { 0xFF, 0x00, 'x', 0x00, 0xFF, 0xFF, 0xFF, 0xBD, 0xB3, 0xE2, 0, 0, 0, 0x41, 0x11, 0x20, 0x43 };
    static const uint16_t sizes[] = { 1, 8, 32, 85, 170 };
    double sck = argc > 1 ? atof(argv[1]) : 10e6;
    unsigned ovh = argc > 2 ? (unsigned)atoi(argv[2]) : 2000u;
    ecp5_gpio_hal io = mock_gpio;
    arc1_spi_hal spi = mock_spi;
    size_t fl, i, k;
    memcpy(bit, head, sizeof head);
    for (i = sizeof head; i < sizeof bit; i++) bit[i] = (uint8_t)i;
    fl = ecp5_image_build(file, sizeof file, bit, sizeof bit, 3, 0, 0);
    mock_init(&M, arc1_crc32(0, bit, sizeof bit));
    io.ctx = &M; spi.ctx = &M;
    svc_init(&S, &io, &spi, 50000);
    if (svc_load(&S, file, fl, 0) != SVC_OK) { puts("{\"error\":\"load\"}"); return 1; }
    M.sck_hz = sck; M.cs_overhead_ns = ovh; M.engine_hz = 80000000u;
    for (i = 0; i < AJOB_MAXCOUNT; i++) {
        arc1_transform_job j = { (int32_t)i << 16, 0, ((int32_t)i + 16) << 16, 16 << 16, 46341, -46341, 0, 46341, 46341, 0, 320, 240, (uint32_t)i };
        jobs[i] = j;
        arc1_transform_rectangle(&jobs[i], &ref[i]);
    }
    for (k = 0; k < sizeof sizes / sizeof sizes[0]; k++) {
        uint16_t n = sizes[k];
        uint64_t t0 = M.t_us, b0 = M.spi_bytes;
        svc_fallback fb = svc_transform(&S, jobs, n, out);
        int ok = fb == SVC_FB_NONE && memcmp(out, ref, sizeof(arc1_transform_result) * n) == 0;
        printf("{\"kernel\":\"transform\",\"n\":%u,\"sck_hz\":%.0f,\"cs_overhead_ns\":%u,\"total_us\":%llu,\"spi_bytes\":%llu,"
               "\"engine_cycles\":%u,\"engine_us\":%.2f,\"fpga_used\":%d}\n", n, sck, ovh, (unsigned long long)(M.t_us - t0),
               (unsigned long long)(M.spi_bytes - b0), S.last_cycles, S.last_cycles / 80.0, ok);
    }
    return 0;
}
