/* ARC-1 R10 -- D213-side loader for the ECP5-45F (ARC1_MEMORY_R10 v0.1 s3.1 "D213 -> ECP5-45F: D213 sends the 45F
 * bitstream using vendor-supported configuration pins; source delivered from F133").
 * Flow: the F133 streams the ACFG container from its NOR over the USB graphics link (gfx_link FPGA_IMAGE); gl_dev
 * stages it in D213 DDR3 and calls d213_fpga45_load(), which checks it (container CRC, LFE5U-45 IDCODE, ABI) and
 * configures the 45F through the R8.5-C sysCONFIG slave-SPI sequence (ecp5_cfg.c, R10 copy).
 * D213 binding (hardware/R10_flash_pinmux.csv, group CFG45): SPI1 PB11 CLK / PB10 MOSI / PB9 MISO / PB8 CS (= SN,
 * SPI1 is dedicated to the 45F, so SN may stay low for the whole burst); PA4 PROGRAMN (open drain), PA5 INITN,
 * PA6 DONE. ECP5_PIN_PWR_EN / VCC_PG / BUS_EN_N / PSRAM_REQ have no D213 pin in R10: the binding ignores PWR_EN,
 * BUS_EN_N and PSRAM_REQ and reports VCC_PG = 1 (45F rails follow the board supply) -- a schematic decision, OPEN.
 * No D213 BSP binding exists yet. HOST_TESTED against the R8.5-C ECP5 mock. */
#ifndef D213_FPGA45_H
#define D213_FPGA45_H
#include <stdint.h>
#include "ecp5_cfg.h"

typedef struct d213_fpga45 {
    ecp5_cfg cfg;
    uint16_t abi_major;
    int      configured;
    uint64_t loads_ok, image_bad, cfg_bad;
} d213_fpga45;

void    d213_fpga45_init(d213_fpga45 *f, const ecp5_gpio_hal *io, const arc1_spi_hal *spi, uint16_t abi_major);
/* gl_dev fpga_load callback: returns GL_S_OK, GL_S_FPGA_IMAGE (container rejected, nothing sent to the FPGA) or
 * GL_S_FPGA_CFG (configuration failed; *detail = ecp5_err); ctx is the d213_fpga45 */
uint8_t d213_fpga45_load(void *ctx, const uint8_t *img, uint32_t len, uint16_t *detail);
#endif
