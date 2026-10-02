#!/bin/sh
# STRUTHIO ONE · Gerbers + drill (zip for JLCPCB) and board pictures, from out/struthio_one.kicad_pcb
set -e
cd "$(dirname "$0")/out"
rm -rf gerbers && mkdir gerbers
kicad-cli pcb export gerbers --layers F.Cu,B.Cu,F.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts --subtract-soldermask --no-x2 -o gerbers/ struthio_one.kicad_pcb >/dev/null
kicad-cli pcb export drill --format excellon --drill-origin absolute --excellon-separate-th -u mm -o gerbers/ struthio_one.kicad_pcb >/dev/null
rm -f gerbers/*.gbrjob struthio_one_gerbers.zip
(cd gerbers && zip -q -X ../struthio_one_gerbers.zip *)
echo "gerbers: $(ls gerbers | wc -l) files -> out/struthio_one_gerbers.zip"
