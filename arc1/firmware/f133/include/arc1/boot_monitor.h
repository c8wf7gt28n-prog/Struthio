#ifndef ARC1_BOOT_MONITOR_H
#define ARC1_BOOT_MONITOR_H
#include <arc1/lcd_status.h>
/* Explicit evidence inputs only. No stage advances from elapsed time. */
typedef struct arc1_boot_monitor {
    unsigned verified;
    arc1_boot_stage_t stage;
    unsigned fault_code;
} arc1_boot_monitor_t;
/* Initializes in POWER; caller must separately verify rails in hardware. */
void arc1_boot_monitor_init(arc1_boot_monitor_t *m);
/* 0 accepted, -1 invalid, -2 missing prerequisite, -3 latched fault */
int arc1_boot_monitor_mark(arc1_boot_monitor_t *m, arc1_boot_stage_t stage);
/* Latch a nonzero fault. 0 accepted, -1 invalid, -3 fault already latched */
int arc1_boot_monitor_fault(arc1_boot_monitor_t *m, unsigned fault_code);
/* LCD output is best-effort; failure never grants boot readiness. */
int arc1_boot_monitor_display(const arc1_boot_monitor_t *m, arc1_lcd_rows_fn emit, void *ctx);
#endif
