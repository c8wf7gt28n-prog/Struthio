idf_component_register(
    SRCS "main.c" "struthio_buttons.c" "service.c" "selftest.c" "board_waveshare_35b.c" "board_pmu.cpp"
    INCLUDE_DIRS "."
    REQUIRES struthio driver esp_timer nvs_flash esp_lcd esp_system esp_hw_support esp_partition XPowersLib
    # One golden trace rides in flash so service mode can prove the core on the device.
    EMBED_FILES "../../golden/climb.trace"
)
