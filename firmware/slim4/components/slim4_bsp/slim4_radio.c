/* SLIM4 radio driver (PCB R28+): U15 RAK3172-SiP (STM32WLE5 running RAKwireless RUI3) on UART1, pins in slim4_pins.h.
 * The module takes AT commands on its UART2 at 115200 8N1 (RAK3172 datasheet; RUI3 AT command manual: AT, AT+VER=?,
 * AT+NWM=<0 P2P | 1 LoRaWAN>, AT+P2P=<freq>:<sf>:<bw>:<cr>:<preamble>:<dBm>, AT+PSEND=<hex>, AT+PRECV=<ms>, replies
 * OK / AT_*_ERROR and events +EVT:TXP2P DONE, +EVT:RXP2P:<rssi>:<snr>:<hex>, +EVT:RXP2P RECEIVE TIMEOUT).
 *
 * NRST is driven open-drain (low only), so U1 never feeds an unpowered module through it. BOOT0 is not on U1: R702
 * holds it low, so the SiP always starts RUI3 (which updates itself over this UART after AT+BOOT); a wire from R702's
 * BOOT0 pad to R703's RADIO_3V3 pad starts the STM32 ROM bootloader for recovery. Every wait is bounded. A board without the
 * module (its TX line, U1's RX, pulled down by U1 and nothing driving it) reads as "not fitted" and is left alone. */
#include "slim4_radio.h"

#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/uart.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "slim4_pins.h"

static const char *TAG = "slim4_radio";

#define RADIO_UART      UART_NUM_1
#define BAUD            115200
#define BOOT_LIMIT_MS   1500        /* NRST release to the first "OK" (RUI3 starts in a few hundred ms) */
#define CMD_LIMIT_MS    400

static bool s_uart, s_present;
static int s_nwm = -1;
static SemaphoreHandle_t s_lock;

static int64_t now_ms(void) { return esp_timer_get_time() / 1000; }

static void pins_safe(void)
{
    (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 1);                    /* open drain: released */
    const gpio_config_t nrst = {.pin_bit_mask = 1ULL << SLIM4_GPIO_RADIO_NRST, .mode = GPIO_MODE_OUTPUT_OD};
    (void)gpio_config(&nrst);
}

static bool uart_up(void)
{
    if (s_uart) return true;
    if (!s_lock) s_lock = xSemaphoreCreateMutex();
    const uart_config_t c = {.baud_rate = BAUD, .data_bits = UART_DATA_8_BITS, .parity = UART_PARITY_DISABLE,
                             .stop_bits = UART_STOP_BITS_1, .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
                             .source_clk = UART_SCLK_DEFAULT};
    if (uart_driver_install(RADIO_UART, 1024, 0, 0, NULL, 0) != ESP_OK) return false;
    if (uart_param_config(RADIO_UART, &c) != ESP_OK ||
        uart_set_pin(RADIO_UART, SLIM4_GPIO_RADIO_UART_TX, SLIM4_GPIO_RADIO_UART_RX, UART_PIN_NO_CHANGE,
                     UART_PIN_NO_CHANGE) != ESP_OK) {
        (void)uart_driver_delete(RADIO_UART);
        return false;
    }
    s_uart = true;
    return true;
}

/* Read one line (CR/LF stripped) within limit_ms; false on timeout. */
static bool read_line(char *buf, size_t len, int limit_ms)
{
    size_t n = 0;
    const int64_t end = now_ms() + limit_ms;
    while (now_ms() < end) {
        uint8_t c;
        if (uart_read_bytes(RADIO_UART, &c, 1, pdMS_TO_TICKS(10)) != 1) continue;
        if (c == '\r') continue;
        if (c == '\n') {
            if (n == 0) continue;
            buf[n] = '\0';
            return true;
        }
        if (n + 1 < len) buf[n++] = (char)c;
    }
    buf[n] = '\0';
    return false;
}

