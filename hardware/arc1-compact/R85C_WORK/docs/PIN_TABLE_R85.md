# ARC-1 Compact R8.5 pin table (GENERATED from board/r85_board_plan.json; the KiCad schematic is generated from the same source)

## U15 F133-B -- F133-B (all 129 pins incl. EPAD)

| Pin | Name | Net | No-connect reason |
|---|---|---|---|
| 1 | PG6 | BTN_X |  |
| 2 | PG7 | BTN_Y |  |
| 3 | PG8 | BTN_L |  |
| 4 | PG9 | BTN_R |  |
| 5 | PG10 | BTN_START |  |
| 6 | PG11 | BTN_SELECT |  |
| 7 | PF0 | SD_D1 |  |
| 8 | PF1 | SD_D0 |  |
| 9 | PF2 | SD_CLK_F |  |
| 10 | PF3 | SD_CMD |  |
| 11 | PF4 | SD_D3 |  |
| 12 | PF5 | SD_D2 |  |
| 13 | PF6 | SD_DET_N |  |
| 14 | PC7 | SPI0_IO3 |  |
| 15 | PC6 | SPI0_IO2 |  |
| 16 | PC5 | SPI0_MISO |  |
| 17 | PC4 | SPI0_MOSI |  |
| 18 | PC3 | SPI0_CS0_N |  |
| 19 | PC2 | SPI0_CLK_F |  |
| 20 | VCC-PLL | 1V8_LDOA |  |
| 21 | REFCLK-OUT |  | 24 MHz fan-out unused |
| 22 | DXOUT | XTAL24_OUT |  |
| 23 | DXIN | XTAL24_IN |  |
| 24 | X32KOUT |  | RTC 32k crystal optional |
| 25 | X32KIN |  | RTC 32k crystal optional (internal RC) -- OPEN: confirm |
| 26 | VCC-RTC | 1V8_LDOA |  |
| 27 | RESET | F133_RESET_N |  |
| 28 | LDOA-OUT | 1V8_LDOA |  |
| 29 | LDO-IN | 3V3 |  |
| 30 | LDOB-OUT | F133_LDOB |  |
| 31 | PE13 | USB_CUR_OUT2 |  |
| 32 | PE12 | USB_CUR_OUT1 |  |
| 33 | PE3 | UART0_RX |  |
| 34 | VCC-PE | 3V3 |  |
| 35 | PE2 | UART0_TX |  |
| 36 | PE11 | PSRAM_PG |  |
| 37 | PE10 | AMP_EN |  |
| 38 | PE9 | FPGA_DONE |  |
| 39 | PE8 | FPGA_PROGRAMN_F |  |
| 40 | PE7 | PSRAM_PWR_REQ |  |
| 41 | PE6 | FPGA_BUS_EN_N |  |
| 42 | PE5 | FPGA_IRQ_N |  |
| 43 | PE4 | FPGA_SS_N_F |  |
| 44 | PE0 | FPGA_PWR_EN_F |  |
| 45 | PE1 | VBUS_SENSE |  |
| 46 | VDD-SYS0 | VDD_CORE |  |
| 47 | NC | F133_PIN47_DZQ |  |
| 48 | VCC-DRAM0 | 1V8_DRAM |  |
| 49 | VCC-DRAM1 | 1V8_DRAM |  |
| 50 | VDD18-DRAM | 1V8_LDOA |  |
| 51 | VDD-SYS1 | VDD_CORE |  |
| 52 | PD22 |  | spare GPIO |
| 53 | PD21 | MN_PWR_EN |  |
| 54 | PD20 | SD_PWR_EN |  |
| 55 | PD0 | FPGA_INITN |  |
| 56 | PD1 | FPGA_VCC_PG |  |
| 57 | PD2 |  | spare GPIO |
| 58 | PD3 |  | spare GPIO |
| 59 | PD4 |  | spare GPIO |
| 60 | PD5 |  | spare GPIO |
| 61 | PD6 |  | spare GPIO |
| 62 | PD7 |  | spare GPIO |
| 63 | PD8 |  | spare GPIO |
| 64 | PD9 |  | spare GPIO |
| 65 | VCC-LVDS | 1V8_LDOA |  |
| 66 | VCC-PD | 3V3 |  |
| 67 | PD10 | BT_SS_N |  |
| 68 | PD11 | BT_SCK_F |  |
| 69 | PD13 | BT_MISO |  |
| 70 | PD12 | BT_MOSI_F |  |
| 71 | PD14 |  | spare GPIO |
| 72 | PD15 |  | spare GPIO |
| 73 | PD16 | BT_RST_N_F |  |
| 74 | PD17 | BT_INT_N |  |
| 75 | PD18 | LED_STATUS |  |
| 76 | PD19 | LED_ERROR |  |
| 77 | VCC-TVOUT | 3V3 |  |
| 78 | TVOUT0 |  | CVBS out unused |
| 79 | PB7 |  | spare GPIO |
| 80 | PB6 | I2S_LRCK |  |
| 81 | VDD-SYS2 | VDD_CORE |  |
| 82 | PB5 | I2S_BCLK |  |
| 83 | VCC-IO | 3V3 |  |
| 84 | PB4 | I2S_DOUT |  |
| 85 | PB3 |  | spare GPIO |
| 86 | PB2 |  | spare GPIO |
| 87 | MICIN3P |  | codec input unused (I2S audio) |
| 88 | MICIN3N |  | codec input unused |
| 89 | AVCC | 1V8_AN |  |
| 90 | VRA2 | F133_VRA2 |  |
| 91 | AGND | GND |  |
| 92 | VRA1 | F133_VRA1 |  |
| 93 | FMINR |  | unused |
| 94 | FMINL |  | unused |
| 95 | LINEINR |  | unused |
| 96 | LINEINL |  | unused |
| 97 | HPVCC | 1V8_AN |  |
| 98 | HPOUTR |  | analog HP out unused: audio = I2S amps (owner decision) |
| 99 | HPOUTL |  | analog HP out unused |
| 100 | HPOUTFB |  | unused |
| 101 | GPADC0 |  | spare ADC |
| 102 | TP-X1 |  | unused |
| 103 | TP-X2 |  | unused |
| 104 | TP-Y1 |  | unused |
| 105 | TP-Y2 |  | unused |
| 106 | NC0 |  | datasheet NC |
| 107 | VCC-TVIN | 1V8_AN |  |
| 108 | TVIN0 |  | CVBS in unused |
| 109 | TVIN1 |  | CVBS in unused |
| 110 | TVIN-VRP |  | CVBS ref unused -- OPEN: datasheet gives no termination |
| 111 | TVIN-VRN |  | CVBS ref unused -- OPEN |
| 112 | USB1-DP |  | USB1 host: removed (D-04) |
| 113 | USB1-DM |  | USB1 host: removed (D-04) |
| 114 | USB0-DM | USB0_DM |  |
| 115 | USB0-DP | USB0_DP |  |
| 116 | VDD-CORE0 | VDD_CORE |  |
| 117 | VDD-CORE1 | VDD_CORE |  |
| 118 | PG1 | BTN_DOWN |  |
| 119 | PG2 | BTN_LEFT |  |
| 120 | PG0 | BTN_UP |  |
| 121 | PG3 | BTN_RIGHT |  |
| 122 | PG5 | BTN_B |  |
| 123 | PG4 | BTN_A |  |
| 124 | PG12 | BTN_HOME |  |
| 125 | PG13 |  | spare GPIO |
| 126 | PG14 |  | spare GPIO |
| 127 | PG15 |  | spare GPIO |
| 128 | VCC-PG | 3V3 |  |
| 129 | EPAD | GND |  |

