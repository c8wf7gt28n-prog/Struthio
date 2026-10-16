/* ARC-1 R10 -- F133 side of the 45F configuration path: NOR (C45A / C45G) -> USB graphics link -> D213 -> 45F
 * slave SPI (ARC1_MEMORY_R10 s3.1 / s5.1 step 6). HOST_TESTED (tests/test_fpga45_path.c). */
#include "r10_boot.h"
#include "gfx_link.h"

typedef struct nor_src { nor_dev *nor; uint32_t base; } nor_src;
static int nor_rd(void *ctx, uint32_t off, uint8_t *buf, uint32_t n)
{
    nor_src *s = (nor_src *)ctx;
    return nor_read(s->nor, s->base + off, buf, n) == NOR_OK ? 0 : -1;
}

int r10_boot_fpga45(r10_boot *b, struct gl_host *h, enum r10_slot *used, uint8_t *dev_status, uint16_t *detail)
{
    r10_manifest m;
    int slot, rc;
    *used = R10S_NONE; *dev_status = 0xFF; *detail = 0;
    if ((rc = r10_manifest_load(b, &m, NULL)) != R10_OK) return rc;
    for (slot = 0; slot < 2; slot++) {
        uint32_t total;
        nor_src src;
        if (slot == 0 && (m.c[R10C_C45].bad_mask & 1u)) continue;
        total = r10_fpga_size(b, R10C_C45, slot);              /* checked on the F133 before anything is sent */
        if (!total) {
            if (slot == 0) { m.c[R10C_C45].bad_mask |= 1u; if (r10_manifest_store(b, &m) != R10_OK) return R10_E_NOR; }
            continue;
        }
        src.nor = b->nor; src.base = r10_part_base(R10C_C45, slot);
        rc = gl_send_fpga(h, total, nor_rd, &src, dev_status, detail);
        if (rc == GL_FALLBACK) return R10_E_LINK;
        if (rc != GL_OK) return R10_E_NOR;
        if (*dev_status == GL_S_OK) { *used = (enum r10_slot)slot; return R10_OK; }
        if (*dev_status == GL_S_FPGA_IMAGE && slot == 0) {        /* the D213 rejected the image itself */
            m.c[R10C_C45].bad_mask |= 1u;
            if (r10_manifest_store(b, &m) != R10_OK) return R10_E_NOR;
        }
    }
    return R10_E_FPGA;
}
