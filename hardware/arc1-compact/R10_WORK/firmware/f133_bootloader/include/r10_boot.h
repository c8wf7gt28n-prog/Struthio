/* ARC-1 R10 -- F133 bootloader core for the single 64 MiB system NOR (ARC1_MEMORY_R10 v0.1 s3-s5, s7.3 item 4).
 * Partition map: r10_nor_layout.h, GENERATED from memory/gen_nor_partition.py. Reuses the R08/R8.5-C NOR driver
 * (dedicated 4-byte opcodes; the device is never left in 4-byte mode), the R08 image header (flash_layout.h) and the
 * R8.5-C ECP5 slave-SPI loader and ACFG container (ecp5_cfg.h).
 *
 * Components and slots
 *   F133 firmware  : slots A/B = F1MA/F1MB (R08 image header, kind 1); fallback = rescue F1RC (kind 2)
 *   D213 firmware  : slots A/B = D2FA/D2FB (R08 image header, kind 3); no fallback (memory spec 7.2: local NOR)
 *   12F bitstream  : slot 0 = application C12A, slot 1 = golden C12G (ACFG container, IDCODE LFE5U-12)
 *   45F bitstream  : slot 0 = application C45A, slot 1 = golden C45G (ACFG container, IDCODE LFE5U-45)
 * Manifest (META): two 64-byte records in two separate 4 KiB sectors (META+0, META+64 KiB), each with a generation
 *   counter and CRC-32. Load = the valid record with the highest generation. Store = erase and write the OTHER
 *   copy, then verify: a power cut at any point leaves the previous record intact (memory spec s4 update rules).
 * A/B rule (R08 journal semantics, per component): an update goes to the inactive slot and is armed as a trial with
 *   3 attempts; each boot of the trial consumes one attempt BEFORE the jump; r10_confirm() makes it active;
 *   attempts exhausted or image invalid -> the slot is marked bad and the active slot boots.
 * FPGA rule: application if valid and not marked bad, else golden; a failed configuration of the application marks
 *   it bad and the golden image is tried; with both failing the F133 still boots and reports the 12F as down
 *   (memory spec s5.3). Golden and boot/rescue partitions are never written by the updater (locked).
 * HOST_TESTED (tests/test_boot.c with the R08 NOR mock at 64 MiB and the R8.5-C ECP5 mock). Not run on silicon. */
#ifndef R10_BOOT_H
#define R10_BOOT_H
#include <stdint.h>
#include "spi_nor.h"
#include "ecp5_cfg.h"
#include "r10_nor_layout.h"

#define R10_IDCODE_LFE5U_12 0x21111043u   /* Lattice ECP5 IDCODE list (LFE5U-12F); bench-verify */
#define R10_MF_MAGIC 0x464D3141u          /* "A1MF" */
#define R10_MF_SIZE  64u
#define R10_MF_COPY1 0x00010000u          /* offset of copy 1 inside META */
#define R10_TRIALS   3u
#define R10_IMG_KIND_F133 1u
#define R10_IMG_KIND_RESCUE 2u
#define R10_IMG_KIND_D213 3u

/* R10 additions to the copied ecp5_cfg.c */
static inline int r10_idcode_ok(uint32_t id) { return id == ECP5_IDCODE_LFE5U_45 || id == R10_IDCODE_LFE5U_12; }
size_t ecp5_image_build_id(uint8_t *out, size_t cap, const uint8_t *bit, uint32_t bit_len, uint16_t abi_major,
                           uint16_t abi_minor, uint32_t caps_required, uint32_t idcode);

enum r10_comp { R10C_F133 = 0, R10C_D213 = 1, R10C_C12 = 2, R10C_C45 = 3, R10C_COUNT = 4 };
enum r10_slot { R10S_0 = 0, R10S_1 = 1, R10S_FALLBACK = 2, R10S_NONE = 3 };   /* 0/1 = A/B or app/golden */
enum r10_err  { R10_OK = 0, R10_E_NOR = 1, R10_E_ARG = 2, R10_E_LOCKED = 3, R10_E_IMAGE = 4, R10_E_STATE = 5,
                R10_E_STAGE = 6, R10_E_FPGA = 7, R10_E_NONE = 8, R10_E_LINK = 9 };

