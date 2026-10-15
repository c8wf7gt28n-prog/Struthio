/* R07 regression probe: compiled against the FROZEN R06 driver
 * (R06_WORK/firmware) on purpose. It asks for the R07 requirement "a write
 * to RAM_CMD at 0x7F000000 is emitted". Exit 0 would mean R06 already met it;
 * the expected result is exit 1 (R06 defect R06-BT-0x7F reproduced). */
#include <stdio.h>
#include "bt820_host.h"
#include "mocks.h"
static mock_bt820 m;
int main(void) {
    bt820_dev d;
    arc1_spi_hal h;
    uint8_t w[4] = {0, 0xFF, 0xFF, 0xFF};
    int rc;
    mbt_init(&m);
    h = mbt_hal(&m);
    (void)bt820_init(&d, &h, 64);
    rc = bt820_write(&d, 0x7F000000u, w, 4);
    printf("R06 bt820_write(0x7F000000) -> %d (%s)\n", rc, bt820_error_string(rc));
    if (rc == BT820_OK) { printf("R06_ACCEPTS_RAM_CMD_WRITE\n"); return 0; }
    printf("R06_DEFECT_REPRODUCED: write to RAM_CMD refused\n");
    return 1;
}
