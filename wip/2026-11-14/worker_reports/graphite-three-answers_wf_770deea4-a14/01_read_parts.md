{
 "summary": "Read-only inventory of /home/user/Struthio as it stands now (HEAD e3a0a23, two commits after 37b78f0; those two commits change only own code and records). I am not a lawyer; items that need one are marked.\n\nHeadline findings\n1. Nothing AGPL or GPL-3.0-only is imported or bundled. The PDF library is pypdf 7.0.0 (BSD-3-Clause), plus Qt PDF and the poppler command-line tools. PyMuPDF and numpy are not referenced anywhere in the tree.\n2. Qt for Python confirmed from installed metadata: PySide6, PySide6_Essentials, PySide6_Addons and shiboken6 6.8.3 all say \"LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only\". Graphite must take the GPL-2.0-only option (LGPL-3.0 alone does not combine with GPL-2.0-only). No GPL-3-only Qt add-on (Graphs, HTTP Server, Network Authorization, Quick 3D, Virtual Keyboard and the like) is imported; keep it that way.\n3. The one real class of conflict is Apache-2.0 code loaded into the same process as Graphite's own code: OpenSSL (through the cryptography package and Python's own ssl/hashlib), the LibreOffice UNO JAR, third-party parts of Qt PDF and Qt WebEngine, wasmtime, and optional OCP. The owner, as copyright holder, cures all of them with one additional permission (draft in wording_needed).\n4. The programs named in the question are all run as separate processes, never imported: llama-server (subprocess plus HTTP on 127.0.0.1), LibreOffice (soffice subprocess, driven over a local UNO socket), KiCad (kicad-cli subprocess), ngspice (subprocess), poppler tools (subprocess). Mere aggregation.\n5. Third-party material physically in the tree is small: three runtimes (llama.cpp archives, MIT; LibreOffice UNO JAR, MPL-2.0; CPython WASI build, PSF-2.0) and three font families, eight font files (IBM Plex, Parisienne, OpenDyslexic, all OFL-1.1). No third-party source code is vendored: no file under workbench/, sdk/, pillkit/, tools/ or games/ carries a third-party copyright or licence header. By the tree's own records every image is owner-supplied (several are machine-generated); I found none that is third-party.\n\nWhere the tree's own list is wrong (/home/user/Struthio/THIRD_PARTY_NOTICES.md)\n- Lines 5-9 name FreeRTOS, RT-Thread, U-Boot, Linux-derived references and FatFs under software/ and hardware/. Neither folder exists in this tree, and no commit on this branch ever touched those paths. Remove the five lines.\n- Line 19 says llama.cpp is redistributed as \"Linux x64 and Windows x64 CPU archives\". The tree holds the Linux x64 CPU archive and the Linux x64 Vulkan archive; there is no Windows archive (runtime.json line 19 still describes one). The Vulkan archive and the LLVM-OpenMP remark need correcting.\n- The CPython WASI runtime (runtimes/python-wasi, PSF-2.0) is not mentioned at all.\n- /home/user/Struthio/branding/fonts/NOTICE.md and LICENSE.txt describe Noto Sans CJK SC, but that font file is not in the tree; four code sites still look for it.\n- Dependencies it does not name: pypdf, cryptography (with OpenSSL), python-docx and lxml, wasmtime, cffi, pycparser.\n- /home/user/Struthio/RIGHTS.md line 3 says \"No licence is assigned\" and that publication grants no right to reuse. It must be rewritten when GPL-2.0-only is adopted; /home/user/Struthio/README.md line 128 points to it.\n\nScope the licence must state: fonts (OFL), the three runtimes, and whatever the owner decides for artwork, the Stacy character and the game's music cannot simply be swept under the GPL grant.",
 "components": [
  {
   "name": "llama.cpp b11669 prebuilt archives (Linux x64 CPU and Linux x64 Vulkan)",
   "where": "/home/user/Struthio/runtimes/llama.cpp/b11669/llama-b11669-bin-ubuntu-x64.tar.gz and llama-b11669-bin-ubuntu-vulkan-x64.tar.gz, with LICENSE and runtime.json beside them",
   "licence": "MIT (Copyright 2023-2026 The ggml authors). One LICENSE file inside each archive; digests match runtime.json.",
   "kind": "bundled-binary",
   "how_used": "Unpacked and run as a separate program. /home/user/Struthio/workbench/local_brain.py:342-344 starts python -m workbench.brain_worker, which starts llama-server (/home/user/Struthio/workbench/brain_worker.py:44, subprocess.Popen); Graphite talks to it over HTTP on 127.0.0.1 (local_brain.py:244). No llama library is loaded into Graphite (the only ctypes use is libc).",
   "issue_with_gpl2_only": "None: separate program, mere aggregation. Notice errors only: THIRD_PARTY_NOTICES.md:19 claims a Windows archive that is not in the tree and does not name the Vulkan archive."
  },
  {
   "name": "LibreOffice UNO Java classes 25.2.0 (libreoffice-25.2.0.jar)",
   "where": "/home/user/Struthio/runtimes/office-uno/ (jar, pom, LICENSE, runtime.json)",
   "licence": "MPL-2.0 (pom and runtime.json:7). The LICENSE beside it also lists Apache-2.0 material; LibreOffice code derived from OpenOffice carries Apache-2.0 notices (from general knowledge, not read out of the class files).",
   "kind": "bundled-binary",
   "how_used": "Graphite's own LedgerOffice.java and LedgerSession.java are run with it on the class path in a separate Java process: /home/user/Struthio/workbench/office_math_runtime.py:30-38 and /home/user/Struthio/workbench/native_sessions.py:155-162 (java -cp <jar> LedgerOffice.java ...). That client talks to a separate soffice process over a local socket.",
   "issue_with_gpl2_only": "MPL-2.0 itself is fine (its section 3.3 names GPL 2.0). The Apache-2.0-derived parts inside it share a Java process with Graphite's own Java files: covered by the additional permission. See problems."
  },
  {
   "name": "CPython 3.13.17 WASI build (python-wasi.zip, 559 files, python.wasm)",
   "where": "/home/user/Struthio/runtimes/python-wasi/ (zip, LICENSE, runtime.json)",
   "licence": "PSF-2.0, with the usual notices for software incorporated into Python (LICENSE in the folder is identical to the one in the zip).",
   "kind": "bundled-binary",
   "how_used": "Run as a guest program inside the wasmtime sandbox by /home/user/Struthio/workbench/experiment_runtime.py:60-66. It is executed, not imported into Graphite's code.",
   "issue_with_gpl2_only": "None (PSF-2.0 is GPL-compatible, and it is a separate program). Not listed in THIRD_PARTY_NOTICES.md at all: add it."
  },
  {
   "name": "IBM Plex Sans and IBM Plex Mono (5 TTF files)",
   "where": "/home/user/Struthio/branding/fonts/plex/",
   "licence": "SIL Open Font License 1.1, Copyright 2017 IBM Corp., Reserved Font Name Plex. LICENSE.txt and NOTICE.md are beside the files.",
   "kind": "bundled-font",
   "issue_with_gpl2_only": "No conflict when bundled, but the fonts must stay under the OFL and cannot be put under the GPL. The licence note must exclude them."
  },
  {
   "name": "Parisienne Regular",
   "where": "/home/user/Struthio/branding/fonts/script/Parisienne-Regular.ttf with OFL-Parisienne.txt",
   "licence": "SIL Open Font License 1.1, Copyright 2012 Brian J. Bonislawsky DBA Astigmatic.",
   "kind": "bundled-font",
   "issue_with_gpl2_only": "Same as Plex: stays under the OFL; exclude from the GPL grant."
  },
  {
   "name": "OpenDyslexic Regular and Bold",
   "where": "/home/user/Struthio/branding/ux17/fonts/ (two OTF files, OFL.txt, SOURCE.json)",
   "licence": "SIL Open Font License 1.1, Copyright Abbie Gonzalez, Reserved Font Name OpenDyslexic.",
   "kind": "bundled-font",
   "issue_with_gpl2_only": "Same as Plex: stays under the OFL; exclude from the GPL grant."
  },
  {
   "name": "Noto Sans CJK SC notice and licence text (the font itself is absent)",
   "where": "/home/user/Struthio/branding/fonts/NOTICE.md and /home/user/Struthio/branding/fonts/LICENSE.txt",
   "licence": "SIL Open Font License 1.1 (text only).",
   "kind": "bundled-text-or-data",
   "how_used": "Code still looks for branding/fonts/NotoSansCJKsc-Regular.otf: /home/user/Struthio/workbench/reference_qt.py:49, pdf_qt.py:52, office_qt.py:85, office_runtime.py:13. The file is not in the tree and never was on this branch.",
   "issue_with_gpl2_only": "None. An orphan notice: either restore the font with it or remove the notice."
  },
  {
   "name": "Desk and Stacy artwork (plates, operator portraits, Stacy portraits, Slate bird sprites)",
   "where": "/home/user/Struthio/branding/boss/ (8 plates, journal-operator.webp, preview-operator.webp, night-signal.svg, roof-antenna.txt), /home/user/Struthio/branding/stacy/, /home/user/Struthio/branding/noir/clip.png, /home/user/Struthio/branding/slate/",
   "licence": "None assigned (RIGHTS.md:3 and :7). Recorded as owner-supplied; branding/stacy/character.json:9 says the Stacy art was 'generated with built-in image generation'; branding/slate/PROVENANCE.txt says owner-supplied generated pose keys.",
   "kind": "owner-made",
   "how_used": "Loaded as image files at run time (for example /home/user/Struthio/workbench/boss_qt.py:14-42).",
   "issue_with_gpl2_only": "No third-party image found (I viewed contact sheets of all of branding/). Not a GPL conflict, but the owner must say whether art is under the GPL or kept separate. Needs a lawyer: copyright in machine-generated images; branding/boss/plates has no per-file provenance record; docs/BOSS_visual_references/README.md:5 and :53 name Serial Experiments Lain and Evangelion as the mood for 'original' characters; 'RISC is good' and the 'Brain on Disk' plate play on a film line and a public-service advert."
  },
  {
   "name": "Marks and icons (Graphite point and cat, Hatch egg, Struthio bird, ARC-1 mark, interface icons)",
   "where": "/home/user/Struthio/branding/graphite/, hatch/, ledger/, logo/, shell2/, ux16/, noir/*.svg; /home/user/Struthio/workbench/nav_icons/ (40 PNG), workbench/arc1.ico, arc1_icon.png, logo.png, logo_compact.png, workbench/remote_pwa/*.png and icon.svg",
   "licence": "None assigned; project artwork by the tree's records (branding/graphite/README.txt, branding/hatch/README.txt, branding/ux16/ASSET_SOURCE.json, workbench/remote_pwa/SLATE_ICONS.txt).",
   "kind": "owner-made",
   "issue_with_gpl2_only": "None found. workbench/nav_icons has no provenance file (used at /home/user/Struthio/workbench/qt_app.py:2793); it looks like the same family as the owner's ARC Visual Foundation pack. Not independently verified."
  },
  {
   "name": "STRUTHIO ARCADE 1.9.0 (the game behind System)",
   "where": "/home/user/Struthio/games/struthio/ (62 files: index.html, src/*.mjs, assets/art, assets/audio, sw.js)",
   "licence": "None assigned. Copied from the owner's own repository at commit c3edde7 (FROM_REPOSITORY.txt:1). No third-party script, web font or external URL in it.",
   "kind": "owner-made",
   "how_used": "Opened in a separate player process: /home/user/Struthio/workbench/struthio_qt.py:63 starts python -m workbench.struthio_play, which uses Qt WebEngine (/home/user/Struthio/workbench/struthio_play.py:18-19).",
   "issue_with_gpl2_only": "None in the code. Unknown: assets/audio/tarmac-at-midnight-loop.mp3 (3.2 MB) has no tags and no origin recorded anywhere in this tree (referenced at games/struthio/src/app/art.mjs:12). Its origin must be known before a licence is put on it."
  },
  {
   "name": "Graphite's own code: workbench/, sdk/cli/arc1cli/, pillkit/, tools/, tests_integrated/, top-level scripts",
   "where": "/home/user/Struthio/workbench/ (506 files), /home/user/Struthio/sdk/ (74), /home/user/Struthio/pillkit/ (6), /home/user/Struthio/tools/ (45), /home/user/Struthio/tests_integrated/ (57), /home/user/Struthio/*.sh, *.py, *.cmd",
   "licence": "None assigned today (RIGHTS.md:3). To become GPL-2.0-only.",
   "kind": "owner-made",
   "how_used": "Includes the staC language (sdk/cli/arc1cli/typed_pipeline.py, workbench/stacy_language.py, workbench/stac/), the phone page in workbench/remote_pwa (own JavaScript, no library), LedgerOffice.java and LedgerSession.java, and workbench/view_modules (its header, __init__.py:11, says standard library and Qt only).",
   "issue_with_gpl2_only": "No vendored third-party module and no third-party licence header found by a tree-wide search. Needs a lawyer: an additional permission is only valid for code the owner holds copyright in, including code written with machine help. Dead imports of a module that is not in the tree: vendor_kb (/home/user/Struthio/workbench/vendor_adapter.py:16, integration_tools.py:21)."
  },
  {
   "name": "algorithm_corpus.json (the Algorithm Atlas, 12 entries)",
   "where": "/home/user/Struthio/workbench/algorithm_corpus.json",
   "licence": "Own text. It cites NIST SP 330, the NIST/SEMATECH e-Handbook, SymPy and SciPy documentation, the Z3 guide and MIT OpenCourseWare by title and URL only; no copied passages seen.",
   "kind": "owner-made",
   "issue_with_gpl2_only": "None. Its own 'licence' fields say dependency licences were not reviewed by the Atlas."
  },
  {
   "name": "Documents, captures and briefs",
   "where": "/home/user/Struthio/docs/ (189 files: Markdown, JSON records, screenshots, 4 .docx, docs/briefs/Graphite_Master_Specification_v5_BOSS.pdf, docs/BOSS_visual_references/ five concept screens) and /home/user/Struthio/build/ (screenshots, model-trial records)",
   "licence": "None assigned; owner's documents and program screenshots. No vendor datasheet or vendor PDF is in docs/ (RIGHTS.md:5 says such originals are excluded).",
   "kind": "owner-made",
   "issue_with_gpl2_only": "None found. The owner decides whether documents go under the GPL or another licence. The handbook module names docs/orange_book/chapters.json (/home/user/Struthio/workbench/handbook.py:17), which is not in the tree."
  },
  {
   "name": "Examples and seed index",
   "where": "/home/user/Struthio/examples/clock_lab/, /home/user/Struthio/examples/thinkpad_first_run/, /home/user/Struthio/project/stacy_seed/current/ (catalog.json, index.sqlite, manifest.json)",
   "licence": "Own. examples/clock_lab/INPUTS.json marks the set 'synthetic': true; the seed is an index built from this tree's own files by workbench.stacy_foundation.",
   "kind": "owner-made",
   "issue_with_gpl2_only": "None. The seed index contains text of whatever is in the tree, so it follows the tree."
  },
  {
   "name": "Qt 6.8.3 through Qt for Python: PySide6 (QtCore, QtGui, QtWidgets, QtSvg, QtDBus, QtTest, QtMultimedia, QtMultimediaWidgets) and shiboken6",
   "where": "Not in the tree. /home/user/Struthio/requirements-qt.txt:2 (PySide6==6.8.3). Offline kit wheels: PySide6, PySide6_Essentials, PySide6_Addons, shiboken6 6.8.3.",
   "licence": "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only (METADATA of all four distributions in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/lib/python3.13/site-packages/PySide6-6.8.3.dist-info/METADATA and its three siblings).",
   "kind": "dependency-not-bundled",
   "how_used": "Imported in-process by 159 files under workbench/ (for example /home/user/Struthio/workbench/research_qt.py:4-5); shiboken6 at /home/user/Struthio/workbench/organizer_qt.py:7 and ten other files; QtDBus at session_power.py:86; QtMultimedia at view_modules/media.py:61.",
   "issue_with_gpl2_only": "No conflict if Graphite states that it uses Qt and Qt for Python under their GPL-2.0-only option. LGPL-3.0 alone would not combine with GPL-2.0-only. The PySide6_Addons wheel also carries GPL-3-only Qt modules (Qt's licensing page lists Graphs, HTTP Server, Network Authorization, Quick 3D, Virtual Keyboard and others); none is imported, and none may be."
  },
  {
   "name": "Qt PDF (PySide6.QtPdf, QtPdfWidgets)",
   "where": "Not in the tree; inside the PySide6_Addons wheel.",
   "licence": "Qt part: LGPL-3.0 or GPL-2.0 (Qt PDF licensing page). Contains PDFium (BSD-3-Clause) and third-party code including Abseil (Apache-2.0), FreeType, Little CMS, libjpeg-turbo, libpng, zlib.",
   "kind": "dependency-not-bundled",
   "how_used": "In-process: /home/user/Struthio/workbench/universal_viewer_qt.py:302-303 and /home/user/Struthio/workbench/thumbnails.py:162.",
   "issue_with_gpl2_only": "Apache-2.0 third-party part (Abseil) in the same process. Covered by the additional permission. See problems."
  },
  {
   "name": "Qt WebEngine (PySide6.QtWebEngineCore, QtWebEngineWidgets)",
   "where": "Not in the tree; inside the PySide6_Addons wheel.",
   "licence": "Qt part: LGPL-3.0, GPL-3.0 or GPL-2.0 (Qt WebEngine licensing page). Chromium part: many licences, the page says the most restrictive is LGPL-2.1, and the list includes Apache-2.0 components.",
   "kind": "dependency-not-bundled",
   "how_used": "Only in the game player process: /home/user/Struthio/workbench/struthio_play.py:18-19, started by /home/user/Struthio/workbench/struthio_qt.py:63.",
   "issue_with_gpl2_only": "Apache-2.0 parts of Chromium share a process with Graphite's own module. Covered by the additional permission. See problems."
  },
  {
   "name": "cryptography 50.0.2, with OpenSSL inside (and its helpers cffi 2.1.1, pycparser 3.12)",
   "where": "Not in the tree. /home/user/Struthio/requirements-qt.txt:4 and requirements-pills.txt:2; wheels in the offline kit.",
   "licence": "cryptography: Apache-2.0 OR BSD-3-Clause (take BSD-3-Clause). The wheel statically links OpenSSL 4.0.3 (Apache-2.0) and the Rust 'openssl' crate 0.10.81 (Apache-2.0 only): see /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/work/venv/lib/python3.13/site-packages/cryptography-50.0.2.dist-info/sboms/sbom.json and cryptography-rust.cyclonedx.json in the same folder. cffi: MIT-0. pycparser: BSD-3-Clause.",
   "kind": "dependency-not-bundled",
   "how_used": "Imported in-process: /home/user/Struthio/pillkit/pill.py:87-89, /home/user/Struthio/pillkit/tls_link.py:40-42, 73-76, 119-120, /home/user/Struthio/workbench/release_updates.py:116-117, /home/user/Struthio/workbench/release_publisher.py:7-8.",
   "issue_with_gpl2_only": "OpenSSL is Apache-2.0, which the FSF reads as incompatible with GPL version 2. This is the old 'OpenSSL exception' case. Covered by the additional permission. See problems."
  },
  {
   "name": "Python 3.13 and its standard library (ssl, hashlib, sqlite3, curses, tkinter, ctypes to libc)",
   "where": "Not in the tree. Debian python3; the offline kit carries the Debian packages.",
   "licence": "PSF-2.0 (GPL-compatible). Its ssl and hashlib modules bind to Debian's OpenSSL (Apache-2.0); sqlite3 is public domain; ncurses and Tcl/Tk are permissive; glibc is LGPL-2.1-or-later.",
   "kind": "dependency-not-bundled",
   "how_used": "ssl at /home/user/Struthio/workbench/remote_service.py:18 and /home/user/Struthio/pillkit/tls_link.py:20; hashlib in 168 files; curses at /home/user/Struthio/sdk/cli/arc1cli/ui.py:528; tkinter only in the old /home/user/Struthio/workbench/app.py:16. readline and dbm (GPL-3 libraries) are not imported.",
   "issue_with_gpl2_only": "Python itself: none. OpenSSL reached through ssl/hashlib is the same Apache-2.0 question as cryptography; same permission covers it."
  },
  {
   "name": "pypdf 7.0.0",
   "where": "Not in the tree. /home/user/Struthio/requirements-qt.txt:6; wheel in the offline kit.",
   "licence": "BSD-3-Clause (installed METADATA).",
   "kind": "dependency-not-bundled",
   "how_used": "In-process: /home/user/Struthio/workbench/universal_view.py:248, /home/user/Struthio/workbench/program_print.py:66 and 122-123, /home/user/Struthio/sdk/cli/arc1cli/pdf_evidence.py:46, intake_profiles.py:105, reference_extract.py:82.",
   "issue_with_gpl2_only": "None."
  },
  {
   "name": "python-docx 1.2.0 (brings lxml 6.1.3 and typing_extensions 4.16.0)",
   "where": "Not in the tree. /home/user/Struthio/requirements-office.txt:2 (optional, installed with --math).",
   "licence": "python-docx: MIT. lxml: BSD-3-Clause (bundles libxml2 and libxslt, MIT). typing_extensions: PSF-2.0. All from installed METADATA.",
   "kind": "dependency-not-bundled",
   "how_used": "In-process: /home/user/Struthio/workbench/office_service.py:67 and 142, /home/user/Struthio/sdk/cli/arc1cli/office_documents.py:73-78, /home/user/Struthio/tools/build_project_spec.py:4-10.",
   "issue_with_gpl2_only": "None."
  },
  {
   "name": "SymPy 1.14.0, mpmath 1.3.0, z3-solver 4.15.4.0",
   "where": "Not in the tree. /home/user/Struthio/requirements-math.txt:2-4 (optional, --math).",
   "licence": "SymPy: BSD-3-Clause. mpmath: BSD-3-Clause. z3-solver: MIT. All from installed METADATA.",
   "kind": "dependency-not-bundled",
   "how_used": "Imported in a child Python process that runs Graphite's own module: /home/user/Struthio/workbench/math_backend.py:36 starts the worker, :55 imports z3, :84 imports sympy.",
   "issue_with_gpl2_only": "None."
  },
  {
   "name": "wasmtime 50.0.1 (Python binding with the native library)",
   "where": "Not in the tree. /home/user/Struthio/requirements-experiments.txt:2 (optional, --experiments).",
   "licence": "Apache-2.0 WITH LLVM-exception (installed METADATA and LICENSE). The exception text contains a clause written for GPL version 2 combinations: conflicting sections may be deemed waived for the combined software.",
   "kind": "dependency-not-bundled",
   "how_used": "Imported in-process: /home/user/Struthio/workbench/experiment_runtime.py:23 and :60. Graphite's own catalogue already records this licence (/home/user/Struthio/workbench/capability_catalog.py:48).",
   "issue_with_gpl2_only": "Low risk because of the LLVM exception's GPLv2 clause, but still Apache-2.0 in the same process. Name it in the additional permission. Crates inside the native library were not checked."
  },
  {
   "name": "OCP (cadquery-ocp, Python bindings to Open CASCADE)",
   "where": "Not in the tree and not in any requirements file or installer.",
   "licence": "From general knowledge, not from metadata (not installed in the checking environment): OCP is Apache-2.0; Open CASCADE is LGPL-2.1 with an exception.",
   "kind": "dependency-not-bundled",
   "how_used": "Optional STEP reading in a child process: /home/user/Struthio/workbench/assembly_data.py:64-71, started by /home/user/Struthio/workbench/assembly_view.py:107.",
   "issue_with_gpl2_only": "Apache-2.0 in the same process if anyone installs it. Name it in the additional permission, or drop the STEP path. LGPL-2.1 itself is fine with GPL version 2."
  },
  {
   "name": "Pillow and tkinterdnd2 (optional, not installed by any installer)",
   "where": "Not in the tree and not in any requirements file.",
   "licence": "From general knowledge: Pillow is MIT-CMU (HPND); tkinterdnd2 is MIT.",
   "kind": "dependency-not-bundled",
   "how_used": "Pillow: /home/user/Struthio/workbench/surfer_tools.py:72 and /home/user/Struthio/sdk/cli/arc1cli/intake_profiles.py:123. tkinterdnd2: /home/user/Struthio/workbench/app.py:23 (old Tk workbench, guarded by try/except).",
   "issue_with_gpl2_only": "None."
  },
  {
   "name": "LibreOffice (soffice) and a Java runtime",
   "where": "Not in the tree. Debian packages: /home/user/Struthio/INSTALL_DEBIAN.sh:48-49 (libreoffice-calc, libreoffice-writer, default-jdk-headless). The offline kit carries libreoffice-calc.",
   "licence": "LibreOffice: MPL-2.0 with many third-party parts. OpenJDK: GPL-2.0 with the Classpath exception (general knowledge).",
   "kind": "dependency-not-bundled",
   "how_used": "Separate programs. soffice found by name at /home/user/Struthio/workbench/office_runtime.py:7, run with subprocess (office_runtime.py:9; office_math_runtime.py:29 and :37; native_sessions.py:154 and :161) and opened detached at /home/user/Struthio/workbench/sheet_workbench_qt.py:432-434. java found at office_math_runtime.py:10. No Python 'import uno'.",
   "issue_with_gpl2_only": "None: mere aggregation. (The Apache question is only about the UNO JAR that Graphite's own Java file links to, listed above.)"
  },
  {
   "name": "KiCad (kicad-cli)",
   "where": "Not in the tree. /home/user/Struthio/INSTALL_DEBIAN.sh:50 (kicad, with --experiments).",
   "licence": "GPL-3.0-or-later (general knowledge).",
   "kind": "dependency-not-bundled",
   "how_used": "Separate program: found by name at /home/user/Struthio/workbench/cad_export.py:32 and /home/user/Struthio/workbench/kicad_tools.py:38, run by subprocess (cad_export.py:36-39; kicad_tools.py:94). No 'import pcbnew' anywhere.",
   "issue_with_gpl2_only": "None: run as a program, never imported. It must stay that way: importing KiCad's Python module would bring GPL-3 code into a GPL-2.0-only process."
  },
  {
   "name": "ngspice",
   "where": "Not in the tree and not installed by the installer scripts.",
   "licence": "Mostly BSD-3-Clause (general knowledge).",
   "kind": "dependency-not-bundled",
   "how_used": "Separate program: found at /home/user/Struthio/workbench/spice_tools.py:38, run through the subprocess helper (spice_tools.py:58 and :224; /home/user/Struthio/workbench/kicad_tools.py:90-94).",
   "issue_with_gpl2_only": "None: mere aggregation."
  },
  {
   "name": "poppler-utils (pdftotext, pdftoppm)",
   "where": "Not in the tree. /home/user/Struthio/INSTALL_DEBIAN.sh:46 (default prerequisite); in the offline kit.",
   "licence": "GPL-2.0-only OR GPL-3.0-only (general knowledge).",
   "kind": "dependency-not-bundled",
   "how_used": "Separate programs: /home/user/Struthio/sdk/cli/arc1cli/reference_extract.py:21, :36-43; /home/user/Struthio/workbench/reference_service.py:255-261; /home/user/Struthio/workbench/knowledge_service.py:162.",
   "issue_with_gpl2_only": "None: run as programs."
  },
  {
   "name": "Other host programs Graphite runs by name when present",
   "where": "Not in the tree.",
   "licence": "Various, from general knowledge: bubblewrap (LGPL-2.0-or-later), Icarus Verilog (GPL-2.0-or-later), QEMU (GPL-2.0), FFmpeg (LGPL/GPL), Inkscape (GPL), FreeCAD (LGPL), Thunderbird (MPL-2.0), RetroArch (GPL-3.0), Node.js (MIT), 7-Zip (LGPL with an unRAR restriction), OpenSSL command (Apache-2.0), curl, git (GPL-2.0-only), xfel (MIT), dumpcap and tcpdump, Surfer (EUPL-1.2), Xvfb and xauth (MIT), compilers and make, loginctl and systemctl.",
   "kind": "dependency-not-bundled",
   "how_used": "All looked up with shutil.which and run as separate processes, for example /home/user/Struthio/workbench/workshop_sandbox.py:13 (bwrap), federation_rtl.py:10-22 (iverilog, vvp), program_media.py:204 (ffmpeg), program_vector.py:315 (inkscape), program_freecad.py:75, program_mail.py:175 (thunderbird), program_cartridge.py:68 (retroarch), owner_tls.py:29 (openssl), network_watch.py:568 (dumpcap, tcpdump), surfer_tools.py:41, session_power.py:49-50.",
   "issue_with_gpl2_only": "None: mere aggregation, whatever their licences."
  },
  {
   "name": "Offline first-boot kit: 396 Debian packages and 8 wheels",
   "where": "Not in the tree. Listed in /tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad/x/Graphite_00_START_HERE/Graphite_Transfer/App/OFFLINE_FILES.json; read by /home/user/Struthio/PREPARE_DEBIAN.sh:13-30 and /home/user/Struthio/INSTALL_LS.py:212.",
   "licence": "Each package keeps its own. Wheels: PySide6, PySide6_Addons, PySide6_Essentials, shiboken6 (6.8.3), cryptography 50.0.2, cffi 2.1.1, pycparser 3.12, pypdf 7.0.0. Debian packages include the X server, Mesa, fluxbox, LibreOffice Calc, poppler-utils, Python 3.13, OpenSSL, and also firmware-amd-graphics (non-free firmware) and libgs10 (Ghostscript, AGPL).",
   "kind": "dependency-not-bundled",
   "how_used": "Installed on the ThinkPad before Graphite. Graphite does not import Ghostscript or the firmware.",
   "issue_with_gpl2_only": "No conflict with Graphite's licence: separate works on the same medium. Using the kit on the owner's own machine is not distribution. If the kit is ever published, the publisher takes on each package's own duties (source for GPL and LGPL binaries, the firmware's terms). Needs a lawyer before publishing the kit."
  },
  {
   "name": "Model weights (GGUF files)",
   "where": "Not in the tree; none ships (THIRD_PARTY_NOTICES.md:19, runtime.json 'model_downloads': false).",
   "licence": "Whatever the model's publisher states; Graphite records it as declared (/home/user/Struthio/workbench/local_brain.py:135).",
   "kind": "dependency-not-bundled",
   "how_used": "Data read by the separate llama-server process.",
   "issue_with_gpl2_only": "None: data for a separate program. The model's own licence still binds whoever redistributes the file."
  }
 ],
 "problems": [
  "Apache-2.0 code in the same process as Graphite's own code (the FSF reads Apache-2.0 as incompatible with GPL version 2; this is the only real class of conflict found). Case 1, OpenSSL: the cryptography wheel statically links OpenSSL 4.0.3 and the Apache-only Rust 'openssl' crate (its own SBOM files in cryptography-50.0.2.dist-info/sboms/), and Debian's python3-cryptography and Python's ssl/hashlib link the system OpenSSL. Graphite imports them at /home/user/Struthio/pillkit/pill.py:87-89, /home/user/Struthio/pillkit/tls_link.py:20 and :40-42, /home/user/Struthio/workbench/release_updates.py:116-117, /home/user/Struthio/workbench/release_publisher.py:7-8, /home/user/Struthio/workbench/remote_service.py:18. Smallest remedy: the owner, as copyright holder, adds one additional permission naming OpenSSL and the cryptography package (draft in wording_needed). This is the long-standing 'OpenSSL exception' practice. It matters most when Graphite is handed out together with these libraries (the offline kit, a prepared machine). Needs a lawyer's eye on the final words.",
  "Apache-2.0, case 2, the LibreOffice UNO JAR: /home/user/Struthio/runtimes/office-uno/libreoffice-25.2.0.jar is MPL-2.0 (compatible with GPL 2.0 through MPL section 3.3) but LibreOffice code carries Apache-2.0 notices from OpenOffice, and Graphite's own LedgerOffice.java and LedgerSession.java run in the same Java process with it (/home/user/Struthio/workbench/office_math_runtime.py:30-31, /home/user/Struthio/workbench/native_sessions.py:155-156). Smallest remedy: name the UNO classes in the same additional permission. Alternative with no permission needed: state that the two small Java client files are under MPL-2.0 or a permissive licence instead of the GPL, since they are a thin client. I did not read licence headers out of the JAR's class files; the Apache point rests on LibreOffice's published source headers.",
  "Apache-2.0, case 3, third-party code inside Qt PDF and Qt WebEngine: Qt's own pages list Abseil (Apache-2.0) inside Qt PDF and Apache-2.0 components inside the Chromium part of Qt WebEngine. Graphite loads Qt PDF in the main process (/home/user/Struthio/workbench/universal_viewer_qt.py:302-303, /home/user/Struthio/workbench/thumbnails.py:162) and Qt WebEngine in the game player process (/home/user/Struthio/workbench/struthio_play.py:18-19). Smallest remedy: the additional permission names Qt and Qt for Python 'with the third-party code in their standard releases'. Needs a lawyer: whether The Qt Company's GPL-2.0 offer already settles this.",
  "Apache-2.0, case 4, optional libraries: wasmtime 50.0.1 (Apache-2.0 WITH LLVM-exception) at /home/user/Struthio/workbench/experiment_runtime.py:23 and :60, and OCP (Apache-2.0, not in any requirements file) at /home/user/Struthio/workbench/assembly_data.py:64-71. wasmtime's exception text already has a clause for GPL version 2 combinations, so the risk is low. Smallest remedy: name both in the same additional permission; for OCP the alternative is to drop the optional STEP reader."
 ],
 "wording_needed": "Draft note to stand above the unmodified GPL version 2 text in COPYING, the way the kernel's note does. Square brackets mark choices and lawyer checks.\n\nGRAPHITE: LICENCE NOTE\n\nGraphite's own code is copyright (C) 2026 [owner's name]. [LAWYER: confirm who holds copyright in every part, including code written with machine help.]\n\nGraphite's own code is free software under the GNU General Public License, version 2. Only version 2 applies. No later version applies. (SPDX: GPL-2.0-only.)\n\nNOTE 1. Other programs. This licence does not cover programs that Graphite starts and talks to. Starting a program, handing it files, and talking to it over a pipe or a local socket is normal use. It does not make that program a derived work of Graphite. This covers the llama.cpp server (MIT licence, shipped unchanged in runtimes/llama.cpp), LibreOffice, KiCad, ngspice, the poppler tools, Java, and every other program Graphite runs by name. It covers the Python build in runtimes/python-wasi (Python Software Foundation licence), which runs as a guest in a sandbox. Each keeps its own licence.\n\nNOTE 2. Your work. This licence does not cover what you make with Graphite. Your documents, sheets, drawings, staC lines and results are yours. Model files are data. They keep the licence their publisher gave them.\n\nNOTE 3. Libraries. Graphite is written in Python and loads libraries it does not own. They are not part of Graphite's own code. They keep their own terms:\n- Python and its standard library: Python Software Foundation licence.\n- Qt and Qt for Python (PySide6, shiboken6): Graphite uses them under their GNU GPL version 2 option.\n- pypdf, SymPy, mpmath, lxml, pycparser: BSD licences. python-docx, Z3, cffi: MIT licences.\n- cryptography: BSD or Apache 2.0, at your choice. It contains OpenSSL, which is Apache 2.0.\n- wasmtime: Apache 2.0 with the LLVM exception.\n- The LibreOffice UNO Java classes in runtimes/office-uno: Mozilla Public License 2.0, with parts under Apache 2.0.\n\nNOTE 4. Additional permission. Some of these libraries, or parts inside them, are under the Apache License 2.0, which the GPL version 2 does not accept in a combined work. As a special exception, the copyright holder of Graphite gives you permission to combine Graphite's own code with: Python; OpenSSL; the cryptography package; wasmtime; the LibreOffice UNO classes; OCP and Open CASCADE; and Qt and Qt for Python, with the third-party code in their standard releases. You may copy and distribute the combination. You must follow the GNU GPL version 2 for Graphite's own code. You must follow each library's own licence for that library. If you change Graphite, you may keep this permission on your version or remove it. This permission covers only code whose copyright the Graphite copyright holder holds. [LAWYER: review this paragraph. Decide whether to name libraries, as here, or to permit any library under a free software licence, which needs no update when a dependency changes.]\n\nNOTE 5. Not under the GPL. The fonts in branding/fonts and branding/ux17/fonts are under the SIL Open Font License 1.1; the licence file is beside each. The files in runtimes/ are under the licence file in each folder. Artwork, the Stacy character, the game's music, and the names Graphite, staC and Stacy: [OWNER TO CHOOSE: all rights reserved, as RIGHTS.md says today, or a named licence]. [LAWYER: artwork made with image generation; names and likeness; the music file has no recorded origin.]\n\nHousekeeping that goes with the note (not wording): replace RIGHTS.md line 3; correct THIRD_PARTY_NOTICES.md as listed in the summary; add the GPL version 2 text as COPYING; consider one line, 'SPDX-License-Identifier: GPL-2.0-only', at the top of each source file, since the FSF advises stating an exception where the code is.",
 "not_checked": "- I am not a lawyer. Compatibility statements follow the FSF's published reading (its licence list confirms: Apache-2.0 is not compatible with GPL version 2; MPL-2.0 section 3.3 gives compatibility with GPL 2.0; current Python licence is GPL-compatible). The FSF FAQ passages on interpreters with bindings and the LGPLv3 with 'GPLv2 only' table cell could not be retrieved in this session (the page was cut off); those two points are stated from general knowledge.\n- I ran no test suite and not tools/check_release.py, as instructed. Nothing under /home/user/Struthio was changed.\n- The tree was read at HEAD e3a0a23, not 37b78f0; I checked that the two later commits touch only own code and records. I looked at this branch's nine commits only for the paths the notices name; I did not audit history for other removed material.\n- llama.cpp archives: members listed and digests verified against runtime.json; I did not examine which third-party code is compiled into llama-server (the archives carry a single MIT LICENSE).\n- UNO JAR: class files carry no headers; the statement that parts derive from Apache-licensed OpenOffice code rests on LibreOffice's source headers and the LICENSE file beside the JAR, not on the JAR itself.\n- python.wasm and the wasmtime native library: I did not enumerate the libraries or Rust crates compiled into them.\n- Qt: per-module licences for QtCore, QtGui, QtWidgets, QtSvg, QtDBus, QtTest and QtMultimedia are taken from the PySide6 metadata, not from a per-module Qt page; the third-party code inside those modules (FFmpeg in Qt Multimedia, for instance) was not enumerated. The PySide6 wheels contain no licence files. Qt Charts and Qt Data Visualization being GPL-3-only is from general knowledge.\n- OCP, Pillow and tkinterdnd2 are not installed in the checking environment, so their licences are from general knowledge. So are the licences of the host programs (KiCad, ngspice, poppler, LibreOffice, OpenJDK and the rest).\n- Offline kit: I read the list of 396 Debian packages and 8 wheels but did not check each Debian package's licence; I named only the ones that stand out. The kit is not in the tree.\n- Images: I viewed contact sheets of branding/ and workbench/nav_icons and found nothing that is recognisably third-party, but I cannot prove origin. I did not open every screenshot in docs/ and build/, the art in games/struthio/assets/art, the four .docx files, or the master specification PDF (embedded fonts and images not examined).\n- games/struthio/assets/audio/tarmac-at-midnight-loop.mp3: origin unknown; no tags, no record in this tree; the owner's STRUTHIO repository was not consulted.\n- Authorship of Graphite's own code (who wrote what, and with what tools) cannot be established from the tree; it decides who can grant the additional permission."
}