typedef struct r10_comp_state {
    uint8_t  active;        /* A/B: confirmed slot; FPGA: unused (app preferred) */
    uint8_t  trial;         /* 0xFF none, else slot under trial (A/B only) */
    uint8_t  trials_left;
    uint8_t  bad_mask;      /* bit s: slot s failed */
    uint32_t version[2];
} r10_comp_state;

typedef struct r10_manifest {
    uint32_t generation;
    r10_comp_state c[R10C_COUNT];
} r10_manifest;

typedef struct r10_boot {
    nor_dev *nor;
    uint8_t *stage;         /* DRAM staging buffer for one bitstream container (owner map: NOR staging window) */
    uint32_t stage_cap;
    uint16_t fpga_abi;      /* ACFG abi_major the firmware accepts */
    uint64_t mf_writes;     /* statistics */
} r10_boot;

typedef struct r10_update {
    r10_boot *b;
    enum r10_comp comp;
    uint8_t  slot;
    uint32_t base, cap, off;
} r10_update;

uint32_t r10_part_base(enum r10_comp c, int slot);         /* 0 if none */
uint32_t r10_part_len(enum r10_comp c, int slot);
/* 1 if [addr, addr+n) lies wholly inside one unlocked partition */
int  r10_write_allowed(uint32_t addr, uint32_t n);
int  r10_layout_check(void);                                 /* 0 = generated map is contiguous, aligned, 64 MiB */

void r10_manifest_default(r10_manifest *m);
int  r10_manifest_load(r10_boot *b, r10_manifest *m, int *copy);        /* copy: -1 none valid (defaults) */
int  r10_manifest_store(r10_boot *b, r10_manifest *m);                  /* generation++ */

/* validity of what is stored in a slot (header + full CRC, streamed from NOR) */
int  r10_slot_valid(r10_boot *b, enum r10_comp c, int slot);
/* boot decision for one component; for F133/D213 this consumes a trial attempt (manifest write) */
int  r10_select(r10_boot *b, enum r10_comp c, enum r10_slot *out);
int  r10_confirm(r10_boot *b, enum r10_comp c, enum r10_slot running);
/* FPGA: read the container of `slot` into b->stage, check it; fills img (img->bit points into the stage) */
int  r10_fpga_stage(r10_boot *b, enum r10_comp c, int slot, ecp5_image *img);
/* 12F bring-up: application, else golden; marks a failing application bad. used = slot configured or R10S_NONE */
int  r10_boot_fpga12(r10_boot *b, ecp5_cfg *cfg, enum r10_slot *used, ecp5_err *last);

/* total container size (ACFG header + bitstream) of a valid FPGA slot, else 0 */
uint32_t r10_fpga_size(r10_boot *b, enum r10_comp c, int slot);

/* streamed update into the inactive slot (A/B) or the application slot (FPGA); never a locked partition */
int  r10_update_begin(r10_boot *b, enum r10_comp c, r10_update *u);
int  r10_update_write(r10_update *u, const uint8_t *p, uint32_t n);    /* sequential; 4 KiB-aligned erases */
int  r10_update_commit(r10_update *u, uint32_t version);              /* verify on NOR, then arm (manifest) */

/* 45F bring-up through the D213 (r10_fpga45.c): application, else golden, streamed from the NOR over the USB graphics
 * link; the D213 configures the 45F. used = slot or R10S_NONE; dev_status and detail = the D213's last answer.
 * R10_E_LINK: graphics link down (the D213 keeps its 2D path); R10_E_FPGA: neither image configured. */
struct gl_host;
int  r10_boot_fpga45(r10_boot *b, struct gl_host *h, enum r10_slot *used, uint8_t *dev_status, uint16_t *detail);
#endif
