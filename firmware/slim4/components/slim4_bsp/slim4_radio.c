/* SLIM4 radio driver (PCB R28+): U15 Seeed Wio-SX1262 on SPI2, pins in slim4_pins.h. Command set and timings from the
 * Semtech SX1261/2 datasheet (rev 2.1): section 13 (commands), 8.3 (BUSY), 9.6 (calibration), 15 (errata 15.1, 15.2,
 * 15.4). The Wio-SX1262 specifics (Seeed datasheet V1.1): a 32 MHz TCXO powered from DIO3, the module's TX/RX switch
 * driven by DIO2, an RF_SW input that enables the receive path (driven high only while receiving, as RadioLib's RXEN),
 * a DC-DC regulator fitted inside the module.
 *
 * Every wait is bounded. A board without the module (BUSY and MISO pulled down by U1, nothing answering) reads as
 * "not fitted" and is left alone: all radio pins inputs except NSS (high) and NRST (high). */
#include "slim4_radio.h"

#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "driver/spi_master.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_rom_sys.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "slim4_pins.h"

static const char *TAG = "slim4_radio";

#define SPI_HZ            8000000     /* SX1262 SPI up to 16 MHz */
#define BUSY_CMD_US       10000       /* BUSY after an ordinary command: under 1 ms */
#define BUSY_BOOT_US      20000       /* after reset: cold start with calibration, about 3.5 ms */
#define BUSY_CAL_US       30000       /* Calibrate with the 5 ms TCXO start: about 9 ms */
#define TCXO_DELAY        320u        /* 5 ms in 15.625 us steps */

/* SX1262 opcodes (datasheet 13) */
enum {
    OP_SET_SLEEP = 0x84, OP_SET_STANDBY = 0x80, OP_SET_TX = 0x83, OP_SET_RX = 0x82, OP_SET_REGULATOR = 0x96,
    OP_CALIBRATE = 0x89, OP_CALIBRATE_IMAGE = 0x98, OP_SET_PA_CONFIG = 0x95, OP_WRITE_REG = 0x0D, OP_READ_REG = 0x1D,
    OP_WRITE_BUF = 0x0E, OP_READ_BUF = 0x1E, OP_SET_DIO_IRQ = 0x08, OP_GET_IRQ = 0x12, OP_CLEAR_IRQ = 0x02,
    OP_DIO2_RF_SWITCH = 0x9D, OP_DIO3_TCXO = 0x97, OP_SET_RF_FREQ = 0x86, OP_SET_PACKET_TYPE = 0x8A,
    OP_SET_TX_PARAMS = 0x8E, OP_SET_MOD_PARAMS = 0x8B, OP_SET_PKT_PARAMS = 0x8C, OP_SET_BUF_BASE = 0x8F,
    OP_GET_STATUS = 0xC0, OP_GET_RX_BUF_STATUS = 0x13, OP_GET_PKT_STATUS = 0x14, OP_GET_ERRORS = 0x17,
    OP_CLEAR_ERRORS = 0x07,
};
enum { IRQ_TX_DONE = 1u << 0, IRQ_RX_DONE = 1u << 1, IRQ_HEADER_ERR = 1u << 5, IRQ_CRC_ERR = 1u << 6, IRQ_TIMEOUT = 1u << 9 };
#define REG_SYNC_WORD     0x0740
#define REG_TX_MODULATION 0x0889      /* errata 15.1: bit 2 clear for 500 kHz LoRa */
#define REG_TX_CLAMP      0x08D8      /* errata 15.2: bits 4:1 set */
#define REG_IQ_POLARITY   0x0736      /* errata 15.4: bit 2 set for standard IQ */
#define REG_OCP           0x08E7

/* DIO1 and NRST are optional: a board revision that does not wire them defines the pin as GPIO_NUM_NC. Without DIO1
 * the interrupt flags are polled over SPI (GetIrqStatus); without NRST the SX1262 starts at power-up (its NRESET has
 * a pull-up on the board) and a stuck chip is recovered by SetStandby. */
#define HAS_DIO1 (SLIM4_GPIO_RADIO_DIO1 >= 0)
#define HAS_NRST (SLIM4_GPIO_RADIO_NRST >= 0)

static spi_device_handle_t s_dev;
static bool s_bus, s_present, s_asleep;
static SemaphoreHandle_t s_lock;

