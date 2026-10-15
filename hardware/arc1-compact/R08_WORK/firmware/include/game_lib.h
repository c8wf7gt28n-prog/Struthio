/* ARC-1 Compact R08 -- microSD game library: package validation, library scan,
 * power-fail/removal-safe saves. HOST_TESTED with a mock card only.
 * Policy (corrective handoff v1.0 s.7): the card holds games, assets and saves
 * only; it is never a boot medium. An absent card is a NORMAL state. A corrupt
 * or malicious package is rejected by the launcher and cannot stop the NOR
 * system from starting (the scan runs after the launcher is up and every field
 * is bounds-checked). The filesystem driver itself is OUT OF SCOPE here: the
 * card ops below abstract it (FAT/exFAT choice is an R09 firmware item). */
#ifndef GAME_LIB_H
#define GAME_LIB_H
#include <stddef.h>
#include <stdint.h>

#define A1GP_MAGIC   0x50474131u   /* "A1GP" */
#define A1GP_HDR_LEN 128u

enum a1gp_status { A1GP_OK = 0, A1GP_TRUNCATED, A1GP_BAD_MAGIC, A1GP_UNSUPPORTED_VERSION, A1GP_BAD_HDR_CRC,
                   A1GP_BAD_FIELD, A1GP_NEEDS_NEWER_FW, A1GP_BAD_PAYLOAD_LEN, A1GP_BAD_PAYLOAD_CRC, A1GP_IO };

typedef struct a1gp_info {
    char     game_id[17];
    char     title[49];
    uint32_t min_fw;
    uint32_t payload_len;
    uint32_t payload_crc32;
    uint32_t flags;
} a1gp_info;

int a1gp_parse(const uint8_t *hdr, size_t n, uint32_t fw_version, uint64_t file_size, a1gp_info *out);
/* test helper / packaging tool core: build a valid header */
void a1gp_build(uint8_t hdr[A1GP_HDR_LEN], const char *id, const char *title, uint32_t min_fw,
                uint32_t payload_len, uint32_t payload_crc32);

/* ---------------- card abstraction ---------------- */
enum lib_card_state { LIB_NO_CARD = 0, LIB_UNSUPPORTED_FS, LIB_IO_ERROR, LIB_CARD_OK };
typedef struct lib_card_ops {
    void *ctx;
    int (*present)(void *ctx);                                        /* card-detect switch */
    int (*mount)(void *ctx);                                          /* 0 ok, -1 unsupported fs, -2 I/O */
    int (*list)(void *ctx, unsigned idx, char *name, size_t cap);     /* 1 entry, 0 end, <0 I/O */
    int (*size)(void *ctx, const char *name, uint64_t *sz);           /* 0 ok */
    int (*read)(void *ctx, const char *name, uint64_t off, void *buf, size_t n);   /* bytes read or <0 */
    int (*write)(void *ctx, const char *name, uint64_t off, const void *buf, size_t n); /* bytes written or <0 */
} lib_card_ops;

typedef struct lib_entry { char file[64]; int status; a1gp_info info; } lib_entry;
/* Scans *.a1gp files in the library directory. Never fails the caller: the
 * card state says why the list is empty. */
enum lib_card_state lib_scan(const lib_card_ops *c, uint32_t fw_version, lib_entry *e, unsigned max, unsigned *count);
/* Deep check before launch: payload length and CRC32. */
int lib_verify_payload(const lib_card_ops *c, const lib_entry *e);

/* ---------------- saves: two alternating records per game ---------------- */
#define SAVE_MAGIC 0x56534131u     /* "A1SV" */
#define SAVE_MAX   4096u
enum save_status { SAVE_OK = 0, SAVE_NONE, SAVE_IO, SAVE_TOO_BIG, SAVE_NO_CARD };
/* writes the record into the slot that does NOT hold the newest valid save,
 * reads it back; the previous save stays intact until the new one verifies */
int save_commit(const lib_card_ops *c, const char *game_id, const void *data, uint32_t len);
int save_load(const lib_card_ops *c, const char *game_id, void *data, uint32_t cap, uint32_t *len, uint32_t *seq);
#endif
