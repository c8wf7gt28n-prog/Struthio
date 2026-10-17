#ifndef ARC1_SERLCD_I2C_H
#define ARC1_SERLCD_I2C_H
#include <stdint.h>
#include <stddef.h>
#define ARC1_SERLCD_DEFAULT_ADDR 0x72u
/* Bus callback must finish the transaction synchronously. Nonzero means error.
   Physical pinmux, clocks, pullups, timeouts and recovery belong to F133 BSP. */
typedef int (*arc1_i2c_write_fn)(void *context, uint8_t addr, const uint8_t *bytes, size_t count);
typedef struct arc1_serlcd_bus {
    arc1_i2c_write_fn write;
    void *context;
    uint8_t address;
} arc1_serlcd_bus_t;
/* Accepts EXACT 16 ASCII characters per row (NUL byte at position 16).
   No LCD access until a real board TWI HAL installs the callback. */
int arc1_serlcd_write_rows(void *context, const char row0[17], const char row1[17]);
#endif
