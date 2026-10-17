/* Portable ARC-1 status protocol — not a hardware I2C/SerLCD driver. */
#include <arc1/lcd_status.h>
static void format_row(char dest[17], const char *source) {
    unsigned i = 0;
    while (i < 16 && source && source[i]) { dest[i] = source[i]; i++; }
    while (i < 16) dest[i++] = ' ';
    dest[16] = '\0';
}
int arc1_lcd_emit(arc1_boot_stage_t stage, unsigned verified,
                  arc1_lcd_rows_fn write_rows, void *context) {
    if (!write_rows || (unsigned)stage > (unsigned)ARC1_BOOT_FAULT) return -1;
    if (stage == ARC1_BOOT_READY && (verified & ARC1_LCD_READY_MASK) != ARC1_LCD_READY_MASK)
        return -2;
    arc1_lcd_message_t message = arc1_boot_lcd_message(stage);
    char row0[17], row1[17];
    format_row(row0, message.row0);
    format_row(row1, message.row1);
    return write_rows(context, row0, row1);
}
