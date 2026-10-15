/* ARC-1 Compact R06 -- optional T35 offload of R05 rectangle transforms with
 * mandatory CPU fallback.
 *
 * Wire: R05 ARC1 frames (protocol/WIRE_ABI.md) carrying the R05 transform
 * payload v1 (integration/SCENE_PAYLOAD_V1.md), sent through the AMBX mailbox.
 * Every failure (disabled, absent, not ready, timeout, I/O, malformed or
 * mismatching response, session or application error) makes this batch run
 * on the CPU with the R05 C reference (compute/arc1_transform.c), and drops
 * the session so the next attempt starts a new, larger epoch (R05 rule).
 * The caller always receives results. HOST_TESTED with mocks only. */
#ifndef ACCEL_DISPATCH_H
#define ACCEL_DISPATCH_H
#include "arc1_transform.h"
#include "t35_link.h"

#define ACCEL_MAX_BATCH 85u   /* 8 + 85*48 = 4088 payload bytes (R05 SCENE_PAYLOAD_V1) */

typedef enum {
    ACCEL_FB_NONE = 0,        /* FPGA result used */
    ACCEL_FB_DISABLED,
    ACCEL_FB_NOT_READY,
    ACCEL_FB_TIMEOUT,
    ACCEL_FB_LINK,            /* I/O, busy, protocol at mailbox level */
    ACCEL_FB_FRAME,           /* response frames malformed / CRC / unexpected */
    ACCEL_FB_SESSION,         /* HELLO/JOB status not as required */
    ACCEL_FB_RESULT,          /* RESULT payload invalid or tags mismatch */
    ACCEL_FB_VERIFY,          /* debug verify found a numeric mismatch */
    ACCEL_FB_COUNT
} accel_fallback;

typedef struct accel_ctx {
    t35_link *link;           /* NULL = no FPGA fitted */
    int enabled;
    int verify;               /* bring-up only: recompute on CPU and compare */
    int session_ok;
    uint32_t epoch;
    uint32_t next_sequence;
    uint64_t fpga_batches;
    uint64_t cpu_batches;
    uint64_t reasons[ACCEL_FB_COUNT];
} accel_ctx;

void accel_init(accel_ctx *a, t35_link *link, int enabled);
/* n in 1..ACCEL_MAX_BATCH. Always fills out[0..n-1]; returns the reason the
 * CPU path was used (ACCEL_FB_NONE when the FPGA answer was accepted). */
accel_fallback accel_transform_batch(accel_ctx *a, const arc1_transform_job *jobs, size_t n,
                                     arc1_transform_result *out);
const char *accel_fallback_string(accel_fallback f);

/* R05 SCENE_PAYLOAD_V1 helpers (explicit little-endian, no struct copies). */
size_t accel_pack_jobs(const arc1_transform_job *jobs, size_t n, uint8_t *out, size_t cap);
int accel_unpack_results(const uint8_t *p, size_t len, size_t expect, arc1_transform_result *out);

#endif
