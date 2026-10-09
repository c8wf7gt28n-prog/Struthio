/* Bring-up console over the USB-C port (USB-Serial-JTAG). Type a command and Enter in any serial terminal
 * (`idf.py monitor`, or 115200 8N1 on the USB port); `help` lists them. It reads pins, sets the backlight, shows test
 * patterns, plays tones on one side and repeats the self-test report, so a board can be probed with a meter in one
 * hand without reflashing.
 *
 * Output goes through stdout (UART0 and the USB port). Installing the USB-Serial-JTAG driver routes the USB output
 * through it too; when no host reads, the driver gives up after one short wait and drops output, so a board on a
 * charger or battery never stalls on it. */
#include "slim4_console.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/usb_serial_jtag.h"
#include "driver/usb_serial_jtag_vfs.h"
#include "esp_app_desc.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_heap_caps.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_psram.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "slim4_board.h"
#include "slim4_game_api.h"
#include "slim4_power.h"
#include "slim4_selftest.h"

static const char *TAG = "slim4_console";
static volatile bool s_display_hold;

bool slim4_console_display_hold(void)
{
    return s_display_hold;
}

static void cmd_help(void)
{
    printf("commands:\n"
           "  info                 chip, memory, flash, firmware, reset reason, uptime\n"
           "  report               the self-test lines again\n"
           "  page                 the self-test page on the panel (diag resumes the diagnostic screen)\n"
           "  gpio [n]             level of GPIO n, or of every self-test pin with its net\n"
           "  power                battery, USB, charger, input limit, backlight cap, die temperature\n"
           "  panel                panel probe result and frames per second over 1 s\n"
           "  bl <0-100>           backlight percent (still limited by the power policy's cap)\n"
           "  pattern <name>       white black red green blue bars checker gradient (holds the screen)\n"
           "  diag                 back to the diagnostic screen\n"
           "  display <normal|safe>  DSI profile for the next boot: normal 1000 Mbit/s 59 Hz, safe 560 Mbit/s 45 Hz\n"
           "  tone <left|right|both> [hz] [ms]   test tone, 20..20000 Hz, up to 3000 ms\n"
           "  vol <0-100>          master volume\n"
           "  sleep                power off (deep sleep; the power button wakes it)\n"
           "  reboot\n");
}

static void cmd_info(void)
{
    const esp_app_desc_t *app = esp_app_get_description();
    esp_chip_info_t chip;
    esp_chip_info(&chip);
    uint32_t id = 0, size = 0;
    const bool id_ok = esp_flash_read_id(NULL, &id) == ESP_OK;
    const bool size_ok = esp_flash_get_physical_size(NULL, &size) == ESP_OK;
    uint8_t mac[6] = {0};
    (void)esp_efuse_mac_get_default(mac);
    printf("firmware %s %s (%s %s)\n", app->project_name, app->version, app->date, app->time);
    printf("chip ESP32-P4 v%d.%d, %d cores; MAC %02X:%02X:%02X:%02X:%02X:%02X\n", chip.revision / 100,
           chip.revision % 100, chip.cores, mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    printf("flash ID %s%06lX, %lu MiB; PSRAM %u MiB\n", id_ok ? "" : "(read failed) ", (unsigned long)id,
           (unsigned long)(size_ok ? size >> 20 : 0), (unsigned)(esp_psram_get_size() >> 20));
    printf("heap free: internal %u B, PSRAM %u B; largest internal block %u B\n",
           (unsigned)heap_caps_get_free_size(MALLOC_CAP_INTERNAL), (unsigned)heap_caps_get_free_size(MALLOC_CAP_SPIRAM),
           (unsigned)heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL));
    printf("reset reason %d, up %.1f s\n", (int)esp_reset_reason(), esp_timer_get_time() / 1e6);
}

static void cmd_gpio(const char *arg)
{
    if (arg && *arg) {
        const int n = atoi(arg);
        if (n < 0 || n > 54 || !GPIO_IS_VALID_GPIO(n)) {
            printf("no GPIO %s\n", arg);
            return;
        }
        printf("GPIO%d = %d\n", n, gpio_get_level((gpio_num_t)n));
        return;
    }
    for (size_t i = 0; i < SLIM4_ST_PIN_COUNT; ++i) {
        const slim4_pin_desc_t *p = &SLIM4_ST_PINS[i];
        printf("  GPIO%-2u pad %-3u %-15s %d\n", p->gpio, p->pad, p->net, gpio_get_level((gpio_num_t)p->gpio));
    }
    printf("(a pin driven by a peripheral with its input buffer off reads 0)\n");
}

