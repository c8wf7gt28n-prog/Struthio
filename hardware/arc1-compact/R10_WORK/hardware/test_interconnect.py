"""Regression and negative tests for the exact-package SDRAM checker."""
import copy
import csv
from pathlib import Path
import subprocess
import sys
import unittest

from check_interconnect import validate


class InterconnectTests(unittest.TestCase):
    def setUp(self):
        with Path(__file__).with_name('R10_flash_pinmux.csv').open() as f:
            self.rows = list(csv.DictReader(f))

    def test_generated_map(self):
        validate(self.rows)

    def test_old_eight_pin_nor_mapping_rejected(self):
        next(r for r in self.rows if r['group'] == 'NOR' and r['signal'] == 'SPI0_CLK')['peer_pin'] = '6 CLK'
        with self.assertRaises(ValueError):
            validate(self.rows)

    def test_swapped_memory_pins_rejected(self):
        rows = copy.deepcopy(self.rows)
        data = [r for r in rows if r['group'] == 'SDRAM45']
        data[0]['peer_pin'], data[1]['peer_pin'] = data[1]['peer_pin'], data[0]['peer_pin']
        with self.assertRaises(ValueError):
            validate(rows)

    def test_duplicate_fpga_pin_rejected(self):
        data = [r for r in self.rows if r['group'] == 'SDRAM45']
        data[0]['pin'] = data[1]['pin']
        with self.assertRaises(ValueError):
            validate(self.rows)

    def test_missing_supply_rejected(self):
        rows = [r for r in self.rows if not (r['group'] == 'SDRAM45_POWER' and r['pin'] == '1')]
        with self.assertRaises(ValueError):
            validate(rows)

    def test_nc_must_remain_unconnected(self):
        next(r for r in self.rows if r['group'] == 'SDRAM45_POWER' and r['function'] == 'NC')['peer_chip'] = 'GND'
        with self.assertRaises(ValueError):
            validate(self.rows)

    def test_release_is_blocked(self):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_interconnect.py')), '--require-release'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('BOARD_RELEASE_HOLD', result.stdout)


if __name__ == '__main__':
    unittest.main()
