#!/usr/bin/env python3
"""Independent SDRAM endpoint check; never treats this as board release evidence."""
import argparse
import csv
from pathlib import Path


def validate(rows):
    signals = [r for r in rows if r['group'] == 'SDRAM45']
    supplies = [r for r in rows if r['group'] == 'SDRAM45_POWER']
    # Manufacturer Figure 1, in ascending TSOP-II pin order, independently
    # transcribed rather than imported from the generator's mapping.
    pin_names = ('VDD DQ0 VDDQ DQ1 DQ2 VSSQ DQ3 DQ4 VDDQ DQ5 DQ6 VSSQ '
                 'DQ7 VDD LDQM WE CAS RAS CS BA0 BA1 A10 A0 A1 A2 A3 VDD '
                 'VSS A4 A5 A6 A7 A8 A9 A11 A12 CKE CLK UDQM NC VSS '
                 'DQ8 VDDQ DQ9 DQ10 VSSQ DQ11 DQ12 VDDQ DQ13 DQ14 VSSQ DQ15 VSS').split()
    def name(signal):
        return {'sd_dqm[0]': 'LDQM', 'sd_dqm[1]': 'UDQM'}.get(
            signal, signal.removeprefix('sd_').removesuffix('_n').replace('[', '').replace(']', '').upper())
    actual = [(int(r['peer_pin']), name(r['signal'])) for r in signals]
    actual += [(int(r['pin']), r['function']) for r in supplies]
    if sorted(actual) != list(enumerate(pin_names, 1)):
        raise ValueError('SDRAM pin map differs from manufacturer TSOP-II Figure 1')
    if len({r['pin'] for r in signals}) != 39:
        raise ValueError('SDRAM FPGA endpoint reused')
    for r in supplies:
        expected = 'NO_CONNECT' if r['function'] == 'NC' else ('GND' if r['function'].startswith('VSS') else '3V3_45_MEM')
        if r['peer_chip'] != expected:
            raise ValueError('SDRAM supply/NC net mismatch')
    nor_names = {'SPI0_CLK': 'CLK', 'SPI0_CS0_N': 'CS', 'SPI0_MOSI': 'DI',
                 'SPI0_MISO': 'DO', 'SPI0_IO2': 'WP', 'SPI0_IO3': 'HOLD'}
    nor = [(int(r['peer_pin'].split()[0]), nor_names[r['signal']]) for r in rows if r['group'] == 'NOR']
    nor += [(int(r['pin']), r['function'].lstrip('/')) for r in rows if r['group'] == 'NOR_AUX']
    if sorted(nor) != list(enumerate('HOLD VCC RESET NC NC NC CS DO WP GND NC NC NC NC DI CLK'.split(), 1)):
        raise ValueError('NOR map differs from SOIC16 Figure 1b')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-release', action='store_true')
    args = parser.parse_args()
    with Path(__file__).with_name('R10_flash_pinmux.csv').open() as f:
        validate(list(csv.DictReader(f)))
    print('SDRAM_ENDPOINT_PASS: 54 package pins; 39 distinct FPGA signal endpoints')
    print('NOR_ENDPOINT_PASS: 16 package pins; dedicated RESET pin 3')
    print('BOARD_RELEASE_HOLD: schematic, power, boot, video and hardware validation incomplete')
    return 2 if args.require_release else 0


if __name__ == '__main__':
    raise SystemExit(main())
