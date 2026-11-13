# R27 edit 42: USB series resistors. R401/R402 on USB_JTAG_DP/DM were 0 ohm; Espressif's hardware design guidelines
# and its EV board use 22-33 ohm series resistors on the ESP32-P4's USB data lines (pre-order review P4CORE, AUDIO_IO
# M3). They become 22 ohm 1 % (UNI-ROYAL 0402WGF220JTCE, JLC C25092) in the same 0402 places.
exec(open(sys.argv[2]).read())
for r in ('R401','R402'): set_part(r,'0402WGF220JTCE','C25092','R27: 22 ohm USB series resistor (was 0 ohm); R8 first-copper land')
print('usb: R401, R402 22 ohm')
