#include <arc1/lcd_status.h>
#include <stdio.h>
#include <string.h>
typedef struct {char top[17]; char bottom[17]; unsigned calls;} fake_lcd;
static int output(void *context, const char first[17], const char second[17]) {
    fake_lcd *lcd = (fake_lcd *)context;
    memcpy(lcd->top, first, 17); memcpy(lcd->bottom, second, 17);
    lcd->calls++; return 0;
}
int main(void) {
    fake_lcd lcd = {{0},{0},0};
    if (arc1_lcd_emit(ARC1_BOOT_F133,0,output,&lcd)) return 1;
    if (strcmp(lcd.top,"ARC-1  START    ") || strcmp(lcd.bottom,"F133 BOOT       ")) return 2;
    if (arc1_lcd_emit(ARC1_BOOT_READY,ARC1_OK_F133,output,&lcd) != -2) return 3;
    if (lcd.calls != 1) return 4;
    if (arc1_lcd_emit(ARC1_BOOT_READY,ARC1_LCD_READY_MASK,output,&lcd)) return 5;
    if (strcmp(lcd.top,"ARC-1   READY   ")) return 6;
    if (arc1_lcd_emit(ARC1_BOOT_FAULT,0,output,&lcd)) return 7;
    if (strstr(lcd.top,"FAULT") == 0) return 8;
    if (arc1_lcd_emit((arc1_boot_stage_t)99,0,output,&lcd) != -1) return 9;
    if (arc1_lcd_emit(ARC1_BOOT_F133,0,0,&lcd) != -1) return 10;
    puts("PASS lcd protocol: rows, READY gate, FAULT, invalid inputs");
    return 0;
}
