/* Test doubles: byte-level BT820 QSPI-host slave and AMBX T35 mailbox.
 * Behaviour follows BT820 DS 4.5 and R06 mbx_regs.sv; mock-only choices are
 * marked. These are NOT device models for timing or electrical behaviour. */
#ifndef MOCKS_H
#define MOCKS_H
#include <stddef.h>
#include <stdint.h>

#include "arc1_hal.h"
#include "arc1_protocol.h"

/* ---------------- BT820 ---------------- */
#define MBT_RAM_BYTES (1u << 20)        /* mock window 0x0000_0000..0x000F_FFFF */
typedef struct mock_bt820 {
    uint8_t ram[MBT_RAM_BYTES];
    int cs;
    size_t nbytes;                      /* bytes in current CS# period */
    uint8_t hdr[5];
    int is_write, is_read;
    uint32_t addr;
    uint8_t wword[4];
    size_t wn;
    uint32_t poll_latency;              /* 0x00 bytes before 0x01 */
    int never_valid;
    int sent_valid;
    uint32_t rd_poll_left;
    size_t rd_pos;
    uint64_t now_us;
    uint32_t trace_hash;                /* FNV-1a over writes and host commands */
    uint64_t n_writes, n_reads, n_cmds, n_active, n_partial_words;
    uint8_t last_cmd[3];
    uint8_t last_hdr[4];
} mock_bt820;
void mbt_init(mock_bt820 *m);
arc1_spi_hal mbt_hal(mock_bt820 *m);

/* ---------------- T35 / AMBX ---------------- */
typedef enum {
    ENG_LOOPBACK = 0, ENG_SW_ACCEL, ENG_DROP, ENG_SLOW, ENG_CORRUPT_CRC,
    ENG_WRONG_TAG, ENG_APP_ERROR, ENG_RESET_ON_JOB, ENG_WRONG_VALUE, ENG_NO_DONE
} mt35_engine;
typedef struct mock_t35 {
    int present;
    mt35_engine engine;
    uint32_t latency_us;
    uint8_t req[8192], resp[8192];
    uint16_t req_len, resp_len;
    int job_pending, resp_ready, overrun;
    uint64_t ready_at_us;
    uint64_t absent_until_us;
    uint32_t doorbells;
    /* SPI byte machine */
    int cs; size_t nbytes; uint8_t cmd; uint16_t addr;
    uint64_t now_us;
    arc1_session session;
    uint64_t jobs_executed;
} mock_t35;
void mt35_init(mock_t35 *m, mt35_engine e);
arc1_spi_hal mt35_hal(mock_t35 *m);

#endif
