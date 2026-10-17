/* Build-stage only; D213 boot ROM, DRAM training, UART, HDMI are not implemented. */
#include <stdint.h>
__attribute__((used,section(".arc1.stage")))
const char arc1_d213_stage_identity[] = "ARC1 R04 D213 LINK_TEST_ONLY NOT_BOOTABLE";
static volatile uint32_t stage_progress;
void arc1_stage_main(void) {
    stage_progress = 0xD2130004u;
    for (;;) { __asm__ volatile ("wfi"); }
}
