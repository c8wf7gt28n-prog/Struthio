"""Deterministic FAT32 fixture writer, not a filesystem reader or target format.

The firmware reads these bytes using pinned read-only FatFs over modeled USB.
Single short-name file, 512B sectors, one FAT and no partition table.
"""
import struct
SECTOR=512
SECTORS=70000
RESERVED=32
FAT_SECTORS=600
DATA=RESERVED+FAT_SECTORS
MAX_FILE=16*1024*1024

def pack(package):
    if not isinstance(package,bytes) or not 32<=len(package)<=MAX_FILE:
        raise ValueError('FAT_FIXTURE_PACKAGE_SIZE')
    clusters=(len(package)+SECTOR-1)//SECTOR
    if clusters+2>=SECTORS-DATA:raise ValueError('FAT_FIXTURE_CAPACITY')
    image=bytearray(SECTORS*SECTOR)
    image[:11]=b'\xeb\x58\x90ARCFS   '
    struct.pack_into('<HBHBHHBHHHII',image,11,512,1,RESERVED,1,0,0,0xf8,0,32,64,0,SECTORS)
    struct.pack_into('<IHHIHH',image,36,FAT_SECTORS,0,0,2,1,6)
    image[64]=0x80;image[66]=0x29;struct.pack_into('<I',image,67,0x31435241)
    image[71:82]=b'ARC MEDIA  ';image[82:90]=b'FAT32   ';image[510:512]=b'\x55\xaa'
    struct.pack_into('<I',image,SECTOR,0x41615252);struct.pack_into('<III',image,SECTOR+484,0x61417272,SECTORS-DATA-clusters-1,clusters+3);struct.pack_into('<I',image,SECTOR+508,0xaa550000)
    image[6*SECTOR:7*SECTOR]=image[:SECTOR];image[7*SECTOR:8*SECTOR]=image[SECTOR:2*SECTOR]
    fat=RESERVED*SECTOR
    for index,value in ((0,0x0ffffff8),(1,0xffffffff),(2,0x0fffffff)):struct.pack_into('<I',image,fat+4*index,value)
    for i in range(clusters):struct.pack_into('<I',image,fat+4*(3+i),0x0fffffff if i==clusters-1 else 4+i)
    directory=DATA*SECTOR;image[directory:directory+11]=b'GAME    ARC';image[directory+11]=0x20
    struct.pack_into('<H',image,directory+26,3);struct.pack_into('<I',image,directory+28,len(package))
    offset=(DATA+1)*SECTOR;image[offset:offset+len(package)]=package
    return bytes(image)
