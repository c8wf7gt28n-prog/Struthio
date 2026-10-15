/* ARC-1 Compact R08 -- 32 MiB boot NOR layout and A/B system-image selection.
 * HOST_TESTED only. The partition sizes are a PLAN: no system/launcher binary
 * exists yet, so only the boot images built in R07/R08 are measured
 * (docs/NOR_BOOT_AND_FLASH.md, image-size ledger).
 *
 *  0x0000000  BOOT      1 MiB   boot0 (eGON, offset 0, read by the F133 BROM with
 *                               3-byte addressing) + ARC-1 loader at 0x10000
 *  0x0100000  JOURNAL   64 KiB  two 4 KiB sectors (ping-pong boot-state records)
 *  0x0110000  SETTINGS  64 KiB  two 4 KiB sectors (ping-pong user settings)
 *  0x0120000  RECOVERY  3.875 MiB  minimal recovery system (USB device service)
 *  0x0500000  ASSETS    4 MiB   boot-critical assets + T35 diagnostic bitstream copy
 *  0x0900000  SLOT_A    7 MiB   system image A (lower half)
 *  0x1000000  SLOT_B    7 MiB   system image B (upper half: starts exactly at 16 MiB)
 *  0x1700000  SPARE     9 MiB   growth; last 64 KiB = factory capacity-test block
 */
#ifndef FLASH_LAYOUT_H
#define FLASH_LAYOUT_H
#include <stdint.h>
#include "spi_nor.h"

#define FL_SIZE          0x02000000u
#define FL_BOOT          0x00000000u
#define FL_BOOT_LEN      0x00100000u
#define FL_LOADER        0x00010000u
#define FL_JOURNAL       0x00100000u
#define FL_JOURNAL_LEN   0x00010000u
#define FL_SETTINGS      0x00110000u
#define FL_SETTINGS_LEN  0x00010000u
#define FL_RECOVERY      0x00120000u
#define FL_RECOVERY_LEN  0x003E0000u
#define FL_ASSETS        0x00500000u
#define FL_ASSETS_LEN    0x00400000u
#define FL_SLOT_A        0x00900000u
#define FL_SLOT_B        0x01000000u
#define FL_SLOT_LEN      0x00700000u
#define FL_SPARE         0x01700000u
#define FL_SPARE_LEN     0x00900000u
#define FL_TESTBLOCK     0x01FF0000u

typedef struct fl_region { const char *name; uint32_t base, len; } fl_region;
extern const fl_region fl_regions[];
extern const unsigned fl_region_count;
/* 0 if regions are inside the device, 64 KiB aligned, ordered and disjoint */
int fl_layout_check(uint32_t device_size);

/* Image header, 64 bytes, at the start of RECOVERY / SLOT_A / SLOT_B. LE. */
#define FL_IMG_MAGIC 0x4D493141u   /* "A1IM" */
typedef struct fl_img_hdr {
    uint32_t magic;
    uint16_t hdr_version;   /* 1 */
    uint16_t kind;          /* 1 system, 2 recovery */
    uint32_t img_len;       /* payload bytes after the header */
    uint32_t img_crc32;
    uint32_t load_addr;
    uint32_t entry;
    uint32_t version;       /* monotonic build number */
    uint8_t  build_id[28];
    uint32_t hdr_crc32;     /* over the first 60 bytes */
} fl_img_hdr;

enum fl_img_status { FL_IMG_OK = 0, FL_IMG_BLANK, FL_IMG_BAD_MAGIC, FL_IMG_BAD_HDR_CRC, FL_IMG_BAD_LEN,
                     FL_IMG_BAD_CRC, FL_IMG_IO };
int fl_image_check(nor_dev *d, uint32_t slot_base, uint32_t slot_len, uint16_t kind, fl_img_hdr *out);
void fl_hdr_finalise(fl_img_hdr *h);

/* Boot-state journal record, 32 bytes, appended in the active journal sector. */
#define FL_JR_MAGIC 0x524A3141u    /* "A1JR" */
typedef struct fl_journal {
    uint32_t magic;
    uint32_t seq;
    uint8_t  active;        /* 0 = A, 1 = B: last confirmed slot */
    uint8_t  trial;         /* 0xFF none, else slot under trial */
    uint8_t  trials_left;
    uint8_t  bad_mask;      /* bit0 A, bit1 B: failed trials */
    uint32_t reserved[4];
    uint32_t crc32;         /* over the first 28 bytes */
} fl_journal;

int fl_journal_load(nor_dev *d, fl_journal *j);    /* newest valid record, or defaults */
int fl_journal_store(nor_dev *d, fl_journal *j);   /* append; seq is incremented */

enum fl_boot_target { FL_BOOT_SLOT_A = 0, FL_BOOT_SLOT_B = 1, FL_BOOT_RECOVERY = 2, FL_BOOT_NONE = 3 };
/* Decide what to boot; updates the journal when a trial is consumed or fails. */
int fl_boot_select(nor_dev *d, enum fl_boot_target *target);
/* Install an image into the inactive slot, verify, and arm a trial (3 attempts). */
int fl_install_update(nor_dev *d, const uint8_t *img_with_hdr, uint32_t len);
/* Called by the running system after a successful start of the trial slot. */
int fl_confirm_running(nor_dev *d, enum fl_boot_target running);
#endif