static void pins_safe(void)
{
    /* inputs with U1's pull-downs (a missing module then reads 0), RF_SW low, NRST high */
    uint64_t in_mask = 1ULL << SLIM4_GPIO_RADIO_BUSY, out_mask = 1ULL << SLIM4_GPIO_RADIO_RF_SW;
    if (HAS_DIO1) in_mask |= 1ULL << SLIM4_GPIO_RADIO_DIO1;
    if (HAS_NRST) out_mask |= 1ULL << SLIM4_GPIO_RADIO_NRST;
    const gpio_config_t in = {.pin_bit_mask = in_mask, .mode = GPIO_MODE_INPUT, .pull_down_en = GPIO_PULLDOWN_ENABLE};
    (void)gpio_config(&in);
    (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 0);
    if (HAS_NRST) (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 1);
    const gpio_config_t out = {.pin_bit_mask = out_mask, .mode = GPIO_MODE_OUTPUT};
    (void)gpio_config(&out);
}

static bool bus_up(void)
{
    if (s_bus) return true;
    if (!s_lock) s_lock = xSemaphoreCreateMutex();
    pins_safe();
    const spi_bus_config_t bc = {.mosi_io_num = SLIM4_GPIO_RADIO_MOSI, .miso_io_num = SLIM4_GPIO_RADIO_MISO,
                                 .sclk_io_num = SLIM4_GPIO_RADIO_SCK, .quadwp_io_num = -1, .quadhd_io_num = -1,
                                 .max_transfer_sz = 64};
    if (spi_bus_initialize(SPI2_HOST, &bc, SPI_DMA_DISABLED) != ESP_OK) return false;
    const spi_device_interface_config_t dc = {.clock_speed_hz = SPI_HZ, .mode = 0,
                                              .spics_io_num = SLIM4_GPIO_RADIO_NSS, .queue_size = 1};
    if (spi_bus_add_device(SPI2_HOST, &dc, &s_dev) != ESP_OK) {
        (void)spi_bus_free(SPI2_HOST);
        return false;
    }
    (void)gpio_pulldown_en(SLIM4_GPIO_RADIO_MISO);   /* no module: MISO reads 0 */
    s_bus = true;
    return true;
}

static int64_t now_us(void) { return esp_timer_get_time(); }

/* Wait for BUSY low; returns the wait in us, or -1 on timeout. */
static int32_t wait_busy(uint32_t limit_us)
{
    const int64_t t0 = now_us();
    while (gpio_get_level(SLIM4_GPIO_RADIO_BUSY)) {
        const int64_t dt = now_us() - t0;
        if (dt > limit_us) return -1;
        if (dt > 2000) vTaskDelay(1);
    }
    return (int32_t)(now_us() - t0);
}

static bool xfer(const uint8_t *tx, uint8_t *rx, size_t n)
{
    spi_transaction_t t = {.length = 8 * n, .tx_buffer = tx, .rx_buffer = rx};
    return spi_device_polling_transmit(s_dev, &t) == ESP_OK;
}

/* One command: wait for BUSY low, then the transfer. rx may be NULL. */
static bool cmd(const uint8_t *tx, uint8_t *rx, size_t n)
{
    uint8_t dummy[64];
    if (n > sizeof(dummy)) return false;
    if (wait_busy(BUSY_CMD_US) < 0) return false;
    return xfer(tx, rx ? rx : dummy, n);
}

static bool wake(void)
{
    if (!s_asleep) return true;
    /* NSS falling edge wakes it (datasheet 13.1.1); BUSY then stays high until it is ready */
    uint8_t tx[2] = {OP_GET_STATUS, 0}, rx[2];
    (void)xfer(tx, rx, 2);
    s_asleep = false;
    return wait_busy(BUSY_BOOT_US) >= 0;
}

static bool read_regs(uint16_t addr, uint8_t *out, size_t n)
{
    uint8_t tx[4 + 8] = {OP_READ_REG, (uint8_t)(addr >> 8), (uint8_t)addr, 0}, rx[4 + 8];
    if (n > 8 || !cmd(tx, rx, 4 + n)) return false;
    memcpy(out, rx + 4, n);
    return true;
}

static bool write_regs(uint16_t addr, const uint8_t *in, size_t n)
{
    uint8_t tx[3 + 8] = {OP_WRITE_REG, (uint8_t)(addr >> 8), (uint8_t)addr};
    if (n > 8) return false;
    memcpy(tx + 3, in, n);
    return cmd(tx, NULL, 3 + n);
}

static bool reg_update(uint16_t addr, uint8_t clear, uint8_t set)
{
    uint8_t v;
    if (!read_regs(addr, &v, 1)) return false;
    v = (uint8_t)((v & ~clear) | set);
    return write_regs(addr, &v, 1);
}

