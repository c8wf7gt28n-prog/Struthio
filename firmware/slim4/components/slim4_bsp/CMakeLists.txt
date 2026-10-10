idf_component_register(SRCS "slim4_board.c" "slim4_power.c" "slim4_panel_cfaf.c" "slim4_selftest.c" "slim4_selftest_logic.c"
                            "slim4_radio.c" "slim4_radio_logic.c"
                       INCLUDE_DIRS "include"
                       REQUIRES esp_common esp_driver_gpio esp_driver_i2s esp_driver_ledc esp_driver_spi esp_driver_tsens
                                esp_driver_usb_serial_jtag esp_adc esp_hal_lcd esp_hw_support esp_lcd esp_lcd_ili9881c
                                esp_psram esp_system esp_timer freertos heap nvs_flash slim4_types soc spi_flash log)
