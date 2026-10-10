#pragma once
/* SLIM4 radio (PCB R28+): U15 RAKwireless RAK3172, an STM32WLE5 (SX126x-class LoRa/FSK radio with its own Cortex-M4)
 * running RAKwireless's RUI3 firmware, which takes AT commands on its UART2 at 115200 8N1. U1 talks to it on UART1
 * (pins in slim4_pins.h). Peer-to-peer LoRa ("P2P", AT+NWM=0) carries the games; no gateway or network is involved.
 *
 * What lives where:
 *   slim4_radio_logic.c  no ESP-IDF: the RF plan, the TX power cap from the power state, AT reply parsing, the P2P
 *                        settings string, the ping packet format. Covered by tests/host/test_radio_logic.c.
 *   slim4_radio.c        the UART, the reset and BOOT0 lines, the probe, ping and listen.
 * The self-test's judgement of a probe is slim4_st_judge_radio() in slim4_selftest_logic.c.
 *
 * Nothing here runs at boot except slim4_radio_probe() from the self-test, which is bounded (under 1.6 s, most of it
 * the module's own start-up) and leaves the module idle. A board without U15 (PCB R27 and older, or R701 left off)
 * reads as "not fitted". */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "slim4_power.h"

/* ---- RF plan --------------------------------------------------------------------------------------------------- */
#define SLIM4_RADIO_FREQ_HZ        915000000u  /* default channel: US 902-928 MHz ISM, 5 MHz from 920 MHz */
#define SLIM4_RADIO_BAND_LO_HZ     902000000u
#define SLIM4_RADIO_BAND_HI_HZ     928000000u
#define SLIM4_RADIO_BW_HZ          500000u     /* LoRa 500 kHz: a digital-modulation (DTS) channel under FCC 15.247 */
#define SLIM4_RADIO_SF             7u
#define SLIM4_RADIO_TX_MAX_DBM     22
#define SLIM4_RADIO_TX_LOW_DBM     14
#define SLIM4_RADIO_TX_OFF         (-128)

/* True when a LoRa channel of bw_hz at freq_hz lies inside the band and keeps 1 MHz (plus half the channel) from every
 * harmonic of the board's 40 MHz crystal (Y1: 920 MHz) and of the module's 32 MHz reference (896, 928 MHz). */
bool slim4_radio_freq_ok(uint32_t freq_hz, uint32_t bw_hz);
/* Highest TX power (dBm) the power state allows: SLIM4_RADIO_TX_OFF when the battery is at its cut-off with no USB,
 * 14 dBm on the battery below 3.5 V or with an uncalibrated reading, else 22 dBm. A +22 dBm burst draws about
 * 120 mA from 3V3_SYS; on a sagging cell that step must not reach the brown-out level. */
int slim4_radio_tx_cap_dbm(const slim4_power_state_t *ps);

/* ---- AT replies (RUI3) -------------------------------------------------------------------------------------------- */
typedef enum {
    SLIM4_AT_NONE = 0,     /* empty or unrecognised line */
    SLIM4_AT_OK,
    SLIM4_AT_ERROR,        /* AT_ERROR, AT_PARAM_ERROR, AT_BUSY_ERROR, AT_COMMAND_NOT_FOUND, ... */
    SLIM4_AT_TX_DONE,      /* +EVT:TXP2P DONE */
    SLIM4_AT_RX,           /* +EVT:RXP2P:<rssi>:<snr>:<hex payload> */
    SLIM4_AT_RX_TIMEOUT,   /* +EVT:RXP2P RECEIVE TIMEOUT */
    SLIM4_AT_VALUE,        /* any other text (a query's answer, e.g. "RUI_4.0.6_RAK3172-E" or "AT+NWM=0") */
} slim4_at_kind_t;

typedef struct {
    slim4_at_kind_t kind;
    int rssi, snr;             /* SLIM4_AT_RX */
    uint8_t payload[64];       /* SLIM4_AT_RX, decoded from hex */
    uint8_t len;
} slim4_at_line_t;

/* Classify one received line (without its CR/LF). */
void slim4_at_parse(const char *line, slim4_at_line_t *out);
/* "AT+P2P=<freq>:<sf>:<bw kHz>:<cr 0=4/5>:<preamble>:<dBm>" into buf; returns false if it does not fit. */
bool slim4_at_p2p_settings(char *buf, size_t len, uint32_t freq_hz, unsigned sf, uint32_t bw_hz, int dbm);
/* "AT+PSEND=<hex>" into buf; returns false if it does not fit. */
bool slim4_at_psend(char *buf, size_t len, const uint8_t *data, size_t n);

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
    bool uart_ready;         /* UART1 and the radio pins could be set up */
    bool rx_low_in_reset;    /* with NRST held low, the module's TX line (U1 RX, pulled down by U1) read low */
    bool rx_high_after;      /* after NRST was released, the module drove its TX line high (UART idle) */
    bool answered;           /* "AT" was answered "OK" */
    uint32_t answer_ms;      /* NRST release to the first "OK" */
    char version[40];        /* AT+VER=? answer, "" if none */
    int nwm;                 /* AT+NWM=? : 0 P2P, 1 LoRaWAN, -1 unknown */
} slim4_radio_probe_t;

/* ---- the driver (slim4_radio.c) ----------------------------------------------------------------------------------- */
/* Reset and probe the module (bounded, under 1.6 s). Safe on a board without U15. */
void slim4_radio_probe(slim4_radio_probe_t *out);
/* Whether the last probe found a module that answers. */
bool slim4_radio_present(void);
/* Bring-up link test: send n pings at freq_hz and wait up to 300 ms for each answer; prints one line per ping. */
int slim4_radio_ping(unsigned n, uint32_t freq_hz, int dbm);
/* Bring-up link test: answer every ping heard at freq_hz for seconds; prints one line per ping. */
int slim4_radio_listen(unsigned seconds, uint32_t freq_hz, int dbm);
/* Send one AT command and print every reply line for up to ms (console 'radio at ...'). */
void slim4_radio_at(const char *cmd, unsigned ms);
