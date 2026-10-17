/* ARC-1 R10 -- F133 <-> D213 graphics command link (R10 12.1 item 7), carried over USB 2.0 bulk endpoints:
 * F133 USB1 host -> D213 USB0 device (R10 5.1 "preferred investigation"; pads in architecture/R10_interface_matrix.csv).
 * The link carries per-frame command lists (game state -> D213 2D/3D renderer), not pixels.
 *
 * Packet (both directions): 16-byte header + payload
 *   0 magic "GCMD" (host->device) or "GRSP" (device->host) | 4 version 1 | 5 type | 6 payload length (u16 LE) |
 *   8 seq (u32 LE) | 12 CRC-32 (IEEE, over header bytes 0..11 then the payload)
 *   types: 1 HELLO, 2 FRAME, 3 PING, 4 FPGA_IMAGE
 *   FPGA_IMAGE request payload: offset u32 | total u32 | data (<= GL_CHUNK): the 45F bitstream container (ACFG) from the
 *                     F133 NOR, chunks strictly in order (offset 0 restarts). When `total` bytes have arrived the
 *                     device calls fpga_load() (D213: validate + configure the 45F over slave SPI) and answers that
 *                     chunk with its result; the repeated-seq rule means a retried last chunk never configures twice.
 *   FRAME request payload: frame_no u32 | chunk u16 | nchunks u16 | command bytes (<= GL_CHUNK)
 *   every response payload: status u8 | type echo u8 | detail u16 (FPGA_IMAGE: ecp5_err) | last completed frame u32 | device boot id u32 |
 *                           caps u32 (HELLO: GL_CAP_*; else 0)
 * Rules: one request outstanding; the host retries the SAME seq on timeout or a corrupt/BAD_CRC response; the device
 * answers a repeated seq from its cached response without executing again; a changed boot id means the device
 * restarted: the host re-sends HELLO and restarts the current frame from chunk 0. After `max_fail` consecutive failed
 * exchanges the link is DOWN: frames are dropped (GL_FALLBACK) and HELLO is retried every `reprobe` submits.
 * HOST_TESTED (tests/usb_mock.c fault injection). No USB stack, no silicon. */
#ifndef GFX_LINK_H
#define GFX_LINK_H
#include <stddef.h>
#include <stdint.h>

#define GL_VERSION   1u
#define GL_HDR       16u
#define GL_FRAME_HDR 8u
#define GL_CHUNK     16384u                         /* command bytes per FRAME packet (32 x 512-byte HS packets) */
#define GL_MAX_PKT   (GL_HDR + GL_FRAME_HDR + GL_CHUNK)
#define GL_RSP_LEN   16u
#define GL_MAX_FRAME (64u * GL_CHUNK)               /* device assembly buffer per frame */

enum gl_type   { GL_T_HELLO = 1, GL_T_FRAME = 2, GL_T_PING = 3, GL_T_FPGA = 4 };
enum gl_status { GL_S_OK = 0, GL_S_BAD_CRC = 1, GL_S_BAD_VERSION = 2, GL_S_BAD_TYPE = 3, GL_S_ORDER = 4,
                 GL_S_TOO_BIG = 5, GL_S_FPGA_IMAGE = 6, GL_S_FPGA_CFG = 7, GL_S_FPGA_NOBUF = 8 };
enum gl_result { GL_OK = 0, GL_FALLBACK = 1, GL_TIMEOUT = 3, GL_IO = 4, GL_PROTOCOL = 5, GL_ARG = 6 };
#define GL_CAP_2D    0x1u
#define GL_CAP_3D    0x2u                           /* 45F rasterizer reachable from the D213 */

typedef struct gl_hal {
    void *ctx;
    /* bulk OUT transfer of len bytes (ZLP handling is the USB stack's). 0 = sent, < 0 = error */
    int (*bulk_out)(void *ctx, const uint8_t *buf, size_t len, uint32_t timeout_us);
    /* bulk IN: 0 = one transfer received (*len set), 1 = timeout, < 0 = error */
    int (*bulk_in)(void *ctx, uint8_t *buf, size_t cap, size_t *len, uint32_t timeout_us);
} gl_hal;

