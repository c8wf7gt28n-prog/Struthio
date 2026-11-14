# Third-party notices

Preserve the licence and provenance files beside bundled upstream source.

- OpenDyslexic: branding/ux17/fonts/OFL.txt.
- IBM Plex Sans and IBM Plex Mono (interface fonts, SIL Open Font License 1.1, © IBM Corp.): branding/fonts/plex/LICENSE.txt and NOTICE.md.
- Parisienne (the script for short greetings and pleasantries, SIL Open Font License 1.1, © 2012 Brian J. Bonislawsky DBA Astigmatic): branding/fonts/script/OFL-Parisienne.txt.
- Special Elite (the typewriter face of headings in the Kasandra appearance, Apache License 2.0, Astigmatic): branding/fonts/typewriter/SpecialElite-LICENSE.txt and NOTICE.md.

- CPython WASI build (the sandboxed Python guest, Python Software Foundation licence): runtimes/python-wasi/LICENSE and runtime.json.

Graphite's own code and documents are under the GNU GPL, version 2 only (COPYING). The parts on this page are not Graphite's own and keep the terms named here.

PySide6 and other installed tools are dependencies, not bundled binaries. Retain their upstream notices when distributing an installed environment. The libraries Graphite loads, as their own distributions declare them: Qt and Qt for Python (PySide6, shiboken6: LGPL 3.0 or GPL 2.0 or GPL 3.0; Graphite uses the GPL 2.0 option); pypdf (BSD); cryptography (BSD or Apache 2.0), which contains OpenSSL (Apache 2.0), with cffi (MIT) and pycparser (BSD); python-docx (MIT) with lxml (BSD); wasmtime (Apache 2.0 with the LLVM exception). COPYING, note 4, gives the permission that combining with the Apache-licensed ones needs.


## Local inference worker — Pass 3

llama.cpp b11669 / commit 620d2225cc436ab0b001e3200e590e3b286ef9ab is redistributed as two unchanged official Linux x64 archives, the CPU build and the Vulkan build, under runtimes/llama.cpp/b11669. Its MIT LICENSE is included there. Original archive licenses and provenance are preserved. Model weights are external and are not redistributed in this program ZIP. The independent GGUF inspector follows the public GGUF specification; the upstream PySide6 editor is a design reference, with no write/edit facilities exposed.

## I02 mathematical tools and Office bridge

Optional Python dependencies are pinned in requirements-math.txt: SymPy 1.14.0 (BSD), mpmath 1.3.0 (BSD), and z3-solver 4.15.4.0 (MIT). Their distributions retain their own notices.

The unmodified LibreOffice Java UNO API JAR 25.2.0 is included under MPL 2.0. See runtimes/office-uno/LICENSE, its upstream Maven POM, and runtime.json for source and digest. Upstream source: https://git.libreoffice.org/core. The fixed LedgerOffice.java client is Ledger application code. LibreOffice and the JDK themselves are supplied by the host installation.