static void cmd_power(void)
{
    slim4_power_state_t ps;
    if (slim4_power_read(&ps) != SLIM4_OK) {
        printf("power service not running\n");
        return;
    }
    static const char *const usb[] = {"none", "default 500 mA", "1.5 A", "3 A"};
    printf("battery %u mV (%u %%)%s%s%s\n", ps.battery_mv, ps.battery_percent, ps.battery_approx ? " approx" : "",
           ps.battery_low ? " LOW" : "", ps.battery_fault ? " FAULT (reversed or shorted)" : "");
    printf("USB %s, USB-C %s, %s%s; input limit %u mA\n", ps.usb_power ? "valid (PGOOD low)" : "absent",
           usb[ps.usb_current < 4 ? ps.usb_current : 0], ps.charging ? "charging" : "not charging",
           ps.charge_suspended ? " (suspended: hot)" : "", ps.input_limit_ma);
    printf("backlight cap %u %%, audio %s, die %d C\n", ps.backlight_cap_percent, ps.audio_muted ? "MUTED" : "on",
           ps.chip_temp_c);
}

static void cmd_panel(void)
{
    slim4_panel_probe_t p;
    slim4_board_panel_probe(&p);
    printf("probe: %s; ID %02X %02X %02X%s; host flags before %08lX/%08lX, first %08lX/%08lX, after %08lX/%08lX\n",
           !p.attempted ? "not run" : (p.answered ? "answered" : "NO ANSWER"), p.id[0], p.id[1], p.id[2],
           p.repeat_ok ? "" : " (repeat differs)", (unsigned long)p.int_st0_before, (unsigned long)p.int_st1_before,
           (unsigned long)p.int_st0_first, (unsigned long)p.int_st1_first, (unsigned long)p.int_st0,
           (unsigned long)p.int_st1);
    if (p.stopped_at) printf("stopped at: %s\n", p.stopped_at);
    const uint32_t c0 = slim4_board_get_vsync_count();
    vTaskDelay(pdMS_TO_TICKS(1000));
    printf("frames in 1 s: %lu\n", (unsigned long)(slim4_board_get_vsync_count() - c0));
}

static void cmd_pattern(const char *arg)
{
    static const char *const names[] = {"white", "black", "red", "green", "blue", "bars", "checker", "gradient"};
    for (int i = 0; i < 8; ++i) {
        if (arg && !strcmp(arg, names[i])) {
            s_display_hold = true;
            vTaskDelay(pdMS_TO_TICKS(40));   /* let a diagnostic frame in flight finish */
            const slim4_status_t st = slim4_board_show_pattern((slim4_pattern_t)i);
            printf("%s: %s\n", names[i], st == SLIM4_OK ? "shown (diag to go back)" : "display not ready");
            return;
        }
    }
    printf("pattern: white black red green blue bars checker gradient\n");
}

static void cmd_tone(const char *side, const char *hz_s, const char *ms_s)
{
    const bool left = side && (!strcmp(side, "left") || !strcmp(side, "both"));
    const bool right = side && (!strcmp(side, "right") || !strcmp(side, "both"));
    if (!left && !right) {
        printf("tone <left|right|both> [hz] [ms]\n");
        return;
    }
    int hz = hz_s ? atoi(hz_s) : 1000, ms = ms_s ? atoi(ms_s) : 500;
    if (hz < 20 || hz > 20000 || ms < 10 || ms > 3000) {
        printf("20..20000 Hz, 10..3000 ms\n");
        return;
    }
    slim4_power_state_t ps;
    if (slim4_power_read(&ps) == SLIM4_OK && ps.audio_muted) {
        printf("audio is muted by the power policy (USB below 1 A, no qualified cell): no sound expected\n");
    }
    static int16_t buf[2048 * 2];
    const uint32_t total = (uint32_t)(48000 * ms / 1000);
    uint32_t done = 0;
    while (done < total) {
        uint32_t n = total - done;
        if (n > 2048) n = 2048;
        for (uint32_t i = 0; i < n; ++i) {
            const uint32_t k = done + i;
            const uint32_t phase = (uint32_t)((uint64_t)k * (uint32_t)hz % 48000u);
            int32_t v = phase < 24000u ? -12000 + (int32_t)(24000u * phase / 24000u)
                                       : 12000 - (int32_t)(24000u * (phase - 24000u) / 24000u);
            const uint32_t fade = 480;   /* 10 ms in and out: no click */
            if (k < fade) v = v * (int32_t)k / (int32_t)fade;
            if (total - k < fade) v = v * (int32_t)(total - k) / (int32_t)fade;
            buf[i * 2] = left ? (int16_t)v : 0;
            buf[i * 2 + 1] = right ? (int16_t)v : 0;
        }
        slim4_status_t st;
        int tries = 0;
        while ((st = slim4_audio_play_pcm_s16(buf, n, 48000)) == SLIM4_ERR_NOT_READY && ++tries < 200) {
            vTaskDelay(pdMS_TO_TICKS(5));
        }
        if (st != SLIM4_OK) {
            printf("audio error %d after %lu of %lu frames\n", (int)st, (unsigned long)done, (unsigned long)total);
            return;
        }
        done += n;
    }
    printf("tone %s %d Hz %d ms queued\n", side, hz, ms);
}