static bool get_status(uint8_t *st)
{
    uint8_t tx[2] = {OP_GET_STATUS, 0}, rx[2];
    if (!cmd(tx, rx, 2)) return false;
    *st = rx[1];
    return true;
}

static bool get_errors(uint16_t *err)
{
    uint8_t tx[4] = {OP_GET_ERRORS, 0, 0, 0}, rx[4];
    if (!cmd(tx, rx, 4)) return false;
    *err = (uint16_t)((rx[2] << 8) | rx[3]);
    return true;
}

static bool get_irq(uint16_t *irq)
{
    uint8_t tx[4] = {OP_GET_IRQ, 0, 0, 0}, rx[4];
    if (!cmd(tx, rx, 4)) return false;
    *irq = (uint16_t)((rx[2] << 8) | rx[3]);
    return true;
}

static bool clear_irq(void)
{
    const uint8_t tx[3] = {OP_CLEAR_IRQ, 0xFF, 0xFF};
    return cmd(tx, NULL, 3);
}

static bool standby(void)
{
    const uint8_t tx[2] = {OP_SET_STANDBY, 0x00};   /* STDBY_RC */
    return cmd(tx, NULL, 2);
}

static void sleep_radio(void)
{
    (void)standby();
    (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 0);
    const uint8_t tx[2] = {OP_SET_SLEEP, 0x04};    /* warm start: configuration kept */
    if (cmd(tx, NULL, 2)) s_asleep = true;
}

/* Reset, regulator, TCXO, calibration, RF switch (datasheet 9.6, 13.3.6, 13.1.12). */
static bool init_chip(void)
{
    const uint8_t code = slim4_radio_tcxo_code(SLIM4_RADIO_TCXO_MV);
    const uint8_t c_standby[2] = {OP_SET_STANDBY, 0x00};
    const uint8_t c_reg[2] = {OP_SET_REGULATOR, 0x01};                                    /* DC-DC (fitted in the module) */
    const uint8_t c_tcxo[5] = {OP_DIO3_TCXO, code, 0, (uint8_t)(TCXO_DELAY >> 8), (uint8_t)TCXO_DELAY};
    const uint8_t c_clear_err[3] = {OP_CLEAR_ERRORS, 0, 0};
    const uint8_t c_cal[2] = {OP_CALIBRATE, 0x7F};
    const uint8_t c_cal_img[3] = {OP_CALIBRATE_IMAGE, 0xE1, 0xE9};                        /* 902-928 MHz */
    const uint8_t c_rf_switch[2] = {OP_DIO2_RF_SWITCH, 0x01};
    if (!cmd(c_standby, NULL, 2) || !cmd(c_reg, NULL, 2) || !cmd(c_tcxo, NULL, 5) || !cmd(c_clear_err, NULL, 3)) return false;
    if (!cmd(c_cal, NULL, 2) || wait_busy(BUSY_CAL_US) < 0) return false;
    if (!cmd(c_cal_img, NULL, 3) || wait_busy(BUSY_CAL_US) < 0) return false;
    if (!cmd(c_rf_switch, NULL, 2)) return false;
    return reg_update(REG_TX_CLAMP, 0, 0x1E);
}

