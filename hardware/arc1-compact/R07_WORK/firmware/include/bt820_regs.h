/* ARC-1 Compact R07 -- BT820 (BT82X) address map, registers and command
 * words used by the R07 host layer.
 *
 * Sources (MANUFACTURER_DOCUMENTED):
 *   [AN086] Bridgetek BRT_AN_086 BT82X Series Programming Guide v1.4
 *           (2026-09-07): Table 2 memory map, section 2.3 host commands,
 *           2.4 chip ID, 2.5 boot sequence, 2.14 swap chains, chapter 3
 *           register definitions.
 *   [EVEAPPS] Bridgetek EveApps-BT82X, common/eve_hal/EVE_GpuDefs.h,
 *           commit 6b5a57eb (MIT licence): absolute register addresses,
 *           command codes and display-list encodings, cross-checked
 *           against [AN086] where the guide gives the same value.
 * Only the subset needed for boot, identification, the coprocessor FIFO,
 * scan-out and a test frame is listed. */
#ifndef BT820_REGS_H
#define BT820_REGS_H

/* ---- memory map [AN086 Table 2] ---- */
#define BT820_RAM_G            0x00000000u
#define BT820_RAM_G_END        0x7F000000u   /* exclusive; real size = attached DDR */
#define BT820_RAM_G_RESERVED_TOP 2621440u    /* top 2.5 MiB of DDR reserved [AN086 2.1] */
#define BT820_RAM_CMD          0x7F000000u   /* 16 KiB command FIFO */
#define BT820_RAM_CMD_SIZE     0x4000u
#define BT820_REG_CORE_R2      0x7F004000u   /* 2 KiB */
#define BT820_RAM_REPORT       0x7F004800u   /* 128 B */
#define BT820_REG_CORE_R1      0x7F006000u   /* 4 KiB */
#define BT820_RAM_DL           0x7F008000u   /* 16 KiB display list */
#define BT820_REG_CMDB_WRITE   0x7F010000u   /* [AN086 Reg. Def. 128] */
#define BT820_REG_LVDSTX       0x7F800300u   /* 256 B */
#define BT820_REG_SYS          0x7F800400u   /* 256 B */
#define BT820_REG_LVDSRX       0x7F800500u   /* 256 B */
#define BT820_REG_I2S          0x7F800800u   /* 256 B */

/* ---- registers ---- */
#define BT820_REG_ID           (BT820_REG_CORE_R1 + 0x000u)  /* reads 0x7C [AN086 Reg. Def. 144] */
#define BT820_REG_FRAMES       (BT820_REG_CORE_R1 + 0x004u)
#define BT820_REG_FREQUENCY    (BT820_REG_CORE_R1 + 0x00Cu)
#define BT820_REG_RE_DEST      (BT820_REG_CORE_R1 + 0x010u)
#define BT820_REG_SC0_SIZE     (BT820_REG_CORE_R1 + 0x038u)
#define BT820_REG_SC0_PTR0     (BT820_REG_CORE_R1 + 0x03Cu)
#define BT820_REG_SC0_PTR1     (BT820_REG_CORE_R1 + 0x040u)
#define BT820_REG_CPURESET     (BT820_REG_CORE_R1 + 0x088u)
#define BT820_REG_HCYCLE       (BT820_REG_CORE_R1 + 0x08Cu)
#define BT820_REG_HOFFSET      (BT820_REG_CORE_R1 + 0x090u)
#define BT820_REG_HSIZE        (BT820_REG_CORE_R1 + 0x094u)
#define BT820_REG_HSYNC0       (BT820_REG_CORE_R1 + 0x098u)
#define BT820_REG_HSYNC1       (BT820_REG_CORE_R1 + 0x09Cu)
#define BT820_REG_VCYCLE       (BT820_REG_CORE_R1 + 0x0A0u)
#define BT820_REG_VOFFSET      (BT820_REG_CORE_R1 + 0x0A4u)
#define BT820_REG_VSIZE        (BT820_REG_CORE_R1 + 0x0A8u)
#define BT820_REG_VSYNC0       (BT820_REG_CORE_R1 + 0x0ACu)
#define BT820_REG_VSYNC1       (BT820_REG_CORE_R1 + 0x0B0u)
#define BT820_REG_PCLK_POL     (BT820_REG_CORE_R1 + 0x0B8u)
#define BT820_REG_DISP         (BT820_REG_CORE_R1 + 0x0E4u)
#define BT820_REG_PWM_DUTY     (BT820_REG_CORE_R1 + 0x12Cu)
#define BT820_REG_CMD_READ     (BT820_REG_CORE_R1 + 0x14Cu)  /* 0x3FFF = coprocessor fault */
#define BT820_REG_CMD_WRITE    (BT820_REG_CORE_R1 + 0x150u)
#define BT820_REG_CMD_DL       (BT820_REG_CORE_R1 + 0x154u)
#define BT820_REG_CMDB_SPACE   (BT820_REG_CORE_R1 + 0x594u)
#define BT820_REG_SO_MODE      (BT820_REG_CORE_R1 + 0x5F4u)
#define BT820_REG_SO_SOURCE    (BT820_REG_CORE_R1 + 0x5F8u)
#define BT820_REG_SO_FORMAT    (BT820_REG_CORE_R1 + 0x5FCu)
#define BT820_REG_SO_EN        (BT820_REG_CORE_R1 + 0x600u)
#define BT820_REG_SYS_CFG      (BT820_REG_SYS + 0x20u)       /* SPI_WIDTH bits 9:8 */
#define BT820_REG_CHIP_ID      (BT820_REG_SYS + 0x48u)       /* 0x08200100 for BT820B [AN086 Table 6] */
#define BT820_REG_BOOT_STATUS  (BT820_REG_SYS + 0x4Cu)       /* 0x522E2E2E when running [AN086 2.5] */
#define BT820_REG_LVDSTX_EN    (BT820_REG_LVDSTX + 0x00u)
#define BT820_REG_LVDSTX_PLLCFG (BT820_REG_LVDSTX + 0x04u)

