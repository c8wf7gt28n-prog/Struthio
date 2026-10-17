#include <arc1/serlcd_i2c.h>
#include <arc1/lcd_status.h>
#include <stdio.h>
#include <string.h>
typedef struct { int n; unsigned char packets[2][18]; int fail_after; } bus_log;
static int out(void *ctx, unsigned char addr, const unsigned char *data, size_t len) {
    bus_log *b=(bus_log*)ctx;
    if (addr!=0x72u || len!=18 || b->n>=2) return -8;
    if (b->fail_after==b->n) return -7;
    memcpy(b->packets[b->n],data,18);b->n++;return 0;
}
#define CHECK(c) do{if(!(c))return __LINE__;}while(0)
int main(void) {
    bus_log log={0};arc1_serlcd_bus_t bus={out,&log,0x72};
    log.fail_after=-1;
    CHECK(arc1_lcd_emit(ARC1_BOOT_NOR,0,arc1_serlcd_write_rows,&bus)==0);
    CHECK(log.n==2 && log.packets[0][0]==0xfe && log.packets[0][1]==0x80);
    CHECK(log.packets[1][0]==0xfe && log.packets[1][1]==0xc0);
    CHECK(memcmp(log.packets[1]+2,"NOR VERIFY      ",16)==0);
    log.n=0;log.fail_after=1;
    CHECK(arc1_lcd_emit(ARC1_BOOT_F133,0,arc1_serlcd_write_rows,&bus)==-7);
    log.n=0;log.fail_after=-1;bus.address=0;
    CHECK(arc1_lcd_emit(ARC1_BOOT_F133,0,arc1_serlcd_write_rows,&bus)==-1);
    CHECK(arc1_lcd_emit(ARC1_BOOT_READY,0,arc1_serlcd_write_rows,&bus)==-2);
    puts("PASS SerLCD command encoding, I2C failure propagation, READY gate");return 0;
}
