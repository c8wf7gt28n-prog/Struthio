/* ARC-1 Compact R8.5-C -- F133 side of the RGMII job link to the ECP5 (raw Ethernet frames, no PHY, no IP).
 * Frame: dst | src | EtherType 0x88B5 | len16 LE | AJOB request or ARES response | pad (EMAC adds the FCS).
 * FPGA side: fpga_ecp5/rtl/eth_link.sv (source MAC 02:A1:C1:00:00:01; replies to the requester's MAC).
 * The FPGA accepts one frame at a time; a frame arriving while it is busy is dropped (and counted there), so the
 * host sends one request and waits for its response. Responses are matched by ARES sequence number; anything else
 * (stale responses after a timeout, other EtherTypes, other sources) is discarded and counted.
 * HOST_TESTED with tests/emac_mock.c. Not run on silicon. */
#ifndef ETH_LINK_H
#define ETH_LINK_H
#include <stddef.h>
#include <stdint.h>

#define EL_ETHERTYPE   0x88B5u
#define EL_HDR         16u                  /* dst 6 + src 6 + type 2 + len16 2 */
#define EL_MIN_FRAME   60u                  /* without FCS */
#define EL_MAX_PAYLOAD 8192u                /* FPGA RX/TX buffer; the F133 EMAC supports jumbo frames (DS 2.10.3) */
#define EL_MAX_FRAME   (EL_HDR + EL_MAX_PAYLOAD)

typedef struct arc1_eth_hal {
    void *ctx;
    /* queue one frame for transmission (no FCS; the EMAC appends it). 0 = queued */
    int (*send)(void *ctx, const uint8_t *frame, size_t len);
    /* 0 = one frame copied to buf (*len set); 1 = nothing pending; < 0 = error. Frames with a bad FCS are never
     * delivered (the EMAC drops them). Never blocks. */
    int (*recv)(void *ctx, uint8_t *buf, size_t cap, size_t *len);
    /* PG0..PG12 pin function: 0 = IO Disable (0xF, the reset state), 1 = RGMII (function 4, D1-H UM PG_CFG0/1).
     * 1 only while the ECP5 is configured. */
    void (*set_mux)(void *ctx, int rgmii);
    /* EMAC delay chains, D1-H UM 3.4.3.3 EMAC_EPHY_CLK_REG0: ETXDC [12:10] (0..7), ERXDC [9:5] (0..31);
     * the delay per step is not given in the UM or the F133 DS */
    void (*set_delay)(void *ctx, unsigned tx_step, unsigned rx_step);
    uint64_t (*now_us)(void *ctx);
} arc1_eth_hal;

enum el_error { EL_OK = 0, EL_TIMEOUT = 3, EL_IO = 4, EL_PROTOCOL = 5, EL_ARG = 6 };

typedef struct eth_link {
    arc1_eth_hal hal;
    uint8_t host_mac[6];
    uint32_t timeout_us;
    uint64_t sent, received, stray, timeouts;
    uint8_t frame[EL_MAX_FRAME];
} eth_link;

extern const uint8_t el_fpga_mac[6];

void el_init(eth_link *l, const arc1_eth_hal *hal, const uint8_t host_mac[6], uint32_t timeout_us);
/* build a frame around payload[0..n-1] into out (padded to 60 bytes); returns its length or 0 */
size_t el_build(uint8_t *out, size_t cap, const uint8_t dst[6], const uint8_t src[6], const uint8_t *payload, size_t n);
/* parse: returns the payload length (len16) and sets *payload, or -1 if the frame is not a valid link frame from
 * src to dst */
long el_parse(const uint8_t *frame, size_t len, const uint8_t dst[6], const uint8_t src[6], const uint8_t **payload);
/* one exchange: send req, wait for the response. AJOB requests are matched by sequence number (ARES magic + seq);
 * other payloads (legacy loopback) by the first valid frame. */
int el_exchange(eth_link *l, const uint8_t *req, size_t req_len, uint8_t *resp, size_t cap, size_t *resp_len);
/* delay-chain calibration: for each rx step (tx fixed at tx_step) send `frames` loopback frames; choose the centre
 * of the longest error-free run of rx steps (if none passes, the next tx steps are tried in turn), then the same
 * for tx at the chosen rx. Returns 0 and the chosen steps, or -1 if no
 * setting passes. win_rx/win_tx (may be NULL) receive the widths of the chosen windows. */
int el_calibrate(eth_link *l, unsigned steps_tx, unsigned steps_rx, unsigned frames, unsigned *tx_step, unsigned *rx_step,
                 unsigned *win_tx, unsigned *win_rx);
#endif
