// STRUTHIO HANDHELD · AXP2101 power management for the Waveshare
// ESP32-S3-Touch-LCD-3.5B.
//
// Adapted from Waveshare's example (Apache-2.0):
// ESP-IDF/01_factory/components/esp_bsp/bsp_axp2101.cpp, repository
// waveshareteam/ESP32-S3-Touch-LCD-3.5B, commit 840daf2. The rail voltages and
// enables are copied exactly. The schematic is not in hand, so we cannot tell
// which rail feeds the LCD, audio or camera; leaving a rail off is a bring-up
// experiment, not a default. Removed from the example: the debug prints, the
// IRQ set-up and the PMU watchdog (nothing services them in STRUTHIO).
// Uses XPowersLib (MIT, components/XPowersLib).
#include <cstdlib>
#include <cstring>
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "board_pmu.h"

#define XPOWERS_CHIP_AXP2101
#include "XPowersLib.h"

static const char *TAG = "pmu";
static XPowersPMU s_pmu;
static i2c_master_dev_handle_t s_dev;
static bool s_ok;

static int reg_read(uint8_t, uint8_t reg, uint8_t *data, uint8_t len) {
    if (!len) return 0;
    if (!data) return -1;
    return i2c_master_transmit_receive(s_dev, &reg, 1, data, len, pdMS_TO_TICKS(1000)) == ESP_OK ? 0 : -1;
}
static int reg_write(uint8_t, uint8_t reg, uint8_t *data, uint8_t len) {
    if (!data) return -1;
    uint8_t buf[1 + 32];
    if (len > 32) return -1;
    buf[0] = reg;
    memcpy(buf + 1, data, len);
    return i2c_master_transmit(s_dev, buf, len + 1, pdMS_TO_TICKS(1000)) == ESP_OK ? 0 : -1;
}

extern "C" bool board_pmu_init(i2c_master_bus_handle_t bus) {
    i2c_device_config_t dev = {};
    dev.dev_addr_length = I2C_ADDR_BIT_LEN_7;
    dev.device_address = AXP2101_SLAVE_ADDRESS;          // 0x34
    dev.scl_speed_hz = 400 * 1000;
    if (i2c_master_bus_add_device(bus, &dev, &s_dev) != ESP_OK) return false;
    if (!s_pmu.begin(AXP2101_SLAVE_ADDRESS, reg_read, reg_write)) {
        ESP_LOGE(TAG, "AXP2101 not found");
        return false;
    }
    // input and system limits (vendor values)
    s_pmu.setVbusVoltageLimit(XPOWERS_AXP2101_VBUS_VOL_LIM_4V36);
    s_pmu.setVbusCurrentLimit(XPOWERS_AXP2101_VBUS_CUR_LIM_1500MA);
    s_pmu.setSysPowerDownVoltage(2600);
    // rails (vendor values; DC1 is the system 3.3 V and is already on)
    s_pmu.setDC1Voltage(3300);
    s_pmu.setDC2Voltage(1000);
    s_pmu.setDC3Voltage(3300);
    s_pmu.setDC4Voltage(1000);
    s_pmu.setDC5Voltage(3300);
    s_pmu.setALDO1Voltage(3300);
    s_pmu.setALDO2Voltage(3300);
    s_pmu.setALDO3Voltage(3300);
    s_pmu.setALDO4Voltage(3300);
    s_pmu.setBLDO1Voltage(1500);
    s_pmu.setBLDO2Voltage(2800);
    s_pmu.setCPUSLDOVoltage(1000);
    s_pmu.setDLDO1Voltage(3300);
    s_pmu.setDLDO2Voltage(3300);
    s_pmu.enableDC2();
    s_pmu.enableDC3();
    s_pmu.enableDC4();
    s_pmu.enableDC5();
    s_pmu.enableALDO1();
    s_pmu.enableALDO2();
    s_pmu.enableALDO3();
    s_pmu.enableALDO4();
    s_pmu.enableBLDO1();
    s_pmu.enableBLDO2();
    s_pmu.enableCPUSLDO();
    s_pmu.enableDLDO1();
    s_pmu.enableDLDO2();
    // power key (until board_pmu_model says which handheld). On the STRUTHIO ONE the slide switch is the on/off: when it turns on, the ONE board holds
    // PWR (header pin 24) low for ~3-8 s, because on battery alone the AXP2101 waits for that key before it
    // connects the battery (datasheet 6.5.2). So a long press must never mean "power off": that is switched
    // off here, at every boot (the slide switch's hard cut resets the PMU's registers each time).
    s_pmu.disableLongPressShutdown();
    s_pmu.setPowerKeyPressOffTime(XPOWERS_POWEROFF_10S);
    s_pmu.setPowerKeyPressOnTime(XPOWERS_POWERON_128MS);
    // measurement and charger: 4.1 V target (vendor value, gentle on the cell). The constant current starts at
    // 100 mA, safe for the ONE SLIM's 250 mAh cell (0.4 C); board_pmu_model sets 200 mA on the ONE.
    s_pmu.disableTSPinMeasure();
    s_pmu.enableBattDetection();
    s_pmu.enableVbusVoltageMeasure();
    s_pmu.enableBattVoltageMeasure();
    s_pmu.enableSystemVoltageMeasure();
    s_pmu.setChargingLedMode(XPOWERS_CHG_LED_OFF);
    s_pmu.setPrechargeCurr(XPOWERS_AXP2101_PRECHARGE_50MA);
    s_pmu.setChargerConstantCurr(XPOWERS_AXP2101_CHG_CUR_100MA);
    s_pmu.setChargerTerminationCurr(XPOWERS_AXP2101_CHG_ITERM_25MA);
    s_pmu.setChargeTargetVoltage(XPOWERS_AXP2101_CHG_VOL_4V1);
    s_pmu.enableButtonBatteryCharge();
    s_pmu.setButtonBatteryChargeVoltage(3300);
    s_ok = true;
    ESP_LOGI(TAG, "AXP2101 id 0x%x, battery %s", s_pmu.getChipID(), s_pmu.isBatteryConnect() ? "present" : "absent");
    return true;
}

