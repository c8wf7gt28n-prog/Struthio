idf_component_register(SRCS "app_main.c" INCLUDE_DIRS "." REQUIRES slim4_game_api slim4_bsp slim4_system_update app_update esp_app_format esp_common esp_partition esp_system freertos log)
