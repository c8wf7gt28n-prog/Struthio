#!/usr/bin/env python3
"""STRUTHIO · the browser flasher, ready to host (GitHub Pages or any https site).

    python3 make_webflash.py FIRMWARE_BUILD_DIR OUT_DIR

Copies index.html, writes manifest.json (ESP Web Tools) and the five images it flashes. Web Serial needs https
(or localhost), so the folder has to be served, not opened as a file.
"""
import json, os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))
HH = os.path.join(HERE, '..', '..')
build, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
parts = [('bootloader.bin', os.path.join(build, 'bootloader', 'bootloader.bin'), 0x0),
         ('partition-table.bin', os.path.join(build, 'partition_table', 'partition-table.bin'), 0x8000),
         ('struthio.bin', os.path.join(build, 'struthio.bin'), 0x10000),
         ('struthio.pak', os.path.join(HH, 'build', 'assets', 'struthio.pak'), 0x410000),
         ('struthio_music.ima', os.path.join(HH, 'build', 'assets', 'struthio_music.ima'), 0xD10000)]
for name, src, _ in parts: shutil.copyfile(src, os.path.join(out, name))
shutil.copyfile(os.path.join(HERE, 'index.html'), os.path.join(out, 'index.html'))
shutil.copytree(os.path.join(HERE, 'esp-web-tools'), os.path.join(out, 'esp-web-tools'), dirs_exist_ok=True)   # bundled: no CDN
manifest = {'name': 'STRUTHIO', 'version': 'ONE SLIM', 'new_install_prompt_erase': True,
            'builds': [{'chipFamily': 'ESP32-S3', 'parts': [{'path': n, 'offset': o} for n, _, o in parts]}]}
json.dump(manifest, open(os.path.join(out, 'manifest.json'), 'w'), indent=2)
print('wrote', out)
