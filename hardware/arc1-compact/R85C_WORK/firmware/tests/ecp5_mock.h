/* ARC-1 Compact R8.5 -- behavioural model of the board around the ECP5 for host tests:
 * FPGA rails + VCC_PG, POR/INITN, PROGRAMN, sysCONFIG slave-SPI command decoder and burst checker, DONE,
 * and in user mode (DONE high) the AMBX v3 mailbox whose AJOB answers come from ajob_reference_response()
 * (the same reference the RTL is compared against byte for byte in tb_ecp5_top). Virtual time.
 * MODEL ONLY: timing constants are planning values, not ECP5 measurements. */
#ifndef ECP5_MOCK_H
#define ECP5_MOCK_H
#include "ecp5_cfg.h"
#include "fpga_link.h"
#include "accel_job.h"

typedef struct ecp5_mock {
    /* faults */
    int no_vcc_pg, no_initn, programn_held, absent, wrong_idcode, flip_burst_byte, busy_stuck_cfg, done_stuck,
        initn_low_after, ambx_version, mbx_stuck_busy, mbx_corrupt_req_once, mbx_corrupt_resp_once, psram_missing,
        psram_ce_stuck, bist_fail, mbx_wrong_result, lose_fpga_after_jobs, spi_io_error_at_byte;
    long jobs_before_loss;
    /* board state */
    int pwr_en, bus_en_n, programn_drv_low, psram_req, ss;
    uint64_t t_us, t_pwr_on, t_programn_release;
    double sck_hz;                 /* virtual SPI0 clock for time accounting */
    uint32_t cs_overhead_ns;       /* per-transaction driver/CS overhead */
    uint32_t engine_hz;            /* if set, doorbell -> RESP_READY takes perf_cycles/engine_hz (RTL-measured cycles) */
    uint64_t engine_busy_until;
    /* sysCONFIG */
    int configured, isc_enabled, burst, cfg_fail, done, initn_fault;
    uint32_t good_crc, burst_crc, burst_len, idcode;
    uint8_t burst_head[256];
    uint64_t spi_bytes;
    /* transaction decode */
    uint8_t hdr[4];
    unsigned hn;
    int op;
    uint8_t rxq[8];
    unsigned rxn, rxi;
    uint32_t addr;
    /* mailbox */
    uint8_t req[8192], resp[8192];
    uint16_t req_len, resp_len, status;
    int resp_ready, job_pending, psram_ready, bist_state;
    uint32_t perf_cycles, perf_jobs, doorbells;
    long jobs_done;
    int mbx_write;
    ajob_fir_state fir;            /* FPGA-resident FIR state (zero after configuration) */
} ecp5_mock;

void mock_init(ecp5_mock *m, uint32_t good_bit_crc);
void mock_f133_reset(ecp5_mock *m);            /* F133 crash/reset: every F133 output released to its pull state */
extern const ecp5_gpio_hal mock_gpio;
extern const arc1_spi_hal mock_spi;
#endif
