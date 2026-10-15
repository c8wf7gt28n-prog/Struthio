/* ARC-1 Compact R8.5-C -- F133 EMAC driver for the RGMII job link (see header). BUILD_ONLY: never run. */
#include "emac_d1.h"
#include <string.h>

static uint32_t rd(volatile uint32_t *base, uint32_t off) { return base[off / 4u]; }
static void wr(volatile uint32_t *base, uint32_t off, uint32_t v) { base[off / 4u] = v; }

void emac_d1_mux(emac_d1_platform *p, int rgmii)
{
    uint32_t fn = rgmii ? PG_FN_RGMII : PG_FN_IO_DISABLE, cfg0 = 0, cfg1 = rd(p->gpio, GPIO_PG_CFG1);
    unsigned i;
    for (i = 0; i < 8u; i++) cfg0 |= fn << (4u * i);                     /* PG0..PG7 */
    for (i = 0; i < 5u; i++) {                                           /* PG8..PG12; PG11 (EPHY-25M) disabled */
        uint32_t f = (i == 3u) ? PG_FN_IO_DISABLE : fn;
        cfg1 = (cfg1 & ~(0xFu << (4u * i))) | (f << (4u * i));
    }
    if (!rgmii) wr(p->gpio, GPIO_PG_CFG1, cfg1);                         /* off: receive side (PG8..10) first */
    wr(p->gpio, GPIO_PG_CFG0, cfg0);
    if (rgmii) wr(p->gpio, GPIO_PG_CFG1, cfg1);
}

void emac_d1_set_delay(emac_d1_platform *p, unsigned etxdc, unsigned erxdc)
{
    uint32_t v = rd(p->syscfg, SYSCFG_EMAC_EPHY_CLK_REG0);
    v &= ~((7u << EPHY_ETXDC_SHIFT) | (31u << EPHY_ERXDC_SHIFT));
    v |= ((uint32_t)(etxdc & 7u) << EPHY_ETXDC_SHIFT) | ((uint32_t)(erxdc & 31u) << EPHY_ERXDC_SHIFT);
    wr(p->syscfg, SYSCFG_EMAC_EPHY_CLK_REG0, v);
}

static void ring_init(emac_d1_platform *p)
{
    unsigned i;
    for (i = 0; i < EMAC_TX_DESCS; i++) {
        p->tx[i].st = 0; p->tx[i].ctl = 0;
        p->tx[i].buf = p->dma_addr(p->tx_buf + i * EMAC_CHUNK);
        p->tx[i].next = p->dma_addr(&p->tx[(i + 1u) % EMAC_TX_DESCS]);
    }
    for (i = 0; i < EMAC_RX_DESCS; i++) {
        p->rx[i].ctl = EMAC_CHUNK;
        p->rx[i].buf = p->dma_addr(p->rx_buf + i * EMAC_CHUNK);
        p->rx[i].next = p->dma_addr(&p->rx[(i + 1u) % EMAC_RX_DESCS]);
        p->rx[i].st = EMAC_DESC_OWN;
    }
    p->cache_clean(p->tx, sizeof(emac_desc) * EMAC_TX_DESCS);
    p->cache_clean(p->rx, sizeof(emac_desc) * EMAC_RX_DESCS);
    p->tx_i = p->rx_i = 0;
}

void emac_d1_init(emac_d1_platform *p, const uint8_t host_mac[6], unsigned etxdc, unsigned erxdc)
{
    uint32_t v;
    uint64_t t0;
    /* 9.13.4.1 steps 1-3: module reset, release, bus clock */
    v = rd(p->ccu, CCU_EMAC_BGR_REG);
    wr(p->ccu, CCU_EMAC_BGR_REG, v & ~(1u << 16));
    wr(p->ccu, CCU_EMAC_BGR_REG, v | (1u << 16));
    wr(p->ccu, CCU_EMAC_BGR_REG, v | (1u << 16) | 1u);
    /* step 5: external RGMII, RXCLK clock source, no clock inversion, delay chains (Table 9-42 shows 7 / 31) */
    v = EPHY_SHUTDOWN | EPHY_EPIT_RGMII | EPHY_ETCS_RXCLK |
        ((uint32_t)(etxdc & 7u) << EPHY_ETXDC_SHIFT) | ((uint32_t)(erxdc & 31u) << EPHY_ERXDC_SHIFT);
    wr(p->syscfg, SYSCFG_EMAC_EPHY_CLK_REG0, v);
    /* 9.13.4.2: soft reset (needs the RX clock running: the ECP5 forwards it once configured) */
    wr(p->emac, EMAC_BASIC_CTL1, 1u);
    t0 = p->now_us();
    while ((rd(p->emac, EMAC_BASIC_CTL1) & 1u) && p->now_us() - t0 < 10000u) { }
    wr(p->emac, EMAC_BASIC_CTL1, (8u << 24) | (1u << 1));               /* burst 8, RX/TX priority */
    wr(p->emac, EMAC_BASIC_CTL0, 1u);                                    /* 1000 Mbit/s (SPEED 00), full duplex */
    wr(p->emac, EMAC_ADDR_HIGH0, (uint32_t)host_mac[4] | ((uint32_t)host_mac[5] << 8));
    wr(p->emac, EMAC_ADDR_LOW0, (uint32_t)host_mac[0] | ((uint32_t)host_mac[1] << 8) | ((uint32_t)host_mac[2] << 16) |
                                ((uint32_t)host_mac[3] << 24));
    wr(p->emac, EMAC_RX_FRM_FLT, 1u << 17);                              /* unicast to host_mac only, no broadcast */
    ring_init(p);
    wr(p->emac, EMAC_TX_DMA_DESC_LIST, p->dma_addr(&p->tx[0]));
    wr(p->emac, EMAC_RX_DMA_DESC_LIST, p->dma_addr(&p->rx[0]));
    wr(p->emac, EMAC_TX_CTL1, (1u << 30) | (1u << 1));                   /* TX DMA on, store-and-forward */
    wr(p->emac, EMAC_RX_CTL1, (1u << 31) | (1u << 30) | (1u << 1));      /* RX DMA start + on, store-and-forward */
    wr(p->emac, EMAC_TX_CTL0, 1u << 31);
    wr(p->emac, EMAC_RX_CTL0, (1u << 31) | (1u << 29) | (1u << 28) | (1u << 27));   /* RX, jumbo, strip FCS, check CRC */
    wr(p->emac, EMAC_INT_EN, 0);                                         /* polled */
}

