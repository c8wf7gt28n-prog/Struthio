#pragma once
/* SLIM4 radio (PCB R28+): U15 Seeed Wio-SX1262, a Semtech SX1262 with a 32 MHz TCXO powered from its DIO3 and an
 * internal TX/RX switch driven by its DIO2 (Seeed Wio-SX1262 datasheet V1.1). Pins in slim4_pins.h.
 *
 * What lives where:
 *   slim4_radio_logic.c  no ESP-IDF: command encodings, the frequency check, the TX power cap from the power state,
 *                        the ping packet format. Covered by tests/host/test_radio_logic.c.
 *   slim4_radio.c        the SPI link and the SX1262 command sequences (probe, init, ping, listen, sleep).
 * The self-test's judgement of a probe is slim4_st_judge_radio() in slim4_selftest_logic.c.
 *
 * Nothing here runs at boot except slim4_radio_probe() from the self-test, which is bounded (under 60 ms) and puts
 * the SX1262 to sleep afterwards. A board without U15 (PCB R27 and older, or R701 left off) reads as "not fitted". */
#include <stdbool.h>
#include <stdint.h>
#include "slim4_power.h"

/* ---- RF plan --------------------------------------------------------------------------------------------------- */
#define SLIM4_RADIO_XTAL_HZ        32000000u   /* SX1262 reference (the module's TCXO) */
#define SLIM4_RADIO_FREQ_HZ        915000000u  /* default channel: US 902-928 MHz ISM, 5 MHz from 920 MHz */
#define SLIM4_RADIO_BAND_LO_HZ     902000000u
#define SLIM4_RADIO_BAND_HI_HZ     928000000u
#define SLIM4_RADIO_BW_HZ          500000u     /* LoRa 500 kHz: a digital-modulation (DTS) channel under FCC 15.247 */
#define SLIM4_RADIO_SF             7u
#define SLIM4_RADIO_TX_MAX_DBM     22          /* SX1262 high-power PA */
#define SLIM4_RADIO_TX_LOW_DBM     14
#define SLIM4_RADIO_TX_OFF         (-128)
#define SLIM4_RADIO_TCXO_MV        1800u       /* DIO3 TCXO supply: Wio-SX1262 range 1.7-3.3 V, >= 200 mV under VCC */

/* RF frequency register value (SX1262 datasheet 13.4.1: RfFreq = f * 2^25 / Fxtal). */
uint32_t slim4_radio_frf(uint32_t freq_hz);
/* True when a LoRa channel of bw_hz at freq_hz lies inside the band and keeps 1 MHz (plus half the channel) from every
 * harmonic of the board's 40 MHz crystal (Y1: 920 MHz) and of the module's 32 MHz TCXO (896, 928 MHz). */
bool slim4_radio_freq_ok(uint32_t freq_hz, uint32_t bw_hz);
/* Highest TX power (dBm) the power state allows: SLIM4_RADIO_TX_OFF when the battery is at its cut-off with no USB,
 * 14 dBm on the battery below 3.5 V or with an uncalibrated reading, else 22 dBm. A +22 dBm burst draws about
 * 125 mA from 3V3_SYS; on a sagging cell that step must not reach the brown-out level. */
int slim4_radio_tx_cap_dbm(const slim4_power_state_t *ps);
/* SX1262 TCXO voltage code for SetDIO3AsTcxoCtrl (datasheet 13.3.6): 1.6 V = 0 ... 3.3 V = 7; 0xFF if none fits. */
uint8_t slim4_radio_tcxo_code(uint16_t mv);

/* ---- ping packets (bring-up: two boards answer each other) ------------------------------------------------------- */
#define SLIM4_RADIO_PING_LEN 8
typedef struct {
    bool reply;        /* false: ping, true: the answer to one */
    uint8_t seq;
    uint32_t sender;   /* low 32 bits of the sender's MAC */
    int8_t rssi_heard; /* in a reply: the RSSI (dBm) the replying board measured on the ping */
} slim4_radio_ping_t;
void slim4_radio_ping_encode(const slim4_radio_ping_t *p, uint8_t out[SLIM4_RADIO_PING_LEN]);
bool slim4_radio_ping_decode(const uint8_t *buf, uint8_t len, slim4_radio_ping_t *out);

/* ---- probe (self-test) ------------------------------------------------------------------------------------------- */
typedef struct {
    bool spi_ready;          /* the SPI bus and pins could be set up */
    bool has_nrst, has_dio1; /* the board wires NRST / DIO1 to U1 (else: pull-up on NRST; IRQ flags polled over SPI) */
    bool busy_high_in_reset; /* BUSY read high 100 us after NRST was released, or after the wake from sleep */
    bool busy_released;      /* BUSY went low again */
    uint32_t busy_us;        /* NRST release to BUSY low */
    uint8_t status;          /* GetStatus byte after reset */
    uint8_t sync[2];         /* registers 0x0740/0x0741 after reset: 0x14 0x24 */
    uint8_t readback[2];     /* the same after writing 0x5A 0xA5 (restored afterwards) */
    bool init_done;          /* TCXO, regulator, calibration commands accepted (BUSY released each time) */
    uint16_t errors;         /* GetDeviceErrors after calibration and the RX test */
    bool dio1_rose;          /* a 1 ms receive timed out and raised DIO1 (or, without DIO1, its IRQ flag) */
    uint32_t dio1_us;
    uint16_t irq;            /* GetIrqStatus then */
    bool dio1_cleared;       /* DIO1 fell (or the IRQ flags read 0) after ClearIrqStatus */
} slim4_radio_probe_t;

/* ---- the driver (slim4_radio.c) ----------------------------------------------------------------------------------- */
/* Probe and test the module (bounded, under 60 ms), then put it to sleep. Safe on a board without U15. */
void slim4_radio_probe(slim4_radio_probe_t *out);
/* Whether the last probe found a working SX1262. */
bool slim4_radio_present(void);
/* Bring-up link test: send n pings at freq_hz and wait up to 300 ms for each answer; prints one line per ping. */
int slim4_radio_ping(unsigned n, uint32_t freq_hz, int dbm);
/* Bring-up link test: answer every ping heard at freq_hz for seconds; prints one line per ping. */
int slim4_radio_listen(unsigned seconds, uint32_t freq_hz, int dbm);