/* LoRa SF7, 500 kHz, CR 4/5, 8-symbol preamble, explicit header, CRC on; PA for +22 dBm (datasheet 13.1.14). */
static bool setup_lora(uint32_t freq_hz, int dbm, uint8_t payload_len)
{
    const uint32_t frf = slim4_radio_frf(freq_hz);
    if (dbm > SLIM4_RADIO_TX_MAX_DBM) dbm = SLIM4_RADIO_TX_MAX_DBM;
    if (dbm < -9) dbm = -9;
    const uint8_t c_type[2] = {OP_SET_PACKET_TYPE, 0x01};
    const uint8_t c_freq[5] = {OP_SET_RF_FREQ, (uint8_t)(frf >> 24), (uint8_t)(frf >> 16), (uint8_t)(frf >> 8), (uint8_t)frf};
    const uint8_t c_pa[5] = {OP_SET_PA_CONFIG, 0x04, 0x07, 0x00, 0x01};
    const uint8_t c_txp[3] = {OP_SET_TX_PARAMS, (uint8_t)(int8_t)dbm, 0x04};             /* 200 us ramp */
    const uint8_t c_mod[5] = {OP_SET_MOD_PARAMS, SLIM4_RADIO_SF, 0x06, 0x01, 0x00};      /* SF7, BW 500, CR 4/5, no LDRO */
    const uint8_t c_pkt[7] = {OP_SET_PKT_PARAMS, 0x00, 0x08, 0x00, payload_len, 0x01, 0x00};
    const uint8_t c_base[3] = {OP_SET_BUF_BASE, 0x00, 0x00};
    const uint16_t mask = IRQ_TX_DONE | IRQ_RX_DONE | IRQ_TIMEOUT | IRQ_CRC_ERR | IRQ_HEADER_ERR;
    const uint8_t c_dio[9] = {OP_SET_DIO_IRQ, (uint8_t)(mask >> 8), (uint8_t)mask, (uint8_t)(mask >> 8), (uint8_t)mask, 0, 0, 0, 0};
    const uint8_t ocp = 0x38;                                                             /* 140 mA */
    return standby() && cmd(c_type, NULL, 2) && cmd(c_freq, NULL, 5) && cmd(c_pa, NULL, 5) && write_regs(REG_OCP, &ocp, 1)
           && cmd(c_txp, NULL, 3) && cmd(c_mod, NULL, 5) && cmd(c_pkt, NULL, 7) && cmd(c_base, NULL, 3)
           && cmd(c_dio, NULL, 9) && reg_update(REG_IQ_POLARITY, 0, 0x04) && clear_irq();
}

static bool get_irq(uint16_t *irq);

/* Wait for an interrupt the DIO1 mask routes (TxDone, RxDone, Timeout, errors): the DIO1 pin where it is wired,
 * else GetIrqStatus every 0.5 ms. */
static bool wait_irq(uint32_t limit_us, uint32_t *took)
{
    const int64_t t0 = now_us();
    for (;;) {
        bool fired;
        if (HAS_DIO1) {
            fired = gpio_get_level(SLIM4_GPIO_RADIO_DIO1) != 0;
        } else {
            uint16_t irq = 0;
            fired = get_irq(&irq) && irq != 0;
        }
        if (fired) break;
        const int64_t dt = now_us() - t0;
        if (dt > limit_us) return false;
        if (dt > 2000) vTaskDelay(1);
        else if (!HAS_DIO1) esp_rom_delay_us(500);
    }
    if (took) *took = (uint32_t)(now_us() - t0);
    return true;
}

static uint32_t timeout_units(uint32_t ms) { return ms * 64u; }   /* 15.625 us steps */

void slim4_radio_probe(slim4_radio_probe_t *out)
{
    memset(out, 0, sizeof(*out));
    out->spi_ready = bus_up();
    if (!out->spi_ready) { ESP_LOGE(TAG, "SPI2 setup failed"); return; }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    s_present = false;
    /* reset: NRST low 200 us; BUSY is high while the SX1262 starts */
    out->has_nrst = HAS_NRST;
    out->has_dio1 = HAS_DIO1;
    if (HAS_NRST) {
        (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 0);
        esp_rom_delay_us(200);
        (void)gpio_set_level(SLIM4_GPIO_RADIO_NRST, 1);
        esp_rom_delay_us(100);
        out->busy_high_in_reset = gpio_get_level(SLIM4_GPIO_RADIO_BUSY) != 0;
    } else if (s_asleep) {
        uint8_t tx[2] = {OP_GET_STATUS, 0}, rx[2];          /* NSS low wakes it; BUSY is high while it starts */
        (void)xfer(tx, rx, 2);
        esp_rom_delay_us(20);
        out->busy_high_in_reset = gpio_get_level(SLIM4_GPIO_RADIO_BUSY) != 0;
    }
    s_asleep = false;
    const int32_t w = wait_busy(BUSY_BOOT_US);
    out->busy_released = w >= 0;
    out->busy_us = w >= 0 ? (uint32_t)w + 100u : 0;
    if (!out->busy_released) goto done;
    (void)get_status(&out->status);
    (void)read_regs(REG_SYNC_WORD, out->sync, 2);
    const uint8_t pattern[2] = {0x5A, 0xA5};
    if (write_regs(REG_SYNC_WORD, pattern, 2)) (void)read_regs(REG_SYNC_WORD, out->readback, 2);
    (void)write_regs(REG_SYNC_WORD, out->sync, 2);                        /* back to the private-network word */
    if (!(out->sync[0] == 0x14 && out->sync[1] == 0x24)) goto done;
    out->init_done = init_chip();
    if (!out->init_done) goto done;
    /* DIO1: a 1 ms receive with nothing to hear times out and raises it */
    if (setup_lora(SLIM4_RADIO_FREQ_HZ, SLIM4_RADIO_TX_LOW_DBM, 0xFF)) {
        (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 1);
        const uint32_t t = timeout_units(1);
        const uint8_t c_rx[4] = {OP_SET_RX, (uint8_t)(t >> 16), (uint8_t)(t >> 8), (uint8_t)t};
        if (cmd(c_rx, NULL, 4)) out->dio1_rose = wait_irq(20000, &out->dio1_us);
        (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 0);
        (void)get_irq(&out->irq);
        (void)clear_irq();
        esp_rom_delay_us(50);
        if (HAS_DIO1) out->dio1_cleared = !gpio_get_level(SLIM4_GPIO_RADIO_DIO1);
        else { uint16_t after = 0xFFFF; out->dio1_cleared = get_irq(&after) && after == 0; }
    }
    (void)get_errors(&out->errors);
    s_present = out->readback[0] == 0x5A && out->readback[1] == 0xA5 && out->errors == 0 && out->dio1_rose
                && out->dio1_cleared;
done:
    if (out->busy_released) sleep_radio();
    xSemaphoreGive(s_lock);
}

