/* ARC-1 identity contract — host-verified strings, NOT flashed firmware.
   Firmware boot stages and hardware LCD pinout remain unverified. */
#ifndef ARC1_BRAND_H
#define ARC1_BRAND_H

#define ARC1_BRAND_NAME "ARC-1"
#define ARC1_BRAND_EXPANSION "Adaptive RISC-V Console"
#define ARC1_LCD_WIDTH 16
#define ARC1_LCD_ROWS 2

typedef enum arc1_boot_stage {
    ARC1_BOOT_POWER = 0,
    ARC1_BOOT_F133,
    ARC1_BOOT_NOR,
    ARC1_BOOT_D213,
    ARC1_BOOT_FPGA12,
    ARC1_BOOT_FPGA45,
    ARC1_BOOT_CARTRIDGE,
    ARC1_BOOT_READY,
    ARC1_BOOT_SERVICE,
    ARC1_BOOT_RECOVERY,
    ARC1_BOOT_FAULT
} arc1_boot_stage_t;

/* Text rows in ASCII; actual LCD driver formats/pads them and owns I2C. */
typedef struct arc1_lcd_message {
    const char *row0;
    const char *row1;
} arc1_lcd_message_t;

static inline arc1_lcd_message_t arc1_boot_lcd_message(arc1_boot_stage_t stage) {
    switch (stage) {
    case ARC1_BOOT_POWER: return (arc1_lcd_message_t){"ARC-1  POWER", "RAILS CHECK"};
    case ARC1_BOOT_F133: return (arc1_lcd_message_t){"ARC-1  START", "F133 BOOT"};
    case ARC1_BOOT_NOR: return (arc1_lcd_message_t){"ARC-1  SYSTEM", "NOR VERIFY"};
    case ARC1_BOOT_D213: return (arc1_lcd_message_t){"ARC-1  VIDEO", "D213 INIT"};
    case ARC1_BOOT_FPGA12: return (arc1_lcd_message_t){"ARC-1  FPGA12", "CONFIG TEST"};
    case ARC1_BOOT_FPGA45: return (arc1_lcd_message_t){"ARC-1  FPGA45", "CONFIG TEST"};
    case ARC1_BOOT_CARTRIDGE: return (arc1_lcd_message_t){"ARC-1  STORAGE", "USB GAME SCAN"};
    case ARC1_BOOT_READY: return (arc1_lcd_message_t){"ARC-1   READY", "INSERT GAME"};
    case ARC1_BOOT_SERVICE: return (arc1_lcd_message_t){"ARC-1  SERVICE", "USB-C DATA"};
    case ARC1_BOOT_RECOVERY: return (arc1_lcd_message_t){"ARC-1 RECOVERY", "DIAGNOSTICS"};
    case ARC1_BOOT_FAULT: return (arc1_lcd_message_t){"ARC-1   FAULT", "SEE ERROR CODE"};
    default: return (arc1_lcd_message_t){"ARC-1  UNKNOWN", "SEE DIAGNOSTIC"};
    }
}
#endif /* ARC1_BRAND_H */