typedef struct gl_host {
    gl_hal hal;
    uint32_t timeout_us;
    unsigned max_fail, reprobe;
    uint32_t seq, boot_id, caps, dev_last_frame;
    int up;                                         /* HELLO answered and fewer than max_fail failures since */
    unsigned fails, since_probe;
    uint64_t exchanges, retries, stray, corrupt, resyncs, dropped_frames;
    uint8_t tx[GL_MAX_PKT], rx[GL_MAX_PKT], pl[GL_FRAME_HDR + GL_CHUNK];
} gl_host;

uint32_t gl_crc32(uint32_t crc, const uint8_t *p, size_t n);  /* IEEE, crc = 0 to start */
/* build a packet into out; returns its length or 0 if it does not fit */
size_t gl_build(uint8_t *out, size_t cap, const char magic[4], uint8_t type, uint32_t seq, const uint8_t *pl, size_t n);
/* validate a packet; returns the payload length and sets *pl, or -1 (bad magic/length/CRC). *version gets byte 4. */
long gl_parse(const uint8_t *pkt, size_t len, const char magic[4], uint8_t *type, uint32_t *seq, uint8_t *version,
              const uint8_t **pl);

void gl_host_init(gl_host *h, const gl_hal *hal, uint32_t timeout_us, unsigned max_fail, unsigned reprobe);
int  gl_hello(gl_host *h);
/* send one frame's command list (len may be 0). GL_OK = executed by the device; GL_FALLBACK = link down, frame
 * dropped (the caller keeps running game logic and audio); other values only from argument errors. */
int  gl_submit_frame(gl_host *h, uint32_t frame_no, const uint8_t *cmds, size_t len);
/* send a 45F container of `total` bytes, read through read(ctx, off, buf, n) (the F133 NOR). GL_OK = transfer done
 * and *status / *detail hold the device's result (GL_S_OK = configured); GL_FALLBACK = link down; GL_IO = read error */
typedef int (*gl_read_fn)(void *ctx, uint32_t off, uint8_t *buf, uint32_t n);
int  gl_send_fpga(gl_host *h, uint32_t total, gl_read_fn read, void *ctx, uint8_t *status, uint16_t *detail);

/* ---- D213 side (device), transport-independent: one request in, one response out ---- */
typedef struct gl_dev {
    uint32_t boot_id, caps;
    uint32_t last_seq; int have_last;
    uint8_t last_rsp[GL_HDR + GL_RSP_LEN]; size_t last_rsp_len;
    uint32_t cur_frame, next_chunk, nchunks, last_frame; size_t asm_len;
    uint64_t executed, replays, bad, last_ok_us; int lost_signalled;
    void (*execute)(void *ctx, uint32_t frame_no, const uint8_t *cmds, size_t len);
    void (*link_lost)(void *ctx);                   /* show the D213's own 2D fallback screen */
    /* FPGA_IMAGE: staging buffer in D213 DDR3 and the loader; returns a GL_S_* status, *detail = loader error */
    uint8_t *fpga_buf; uint32_t fpga_cap, fpga_rx, fpga_total;
    uint8_t (*fpga_load)(void *ctx, const uint8_t *img, uint32_t len, uint16_t *detail);
    uint64_t fpga_loads; uint16_t detail;
    void *ctx;
    uint8_t asm_buf[GL_MAX_FRAME];
} gl_dev;

void   gl_dev_init(gl_dev *d, uint32_t boot_id, uint32_t caps);
/* handle one received OUT transfer; writes the response into rsp and returns its length (0 = no response: the packet
 * was not addressed to this protocol) */
size_t gl_dev_rx(gl_dev *d, const uint8_t *pkt, size_t len, uint8_t *rsp, size_t cap, uint64_t now_us);
/* watchdog: if no frame completed for watchdog_us after the first one, call link_lost once */
void   gl_dev_tick(gl_dev *d, uint64_t now_us, uint64_t watchdog_us);
#endif
