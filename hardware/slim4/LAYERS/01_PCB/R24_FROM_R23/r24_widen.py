# R24 edit 24: remove a redundant battery run and widen what is left of the power and ground routing (pad-to-via stubs and short runs; the rails
# themselves are now In2 planes and B.Cu copper areas). Each track takes the widest of 0.8/0.6/0.5/0.4/0.3/0.25/0.2 mm
# that keeps 0.12 mm from other nets' copper on its layer; tracks into pins narrower than 0.4 mm keep a 0.6 mm neck at
# their routed width, and tracks beside another net's copper area are left as routed.
exec(open(sys.argv[2]).read())
# The B.Cu BAT_PLUS run from Q2 up the left arm (31.8 mm, 0.152 mm) duplicates the In2 BAT_PLUS plane, which Q2 reaches
# through the two vias beside it: removed with its end via.
kill_tracks(lambda t: t.GetNetname()=='BAT_PLUS' and ((t.Type()==pcbnew.PCB_VIA_T and near(t.GetPosition(),-23.45,21.16,0.02)) or
            (t.Type()!=pcbnew.PCB_VIA_T and abs(mm(t.GetStart().x)+23.45)<0.02 and abs(mm(t.GetEnd().x)+23.45)<0.02 and abs(mm(t.GetLength())-31.79)<0.05)))
POWER={'SYS_RAW','BAT_PLUS','BAT_CONN','USB_VBUS','3V3_SYS','1V1_HP','LCD_1V8','LCD_VCI_3V0','LCD_LED_A','LCD_LED_K',
       'VDD_USBPHY_LOCAL','VDDO_FLASH_3V3','VDDO_PSRAM_1V9','VDDO_MIPI_2V5','GND'}
n=widen(POWER)
print('widen: segments widened', n)
