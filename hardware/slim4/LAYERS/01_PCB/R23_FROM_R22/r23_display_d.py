# R23 edit 15, part D (after part C): remove the stubs left where a route joined the hand-routed column part-way,
#  and unlock the copper again (R22 has nothing locked).
exec(open(sys.argv[2]).read())
NETS={'MIPI_DSI_CLK_P','MIPI_DSI_CLK_N','MIPI_DSI_D0_P','MIPI_DSI_D0_N','MIPI_DSI_D1_P','MIPI_DSI_D1_N','LCD_VCI_3V0','LCD_1V8',
      'LCD_RESX','LCD_LED_A','LCD_LED_K','BQ_EN2','CHG_STATUS','PGOOD_STATUS','PWR_WAKE','USB_CURR_OUT2'}
prune_all(NETS,(-50.0,0.0,50.0,130.0))
for t in b.GetTracks(): t.SetLocked(False)