bool slim4_radio_present(void) { return s_present; }

static uint32_t my_id(void)
{
    uint8_t mac[6] = {0};
    (void)esp_efuse_mac_get_default(mac);
    return (uint32_t)mac[2] << 24 | (uint32_t)mac[3] << 16 | (uint32_t)mac[4] << 8 | mac[5];
}

static bool send(const uint8_t *buf, uint8_t len, uint32_t freq_hz, int dbm)
{
    if (!setup_lora(freq_hz, dbm, len)) return false;
    if (!reg_update(REG_TX_MODULATION, 0x04, 0)) return false;           /* errata 15.1, 500 kHz */
    uint8_t tx[2 + SLIM4_RADIO_PING_LEN] = {OP_WRITE_BUF, 0x00};
    memcpy(tx + 2, buf, len);
    if (!cmd(tx, NULL, 2u + len)) return false;
    (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 0);
    const uint32_t t = timeout_units(100);
    const uint8_t c_tx[4] = {OP_SET_TX, (uint8_t)(t >> 16), (uint8_t)(t >> 8), (uint8_t)t};
    if (!cmd(c_tx, NULL, 4) || !wait_irq(200000, NULL)) return false;
    uint16_t irq = 0;
    (void)get_irq(&irq);
    (void)clear_irq();
    return (irq & IRQ_TX_DONE) != 0;
}

/* Receive one packet; returns its length, 0 on timeout, -1 on a fault. */
static int receive(uint8_t *buf, uint8_t cap, uint32_t freq_hz, uint32_t ms, int *rssi, int *snr)
{
    if (!setup_lora(freq_hz, SLIM4_RADIO_TX_LOW_DBM, 0xFF)) return -1;
    (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 1);
    const uint32_t t = timeout_units(ms);
    const uint8_t c_rx[4] = {OP_SET_RX, (uint8_t)(t >> 16), (uint8_t)(t >> 8), (uint8_t)t};
    const bool armed = cmd(c_rx, NULL, 4);
    const bool fired = armed && wait_irq(ms * 1000u + 50000u, NULL);
    (void)gpio_set_level(SLIM4_GPIO_RADIO_RF_SW, 0);
    if (!armed) return -1;
    uint16_t irq = 0;
    (void)get_irq(&irq);
    (void)clear_irq();
    if (!fired || !(irq & IRQ_RX_DONE)) return 0;
    if (irq & (IRQ_CRC_ERR | IRQ_HEADER_ERR)) return 0;
    uint8_t tx[4] = {OP_GET_RX_BUF_STATUS, 0, 0, 0}, rx[4];
    if (!cmd(tx, rx, 4)) return -1;
    uint8_t len = rx[2] > cap ? cap : rx[2];
    const uint8_t start = rx[3];
    uint8_t tb[3 + 32] = {OP_READ_BUF, start, 0}, rb[3 + 32];
    if (len > 32) len = 32;
    if (!cmd(tb, rb, 3u + len)) return -1;
    memcpy(buf, rb + 3, len);
    uint8_t ps_tx[5] = {OP_GET_PKT_STATUS, 0, 0, 0, 0}, ps[5];
    if (cmd(ps_tx, ps, 5)) {
        *rssi = -(int)ps[2] / 2;
        *snr = (int8_t)ps[3] / 4;
    }
    return len;
}

