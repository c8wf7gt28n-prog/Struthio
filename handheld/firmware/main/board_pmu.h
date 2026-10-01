// STRUTHIO HANDHELD · AXP2101 PMIC (board_pmu.cpp, adapted from the Waveshare example).
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "driver/i2c_master.h"
#include "board.h"

#ifdef __cplusplus
extern "C" {
#endif
bool board_pmu_init(i2c_master_bus_handle_t bus);   // rails, charger, power key (vendor values)
bool board_pmu_read(board_power_t *out);
void board_pmu_power_off(void);
#ifdef __cplusplus
}
#endif