## U18 LFE5U-45F-6BG381C -- LFE5U-45F-6BG381C (signal/config balls only; all 381 balls in board/ECP5_BALL_MAP_R85.csv)

| Pin | Name | Net | No-connect reason |
|---|---|---|---|
| A7 | PT18A | FPGA_LED0 |  |
| A8 | PT18B | FPGA_DBG_TX |  |
| B8 | PT15B | FPGA_DBG_RX |  |
| E6 | PT6A | FPGA_IRQ_N |  |
| L1 | PL65C | PSRAM_CE_N |  |
| L2 | PL62D | PSRAM_SCLK_F |  |
| L3 | PL62C | PSRAM_SIO0 |  |
| M1 | PL65B | PSRAM_SIO1 |  |
| M3 | PL62B | PSRAM_SIO2 |  |
| M4 | PL59A | PSRAM_SIO3 |  |
| N1 | PL65D | PSRAM_PG |  |
| N2 | PL65A | PSRAM_EN |  |
| P3 | PL68C/LLC_GPLL0T_IN | FPGA_OSC_25M |  |
| R1 | PB4A/D7 | FPGA_SCK |  |
| R2 | PB15A/HOLDN | FPGA_HOLDN |  |
| R5 | TDI | FPGA_TDI |  |
| T2 | PB13A/SN | FPGA_SS_N |  |
| T5 | TCK | FPGA_TCK |  |
| U3 | CCLK/MCLK | FPGA_SCK |  |
| U4 | CFG_0 | FPGA_CFG0 |  |
| U5 | TMS | FPGA_TMS |  |
| V2 | PB11A/D1 | FPGA_MISO |  |
| V3 | INITN | FPGA_INITN |  |
| V4 | TDO | FPGA_TDO |  |
| W2 | PB11B/D0 | FPGA_MOSI |  |
| W3 | PROGRAMN | FPGA_PROGRAMN |  |
| Y3 | DONE | FPGA_DONE |  |

