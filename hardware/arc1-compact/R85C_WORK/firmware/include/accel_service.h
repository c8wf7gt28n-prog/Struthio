/* ARC-1 Compact R8.5 -- optional ECP5 accelerator service: change-order state machine P0..P6.
 *
 *  P0 reset      F133 boots from NOR; FPGA unpowered (PE0 pull-down), bus isolated (BUS_EN_N pull-up)
 *  P1 launcher   graphics/audio/USB run without the FPGA; FPGA off or held unconfigured
 *  P2 select     per-game container read from microSD and verified (CRC32, device IDCODE, ABI); PSRAM quiesced
 *  P3 configure  PROGRAMN pulse, INITN, sysCONFIG slave-SPI burst, status, DONE (ecp5_cfg.c)
 *  P4 handshake  DISCOVER (AMBX magic/version/caps) + known-answer AJOB + optional PSRAM power/BIST
 *  P5 play       AJOB batches; bounded timeout, CRC/sequence checks, ABORT, retry once, CPU fallback always
 *  P6 fault      PSRAM off, bus isolated, FPGA powered down; back to P1 (the game keeps running on the CPU)
 * The service never touches SPI1 (BT820) or the NOR chip select; every entry point returns in bounded time.
 * R8.5-C: optional RGMII job transport (eth_link.h). The SPI mailbox stays the configuration/control path and the
 * fallback transport. PG0..PG12 are switched to RGMII only after DONE + DISCOVER (CAPS b4) and back to GPIO inputs
 * before any FPGA power-down. Resident FIR (opcodes 2/3) with a host mirror: every block is also appended to the
 * mirror, so the CPU can take over at any time; after any uncertain FIR exchange the FPGA is re-primed (IR + the
 * last 1024 mirrored samples) before it is trusted again.
 * HOST_TESTED with tests/ecp5_mock.c (behavioural sysCONFIG + AMBX v3 mailbox) and tests/emac_mock.c. Not run on silicon. */
#ifndef ACCEL_SERVICE_H
#define ACCEL_SERVICE_H
#include "ecp5_cfg.h"
#include "fpga_link.h"
#include "accel_job.h"
#include "eth_link.h"

typedef enum { SVC_P0_RESET = 0, SVC_P1_LAUNCHER, SVC_P2_SELECT, SVC_P3_CONFIGURE, SVC_P4_HANDSHAKE, SVC_P5_PLAY,
               SVC_P6_FAULT } svc_state;

typedef enum {
    SVC_OK = 0, SVC_E_IMAGE, SVC_E_CONFIG, SVC_E_DISCOVER, SVC_E_ABI, SVC_E_CAPS, SVC_E_SELFTEST, SVC_E_PSRAM,
    SVC_E_LINK, SVC_E_STATE
} svc_err;

typedef enum {                       /* why a batch ran on the CPU */
    SVC_FB_NONE = 0, SVC_FB_NOT_PLAYING, SVC_FB_LINK, SVC_FB_TIMEOUT, SVC_FB_FRAME, SVC_FB_COUNT_ARG,
    SVC_FB_NO_IR,                    /* R8.5-C: FIR block before any FIR_SET_IR (outputs are zero) */
    SVC_FB_N
} svc_fallback;

#define SVC_TRACE 64
#define SVC_REQ_CAP (AJOB_HDR + AJOB_MAXCOUNT * AJOB_JOB)

typedef enum { SVC_TR_SPI = 0, SVC_TR_ETH = 1 } svc_transport;

typedef struct accel_service {
    ecp5_cfg cfg;
    fpga_link link;
    svc_state state;
    svc_state trace[SVC_TRACE];
    unsigned ntrace;
    ecp5_err last_cfg_err;
    int last_link_err, last_job_err;
    svc_err last_err;
    uint16_t version, caps;
    uint32_t caps_required;
    int psram_ok;
    uint32_t seq;
    unsigned consecutive_errors, max_consecutive_errors;
    uint64_t fpga_batches, cpu_batches, retries, aborts, faults, configs;
    uint64_t fallback[SVC_FB_N];
    uint32_t last_cycles;
    uint8_t req[SVC_REQ_CAP];
    uint8_t resp[AJOB_HDR + AJOB_MAXCOUNT * AJOB_RES];
    /* R8.5-C RGMII transport */
    eth_link eth;
    int eth_attached, mux_on;
    svc_transport transport;
    uint64_t eth_kat_failures;
    /* R8.5-C resident FIR: host mirror + FPGA synchronisation state */
    ajob_fir_state fir;
    int fir_sync;                    /* FPGA history and IR known to equal the mirror */
    uint64_t fir_fpga_blocks, fir_cpu_blocks, fir_resyncs;
} accel_service;

/* P0 -> P1: drive every FPGA control line to its safe level (FPGA off, buffers off) */
void svc_init(accel_service *s, const ecp5_gpio_hal *io, const arc1_spi_hal *spi, uint32_t job_timeout_us);
/* P2..P4 -> P5 on success; on any error P6 -> P1 and the error is returned (caller keeps the CPU path) */
svc_err svc_load(accel_service *s, const uint8_t *file, size_t len, int run_bist);
/* any state: always fills out[0..n-1]; returns SVC_FB_NONE if the FPGA result was used */
svc_fallback svc_transform(accel_service *s, const arc1_transform_job *jobs, uint16_t n, arc1_transform_result *out);
/* game exit / swap: quiesce, power the FPGA down, P1 */
void svc_unload(accel_service *s);
/* R8.5-C: attach the EMAC (before svc_load); PG0..PG12 are set to GPIO inputs at once */
void svc_attach_eth(accel_service *s, const arc1_eth_hal *eth, const uint8_t host_mac[6], uint32_t timeout_us);
/* R8.5-C resident FIR: always takes effect in the mirror; returns SVC_FB_NONE if the FPGA also has it */
svc_fallback svc_fir_set_ir(accel_service *s, const int16_t taps[AJOB_FIR_TAPS]);
/* always fills out[0..n-1] (n 1..1024), bit-exact with the RTL whichever side computes it */
svc_fallback svc_fir_block(accel_service *s, const int16_t *in, uint16_t n, int16_t *out);
const char *svc_state_name(svc_state st);
#endif
