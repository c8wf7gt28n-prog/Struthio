/* SparkFun OpenLCD / SerLCD special-command cursor positioning:
   0xFE, DDRAM-address command; 0x80 for row 0 and 0xC0 for row 1.
   Datasheet/library reference: SparkFun_SerLCD_Arduino_Library SerLCD.h.
   Transport-independent encoding ONLY: no actual F133 TWI register access. */
#include <arc1/serlcd_i2c.h>
static int write_one(const arc1_serlcd_bus_t *bus, unsigned char cursor, const char row[17]) {
    uint8_t packet[18]; unsigned i;
    packet[0]=0xfeu; packet[1]=cursor;
    for (i=0;i<16;i++) {
        unsigned char ch=(unsigned char)row[i];
        /* Prevent command injection and malformed display rows. */
        if (ch<0x20u || ch>0x7eu) return -2;
        packet[i+2]=ch;
    }
    if (row[16]!='\0') return -2;
    return bus->write(bus->context,bus->address,packet,sizeof(packet));
}
int arc1_serlcd_write_rows(void *context, const char row0[17], const char row1[17]) {
    arc1_serlcd_bus_t *bus=(arc1_serlcd_bus_t*)context;
    int rc;
    if (!bus || !bus->write || !row0 || !row1 || bus->address<0x08u || bus->address>0x77u) return -1;
    rc=write_one(bus,0x80u,row0);
    if (rc) return rc;
    return write_one(bus,0xc0u,row1);
}
