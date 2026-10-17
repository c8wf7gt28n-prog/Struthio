#ifndef ARC1_LCD_STATUS_H
#define ARC1_LCD_STATUS_H
#include <arc1/brand.h>
/* Evidence bits supplied by the verified firmware bring-up state machine. */
enum {
    ARC1_OK_F133 = 1u << 0,
    ARC1_OK_NOR = 1u << 1,
    ARC1_OK_D213_VIDEO = 1u << 2,
    ARC1_OK_FPGA12 = 1u << 3,
    ARC1_OK_FPGA45 = 1u << 4
};
#define ARC1_LCD_READY_MASK (ARC1_OK_F133|ARC1_OK_NOR|ARC1_OK_D213_VIDEO|ARC1_OK_FPGA12|ARC1_OK_FPGA45)
/* Transport-independent driver boundary. A future F133 TWI0 HAL uses this callback.
   Two rows are fixed-width ASCII with a terminating NUL. */
typedef int (*arc1_lcd_rows_fn)(void *context, const char row0[17], const char row1[17]);
/* Returns 0 on callback success; -1 invalid argument or stage; -2 READY denied;
   otherwise forwards the transport callback's error. */
int arc1_lcd_emit(arc1_boot_stage_t stage, unsigned verified,
                  arc1_lcd_rows_fn write_rows, void *context);
#endif
