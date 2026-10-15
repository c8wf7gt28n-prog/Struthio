/* ARC-1 Compact R08 -- F133 registers for the diagnostic image (R07 header + SPI0, port F/G).
 * SPI0 base 0x04025000: Linux sunxi-d1s-t113.dtsi spi@4025000 (R06 source LINUX_DTSI_D1S_T113)
 * plus the D1-H UM SPI register map shared with SPI1. CCU SPI0_CLK 0x940, SPI_BGR b0/b16.
 * Source: Allwinner D1-H User Manual v1.0 (2022-01-18) -- the F133 manual was
 * not obtainable (see R07_WORK/docs/F133_BOOT_PIN_POLICY.md). Addresses are
 * ASSUMED identical on F133; the image is BUILD-ONLY until run on silicon.
 *   memory map: GPIO 0x02000000, CCU 0x02001000, UART0 0x02500000,
 *               SPI1 0x04026000, SYS_CFG 0x03000000, SID 0x03006000 (UM 1.x)
 *   CCU: APB1_CLK_REG 0x524, UART_BGR_REG 0x90C, SPI1_CLK_REG 0x944,
 *        SPI_BGR_REG 0x96C (UM 3.2.6)
 *   GPIO: PC_CFG0 0x60, PD_CFG1 0x94, PD_CFG2 0x98, PD_DAT 0xA0,
 *         PE_CFG0 0xC0 (UM 9.7); 4-bit function fields, port stride 0x30
 *   UART: THR/RBR/DLL 0x0, DLH/IER 0x4, FCR 0x8, LCR 0xC, LSR 0x14 (UM 9.2.5)
 *   SPI : GCR 0x4, TCR 0x8, ISR 0x14, FCR 0x18, FSR 0x1C, MBC 0x30, MTC 0x34,
 *         BCC 0x38, TXD 0x200, RXD 0x300 (UM 9.3.5/9.3.6) */
#ifndef F133_REGS_H
#define F133_REGS_H
#include <stdint.h>
#define REG32(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define REG8(a)  (*(volatile uint8_t *)(uintptr_t)(a))

#define GPIO_BASE   0x02000000u
#define CCU_BASE    0x02001000u
#define UART0_BASE  0x02500000u
#define SPI0_BASE   0x04025000u
#define SPI1_BASE   0x04026000u
#define SYSCFG_VER  0x03000024u   /* [12:11] BOOT_SEL_PAD_STA, [8] FEL_SEL_PAD_STA */
#define SID_BOOTSEL 0x03006210u   /* [27:16] eFuse boot select */
#define RTC_FASTBOOT 0x07090120u  /* non-zero -> fast boot path (UM Table 3-8) */

#define CCU_APB1_CLK  (CCU_BASE + 0x524u)
#define CCU_UART_BGR  (CCU_BASE + 0x90Cu)   /* b0 UART0_GATING, b16 UART0_RST */
#define CCU_SPI0_CLK  (CCU_BASE + 0x940u)   /* same layout as SPI1_CLK */
#define CCU_SPI1_CLK  (CCU_BASE + 0x944u)   /* b31 gate, [26:24] src (0 = HOSC 24 MHz), [9:8] N, [3:0] M */
#define CCU_SPI_BGR   (CCU_BASE + 0x96Cu)   /* b0 SPI0_GATING, b1 SPI1_GATING, b16 SPI0_RST, b17 SPI1_RST */

#define GPIO_CFG(port, n) (GPIO_BASE + 0x30u * (port) + 4u * (n))   /* port: B=1 .. G=6 */
#define GPIO_DAT(port)    (GPIO_BASE + 0x30u * (port) + 0x10u)
#define PORT_C 2u
#define PORT_D 3u
#define PORT_E 4u
#define PORT_F 5u
#define PORT_G 6u
#define GPIO_PULL(port, n) (GPIO_BASE + 0x30u * (port) + 0x24u + 4u * (n))   /* 2 bits/pin: 01 up, 10 down */

#define UART_THR 0x00u
#define UART_DLL 0x00u
#define UART_DLH 0x04u
#define UART_FCR 0x08u
#define UART_LCR 0x0Cu
#define UART_LSR 0x14u

#define SPI_GCR 0x04u
#define SPI_TCR 0x08u
#define SPI_ISR 0x14u
#define SPI_FCR 0x18u
#define SPI_FSR 0x1Cu
#define SPI_MBC 0x30u
#define SPI_MTC 0x34u
#define SPI_BCC 0x38u
#define SPI_TXD 0x200u
#define SPI_RXD 0x300u
#endif