## J3 DF40C-100DS-0.4V(51) -- MN820 CN1 mate (all 100 pins)

| Pin | Name | Net | No-connect reason |
|---|---|---|---|
| 1 | GND | GND |  |
| 2 | GND | GND |  |
| 3 | GND | GND |  |
| 4 | LVDS_RX0_D0_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 5 | NC |  | module NC |
| 6 | LVDS_RX0_D0_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 7 | NC |  | module NC |
| 8 | LVDS_RX0_D1_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 9 | NC |  | module NC |
| 10 | LVDS_RX0_D1_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 11 | NC |  | module NC |
| 12 | LVDS_RX0_D2_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 13 | VCC3V3 | 3V3_MN |  |
| 14 | LVDS_RX0_D2_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 15 | VCC3V3 | 3V3_MN |  |
| 16 | LVDS_RX0_CLK_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 17 | VCC3V3 | 3V3_MN |  |
| 18 | LVDS_RX0_CLK_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 19 | VCC3V3 | 3V3_MN |  |
| 20 | LVDS_RX0_D3_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 21 | SD_CD |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 22 | LVDS_RX0_D3_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 23 | SD_D0 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 24 | GND | GND |  |
| 25 | SD_D1 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 26 | LVDS_RX1_D0_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 27 | SD_D2 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 28 | LVDS_RX1_D0_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 29 | SD_D3 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 30 | LVDS_RX1_D1_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 31 | SD_CLK |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 32 | LVDS_RX1_D1_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 33 | SD_CMD |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 34 | LVDS_RX1_D2_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 35 | SPIM_MOSI |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 36 | LVDS_RX1_D2_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 37 | SPIM_MISO |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 38 | LVDS_RX1_CLK_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 39 | SPIM_IO3 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 40 | LVDS_RX1_CLK_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 41 | SPIM_IO2 |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 42 | LVDS_RX1_D3_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 43 | SPIM_SS_N |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 44 | LVDS_RX1_D3_P |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 45 | SPIM_SCLK |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 46 | GND | GND |  |
| 47 | GND | GND |  |
| 48 | AUDIO_R |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 49 | GND | GND |  |
| 50 | GND | GND |  |
| 51 | GND | GND |  |
| 52 | AUDIO_L |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 53 | GND | GND |  |
| 54 | GND | GND |  |
| 55 | GND | GND |  |
| 56 | I2S_LRCLK |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 57 | LVDS_TX0_D0_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 58 | I2S_BCLK |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 59 | LVDS_TX0_D0_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 60 | I2S_SDA |  | module function unused in ARC-1 (CPU owns SD/audio/flash) |
| 61 | LVDS_TX0_D1_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 62 | DISP |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 63 | LVDS_TX0_D1_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 64 | BKLIT_PWM |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 65 | LVDS_TX0_D2_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 66 | GND | GND |  |
| 67 | LVDS_TX0_D2_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 68 | GPIO3 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 69 | LVDS_TX0_CLK_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 70 | GPIO2 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 71 | LVDS_TX0_CLK_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 72 | GPIO4 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 73 | LVDS_TX0_D3_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 74 | GPIO6 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 75 | LVDS_TX0_D3_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 76 | GPIO5 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 77 | GND | GND |  |
| 78 | GPIO7 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 79 | LVDS_TX1_D0_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 80 | GPIO8 |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 81 | LVDS_TX1_D0_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 82 | GND | GND |  |
| 83 | LVDS_TX1_D1_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 84 | SPIS_MISO | BT_MISO_M |  |
| 85 | LVDS_TX1_D1_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 86 | SPIS_SCLK | BT_SCK |  |
| 87 | LVDS_TX1_D2_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 88 | SPIS_SS_N | BT_SS_N_M |  |
| 89 | LVDS_TX1_D2_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 90 | SPIS_MOSI | BT_MOSI |  |
| 91 | LVDS_TX1_CLK_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 92 | SPIS_IO3 | BT_IO3_M |  |
| 93 | LVDS_TX1_CLK_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 94 | SPIS_IO2 | BT_IO2_M |  |
| 95 | LVDS_TX1_D3_N |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 96 | INT_N | BT_INT_N |  |
| 97 | LVDS_TX1_D3_P |  | R09 panel/backlight/touch (deferred, see docs/PANEL_INTERFACE_R09.md) |
| 98 | RESET_N | BT_RST_N |  |
| 99 | GND | GND |  |
| 100 | GND | GND |  |

