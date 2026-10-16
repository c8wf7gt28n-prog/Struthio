/* ARC-1 R10 -- 45F GPU command ABI, version 1 (job-word stream inside RJOB frames, see R10_GPU_ABI.md).
 * Shared by the C reference model (tools/gpu_ref.c), the D213 driver and the RTL test generators. Version 0 commands
 * (TILE_BEGIN / TRI_FLAT / TILE_END) keep their exact v0 meaning; v1 only adds commands and registers.
 * All words are 16-bit little endian in the RJOB payload. */
#ifndef R10_GPU_ABI_H
#define R10_GPU_ABI_H

#define GPU_ABI_MAJOR 1
#define GPU_ABI_MINOR 0

/* ---- commands (first word) ---- */
#define GPU_TILE_BEGIN 0x0001u  /* tile_x, tile_y (px, multiple of 32, 0..2016), clear_rgb565, clear_z            (5 words) */
#define GPU_TRI_FLAT   0x0002u  /* x0 y0 x1 y1 x2 y2 (12.4), z0 z1 z2, rgb565: v0 semantics (z test+write, replace) (11)  */
#define GPU_TILE_END   0x0003u  /* emit 'TI', x, y, 1024 colours, CRC lo, CRC hi                                     (1)   */
#define GPU_SET_REG    0x0010u  /* reg, value_lo, value_hi                                                            (4)   */
#define GPU_TRI_TEX    0x0011u  /* 3 x {x, y, z, q, u, v}, rgb565 (modulate / flat colour)                           (20)  */
#define GPU_UPLOAD_TEX 0x0012u  /* addr_lo, addr_hi (SDRAM word address), n, then n data words                      (4+n) */
#define GPU_UPLOAD_PAL 0x0013u  /* first index, n, then n RGB565 entries (palette is on-chip, 256 entries)          (3+n) */

#define GPU_TRI_TEX_WORDS   20u
#define GPU_UPLOAD_MAX      2048u   /* data words per UPLOAD_TEX command */

/* ---- registers (SET_REG), all reset to 0 at power-up; TILE_BEGIN does not change them ---- */
#define GPU_R_TEX_BASE   0x00u  /* [23:0] SDRAM word address of texel (0,0) */
#define GPU_R_TEX_CFG    0x01u  /* [3:0] log2 W (0..10), [7:4] log2 H (0..10), [9:8] format, [10] clamp U, [11] clamp V */
#define GPU_R_MODE       0x02u  /* see GPU_M_* */
#define GPU_R_ALPHA      0x03u  /* [5:0] constant alpha 0..32 (32 = opaque) */
#define GPU_R_FOG_COLOR  0x04u  /* [15:0] RGB565 */
#define GPU_R_FOG        0x05u  /* [15:0] fog start z, [31:16] fog scale: f = clamp(((z - start) * scale) >> 16, 0, 32) */
#define GPU_R_SCISSOR_X  0x06u  /* [15:0] first px, [31:16] last px (inclusive, screen pixels) */
#define GPU_R_SCISSOR_Y  0x07u  /* [15:0] first py, [31:16] last py */
#define GPU_R_COLOR_KEY  0x08u  /* [15:0] RGB565 texel value that is transparent when GPU_M_KEY is set */
#define GPU_R_COUNT      9u

#define GPU_FMT_RGB565 0u       /* one texel per SDRAM word */
#define GPU_FMT_I8     1u       /* two texels per word, even texel in the low byte, colour = palette[index] */
#define GPU_FMT_NONE   3u       /* untextured: colour = the triangle's rgb565 (blend / fog / dither still apply) */

#define GPU_M_ZTEST    0x0001u  /* pass if z < zbuf (strict) */
#define GPU_M_ZWRITE   0x0002u  /* write z on pass */
#define GPU_M_BLEND_MASK 0x000Cu
#define GPU_M_BLEND_REPLACE 0x0000u
#define GPU_M_BLEND_ALPHA   0x0004u  /* o = (c*a + d*(32-a)) >> 5, a = GPU_R_ALPHA */
#define GPU_M_BLEND_ADD     0x0008u  /* o = min(255, c + d) */
#define GPU_M_KEY      0x0010u  /* texel == COLOR_KEY -> fragment discarded (no colour, no z) */
#define GPU_M_FOG      0x0020u
#define GPU_M_DITHER   0x0040u  /* 4x4 ordered dither when quantising to RGB565 */
#define GPU_M_SCISSOR  0x0080u
#define GPU_M_MODULATE 0x0100u  /* textured colour multiplied by the triangle rgb565 */

/* ---- tile output (unchanged from v0) ---- */
#define GPU_TILE_MAGIC 0x5449u  /* 'TI' */
#define GPU_TILE_WORDS 1029u
#endif