static void send_cmd(const char *cmd)
{
    (void)uart_write_bytes(RADIO_UART, cmd, strlen(cmd));
    (void)uart_write_bytes(RADIO_UART, "\r\n", 2);
}

/* Send a command and wait for OK or an error; a query's value line is copied to value. */
static slim4_at_kind_t command(const char *cmd, char *value, size_t vlen, int limit_ms)
{
    char line[160];
    slim4_at_line_t at;
    if (value && vlen) value[0] = '\0';
    (void)uart_flush_input(RADIO_UART);
    send_cmd(cmd);
    const int64_t end = now_ms() + limit_ms;
    while (now_ms() < end) {
        if (!read_line(line, sizeof(line), (int)(end - now_ms()))) break;
        slim4_at_parse(line, &at);
        if (at.kind == SLIM4_AT_OK || at.kind == SLIM4_AT_ERROR) return at.kind;
        if (at.kind == SLIM4_AT_VALUE && value && vlen && strcmp(line, cmd) != 0) {   /* skip an echo */
            const char *eq = strchr(line, '=');
            const char *v = eq && !strncmp(line, "AT+", 3) ? eq + 1 : line;
            size_t n = strlen(v);
            if (n >= vlen) n = vlen - 1;                      /* a long answer is cut, not an error */
            memcpy(value, v, n);
            value[n] = '\0';
        }
    }
    return SLIM4_AT_NONE;
}

void slim4_radio_probe(slim4_radio_probe_t *out)
{
    memset(out, 0, sizeof(*out));
    out->nwm = -1;
    if (!s_lock) s_lock = xSemaphoreCreateMutex();
    xSemaphoreTake(s_lock, portMAX_DELAY);
    s_present = false;
    pins_safe();
    /* before the UART owns it: U1's RX pin as an input pulled down, to see whether anything drives the line */
    if (s_uart) { (void)uart_driver_delete(RADIO_UART); s_uart = false; }
    const gpio_config_t rx = {.pin_bit_mask = 1ULL << SLIM4_GPIO_RADIO_UART_RX, .mode = GPIO_MODE_INPUT,
                              .pull_down_en = GPIO_PULLDOWN_ENABLE};
    (void)gpio_config(&rx);
    (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 0);                    /* reset: the STM32's pins go high-impedance */
    vTaskDelay(pdMS_TO_TICKS(5));
    out->rx_low_in_reset = gpio_get_level(SLIM4_GPIO_RADIO_UART_RX) == 0;
    (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 1);
    const int64_t released = now_ms();
    while (now_ms() - released < 300) {                                /* RUI3 drives its TX high once its UART is up */
        if (gpio_get_level(SLIM4_GPIO_RADIO_UART_RX)) { out->rx_high_after = true; break; }
        vTaskDelay(pdMS_TO_TICKS(2));
    }
    out->uart_ready = uart_up();
    if (!out->uart_ready) { ESP_LOGE(TAG, "UART1 setup failed"); goto done; }
    if (!out->rx_high_after) goto done;                                /* nothing drives the line: no module */
    while (now_ms() - released < BOOT_LIMIT_MS) {
        if (command("AT", NULL, 0, 100) == SLIM4_AT_OK) {
            out->answered = true;
            out->answer_ms = (uint32_t)(now_ms() - released);
            break;
        }
    }
    if (!out->answered) goto done;
    (void)command("AT+VER=?", out->version, sizeof(out->version), CMD_LIMIT_MS);
    char v[16];
    if (command("AT+NWM=?", v, sizeof(v), CMD_LIMIT_MS) == SLIM4_AT_OK && (v[0] == '0' || v[0] == '1')) out->nwm = v[0] - '0';
    s_nwm = out->nwm;
    s_present = true;
done:
    xSemaphoreGive(s_lock);
}

bool slim4_radio_present(void) { return s_present; }

