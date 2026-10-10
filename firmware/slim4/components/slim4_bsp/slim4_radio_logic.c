/* SLIM4 radio decisions with no ESP-IDF dependency (see slim4_radio.h); host-tested in tests/host/test_radio_logic.c. */
#include "slim4_radio.h"

uint32_t slim4_radio_frf(uint32_t freq_hz)
{
    return (uint32_t)((((uint64_t)freq_hz) << 25) / SLIM4_RADIO_XTAL_HZ);
}

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
    return !near_harmonic(lo, hi, 40000000u) && !near_harmonic(lo, hi, SLIM4_RADIO_XTAL_HZ);
}

int slim4_radio_tx_cap_dbm(const slim4_power_state_t *ps)
{
    if (!ps) return SLIM4_RADIO_TX_LOW_DBM;
    if (ps->usb_power) return SLIM4_RADIO_TX_MAX_DBM;
    if (ps->battery_low) return SLIM4_RADIO_TX_OFF;
    if (ps->battery_approx || ps->battery_mv == 0 || ps->battery_mv < 3500u) return SLIM4_RADIO_TX_LOW_DBM;
    return SLIM4_RADIO_TX_MAX_DBM;
}

uint8_t slim4_radio_tcxo_code(uint16_t mv)
{
    static const uint16_t table[8] = {1600, 1700, 1800, 2200, 2400, 2700, 3000, 3300};
    for (uint8_t i = 0; i < 8; ++i) {
        if (table[i] == mv) return i;
    }
    return 0xFF;
}

/* Ping packet, 8 bytes: ping  'S' 'P' '4'  seq sender[4, little-endian]
 *                        reply 'S' 'R' rssi seq sender[4]   (rssi: what the replying board heard, dBm) */
void slim4_radio_ping_encode(const slim4_radio_ping_t *p, uint8_t out[SLIM4_RADIO_PING_LEN])
{
    out[0] = 'S';
    out[1] = p->reply ? 'R' : 'P';
    out[2] = p->reply ? (uint8_t)p->rssi_heard : 0x34;   /* '4' in a ping */
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
