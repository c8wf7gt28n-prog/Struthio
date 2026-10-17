#include <arc1/boot_monitor.h>
#include <stdio.h>
#include <string.h>
static int fault_seen=0;
static int fake(void *p,const char a[17],const char b[17]) {
    (void)p;(void)a;
    if (strstr(b,"FAULT 0x1203")) fault_seen=1;
    return 0;
}
#define CHECK(c) do { if (!(c)) return __LINE__; } while(0)
int main(void) {
    arc1_boot_monitor_t m; arc1_boot_monitor_init(&m);
    CHECK(m.verified==0 && m.stage==ARC1_BOOT_POWER);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_READY)==-2);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_NOR)==-2);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_F133)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_NOR)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_FPGA45)==-2);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_D213)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_FPGA12)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_FPGA45)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_READY)==0);
    CHECK(arc1_boot_monitor_display(&m,fake,0)==0);
    arc1_boot_monitor_init(&m);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_F133)==0);
    CHECK(arc1_boot_monitor_fault(&m,0x1203)==0);
    CHECK(arc1_boot_monitor_mark(&m,ARC1_BOOT_READY)==-3);
    CHECK(arc1_boot_monitor_fault(&m,0x1234)==-3);
    CHECK(arc1_boot_monitor_display(&m,fake,0)==0);
    CHECK(fault_seen==1);
    CHECK(arc1_boot_monitor_fault(0,1)==-1);
    puts("PASS boot monitor: prerequisites, no false READY, latched fault");return 0;
}