int emac_d1_send(emac_d1_platform *p, const uint8_t *frame, size_t len)
{
    unsigned n = (unsigned)((len + EMAC_CHUNK - 1u) / EMAC_CHUNK), k, i;
    size_t off = 0;
    if (!len || n > EMAC_TX_DESCS) return -1;
    for (k = 0; k < n; k++) {                                            /* all descriptors free (previous frame sent) */
        i = (p->tx_i + k) % EMAC_TX_DESCS;
        p->cache_invalidate(&p->tx[i], sizeof p->tx[i]);
        if (p->tx[i].st & EMAC_DESC_OWN) return -1;
    }
    for (k = n; k-- > 0;) {                                              /* fill last-to-first, hand over the first last */
        size_t c = (k == n - 1u) ? len - (size_t)k * EMAC_CHUNK : EMAC_CHUNK;
        i = (p->tx_i + k) % EMAC_TX_DESCS;
        off = (size_t)k * EMAC_CHUNK;
        memcpy(p->tx_buf + i * EMAC_CHUNK, frame + off, c);
        p->cache_clean(p->tx_buf + i * EMAC_CHUNK, c);
        p->tx[i].ctl = (uint32_t)c | (k == 0 ? EMAC_TXD1_FIRST : 0u) | (k == n - 1u ? EMAC_TXD1_LAST : 0u);
        p->tx[i].st = EMAC_DESC_OWN;
        p->cache_clean(&p->tx[i], sizeof p->tx[i]);
    }
    p->tx_i = (p->tx_i + n) % EMAC_TX_DESCS;
    wr(p->emac, EMAC_TX_CTL1, rd(p->emac, EMAC_TX_CTL1) | (1u << 31));   /* TX_DMA_START */
    return 0;
}

int emac_d1_recv(emac_d1_platform *p, uint8_t *buf, size_t cap, size_t *len)
{
    unsigned i = p->rx_i, k, bad = 0;
    size_t got = 0, flen = 0;
    for (k = 0; k < EMAC_RX_DESCS; k++) {
        unsigned j = (i + k) % EMAC_RX_DESCS;
        uint32_t st;
        p->cache_invalidate(&p->rx[j], sizeof p->rx[j]);
        st = p->rx[j].st;
        if (st & EMAC_DESC_OWN) { if (k == 0) return 1; break; }         /* nothing (more) received */
        if (st & EMAC_RXD0_ERRORS) bad = 1;
        if (st & EMAC_RXD0_LAST) {
            flen = (st >> 16) & 0x3FFFu;                                 /* frame length (FCS stripped) */
            if (!bad && flen <= cap) {
                size_t c = flen - got;
                p->cache_invalidate(p->rx_buf + j * EMAC_CHUNK, c);
                memcpy(buf + got, p->rx_buf + j * EMAC_CHUNK, c);
            }
        } else if (!bad && got + EMAC_CHUNK <= cap) {
            p->cache_invalidate(p->rx_buf + j * EMAC_CHUNK, EMAC_CHUNK);
            memcpy(buf + got, p->rx_buf + j * EMAC_CHUNK, EMAC_CHUNK);
            got += EMAC_CHUNK;
        }
        if (st & EMAC_RXD0_LAST) {
            unsigned m;
            for (m = 0; m <= k; m++) {                                   /* return the chain to the DMA */
                unsigned q = (i + m) % EMAC_RX_DESCS;
                p->rx[q].st = EMAC_DESC_OWN;
                p->cache_clean(&p->rx[q], sizeof p->rx[q]);
            }
            p->rx_i = (i + k + 1u) % EMAC_RX_DESCS;
            wr(p->emac, EMAC_RX_CTL1, rd(p->emac, EMAC_RX_CTL1) | (1u << 31));
            if (bad || flen > cap) return 1;                             /* dropped: report "nothing" */
            *len = flen;
            return 0;
        }
    }
    return 1;                                                            /* frame still arriving */
}

static int h_send(void *c, const uint8_t *f, size_t n) { return emac_d1_send(c, f, n); }
static int h_recv(void *c, uint8_t *b, size_t cap, size_t *n) { return emac_d1_recv(c, b, cap, n); }
static void h_mux(void *c, int on) { emac_d1_mux(c, on); }
static void h_delay(void *c, unsigned tx, unsigned rx) { emac_d1_set_delay(c, tx, rx); }
static uint64_t h_now(void *c) { return ((emac_d1_platform *)c)->now_us(); }
const arc1_eth_hal emac_d1_hal = { 0, h_send, h_recv, h_mux, h_delay, h_now };
