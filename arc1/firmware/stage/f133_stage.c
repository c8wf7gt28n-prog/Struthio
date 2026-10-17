/* Build-stage only; board clocks, UART, NOR and TWI HAL are NOT initialized. */
#include <stdint.h>
#include <arc1/lcd_status.h>
__attribute__((used,section(".arc1.stage")))
const char arc1_f133_stage_identity[] = "ARC1 R04 F133 LINK_TEST_ONLY NOT_BOOTABLE";
static volatile uint32_t stage_progress;
static char diagnostic_rows[2][17];
/* Host-contract callback; no actual I2C hardware or LCD device is accessed. */
static int stage_lcd_rows(void *ctx, const char row0[17], const char row1[17]) {
    char (*rows)[17] = (char (*)[17])ctx;
    unsigned i;
    for (i = 0; i < 17; ++i) { rows[0][i] = row0[i]; rows[1][i] = row1[i]; }
    return 0;
}
/* Never print READY: no hardware evidence exists in this build. */
void arc1_stage_main(void) {
    stage_progress = 0xF1330004u;
    if (arc1_lcd_emit(ARC1_BOOT_F133, 0, stage_lcd_rows, diagnostic_rows) != 0)
        stage_progress = 0xBADF133u;
    for (;;) { __asm__ volatile ("wfi"); }
}