## U16 W25Q256JVFIQ -- W25Q256JVFIQ boot NOR

| Pin | Name | Net | No-connect reason |
|---|---|---|---|
| 1 | IO3 | SPI0_IO3 |  |
| 2 | VCC | 3V3 |  |
| 3 | ~{RESET} | NOR_RESET_N |  |
| 4 | NC |  | NC per datasheet |
| 5 | NC |  | NC per datasheet |
| 6 | NC |  | NC per datasheet |
| 7 | ~{CS} | SPI0_CS0_N |  |
| 8 | DO_IO1 | SPI0_MISO |  |
| 9 | IO2 | SPI0_IO2 |  |
| 10 | GND | GND |  |
| 11 | NC |  | NC per datasheet |
| 12 | NC |  | NC per datasheet |
| 13 | NC |  | NC per datasheet |
| 14 | NC |  | NC per datasheet |
| 15 | DI_IO0 | SPI0_MOSI |  |
| 16 | CLK | SPI0_CLK |  |

## U25 APS6404L-3SQR -- APS6404L PSRAM

| Pin | Name | Net | No-connect reason |
|---|---|---|---|
| 1 | ~{CE} | PSRAM_CE_N |  |
| 2 | SO_SIO1 | PSRAM_SIO1 |  |
| 3 | SIO2 | PSRAM_SIO2 |  |
| 4 | VSS | GND |  |
| 5 | SI_SIO0 | PSRAM_SIO0 |  |
| 6 | SCLK | PSRAM_SCLK |  |
| 7 | SIO3 | PSRAM_SIO3 |  |
| 8 | VDD | PSRAM_VDD |  |