#define BT820_REG_ID_VALUE      0x7Cu
#define BT820_CHIP_ID_BT820B    0x08200100u
#define BT820_BOOT_STATUS_RUN   0x522E2E2Eu
#define BT820_CMD_FAULT         0x3FFFu

/* ---- host commands [AN086 Table 3] (second byte of FF xx pp 00 00) ---- */
#define BT820_HC_STANDBY     0xE0u
#define BT820_HC_SLEEP       0xE1u
#define BT820_HC_POWERDOWN   0xE2u
#define BT820_HC_SETPLLSP1   0xE4u   /* low-power state only */
#define BT820_HC_SETSYSCLKDIV 0xE6u  /* low-power state only */
#define BT820_HC_RESET_PULSE 0xE7u
#define BT820_HC_SETBOOTCFG  0xE8u   /* low-power state only */
#define BT820_HC_BOOTCFGEN   0xE9u   /* low-power state only */
#define BT820_HC_SETDDRTYPE  0xEBu   /* low-power state only */

/* ---- coprocessor commands and display-list words [EVEAPPS] ---- */
#define BT820_CMD_DLSTART         0xFFFFFF00u
#define BT820_CMD_SWAP            0xFFFFFF01u
#define BT820_CMD_GRAPHICSFINISH  0xFFFFFF6Bu
#define BT820_CMD_RENDERTARGET    0xFFFFFF8Du
#define BT820_DL_DISPLAY          0x00000000u
#define BT820_DL_CLEAR_COLOR_RGB(r, g, b) ((0x02u << 24) | (((uint32_t)(r) & 0xFFu) << 16) | \
                                           (((uint32_t)(g) & 0xFFu) << 8) | ((uint32_t)(b) & 0xFFu))
#define BT820_DL_CLEAR(c, s, t)   ((0x26u << 24) | (((uint32_t)(c) & 1u) << 2) | (((uint32_t)(s) & 1u) << 1) | ((uint32_t)(t) & 1u))
#define BT820_SWAPCHAIN_0         0xFFFF00FFu
#define BT820_FMT_RGB8            19u
#define BT820_SO_ONE_PIXEL_SINGLE_LVDS 0u
#define BT820_SO_TWO_PIXEL_SINGLE_LVDS 1u
#define BT820_LVDS_CH0_EN         2u
#define BT820_LVDSTX_PLLCFG(cps, lock, cks, ns, clkdiv) \
    ((((uint32_t)(cps) & 0x7u) << 25) | (((uint32_t)(lock) & 0xFFFu) << 13) | \
     (((uint32_t)(cks) & 0x3u) << 11) | (((uint32_t)(ns) & 0x7Fu) << 4) | ((uint32_t)(clkdiv) & 0xFu))

#endif
