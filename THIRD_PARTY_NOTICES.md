# Third-party notices

Preserve the licence and provenance files beside bundled upstream source.

- FreeRTOS: software/arcos/upstream/freertos/LICENSE.md (MIT).
- RT-Thread: software/arcos/upstream/rtthread/LICENSE (Apache 2.0).
- U-Boot source excerpts: software/boot/upstream/u-boot/COPYING and software/boot/first_stage/reference/u-boot/COPYING (GPL 2.0).
- Linux-derived references: hardware/sources/f133_ehci29/upstream/COPYING and LICENSES_* files; individual source headers identify applicable terms.
- FatFs: hardware/compact-arc1/R10_WORK/firmware/usb_media/fatfs/LICENSE.txt.
- OpenDyslexic: branding/ux17/fonts/OFL.txt.
- IBM Plex Sans and IBM Plex Mono (interface fonts, SIL Open Font License 1.1, © IBM Corp.): branding/fonts/plex/LICENSE.txt and NOTICE.md.
- Parisienne (the script for short greetings and pleasantries, SIL Open Font License 1.1, © 2012 Brian J. Bonislawsky DBA Astigmatic): branding/fonts/script/OFL-Parisienne.txt.

PySide6 and other installed tools are dependencies, not bundled binaries. Retain their upstream notices when distributing an installed environment.


## Local inference worker — Pass 3

llama.cpp b11669 / commit 620d2225cc436ab0b001e3200e590e3b286ef9ab is redistributed as unchanged official Linux x64 and Windows x64 CPU archives under runtimes/llama.cpp/b11669. Its MIT LICENSE is included there. The Windows archive also includes LICENSE-LLVM-OpenMP for its bundled libomp.dll. Original archive licenses and provenance are preserved. Model weights are external and are not redistributed in this program ZIP. The independent GGUF inspector follows the public GGUF specification; the upstream PySide6 editor is a design reference, with no write/edit facilities exposed.

## I02 mathematical tools and Office bridge

Optional Python dependencies are pinned in requirements-math.txt: SymPy 1.14.0 (BSD), mpmath 1.3.0 (BSD), and z3-solver 4.15.4.0 (MIT). Their distributions retain their own notices.

The unmodified LibreOffice Java UNO API JAR 25.2.0 is included under MPL 2.0. See runtimes/office-uno/LICENSE, its upstream Maven POM, and runtime.json for source and digest. Upstream source: https://git.libreoffice.org/core. The fixed LedgerOffice.java client is Ledger application code. LibreOffice and the JDK themselves are supplied by the host installation.