static uint32_t my_id(void)
{
    uint8_t mac[6] = {0};
    (void)esp_efuse_mac_get_default(mac);
    return (uint32_t)mac[2] << 24 | (uint32_t)mac[3] << 16 | (uint32_t)mac[4] << 8 | mac[5];
}

/* P2P mode and the channel settings; AT+NWM=0 makes RUI3 restart, so it is sent only when the mode differs. */
static bool setup_p2p(uint32_t freq_hz, int dbm)
{
    if (s_nwm != 0) {
        send_cmd("AT+NWM=0");
        vTaskDelay(pdMS_TO_TICKS(1500));
        bool back = false;
        for (int i = 0; i < 10 && !back; ++i) back = command("AT", NULL, 0, 200) == SLIM4_AT_OK;
        if (!back) return false;
        char v[16];
        if (command("AT+NWM=?", v, sizeof(v), CMD_LIMIT_MS) != SLIM4_AT_OK || v[0] != '0') return false;
        s_nwm = 0;
    }
    char cmd[64];
    if (!slim4_at_p2p_settings(cmd, sizeof(cmd), freq_hz, SLIM4_RADIO_SF, SLIM4_RADIO_BW_HZ, dbm)) return false;
    return command(cmd, NULL, 0, CMD_LIMIT_MS) == SLIM4_AT_OK;
}

static bool send_packet(const uint8_t *data, size_t n)
{
    char cmd[16 + 2 * SLIM4_RADIO_PING_LEN];
    (void)command("AT+PRECV=0", NULL, 0, CMD_LIMIT_MS);                /* stop any receive first */
    if (!slim4_at_psend(cmd, sizeof(cmd), data, n) || command(cmd, NULL, 0, CMD_LIMIT_MS) != SLIM4_AT_OK) return false;
    char line[160];
    slim4_at_line_t at;
    const int64_t end = now_ms() + 500;
    while (now_ms() < end) {
        if (!read_line(line, sizeof(line), (int)(end - now_ms()))) break;
        slim4_at_parse(line, &at);
        if (at.kind == SLIM4_AT_TX_DONE) return true;
    }
    return false;
}

/* Receive for up to ms; returns the payload length, 0 on timeout, -1 on a fault. */
static int receive(uint8_t *buf, size_t cap, unsigned ms, int *rssi, int *snr)
{
    char cmd[24];
    snprintf(cmd, sizeof(cmd), "AT+PRECV=%u", ms);
    if (command(cmd, NULL, 0, CMD_LIMIT_MS) != SLIM4_AT_OK) return -1;
    char line[160];
    slim4_at_line_t at;
    const int64_t end = now_ms() + ms + 200;
    while (now_ms() < end) {
        if (!read_line(line, sizeof(line), (int)(end - now_ms()))) break;
        slim4_at_parse(line, &at);
        if (at.kind == SLIM4_AT_RX_TIMEOUT) return 0;
        if (at.kind == SLIM4_AT_RX) {
            const size_t n = at.len < cap ? at.len : cap;
            memcpy(buf, at.payload, n);
            *rssi = at.rssi; *snr = at.snr;
            return (int)n;
        }
    }
    return 0;
}

static bool ready_for_link(uint32_t freq_hz, int dbm)
{
    if (!s_present) {
        slim4_radio_probe_t p;
        slim4_radio_probe(&p);
    }
    if (!s_present) {
        printf("radio: no module answering (run 'radio' for the probe report)\n");
        return false;
    }
    if (!slim4_radio_freq_ok(freq_hz, SLIM4_RADIO_BW_HZ)) {
        printf("radio: %lu Hz is not an allowed channel\n", (unsigned long)freq_hz);
        return false;
    }
    if (!setup_p2p(freq_hz, dbm)) {
        printf("radio: the module did not take the P2P settings\n");
        return false;
    }
    return true;
}