extern "C" bool board_pmu_read(board_power_t *out) {
    if (!s_ok || !out) return false;
    out->battery_present = s_pmu.isBatteryConnect();
    out->charging = s_pmu.isCharging();
    out->vbus_present = s_pmu.isVbusIn();
    out->battery_mv = s_pmu.getBattVoltage();
    out->battery_percent = out->battery_present ? s_pmu.getBatteryPercent() : -1;
    return true;
}

extern "C" void board_pmu_power_off(void) {
    if (s_ok) s_pmu.shutdown();
}

extern "C" void board_pmu_model(bool slide_switch) {
    if (!s_ok) return;
    if (slide_switch) {                              // ONE: see the power key note in board_pmu_init
        s_pmu.disableLongPressShutdown();
        s_pmu.setPowerKeyPressOffTime(XPOWERS_POWEROFF_10S);
        s_pmu.setChargerConstantCurr(XPOWERS_AXP2101_CHG_CUR_200MA);   // THOR-503450, 1000 mAh: 0.2 C
    } else {                                         // ONE SLIM: the PWR key is the power button
        s_pmu.setPowerKeyPressOnTime(XPOWERS_POWERON_512MS);         // kept while the cell stays connected
        s_pmu.setPowerKeyPressOffTime(XPOWERS_POWEROFF_4S);
        s_pmu.setLongPressPowerOFF();
        s_pmu.enableLongPressShutdown();
        s_pmu.setChargerConstantCurr(XPOWERS_AXP2101_CHG_CUR_100MA);   // 302535, 250 mAh: 0.4 C
        s_pmu.disableIRQ(XPOWERS_AXP2101_ALL_IRQ);                     // only the short-press flag (self-test)
        s_pmu.enableIRQ(XPOWERS_AXP2101_PKEY_SHORT_IRQ);
        s_pmu.clearIrqStatus();
    }
}

extern "C" bool board_pmu_key_pressed(void) {
    if (!s_ok) return false;
    s_pmu.getIrqStatus();
    bool pressed = s_pmu.isPekeyShortPressIrq();
    if (pressed) s_pmu.clearIrqStatus();
    return pressed;
}
