/* ARC-1 Compact R8.5-C -- behavioural model of the F133 EMAC + RGMII wires + the ECP5 eth_link.sv, for host tests.
 * The FPGA side shares the ecp5_mock state (configuration, DONE, power, resident FIR, counters), so SPI-mailbox and
 * Ethernet jobs see one engine, as in the RTL. Answers come from ajob_reference_response() (the reference the RTL
 * is compared against byte for byte in tb_ecp5_top). Virtual time: wire time at 1 Gb/s + an engine-time model.
 * MODEL ONLY: delay-chain windows and timings are planning values, not F133/ECP5 measurements. */
#ifndef EMAC_MOCK_H
#define EMAC_MOCK_H
#include "ecp5_mock.h"
#include "eth_link.h"

#define EMOCK_Q 6

typedef struct emac_mock {
    ecp5_mock *m;
    int mux;                                  /* PG0..PG12 in RGMII function */
    unsigned mux_violations;                  /* mux on while the ECP5 is unpowered or unconfigured, or a frame sent
                                                 with the mux off */
    /* delay chains: a direction works only inside its window [lo, hi] (planning model of the eye) */
    unsigned tx_step, rx_step, tx_lo, tx_hi, rx_lo, rx_hi;
    /* faults (counts of frames affected, decremented as used) */
    unsigned drop_req, drop_resp, stray_before_resp, dup_resp, link_down;
    int engine_hang;                          /* FPGA accepts the frame but never answers (until ABORT) */
    /* queue of frames delivered to the F133 */
    uint8_t q[EMOCK_Q][EL_MAX_FRAME];
    size_t qlen[EMOCK_Q];
    unsigned qn;
    uint64_t f133_rx_fcs_errors, frames_to_fpga, frames_from_fpga;
    uint8_t last_host_mac[6];
} emac_mock;

void emac_mock_init(emac_mock *e, ecp5_mock *m);
extern const arc1_eth_hal emac_mock_hal;      /* ctx = emac_mock * */
#endif
