/* ARC-1 R10 -- end-to-end host test of the 45F configuration path (ARC1_MEMORY_R10 s3.1, gate "FPGA configuration"):
 * F133 NOR mock (r10_boot) -> USB bulk pipe mock with faults (gfx_link host) -> D213 gl_dev -> d213_fpga45 ->
 * R8.5-C ECP5 sysCONFIG mock (IDCODE LFE5U-45). HOST_TESTED; no USB stack, no silicon. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "r10_boot.h"
#include "gfx_link.h"
#include "d213_fpga45.h"
#include "crc32.h"
#include "nor_mock.h"
#include "ecp5_mock.h"

int g_fail, g_checks;
#define CHECK(c) do { g_checks++; if (!(c)) { g_fail++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #c); } } while (0)

/* ---- F133 side ---- */
static nor_mock nm; static arc1_spi_hal nh; static nor_dev nd; static r10_boot B;
/* ---- D213 side ---- */
static gl_dev D; static d213_fpga45 L; static ecp5_mock M; static uint8_t *dstage;
static uint32_t boot_no;
/* ---- pipe ---- */
static uint8_t q[4][GL_HDR + GL_RSP_LEN]; static size_t qn[4]; static unsigned qh, qt;
static unsigned drop_in, corrupt_out, dead, reset_at_out, outs, drop_at;
static uint8_t scratch[GL_MAX_PKT];

static void d213_boot(void)
{
    ecp5_gpio_hal io = mock_gpio;
    arc1_spi_hal spi = mock_spi;
    gl_dev_init(&D, 0xD2130000u + ++boot_no, GL_CAP_2D | GL_CAP_3D);
    io.ctx = &M; spi.ctx = &M;
    d213_fpga45_init(&L, &io, &spi, 3);
    D.ctx = &L; D.fpga_load = d213_fpga45_load; D.fpga_buf = dstage; D.fpga_cap = 3u << 20;
}
static int p_out(void *ctx, const uint8_t *buf, size_t len, uint32_t to)
{
    uint8_t rsp[GL_HDR + GL_RSP_LEN];
    size_t r;
    (void)ctx; (void)to;
    outs++;
    if (dead) return 0;
    if (reset_at_out && --reset_at_out == 0) d213_boot();
    memcpy(scratch, buf, len);
    if (corrupt_out) { corrupt_out--; scratch[len / 2] ^= 0x20; }
    r = gl_dev_rx(&D, scratch, len, rsp, sizeof rsp, 0);
    if (!r) return 0;
    if (drop_in) { drop_in--; return 0; }
    if (drop_at && outs == drop_at) return 0;
    if (qt - qh < 4) { memcpy(q[qt % 4], rsp, r); qn[qt % 4] = r; qt++; }
    return 0;
}
static int p_in(void *ctx, uint8_t *buf, size_t cap, size_t *len, uint32_t to)
{
    (void)ctx; (void)to;
    if (qh == qt) return 1;
    if (qn[qh % 4] > cap) return -1;
    memcpy(buf, q[qh % 4], qn[qh % 4]); *len = qn[qh % 4]; qh++;
    return 0;
}
static gl_host H;
static int mem_rd(void *ctx, uint32_t off, uint8_t *buf, uint32_t n) { memcpy(buf, (const uint8_t *)ctx + off, n); return 0; }

static uint8_t *make_fpga(uint32_t idcode, uint32_t bit_len, uint32_t seed, uint32_t *total, uint32_t *bit_crc)
{
    uint8_t head[] = { 0xFF, 0x00, 'P', 'a', 'r', 't', 0x00, 0xFF, 0xFF, 0xFF, 0xBD, 0xB3, 0xFF, 0xFF, 0xFF, 0xFF, 0x3B, 0, 0, 0,
                       0xE2, 0, 0, 0, 0, 0, 0, 0 };
    uint8_t *bit = malloc(bit_len), *f = malloc(bit_len + ACFG_HDR);
    uint32_t i, x = seed;
    head[24] = (uint8_t)(idcode >> 24); head[25] = (uint8_t)(idcode >> 16); head[26] = (uint8_t)(idcode >> 8); head[27] = (uint8_t)idcode;
    memcpy(bit, head, sizeof head);
    for (i = sizeof head; i < bit_len; i++) { x = x * 1103515245u + 12345u; bit[i] = (uint8_t)(x >> 16); }
    *bit_crc = arc1_crc32(0, bit, bit_len);
    *total = (uint32_t)ecp5_image_build_id(f, bit_len + ACFG_HDR, bit, bit_len, 3, 0, 0, idcode);
    free(bit);
    return f;
}
static void raw_write(uint32_t a, const uint8_t *p, uint32_t n) { CHECK(nor_write_verified(&nd, a, p, n) == NOR_OK); }
static void raw_flip(uint32_t a)
{
    uint8_t sec[4096];
    uint32_t s = a & ~0xFFFu;
    CHECK(nor_read(&nd, s, sec, sizeof sec) == NOR_OK);
    sec[a - s] ^= 0x01;
    raw_write(s, sec, sizeof sec);
}
static void fresh(uint32_t good_crc)
{
    gl_hal hal = { NULL, p_out, p_in };
    mock_init(&M, good_crc);                                   /* idcode LFE5U-45 */
    d213_boot();
    qh = qt = 0; drop_in = corrupt_out = dead = reset_at_out = drop_at = 0;
    gl_host_init(&H, &hal, 2000, 3, 4);
    CHECK(gl_hello(&H) == GL_OK);
}
static r10_manifest mf(void) { r10_manifest x; r10_manifest_load(&B, &x, NULL); return x; }

