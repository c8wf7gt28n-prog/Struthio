/* ARC-1 Compact R8.5 -- F133 side of the ECP5 accelerator job protocol (AJOB/ARES v1).
 * Frame layouts: R85_WORK/fpga_ecp5/rtl/accel_engine.sv. The job payload is the R05 compute
 * contract v1 (48-byte job, 24-byte result, little endian). HOST_TESTED; cross-simulated
 * byte-for-byte against the RTL (fpga_ecp5/tb/tb_ecp5_top.sv). */
#ifndef ACCEL_JOB_H
#define ACCEL_JOB_H
#include <stddef.h>
#include <stdint.h>
#include "arc1_transform.h"

#define AJOB_HDR      16u
#define AJOB_JOB      48u
#define AJOB_RES      24u
#define AJOB_MAXCOUNT 170u
#define AJOB_OP_TRANSFORM 1u
#define AJOB_OP_FIR_SET_IR 2u          /* R8.5-C: count = 1024 int16 Q15 taps, response count 0 */
#define AJOB_OP_FIR_BLOCK  3u          /* R8.5-C: count = 1..1024 int16 samples, response count int16 outputs */
#define AJOB_FIR_TAPS   1024u
#define AJOB_FIR_HIST   2048u
#define AJOB_FIR_MAXBLK 1024u

enum ajob_status { AJOB_OK = 0, AJOB_BAD_LENGTH = 1, AJOB_BAD_VERSION = 2, AJOB_BAD_OPCODE = 3,
                   AJOB_PAYLOAD_CRC = 4, AJOB_ABORTED = 5, AJOB_BAD_STATE = 6,
                   /* host-side outcomes */
                   AJOB_HOST_BAD_MAGIC = 16, AJOB_HOST_SEQ = 17, AJOB_HOST_RESULT_CRC = 18,
                   AJOB_HOST_TRUNCATED = 19, AJOB_HOST_COUNT = 20, AJOB_HOST_ARGS = 21 };

/* build a request frame; returns its length or 0 if count is out of range */
size_t ajob_build(uint8_t *out, size_t cap, uint32_t seq, const arc1_transform_job *jobs, uint16_t count);
/* parse a response; returns AJOB_OK and fills results only if every check passes */
int ajob_parse(const uint8_t *resp, size_t len, uint32_t seq, uint16_t count, arc1_transform_result *results);
/* FPGA-resident FIR state, mirrored bit-exactly by the reference and by the host service */
typedef struct ajob_fir_state {
    int16_t ir[AJOB_FIR_TAPS];
    int16_t x[AJOB_FIR_HIST];
    uint16_t wp;
    int ir_valid;
} ajob_fir_state;
void ajob_fir_init(ajob_fir_state *f);
/* append n samples at wp, compute y[0..n-1] (y may be NULL), advance wp: the exact RTL arithmetic */
void ajob_fir_run(ajob_fir_state *f, const int16_t *in, uint16_t n, int16_t *y);
/* reference response the FPGA must produce (host test / cross-simulation); f may be NULL (no FIR state) */
size_t ajob_reference_response(uint8_t *out, size_t cap, const uint8_t *req, size_t req_len, ajob_fir_state *f);
/* FIR frames */
size_t ajob_build_fir_ir(uint8_t *out, size_t cap, uint32_t seq, const int16_t *taps);
size_t ajob_build_fir_block(uint8_t *out, size_t cap, uint32_t seq, const int16_t *in, uint16_t n);
int ajob_parse_fir(const uint8_t *resp, size_t len, uint32_t seq, uint8_t op, uint16_t n, int16_t *y);
#endif
