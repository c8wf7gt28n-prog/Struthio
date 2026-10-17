#include <arc1/boot_monitor.h>
void arc1_boot_monitor_init(arc1_boot_monitor_t *m) {
    if (!m) return;
    m->verified=0; m->stage=ARC1_BOOT_POWER; m->fault_code=0;
}
int arc1_boot_monitor_mark(arc1_boot_monitor_t *m, arc1_boot_stage_t s) {
    unsigned need=0, bit=0;
    if (!m) return -1;
    if (m->fault_code) return -3;
    switch (s) {
        case ARC1_BOOT_F133: bit=ARC1_OK_F133; break;
        case ARC1_BOOT_NOR: need=ARC1_OK_F133; bit=ARC1_OK_NOR; break;
        case ARC1_BOOT_D213: need=ARC1_OK_F133|ARC1_OK_NOR; bit=ARC1_OK_D213_VIDEO; break;
        case ARC1_BOOT_FPGA12: need=ARC1_OK_F133|ARC1_OK_NOR; bit=ARC1_OK_FPGA12; break;
        case ARC1_BOOT_FPGA45: need=ARC1_OK_F133|ARC1_OK_NOR|ARC1_OK_D213_VIDEO; bit=ARC1_OK_FPGA45; break;
        case ARC1_BOOT_CARTRIDGE: need=ARC1_OK_F133|ARC1_OK_NOR; break;
        case ARC1_BOOT_READY: need=ARC1_LCD_READY_MASK; break;
        case ARC1_BOOT_SERVICE: case ARC1_BOOT_RECOVERY: break;
        default: return -1;
    }
    if ((m->verified&need)!=need) return -2;
    m->verified |= bit;
    m->stage=s;
    return 0;
}
int arc1_boot_monitor_fault(arc1_boot_monitor_t *m, unsigned code) {
    if (!m || code==0 || code>65535u) return -1;
    if (m->fault_code) return -3;
    m->fault_code=code; m->stage=ARC1_BOOT_FAULT;
    return 0;
}
int arc1_boot_monitor_display(const arc1_boot_monitor_t *m, arc1_lcd_rows_fn emit, void *ctx) {
    if (!m) return -1;
    if (m->fault_code && emit) {
        static const char hex[]="0123456789ABCDEF";
        char a[17]="ARC-1   FAULT   ";
        char b[17]="FAULT 0x0000    ";
        unsigned code=m->fault_code, i;
        for (i=0;i<4u;i++) b[11u-i]=hex[(code>>(i*4u))&15u];
        return emit(ctx,a,b);
    }
    return arc1_lcd_emit(m->stage, m->verified, emit, ctx);
}