static bool ready_for_link(void)
{
    if (!s_present) {
        slim4_radio_probe_t p;
        slim4_radio_probe(&p);
    }
    if (!s_present) {
        printf("radio: no working module (run 'radio' for the probe report)\n");
        return false;
    }
    if (!slim4_radio_freq_ok(SLIM4_RADIO_FREQ_HZ, SLIM4_RADIO_BW_HZ)) return false;
    return true;
}

int slim4_radio_ping(unsigned n, uint32_t freq_hz, int dbm)
{
    if (!ready_for_link()) return -1;
    if (!slim4_radio_freq_ok(freq_hz, SLIM4_RADIO_BW_HZ)) { printf("radio: %lu Hz is not an allowed channel\n", (unsigned long)freq_hz); return -1; }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    int answered = 0;
    if (!wake()) { xSemaphoreGive(s_lock); return -1; }
    const uint32_t id = my_id();
    for (unsigned i = 0; i < n; ++i) {
        slim4_radio_ping_t p = {.reply = false, .seq = (uint8_t)i, .sender = id};
        uint8_t buf[SLIM4_RADIO_PING_LEN];
        slim4_radio_ping_encode(&p, buf);
        const int64_t t0 = now_us();
        if (!send(buf, sizeof(buf), freq_hz, dbm)) { printf("ping %u: transmit failed\n", i); continue; }
        int rssi = 0, snr = 0;
        uint8_t rx[32];
        bool got = false;
        while (!got && now_us() - t0 < 300000) {
            const int len = receive(rx, sizeof(rx), freq_hz, 300, &rssi, &snr);
            if (len < 0) break;
            slim4_radio_ping_t r;
            if (len > 0 && slim4_radio_ping_decode(rx, (uint8_t)len, &r) && r.reply && r.seq == p.seq && r.sender != id) {
                printf("ping %u: answer from %08lx in %lld ms; it heard us at %d dBm, we hear it at %d dBm, SNR %d dB\n", i,
                       (unsigned long)r.sender, (long long)((now_us() - t0) / 1000), r.rssi_heard, rssi, snr);
                got = true; ++answered;
            } else if (len == 0) {
                break;
            }
        }
        if (!got) printf("ping %u: no answer\n", i);
        vTaskDelay(pdMS_TO_TICKS(100));
    }
    printf("radio ping: %d of %u answered at %lu Hz, %d dBm\n", answered, n, (unsigned long)freq_hz, dbm);
    sleep_radio();
    xSemaphoreGive(s_lock);
    return answered;
}

int slim4_radio_listen(unsigned seconds, uint32_t freq_hz, int dbm)
{
    if (!ready_for_link()) return -1;
    if (!slim4_radio_freq_ok(freq_hz, SLIM4_RADIO_BW_HZ)) { printf("radio: %lu Hz is not an allowed channel\n", (unsigned long)freq_hz); return -1; }
    xSemaphoreTake(s_lock, portMAX_DELAY);
    if (!wake()) { xSemaphoreGive(s_lock); return -1; }
    const uint32_t id = my_id();
    const int64_t end = now_us() + (int64_t)seconds * 1000000;
    int heard = 0;
    printf("radio listen: %u s at %lu Hz\n", seconds, (unsigned long)freq_hz);
    while (now_us() < end) {
        int rssi = 0, snr = 0;
        uint8_t rx[32];
        const int len = receive(rx, sizeof(rx), freq_hz, 1000, &rssi, &snr);
        if (len < 0) { printf("radio listen: receive fault\n"); break; }
        slim4_radio_ping_t p;
        if (len > 0 && slim4_radio_ping_decode(rx, (uint8_t)len, &p) && !p.reply && p.sender != id) {
            slim4_radio_ping_t r = {.reply = true, .seq = p.seq, .sender = id,
                                    .rssi_heard = (int8_t)(rssi < -128 ? -128 : rssi)};
            uint8_t buf[SLIM4_RADIO_PING_LEN];
            slim4_radio_ping_encode(&r, buf);
            const bool ok = send(buf, sizeof(buf), freq_hz, dbm);
            printf("ping %u from %08lx at %d dBm, SNR %d dB: %s\n", p.seq, (unsigned long)p.sender, rssi, snr,
                   ok ? "answered" : "answer failed");
            ++heard;
        }
    }
    printf("radio listen: %d pings heard\n", heard);
    sleep_radio();
    xSemaphoreGive(s_lock);
    return heard;
}
