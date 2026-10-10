/* SLIM4 radio decisions with no ESP-IDF dependency (see slim4_radio.h); host-tested in tests/host/test_radio_logic.c. */
#include "slim4_radio.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool near_harmonic(uint32_t lo, uint32_t hi, uint32_t ref_hz)
{
    /* any k * ref inside [lo - 1 MHz, hi + 1 MHz] */
    const uint32_t margin = 1000000u;
    const uint32_t a = lo - margin, b = hi + margin;
    const uint32_t k = (a + ref_hz - 1u) / ref_hz;
    return (uint64_t)k * ref_hz <= b;
}

bool slim4_radio_freq_ok(uint32_t freq_hz, uint32_t bw_hz)
{
    const uint32_t half = bw_hz / 2u;
    if (freq_hz < SLIM4_RADIO_BAND_LO_HZ + half || freq_hz > SLIM4_RADIO_BAND_HI_HZ - half) return false;
    const uint32_t lo = freq_hz - half, hi = freq_hz + half;
    return !near_harmonic(lo, hi, 40000000u) && !near_harmonic(lo, hi, 32000000u);
}

int slim4_radio_tx_cap_dbm(const slim4_power_state_t *ps)
{
    if (!ps) return SLIM4_RADIO_TX_LOW_DBM;
    if (ps->usb_power) return SLIM4_RADIO_TX_MAX_DBM;
    if (ps->battery_low) return SLIM4_RADIO_TX_OFF;
    if (ps->battery_approx || ps->battery_mv == 0 || ps->battery_mv < 3500u) return SLIM4_RADIO_TX_LOW_DBM;
    return SLIM4_RADIO_TX_MAX_DBM;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

void slim4_at_parse(const char *line, slim4_at_line_t *out)
{
    memset(out, 0, sizeof(*out));
    if (!line) return;
    while (*line == ' ' || *line == '\r' || *line == '\n') ++line;
    if (!*line) return;
    if (!strcmp(line, "OK")) { out->kind = SLIM4_AT_OK; return; }
    if (!strncmp(line, "AT_", 3) && strstr(line, "ERROR")) { out->kind = SLIM4_AT_ERROR; return; }
    if (!strcmp(line, "AT_COMMAND_NOT_FOUND") || !strcmp(line, "ERROR")) { out->kind = SLIM4_AT_ERROR; return; }
    if (!strncmp(line, "+EVT:TXP2P", 10)) { out->kind = SLIM4_AT_TX_DONE; return; }
    if (!strncmp(line, "+EVT:RXP2P", 10)) {
        const char *r = line + 10;
        if (strstr(r, "TIMEOUT")) { out->kind = SLIM4_AT_RX_TIMEOUT; return; }
        if (*r != ':') { out->kind = SLIM4_AT_VALUE; return; }
        /* +EVT:RXP2P:<rssi>:<snr>:<hex> */
        char *end;
        const long rssi = strtol(r + 1, &end, 10);
        if (*end != ':') { out->kind = SLIM4_AT_VALUE; return; }
        const long snr = strtol(end + 1, &end, 10);
        if (*end != ':') { out->kind = SLIM4_AT_VALUE; return; }
        const char *h = end + 1;
        size_t n = 0;
        while (h[0] && h[1] && n < sizeof(out->payload)) {
            const int a = hexval(h[0]), b = hexval(h[1]);
            if (a < 0 || b < 0) break;
            out->payload[n++] = (uint8_t)(a * 16 + b);
            h += 2;
        }
        if (*h && *h != '\r' && *h != '\n') { out->kind = SLIM4_AT_VALUE; return; }   /* odd digit or a stray char */
        out->kind = SLIM4_AT_RX; out->rssi = (int)rssi; out->snr = (int)snr; out->len = (uint8_t)n;
        return;
    }
    out->kind = SLIM4_AT_VALUE;
}

bool slim4_at_p2p_settings(char *buf, size_t len, uint32_t freq_hz, unsigned sf, uint32_t bw_hz, int dbm)
{
    const int n = snprintf(buf, len, "AT+P2P=%lu:%u:%lu:0:8:%d", (unsigned long)freq_hz, sf,
                           (unsigned long)(bw_hz / 1000u), dbm);
    return n > 0 && (size_t)n < len;
}

bool slim4_at_psend(char *buf, size_t len, const uint8_t *data, size_t n)
{
    static const char hex[] = "0123456789ABCDEF";
    const size_t need = 9 + 2 * n + 1;            /* "AT+PSEND=" + hex + NUL */
    if (need > len || n == 0) return false;
    memcpy(buf, "AT+PSEND=", 9);
    for (size_t i = 0; i < n; ++i) {
        buf[9 + 2 * i] = hex[data[i] >> 4];
        buf[10 + 2 * i] = hex[data[i] & 15];
    }
    buf[9 + 2 * n] = '\0';
    return true;
}

/* Ping packet, 8 bytes: ping  'S' 'P' '4'  seq sender[4, little-endian]
 *                        reply 'S' 'R' rssi seq sender[4]   (rssi: what the replying board heard, dBm) */
void slim4_radio_ping_encode(const slim4_radio_ping_t *p, uint8_t out[SLIM4_RADIO_PING_LEN])
{
    out[0] = 'S';
    out[1] = p->reply ? 'R' : 'P';
    out[2] = p->reply ? (uint8_t)p->rssi_heard : 0x34;
    out[3] = p->seq;
    for (int i = 0; i < 4; ++i) out[4 + i] = (uint8_t)(p->sender >> (8 * i));
}

bool slim4_radio_ping_decode(const uint8_t *buf, uint8_t len, slim4_radio_ping_t *out)
{
    if (!buf || len != SLIM4_RADIO_PING_LEN || buf[0] != 'S') return false;
    if (buf[1] == 'P') {
        if (buf[2] != 0x34) return false;
        out->reply = false; out->rssi_heard = 0;
    } else if (buf[1] == 'R') {
        out->reply = true; out->rssi_heard = (int8_t)buf[2];
    } else {
        return false;
    }
    out->seq = buf[3];
    out->sender = (uint32_t)buf[4] | ((uint32_t)buf[5] << 8) | ((uint32_t)buf[6] << 16) | ((uint32_t)buf[7] << 24);
    return true;
}
