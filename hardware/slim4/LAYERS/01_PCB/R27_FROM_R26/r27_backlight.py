# R27 edits 39-40: backlight boost output (TPS61165, U7). (39) C309, 1 uF 50 V X5R 0603, keeps only about 0.4-0.6 uF
# at the 20-24 V LED voltage (DC bias), below the TPS61165's 1 uF minimum (pre-order review POWER M5, DISPLAY F10):
# C140, the same part (CL10A105KB8NNNC, JLC C15849), goes in parallel, joined to C309's pads. (40) D2 sees the
# boost's 37-39 V open-LED limit against its 40 V rating: STPS1L40ZFY becomes STPS1L60ZFY (ST, 60 V 1 A, the same
# SOD-123Flat package and family, JLC C448649), so the land pattern is unchanged.
exec(open(sys.argv[2]).read())
c309={p.GetNumber():(mm(p.GetPosition().x),mm(p.GetPosition().y)) for p in fpr('C309').Pads()}
f,txt=place_joined('C140','Capacitor_SMD','C_0603_1608Metric','CL10A105KB8NNNC','C15849',
                   'R27: second 1 uF 50 V on the backlight boost output, beside C309 (KiCad 7 library Capacitor_SMD:C_0603_1608Metric)',
                   [fpr('C309').GetPosition() and (mm(fpr('C309').GetPosition().x),mm(fpr('C309').GetPosition().y))], 3.5,
                   {'1':('LCD_LED_A', [c309['1']], 3.0, False), '2':('GND', copper_points('GND'), 2.0, None)})
d2=set_part('D2','STPS1L60ZFY','C448649','R27: 60 V (was STPS1L40ZFY 40 V), same ST family and SOD-123Flat land as R8')
print('backlight: '+txt+'; D2 now '+d2.GetValue())