int slim4_radio_ping(unsigned n, uint32_t freq_hz, int dbm)
{
    if (!ready_for_link(freq_hz, dbm)) return -1;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    const uint32_t id = my_id();
    int answered = 0;
    for (unsigned i = 0; i < n; ++i) {
        slim4_radio_ping_t p = {.reply = false, .seq = (uint8_t)i, .sender = id};
        uint8_t buf[SLIM4_RADIO_PING_LEN];
        slim4_radio_ping_encode(&p, buf);
        const int64_t t0 = now_ms();
        if (!send_packet(buf, sizeof(buf))) { printf("ping %u: transmit failed\n", i); continue; }
        bool got = false;
        while (!got && now_ms() - t0 < 600) {
            int rssi = 0, snr = 0;
            uint8_t rx[64];
            const int len = receive(rx, sizeof(rx), 300, &rssi, &snr);
            if (len <= 0) break;
            slim4_radio_ping_t r;
            if (slim4_radio_ping_decode(rx, (uint8_t)len, &r) && r.reply && r.seq == p.seq && r.sender != id) {
                printf("ping %u: answer from %08lx in %lld ms; it heard us at %d dBm, we hear it at %d dBm, SNR %d dB\n", i,
                       (unsigned long)r.sender, (long long)(now_ms() - t0), r.rssi_heard, rssi, snr);
                got = true; ++answered;
            }
        }
        if (!got) printf("ping %u: no answer\n", i);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    printf("radio ping: %d of %u answered at %lu Hz, %d dBm\n", answered, n, (unsigned long)freq_hz, dbm);
    xSemaphoreGive(s_lock);
    return answered;
}

int slim4_radio_listen(unsigned seconds, uint32_t freq_hz, int dbm)
{
    if (!ready_for_link(freq_hz, dbm)) return -1;
    xSemaphoreTake(s_lock, portMAX_DELAY);
    const uint32_t id = my_id();
    const int64_t end = now_ms() + (int64_t)seconds * 1000;
    int heard = 0;
    printf("radio listen: %u s at %lu Hz\n", seconds, (unsigned long)freq_hz);
    while (now_ms() < end) {
        int rssi = 0, snr = 0;
        uint8_t rx[64];
        const int len = receive(rx, sizeof(rx), 1000, &rssi, &snr);
        if (len < 0) { printf("radio listen: receive fault\n"); break; }
        slim4_radio_ping_t p;
        if (len > 0 && slim4_radio_ping_decode(rx, (uint8_t)len, &p) && !p.reply && p.sender != id) {
            slim4_radio_ping_t r = {.reply = true, .seq = p.seq, .sender = id,
                                    .rssi_heard = (int8_t)(rssi < -128 ? -128 : rssi)};
            uint8_t buf[SLIM4_RADIO_PING_LEN];
            slim4_radio_ping_encode(&r, buf);
            const bool ok = send_packet(buf, sizeof(buf));
            printf("ping %u from %08lx at %d dBm, SNR %d dB: %s\n", p.seq, (unsigned long)p.sender, rssi, snr,
                   ok ? "answered" : "answer failed");
            ++heard;
        }
    }
    (void)command("AT+PRECV=0", NULL, 0, CMD_LIMIT_MS);
    printf("radio listen: %d pings heard\n", heard);
    xSemaphoreGive(s_lock);
    return heard;
}

void slim4_radio_at(const char *cmd, unsigned ms)
{
    if (!s_present) {
        slim4_radio_probe_t p;
        slim4_radio_probe(&p);
        if (!s_present) { printf("radio: no module answering\n"); return; }
    }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    (void)uart_flush_input(RADIO_UART);
    send_cmd(cmd);
    char line[160];
    const int64_t end = now_ms() + ms;
    while (now_ms() < end) {
        if (read_line(line, sizeof(line), (int)(end - now_ms()))) printf("  %s\n", line);
    }
    xSemaphoreGive(s_lock);
}