static void run_line(char *line)
{
    char *argv[4] = {0};
    int argc = 0;
    for (char *t = strtok(line, " \t"); t && argc < 4; t = strtok(NULL, " \t")) argv[argc++] = t;
    if (argc == 0) return;
    for (char *c = argv[0]; *c; ++c) *c = (char)tolower((unsigned char)*c);
    const char *cmd = argv[0];
    if (!strcmp(cmd, "help") || !strcmp(cmd, "?")) cmd_help();
    else if (!strcmp(cmd, "info")) cmd_info();
    else if (!strcmp(cmd, "report")) {
        const slim4_st_report_t *r = slim4_selftest_last();
        if (r) slim4_selftest_log(r);
        else printf("no self-test report yet\n");
    } else if (!strcmp(cmd, "page")) {
        const slim4_st_report_t *r = slim4_selftest_last();
        s_display_hold = true;
        vTaskDelay(pdMS_TO_TICKS(40));
        printf("%s\n", r && slim4_board_show_selftest(r) == SLIM4_OK ? "page shown (diag to go back)" : "display not ready");
    } else if (!strcmp(cmd, "gpio")) cmd_gpio(argv[1]);
    else if (!strcmp(cmd, "power")) cmd_power();
    else if (!strcmp(cmd, "panel")) cmd_panel();
    else if (!strcmp(cmd, "bl")) {
        const int v = argv[1] ? atoi(argv[1]) : -1;
        if (v < 0 || v > 100) printf("bl <0-100>\n");
        else printf("backlight %d %% (cap %u %%): %s\n", v, slim4_board_backlight_cap(),
                    slim4_board_set_backlight((uint8_t)v) == SLIM4_OK ? "set" : "display not ready");
    } else if (!strcmp(cmd, "pattern")) cmd_pattern(argv[1]);
    else if (!strcmp(cmd, "diag")) {
        s_display_hold = false;
        printf("diagnostic screen resumed\n");
    } else if (!strcmp(cmd, "display")) {
        const char *a = argv[1];
        if (a && (!strcmp(a, "normal") || !strcmp(a, "safe"))) {
            const slim4_status_t st = slim4_board_set_display_profile(!strcmp(a, "safe") ? SLIM4_DISPLAY_SAFE
                                                                                         : SLIM4_DISPLAY_NORMAL);
            printf("%s\n", st == SLIM4_OK ? "saved: reboot to apply" : "could not save (NVS)");
        } else {
            printf("display profile now: %s (display normal|safe)\n",
                   slim4_board_display_profile() == SLIM4_DISPLAY_SAFE ? "safe" : "normal");
        }
    } else if (!strcmp(cmd, "tone")) cmd_tone(argv[1], argv[2], argv[3]);
    else if (!strcmp(cmd, "vol")) {
        const int v = argv[1] ? atoi(argv[1]) : -1;
        printf("%s\n", v >= 0 && v <= 100 && slim4_audio_set_master_volume((uint8_t)v) == SLIM4_OK ? "volume set"
                                                                                                   : "vol <0-100>");
    } else if (!strcmp(cmd, "sleep")) {
        printf("power off\n");
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(100));
        slim4_power_off();
    } else if (!strcmp(cmd, "reboot")) {
        fflush(stdout);
        vTaskDelay(pdMS_TO_TICKS(100));
        esp_restart();
    } else printf("unknown command '%s' (help)\n", cmd);
}

static void console_task(void *arg)
{
    (void)arg;
    char line[96];
    size_t len = 0;
    printf("\nslim4 console: type help and Enter\n> ");
    fflush(stdout);
    for (;;) {
        uint8_t c;
        if (usb_serial_jtag_read_bytes(&c, 1, portMAX_DELAY) != 1) continue;
        if (c == '\r' || c == '\n') {
            printf("\n");
            line[len] = '\0';
            run_line(line);
            len = 0;
            printf("> ");
        } else if ((c == 0x7F || c == 0x08) && len > 0) {
            --len;
            printf("\b \b");
        } else if (c >= 0x20 && c < 0x7F && len + 1 < sizeof(line)) {
            line[len++] = (char)c;
            putchar(c);
        }
        fflush(stdout);
    }
}

void slim4_console_start(void)
{
    usb_serial_jtag_driver_config_t cfg = USB_SERIAL_JTAG_DRIVER_CONFIG_DEFAULT();
    cfg.tx_buffer_size = 4096;   /* the self-test report comes out in one burst */
    esp_err_t err = usb_serial_jtag_driver_install(&cfg);
    if (err != ESP_OK) {
        ESP_LOGW(TAG, "USB-Serial-JTAG driver: %s; no console", esp_err_to_name(err));
        return;
    }
    usb_serial_jtag_vfs_use_driver();
    if (xTaskCreate(console_task, "slim4_console", 6144, NULL, 2, NULL) != pdPASS) {
        ESP_LOGW(TAG, "no memory for the console task");
    }
}
