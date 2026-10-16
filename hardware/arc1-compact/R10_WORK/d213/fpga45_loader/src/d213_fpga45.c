/* ARC-1 R10 -- D213-side 45F loader (see include/d213_fpga45.h). HOST_TESTED only. */
#include "d213_fpga45.h"
#include "gfx_link.h"
#include <string.h>

void d213_fpga45_init(d213_fpga45 *f, const ecp5_gpio_hal *io, const arc1_spi_hal *spi, uint16_t abi_major)
{
    memset(f, 0, sizeof *f);
    ecp5_cfg_init(&f->cfg, io, spi);
    f->abi_major = abi_major;
}

uint8_t d213_fpga45_load(void *ctx, const uint8_t *img, uint32_t len, uint16_t *detail)
{
    d213_fpga45 *f = (d213_fpga45 *)ctx;
    ecp5_image im;
    ecp5_err e = ecp5_image_check(img, len, f->abi_major, &im);
#ifndef MUTANT_D213_NO_IDCODE
    if (e == ECP5_OK && im.idcode != ECP5_IDCODE_LFE5U_45) e = ECP5_E_IMAGE_DEVICE;   /* a 12F image on the 45F */
#endif
    if (e != ECP5_OK) { f->image_bad++; *detail = (uint16_t)e; return GL_S_FPGA_IMAGE; }
    f->configured = 0;
    e = ecp5_configure(&f->cfg, &im);
    *detail = (uint16_t)e;
    if (e != ECP5_OK) { f->cfg_bad++; return GL_S_FPGA_CFG; }
    f->configured = 1; f->loads_ok++;
    return GL_S_OK;
}
