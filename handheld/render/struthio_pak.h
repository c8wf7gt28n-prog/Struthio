// STRUTHIO HANDHELD · the asset pack: everything the panel renderer draws
// with, in one file for the flash 'assets' partition (mapped, not copied).
// Written by host/make_pak from the browser's own textures and HUD
// (tools/reference); read by st_pak_open on the host and on the device.
//
//   "STRPAK01"  u32 count  then count entries of 40 bytes:
//     char name[24]; u32 offset; u32 size; u16 w, h; i16 x, y; u8 format; u8 pad[3]
//     (HUD layers: pad[0] | pad[1] << 8 = 1 + the entry of the base layer, or 0)
//   blobs, 4-byte aligned
#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "struthio_panel.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef struct {
    char name[24];
    uint32_t offset, size;
    uint16_t w, h;
    int16_t x, y;
    uint8_t format, pad[3];
} st_pak_entry_t;

// Fills the panel's textures and HUD assets from a pack in memory (pointers
// point into it). Returns false and names what is missing in err.
bool st_pak_open(const uint8_t *pak, size_t size, st_panel_textures_t *tx, st_hud_assets_t *hud, char *err, size_t err_cap);
const st_pak_entry_t *st_pak_find(const uint8_t *pak, const char *name);

#ifdef __cplusplus
}
#endif
