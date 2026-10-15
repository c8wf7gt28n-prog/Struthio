/* ARC-1 Compact R8.5-C -- F133 (D1 family) EMAC register-level driver for the RGMII job link: BUILD_ONLY.
 * Source: D1-H User Manual v1.0 (sha256 fe5e5287...dc9d): 9.13 EMAC (register list 9.13.5, descriptors 9.13.3.4-6,
 * system configuration 9.13.4.1, initialisation 9.13.4.2), 3.4.3.3 EMAC_EPHY_CLK_REG0, 3.2.6.69 EMAC_BGR_REG,
 * 9.7 GPIO PG_CFG0/PG_CFG1. The F133 uses the same EMAC (F133 DS rev 2.3 2.10.3 / Table 4-3).
 * Evidence: BUILD_ONLY (compiled freestanding, never run). Not bound to an F133 BSP: register base addresses, DMA
 * memory and cache maintenance come from the caller (emac_d1_platform). The C906 core's caches are not coherent with
 * the EMAC DMA: the BSP must supply clean/invalidate for descriptors and buffers. */
#ifndef EMAC_D1_H
#define EMAC_D1_H
#include <stddef.h>
#include <stdint.h>
#include "eth_link.h"

/* register offsets (EMAC base 0x04500000) */
#define EMAC_BASIC_CTL0      0x0000u   /* [3:2] SPEED 00=1000M, [1] LOOPBACK, [0] DUPLEX 1=full */
#define EMAC_BASIC_CTL1      0x0004u   /* [29:24] BURST_LEN, [1] RX_TX_PRI, [0] SOFT_RST (self-clearing) */
#define EMAC_INT_STA         0x0008u
#define EMAC_INT_EN          0x000Cu
#define EMAC_TX_CTL0         0x0010u   /* [31] TX_EN, [30] TX_FRM_LEN_CTL */
#define EMAC_TX_CTL1         0x0014u   /* [31] TX_DMA_START, [30] TX_DMA_EN, [10:8] TX_TH, [1] TX_MD, [0] FLUSH_TX_FIFO */
#define EMAC_TX_DMA_DESC_LIST 0x0020u
#define EMAC_RX_CTL0         0x0024u   /* [31] RX_EN, [30] RX_FRM_LEN_CTL, [29] JUMBO_FRM_EN, [28] STRIP_FCS, [27] CHECK_CRC */
#define EMAC_RX_CTL1         0x0028u   /* [31] RX_DMA_START, [30] RX_DMA_EN, [3] RX_ERR_FRM, [2] RX_RUNT_FRM, [1] RX_MD */
#define EMAC_RX_DMA_DESC_LIST 0x0034u
#define EMAC_RX_FRM_FLT      0x0038u   /* [31] DIS_ADDR_FILTER, [17] DIS_BROADCAST, [0] RX_ALL */
#define EMAC_ADDR_HIGH0      0x0050u
#define EMAC_ADDR_LOW0       0x0054u
#define EMAC_RGMII_STA       0x00D0u
/* CCU base 0x02001000 */
#define CCU_EMAC_BGR_REG     0x097Cu   /* [16] EMAC_RST (1 = de-assert), [0] EMAC_GATING */
/* SYS_CFG base 0x03000000 */
#define SYSCFG_EMAC_EPHY_CLK_REG0 0x0030u
#define EPHY_SHUTDOWN        (1u << 16)  /* internal EPHY powered down (not used) */
#define EPHY_PHY_SELECT_INT  (1u << 15)  /* 0 = external PHY interface (our RGMII link) */
#define EPHY_RMII_EN         (1u << 13)
#define EPHY_ETXDC_SHIFT     10u         /* 3 bits */
#define EPHY_ERXDC_SHIFT     5u          /* 5 bits */
#define EPHY_EPIT_RGMII      (1u << 2)
#define EPHY_ETCS_RXCLK      2u          /* UM 9.13.4.1: RXCLK as the RGMII clock source (ECP5-forwarded 125 MHz) */
/* GPIO base 0x02000000: PG_CFG0 0x0120 (PG0..PG7), PG_CFG1 0x0124 (PG8..PG15), 4 bits per pin */
#define GPIO_PG_CFG0         0x0120u
#define GPIO_PG_CFG1         0x0124u
#define PG_FN_RGMII          0x4u
#define PG_FN_IO_DISABLE     0xFu        /* reset state */

/* descriptors: 4 words each, 32-bit aligned (UM 9.13.3.4) */
#define EMAC_DESC_OWN        (1u << 31)  /* word 0: owned by the DMA */
#define EMAC_TXD1_INT        (1u << 31)
#define EMAC_TXD1_LAST       (1u << 30)
#define EMAC_TXD1_FIRST      (1u << 29)
#define EMAC_RXD0_FIRST      (1u << 9)
#define EMAC_RXD0_LAST       (1u << 8)
#define EMAC_RXD0_ERRORS     ((1u << 14) | (1u << 11) | (1u << 4) | (1u << 3) | (1u << 1) | (1u << 0))
#define EMAC_BUF_MAX         2047u       /* BUF_SIZE is 11 bits: an 8 KiB job frame spans several descriptors */
#define EMAC_CHUNK           1536u

typedef struct emac_desc { uint32_t st, ctl, buf, next; } emac_desc;

#define EMAC_TX_DESCS 8u                 /* 8 x 1536 >= the largest link frame (8208 B) */
#define EMAC_RX_DESCS 16u

typedef struct emac_d1_platform {
    volatile uint32_t *emac, *ccu, *syscfg, *gpio;   /* mapped register bases */
    emac_desc *tx, *rx;                               /* DMA-visible descriptor rings */
    uint8_t *tx_buf, *rx_buf;                         /* EMAC_TX_DESCS / EMAC_RX_DESCS x EMAC_CHUNK bytes */
    uint32_t (*dma_addr)(const void *p);              /* CPU pointer -> 32-bit bus address */
    void (*cache_clean)(const void *p, size_t n);
    void (*cache_invalidate)(void *p, size_t n);
    uint64_t (*now_us)(void);
    unsigned tx_i, rx_i;
} emac_d1_platform;

/* UM 9.13.4.1/9.13.4.2: reset + gate, RGMII with RXCLK source and the given delay chains, 1000M full duplex,
 * jumbo frames, CRC check + FCS strip, unicast filter on host_mac, store-and-forward DMA, rings armed */
void emac_d1_init(emac_d1_platform *p, const uint8_t host_mac[6], unsigned etxdc, unsigned erxdc);
/* PG0..PG12: function 4 (RGMII) or IO Disable */
void emac_d1_mux(emac_d1_platform *p, int rgmii);
void emac_d1_set_delay(emac_d1_platform *p, unsigned etxdc, unsigned erxdc);
int emac_d1_send(emac_d1_platform *p, const uint8_t *frame, size_t len);
int emac_d1_recv(emac_d1_platform *p, uint8_t *buf, size_t cap, size_t *len);
/* arc1_eth_hal binding (ctx = emac_d1_platform *) */
extern const arc1_eth_hal emac_d1_hal;
#endif