int main(void)
{
    uint32_t na, ng, nx, crc_a, crc_g, crc_x;
    uint8_t *app, *gold, *x12, st;
    uint16_t det;
    enum r10_slot used;
    dstage = malloc(3u << 20);
    nor_mock_init(&nm, R10_NOR_SIZE, 0xEF, 0x40, 0x20); nor_mock_hal(&nm, &nh);
    CHECK(nor_init(&nd, &nh) == NOR_OK);
    B.nor = &nd; B.stage = NULL; B.stage_cap = 0; B.fpga_abi = 3;
    app  = make_fpga(ECP5_IDCODE_LFE5U_45, 1055505, 1, &na, &crc_a);       /* the measured 45F size */
    gold = make_fpga(ECP5_IDCODE_LFE5U_45, 299891, 2, &ng, &crc_g);
    x12  = make_fpga(R10_IDCODE_LFE5U_12, 600913, 3, &nx, &crc_x);
    raw_write(r10_parts[R10P_C45A].base, app, na);
    raw_write(r10_parts[R10P_C45G].base, gold, ng);

    /* P01 application image configured through the D213 */
    fresh(crc_a);
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_0 && st == GL_S_OK);
    CHECK(M.done && L.loads_ok == 1 && D.fpga_loads == 1);
    printf("INFO 45F app %u bytes in %u USB transfers\n", na, outs);
    printf("TEST p45_app done fails=%d\n", g_fail);

    /* P02 lost reply to the LAST chunk: retried, replayed from the device cache, configured exactly once */
    fresh(crc_a);
    outs = 0; drop_at = (na + GL_CHUNK - 1) / GL_CHUNK;           /* transfer number of the final chunk */
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_0 && st == GL_S_OK);
    CHECK(H.retries >= 1 && D.replays >= 1 && D.fpga_loads == 1 && L.loads_ok == 1);
    drop_at = 0;
    printf("TEST p45_retry_last done fails=%d\n", g_fail);

    /* P03 corrupt application on the NOR: the F133 sends golden and marks the application bad */
    raw_flip(r10_parts[R10P_C45A].base + ACFG_HDR + 77777);
    fresh(crc_g);
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_1 && M.done);
    CHECK(mf().c[R10C_C45].bad_mask & 1u);
    raw_write(r10_parts[R10P_C45A].base, app, na);              /* repaired (an update would clear the mark) */
    {
        r10_manifest x = mf(); x.c[R10C_C45].bad_mask = 0; CHECK(r10_manifest_store(&B, &x) == R10_OK);
    }
    printf("TEST p45_corrupt_nor done fails=%d\n", g_fail);

    /* P04 the 45F rejects the application during configuration -> golden */
    fresh(crc_g);
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_1 && L.cfg_bad == 1 && L.loads_ok == 1);
    CHECK(!(mf().c[R10C_C45].bad_mask & 1u));                   /* device-side failure: no persistent mark */
    printf("TEST p45_cfg_fail done fails=%d\n", g_fail);

    /* P05 USB corruption in transit: caught by the packet CRC, resent, configured once */
    fresh(crc_a);
    corrupt_out = 2;                                            /* two bad copies of one packet: third attempt OK */
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_0 && D.fpga_loads == 1 && D.bad == 2);
    fresh(crc_a);
    corrupt_out = 3;                                            /* all 3 attempts damaged: reported, not configured */
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_E_LINK && used == R10S_NONE && !M.done);
    printf("TEST p45_usb_crc done fails=%d\n", g_fail);

    /* P06 D213 restarts mid-stream: HELLO, restart from offset 0, configured once */
    fresh(crc_a);
    reset_at_out = 30;
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_0 && H.resyncs >= 1 && L.loads_ok == 1);
    printf("TEST p45_d213_restart done fails=%d\n", g_fail);

    /* P07 link dead: reported as LINK, nothing configured, the F133 continues */
    fresh(crc_a);
    dead = 1;
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_E_LINK && used == R10S_NONE && !M.done);
    printf("TEST p45_link_dead done fails=%d\n", g_fail);

    /* P08 a 12F image: rejected by the D213 when sent directly; caught on the F133 when it sits in C45A */
    fresh(crc_x);
    CHECK(gl_send_fpga(&H, nx, mem_rd, x12, &st, &det) == GL_OK && st == GL_S_FPGA_IMAGE && det == ECP5_E_IMAGE_DEVICE);
    CHECK(!M.done && L.image_bad == 1 && M.spi_bytes == 0);
    raw_write(r10_parts[R10P_C45A].base, x12, nx);
    fresh(crc_g);
    CHECK(r10_boot_fpga45(&B, &H, &used, &st, &det) == R10_OK && used == R10S_1 && (mf().c[R10C_C45].bad_mask & 1u));
    CHECK(L.image_bad == 0);                                    /* never sent: checked on the F133 first */
    printf("TEST p45_wrong_device done fails=%d\n", g_fail);
    free(app); free(gold); free(x12);
    printf("%d checks, %d failed\n", g_checks, g_fail);
    printf(g_fail ? "R10_FPGA45_PATH_FAIL\n" : "R10_FPGA45_PATH_PASS\n");
    return g_fail != 0;
}
