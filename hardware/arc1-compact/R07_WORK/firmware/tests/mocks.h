/* Test doubles: byte-level BT820 QSPI-host slave and AMBX T35 mailbox.
 * Behaviour follows BT820 DS 4.5 and R06 mbx_regs.sv; mock-only choices are
 * marked. These are NOT device models for timing or electrical behaviour. */
#ifndef MOCKS_H
#define MOCKS_H
#include <stddef.h>
#include <stdint.h>

#include "arc1_hal.h"
#include "arc1_protocol.h"

/* ---------------- BT820 (R07: memory map, power state, coprocessor) ---------------- */
#define MBT_RAM_BYTES (1u << 20)        /* mock RAM_G window 0x0000_0000..0x000F_FFFF */
#define MBT_TX_MAX    (20000u)
#define MBT_LOG_MAX   64u
typedef struct mbt_txn { uint8_t bytes[16]; size_t len; } mbt_txn;
typedef struct mock_bt820 {
    uint8_t ram[MBT_RAM_BYTES];
    uint8_t ram_cmd[0x4000];
    uint32_t regs_r1[0x1000 / 4];       /* REG_CORE R1 */
    uint32_t regs_sys[0x100 / 4];
    uint32_t regs_lvdstx[0x100 / 4];
    int cs;
    uint8_t tx[MBT_TX_MAX];             /* bytes of the current CS# period */
    size_t nbytes;
    int is_read;
    uint32_t addr;
    /* behaviour */
    int power_active;                   /* 0 until a valid ACTIVE */
    uint32_t poll_latency;
    int never_valid;
    uint32_t boot_polls_needed;         /* REG_BOOT_STATUS reads before 0x522E2E2E */
    int never_boots, wrong_chip_id, copro_fault_on_swap, copro_stall;
    uint32_t boot_reads;
    int sent_valid;
    uint32_t rd_poll_left;
    size_t rd_pos;
    uint32_t rd_word;
    /* coprocessor model */
    uint32_t dl[4096]; uint32_t dl_len;
    uint32_t swaps, rendertargets, finishes;
    uint32_t last_dl[16]; uint32_t last_dl_len;
    /* observation */
    uint64_t now_us;
    uint32_t trace_hash;                /* FNV-1a over writes and host commands */
    uint64_t n_writes, n_reads, n_cmds, n_active, n_partial_words, n_violations;
    uint8_t cmd_log[MBT_LOG_MAX][5]; uint32_t n_cmd_log;
    mbt_txn last_write;                 /* first 16 wire bytes of the last write */
    char last_violation[96];
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
