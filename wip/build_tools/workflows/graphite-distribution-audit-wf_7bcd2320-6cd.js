export const meta = {
  name: 'graphite-distribution-audit',
  description: 'Audit Graphite 1.0 against "distribution ready": tests, packaging, Windows/DOS comfort, full-GUI coverage, new-user view, portability, security, licences; then a completeness critic',
  phases: [
    { title: 'Audit', detail: 'eight auditors, each one dimension of distribution readiness' },
    { title: 'Critic', detail: 'what the eight missed, and the order to build in' },
  ],
}

const S = '/tmp/claude-0/-home-user-Struthio/62270cd8-8155-590e-b29e-91307882a142/scratchpad'
const REPO = '/home/user/Struthio'
const PY = S + '/work/venv/bin/python'

const COMMON = `
CONTEXT. Graphite is a local-first PySide6 desktop for Debian 13 with an assistant, Kasandra (Kas). Version 1.0 ("The Living Desktop and the Ghost in the Shell") was released yesterday, built by one agent per slice and NOT tested (the owner's rule then). The repository is ${REPO} (branch claude/epic-galileo-c7k11y). The owner has now asked to make it "fully distribution ready" and said: "this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos. But I know I can only get what I want in Debian so I have to switch." Testing is now allowed. You are ONE AUDITOR of that goal. Your job is to FIND AND RANK GAPS, not to fix them.

READ FIRST (skim, do not paste into your answer): ${REPO}/README.md, ${REPO}/docs/RELEASE_NOTES_1.0.md, ${REPO}/docs/GUIDE_LIVING_DESKTOP.md, ${REPO}/docs/GUIDE_KASANDRA.md, ${REPO}/wip/2026-11-26_road_to_1.0/PLAN_1.0.md sections 1 to 4, ${REPO}/wip/2026-11-26_road_to_1.0/DESIGN_DIRECTION_1.0.md. The walkthrough accounts (what real use found) are ${REPO}/wip/2026-11-26_b100_saved/X3.account.md, X4.account.md and X1.account.md. Each slice's builder notes are ${REPO}/wip/2026-11-26_b100_saved/<KEY>.progress.md and <KEY>.build.result.json.

HARD RULES.
- READ ONLY on the repository: never edit, stage or commit anything under ${REPO}. Write your notes and any scripts only under ${S}/work/dist/<your key>/ (create it).
- Anything you RUN (tests, the app, scripts that import the tree) runs only on a throwaway COPY of the tree: cd ${REPO} && git ls-files -z --cached --others --exclude-standard | grep -z -v -E '^(wip/|\\.claude/)' | xargs -0 cp --parents -t <copy>, and wrapped as: nice -n 19 unshare --pid --fork --mount-proc --kill-child env HOME=$(mktemp -d) QT_QPA_PLATFORM=offscreen ${PY} -B <script>. In a fresh copy, first rebuild the seed (${PY} tools/package_graphite.py --manifest-only ; ${PY} tools/record_registry.py ; ${PY} tools/package_graphite.py --manifest-only) or lines refuse with "seed/source binding is not current". At most two heavy processes of yours at once (4 cores, other auditors beside you). Delete your copy when done; keep the disk under 80 % (df -h /).
- Never print long output into your context: send it to a file and read the tail or grep it. Work in few large steps.
- The owner's personal details are not in the tree and must not be sought. Do not load a model. Do not touch the network except where your task says so.
- Be concrete: every finding names files (path:line where you can), says what a user would experience, and proposes the fix. Rank honestly: 'blocker' = a distribution cannot ship with it; 'major' = a real user is stopped or misled; 'minor' = polish. Say which findings can only be confirmed on real hardware.
- Finish by writing your full notes to ${S}/work/dist/<your key>/NOTES.md (the path goes in notes_path), then return the structured result. Keep each finding's text short (under 60 words per field); the notes file holds the detail. At most 25 findings: the most important first.
`

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    area: { type: 'string' },
    verdict: { type: 'string', description: 'Two or three sentences: how far this area is from distribution ready, and the single biggest gap' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' },
          severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          evidence: { type: 'string', description: 'files and lines, or what was run and what it printed' },
          user_experience: { type: 'string', description: 'what a user meets' },
          fix: { type: 'string' },
          effort: { type: 'string', enum: ['S', 'M', 'L'] },
          needs_real_hardware: { type: 'boolean' },
        },
        required: ['title', 'severity', 'fix', 'effort'],
      },
    },
    feasibility: { type: 'string', description: 'What can and cannot be built or checked in this container for this area, as found by trying' },
    notes_path: { type: 'string' },
  },
  required: ['area', 'verdict', 'findings'],
}

const AUDITS = [
  {
    key: 'tests',
    prompt: `YOUR DIMENSION: THE TEST SUITE'S TRUE STATE (key: tests). Forty-five slices were merged with no test run. Find out what the existing suite says now.
- Read tools/run_tiers.py and tests_integrated/ to learn the tiers. In a copy (rules above), run the fastest tier first, then as much of the next tier as fits in about 40 minutes of wall time, output to files. A fresh profile now opens in the Day look: where tests assumed the Graphite look, note it (GRAPHITE_APPEARANCE=graphite restores the old default) rather than counting every such test separately.
- Report: how many tests ran, passed, failed, errored; the failures CLUSTERED BY CAUSE (one finding per cause, with the count of tests it explains, the first error line, and the slice that most likely caused it, from wip/2026-11-26_b100_saved notes: several slices list 'existing_tests_changed' and tests that 'may need' changes). Separate: (a) tests that are wrong now (they assert the old truth), (b) real faults in the program the tests caught, (c) environment (no display, no D-Bus).
- Also list the 1.0 modules that have NO test at all (compare workbench/*.py added since 0.8.7, commit ddf0aed, against tests_integrated), ranked by risk: authority code first (grants, halt, home_reach, assignments, bulk_files, utility_sandbox, network_governed, a11y_hand, hand_door).
- Say what a "minimal test" set for a distribution would be: the smallest set of new tests that would catch the worst faults (name each test in one line).
Do not fix or edit tests. Keep the raw outputs under your notes folder.`,
  },
  {
    key: 'packaging',
    prompt: `YOUR DIMENSION: PACKAGING, INSTALL AND IMAGE (key: packaging). Today Graphite installs from ZIP parts with INSTALL_LS.py and PREPARE_DEBIAN.sh into ~/Applications/Graphite-1.0, a private venv with bundled wheels, and is started by hand from the text console (START_MINIMAL_DEBIAN.sh, LS_XSESSION.sh). A distribution needs better.
- Read INSTALL_LS.py, PREPARE_DEBIAN.sh, INSTALL_DEBIAN.sh, INSTALL_GRAPHITE.sh (wip/build_tools/kit_1.0/), START_MINIMAL_DEBIAN.sh, LS_XSESSION.sh, docs/MINIMAL_DEBIAN_INSTALL_01.md, tools/package_graphite.py, tools/package_release_parts.py, requirements-*.txt, runtimes/, wip/build_tools/kit_1.0/SYSTEM_SET_1.0.json.
- Design, concretely, what "installs like real Debian software" would be: a .deb (or a small set: graphite, graphite-session, graphite-runtime) with correct Depends from SYSTEM_SET_1.0.json, files under /opt/graphite or /usr/lib/graphite, a launcher in /usr/bin, an /usr/share/xsessions/graphite.desktop entry so a display manager offers "Graphite" at login, a graphical login path (which display manager, or autologin plus startx from the profile), systemd user units where they belong, postinst/prerm, an apt repository layout on the USB stick, upgrade from the ~/Applications install, uninstall that leaves the user's workspace alone. Say what each needs changed in the tree (hardcoded paths, the venv, PySide6 from wheels versus python3-pyside6 in Debian 13: check which versions Debian 13 really has).
- FEASIBILITY, BY TRYING in this container (write what you ran and what it printed): is dpkg-deb here? can a .deb be built and inspected (lintian)? is debootstrap available or installable, and does a Debian 13 chroot work under this container's privileges (unshare, chroot, mount)? can the built .deb be installed inside such a chroot with apt resolving its Depends from deb.debian.org (the network policy allowed deb.debian.org earlier)? is live-build / xorriso / squashfs-tools available, and could a bootable live ISO be assembled? is qemu here (without KVM) for a boot smoke? Do not leave large files behind; a chroot is hundreds of MB: build it under ${S}/work/dist/packaging/ only if the disk allows and remove it after.
- List the install-time faults a stranger would hit today (assumptions about ~/Concern, the owner's ThinkPad, Debian 13 point releases, root steps, no network).`,
  },
  {
    key: 'windows_dos',
    prompt: `YOUR DIMENSION: COMFORT FOR A WINDOWS AND DOS PERSON (key: windows_dos). The owner is "mostly comfortable in windows and dos" and is switching to Debian only because Graphite needs it. Audit the whole window from that person's hands.
- KEYS. Find every shortcut the program binds (grep QShortcut, QKeySequence, keyPressEvent, setShortcut in workbench/) and compare with what a Windows user's hands do without thinking: Ctrl+C/X/V/Z/Y/A/S/F/P, F2 rename, Delete, Shift+Delete, Alt+F4, Alt+Tab (window switching under Fluxbox: who handles it, and does the dock follow?), the Windows key (should open Apps), Win+E (files), Win+D, Win+L (lock), Ctrl+Alt+Del (a task page), PrintScreen (a screenshot), Ctrl+Shift+Esc, F5 refresh, Alt+Enter properties, Backspace/Alt+Left for back, Ctrl+Tab between tabs, Esc to close. 1.0's rule was "no keyboard shortcut printed on screen": a Windows user learns keys from menus. Recommend.
- FILES AS EXPLORER. In the Files tree and board: cut/copy/paste of files with the clipboard, drag and drop, double-click to open, Properties, an address bar you can type a path in, sort by name/date/size/type, a details view with columns, thumbnails, "This PC" with drives and free space, the bin, new file, zip/unzip, search in a folder, hidden files. What exists (workbench/computer_tree_qt.py, home_files_qt.py, bulk_files*.py, files_qt.py), what is missing.
- DOS IN THE TERMINAL. The foot's Terminal runs the account's shell. A DOS person types dir, cd.., cls, copy, xcopy, move, del, ren, md, rd, type, more, attrib, tree, help, ver, date, time, path, set, echo, find, edit, format, chkdsk, ipconfig, ping, tasklist, taskkill, and drive letters (A:, C:). Design a "DOS words" layer: which map cleanly to Debian commands, which need care (del without confirmation, format), how it would be offered (aliases installed for the user's shell, or Graphite's Terminal translating and SHOWING the Debian command it ran, so the owner learns), and where it would live in the code (find the Terminal mode: typebar_qt.py, console_qt.py, terminal modules).
- WORDS AND PLACES. Windows vocabulary versus Graphite's: Start/Apps, taskbar/dock, Control Panel/Settings, Task Manager, Recycle Bin/DELETE, My Documents/Home, shortcuts on a desktop, the system tray (volume, network, battery, clock: is there a clock on screen at all?), notifications, "Add or remove programs", Device Manager, right-click > Properties. For each: present, different-but-fine, or missing.
- You may open the window offscreen on a copy to check a behaviour, but reading the code is usually enough. Rank the gaps by how often this person would hit them in the first week.`,
  },
  {
    key: 'full_gui',
    prompt: `YOUR DIMENSION: A FULL GUI FOR DEBIAN (key: full_gui). The owner wants never to need Debian's console or another desktop. Go through everything a desktop user needs and say, for each, whether Graphite 1.0 has it (present / partial / missing), where (file), and what Debian 13 backend would provide it (package and D-Bus service or command), preferring backends already in the 1.0 System set (wip/build_tools/kit_1.0/SYSTEM_SET_1.0.json: udisks2, upower, NetworkManager, pipewire/wireplumber, polkit, xsecurelock, at-spi).
The list, at least: software (install, remove, update, security updates: apt/PackageKit; "is there an update?"), printers and scanners (CUPS, SANE), Bluetooth (BlueZ), date/time/timezone/NTP (timedatectl), language/locale/keyboard layout, users and passwords, login screen and autologin, lock and screensaver timing, power (lid, sleep timers, power profiles, brightness, battery warnings), display (resolution, scaling/HiDPI, night light, multiple monitors: 1.0 has some), touchpad/mouse/keyboard repeat, sound (output, input/microphone, per-app volume), network (Wi-Fi incl. hidden and enterprise, ethernet, VPN, proxy, hotspot, firewall: ufw/nftables), disks (free space, format, partition, SMART, encrypted volumes: 1.0 says no), removable media autoplay, backups of the user's files (schedule, restore), system information and Device Manager, a task manager (processes, kill, startup apps, services), logs, fonts, default apps and file associations (1.0 has some), clipboard history, screenshots and screen recording, archive handling, the everyday apps and whether Graphite recommends or installs them (browser, email, media player, image viewer and editor, PDF, text editor, calculator, calendar), accessibility (zoom, large text, high contrast, screen reader, on-screen keyboard), system-wide dark/light, wallpaper (is there one? Graphite fills the screen), time and a calendar on screen, crash reports.
- Read workbench/machine_real.py, machine_room_qt.py, settings_qt.py, system_settings_qt.py, apps_*.py, session_power.py, notify_qt.py, and S4's and S5's notes to see what exists. Check on-screen strings, not just modules.
- For the TOP 12 missing things, sketch the smallest honest implementation (the backend call, the page, the grant or polkit prompt it needs) and its effort. Say which the build container can exercise against a stand-in and which need real hardware.`,
  },
  {
    key: 'new_user',
    prompt: `YOUR DIMENSION: WHAT A NEW USER SEES: OLD ROOMS, OLD NAMES, FIRST RUN, DOCS (key: new_user). Graphite grew from "Ledger & Slate" through many releases; 1.0 put a new desktop on top. A stranger installing a distribution should meet ONE coherent program.
- OLD SURFACES. List every room, page, menu entry and mode that predates the 1.0 design and is still reachable (Arrange's older rooms: Changes, Continuing work, Exchange & deployment, the Project Desk, the Field; the Cabinet record tabs; BOSS plates; the game; Agenda; Night Shift; the 0.8.x "desk acts"; the Apps panel's GRAPHITE section lists dozens of rooms: Cartridge Bay, Delivery, Laboratory, Media Bench, Print Proof, HDL simulation checks, KiBot, nextpnr ...). For each: what it is, whether 1.0's surfaces replace it, whether anything still depends on it, and a recommendation: keep / hide behind an "Engineering tools" switch / remove. Find modules nothing imports any more (her_hologram_qt, stacy_presence, hologram_qt and others): list dead code with evidence (grep).
- OLD NAMES a user can SEE: on screen, in file paths and in commands: "Ledger", "Slate", "Stacy", "arc1", "ARC_LEDGER_*" variables, ~/.config/arc1-workbench, ~/.local/state/ledger-slate, ~/Concern, LEDGER.sh, INSTALL_LS.py, START_LEDGER.sh, MANIFEST.json's product name, docs/GRAPHITE_0.1_REGISTRY.json, window titles, desktop entries. Which can be renamed safely (with a migration for existing profiles), which are load-bearing (signed updates).
- FIRST RUN for someone who is not the owner: what happens on the very first start with an empty home (workbench/session.py, launch_look.py, the empty workspace board, "no model yet")? Is there a welcome, a choice of look, an explanation of Home/Files/Kas, a way to get a model (the owner downloads a 22 GB file by hand from Hugging Face and checks a sha256: what would a stranger do?), a tour? Open the window offscreen on a copy with a fresh HOME in the day look and read what it shows; save two frames.
- DOCS a stranger would read: README.md (rewritten for 1.0 at the top; the rest?), GETTING_STARTED.md, docs/*.md: which are current, which still describe 0.x (DAILY_GUIDE.md, STAGE*.md, BOSS_*.md, THINKPAD_*.md are owner-specific). The Guide menu still has a Keyboard Shortcuts entry and many old pages. Propose the doc set of a distribution (user guide, install guide, Kas guide, release notes, licence), and what to move to an archive folder.
- Words on screen that only the owner's history explains (e.g. "Concern", "Slate", "the Field", "does and shows", "staC").`,
  },
  {
    key: 'portability',
    prompt: `YOUR DIMENSION: HARDWARE AND PORTABILITY (key: portability). Graphite was built for one machine: a ThinkPad E16 Gen 2 AMD (Ryzen, Radeon 680M, 16 threads, 1920x1200), Debian 13, X11 under a hidden Fluxbox. A distribution runs on other machines.
- Find every assumption in the code and scripts: the equalizer drawn for 16 threads ("01 to 16": what happens with 4, 8, 32?), screen sizes (frames were taken only at 1920x1200 and 1366x768: what happens at 1280x720, 2560x1440, 3840x2160 with scaling, a 4:3 screen, two monitors of different sizes?), HiDPI (QT scale factors, fixed pixel sizes in workbench/design_tokens.py and painted widgets), Vulkan/Radeon assumptions in the model runtime (workbench/brain_runtime.py, runtime_tuning.py, machine_overview.py, hatch_readiness.py: Intel and NVIDIA graphics, no GPU at all, 8 GB of RAM), x86_64 only (the bundled llama.cpp archives; arm64?), X11 only (windows_x11.py, XTest, Fluxbox: what under Wayland? say what a distribution should declare), Debian 13 only (PREPARE_DEBIAN.sh refuses others: Debian 12, Ubuntu 24.04, testing?), English only (is any text translatable? keyboard layouts other than US? right-to-left?), one user per machine (several accounts, shared /opt install, permissions of the workspace), time zones and locales with comma decimals (the maths is exact: are numbers parsed locale-safely?), a home on a network or encrypted filesystem, a read-only or nearly full disk, no battery (desktop PC), no Wi-Fi card, touch screens.
- TRY what this container allows: open the window offscreen on a copy at 1280x720, 2560x1440 and 3840x2160 (QT_SCALE_FACTOR=1 and 2), in the day look, on Rail Demo (Guide's Try Rail Demo, or tools that build it: see X1's notes), save one frame each under your notes folder and READ them: clipping, overlaps, unusable narrow panes. Simulate 4 and 64 CPU threads if the equalizer reads os.cpu_count() (monkeypatch in your own script). Run with LANG=de_DE.UTF-8 and LC_NUMERIC=de_DE.UTF-8 and feed a line with a decimal number.
- Say what a distribution should state as REQUIREMENTS (minimum RAM without a model and with one, disk, screen, graphics) from what the code really needs, and which assumptions are cheap to remove.`,
  },
  {
    key: 'security',
    prompt: `YOUR DIMENSION: SECURITY AND PRIVACY (key: security). A distribution puts an agent with hands on strangers' computers. Review, as a skeptical security reviewer, the code that enforces the owner's authority, written in one day by separate agents and never reviewed:
- workbench/grants.py and grants_qt.py (grants per operation/target/scope, enforced at dispatch: find any operation of hers that reaches a change without passing permit/covering; home_plan.give_set; the built-in standing grant F3 widened), workbench/halt.py (does HALT really stop every managed thing: assignments, the hand, model turns, sandboxes, fetches? races?), workbench/home_reach.py and files_service.may_change (path traversal, symlinks out of Home, hard links, ~ and .. tricks, case and unicode look-alikes, /proc/self/root), workbench/bulk_files.py (the line that moves or deletes: can a crafted file NAME inject a step? TOCTOU between preview and press), workbench/utility_sandbox.py (netns, Landlock, seccomp: what happens on a kernel without Landlock? does it fail CLOSED? resource limits; what the Apply step trusts), workbench/network_governed.py and the quarantine doorway (prompt-injection: can fetched text reach her model as instructions? search words built only from typed words? SSRF to localhost and private ranges? redirects? file:// URLs?), workbench/home_pages.py (her reading documents: the same doorway?), workbench/a11y_hand.py and hand_door.py (the never-press list Send/Pay/Delete/Install: matched how? localized button names? can a window title spoof "a window she opened"?), workbench/brain_seal.py (the model server's flags, loopback binding, the socket, her key), workbench/assignments.py (journal integrity, resume not repeating), workbench/objective_plan.py (the model picks by number: can its output smuggle arguments?), workbench/apps_*.py and app launching (desktop-entry Exec parsing: field codes, shell injection), the notification server (markup, actions, spoofing Graphite's own toasts), session scripts and installers that run as root (PREPARE_DEBIAN.sh, INSTALL_*.sh: quoting, temp files, downloaded content, checksum checks).
- For each real weakness: a concrete scenario (inputs or state -> what goes wrong), the file and line, and the fix. Mark what you verified by running code on a copy (small proof-of-concept scripts under your notes folder, never against real files outside your throwaway area) and what you only read. Do not report style or theory without a scenario.
- Privacy: what leaves the computer ever (the web fetch, search words, anything else: telemetry, update checks, fonts)? what personal data lands in logs, the model-check 'for-sending' files, crash output?
- End with the five things a distribution must fix before strangers run it, in order.`,
  },
  {
    key: 'licence',
    prompt: `YOUR DIMENSION: LICENCES AND REDISTRIBUTION (key: licence). Can this tree be handed to other people legally and cleanly?
- Read COPYING, RIGHTS.md, THIRD_PARTY_NOTICES.md, branding/**/LICENSE*, NOTICE*, runtimes/**/LICENSE, requirements-*.txt, wip/build_tools/kit_1.0/OFFLINE_FILES.json (the wheels and debs the kit carries), tools/package_graphite.py (what goes into the package).
- Graphite's own code is "GPL version 2 only". Check compatibility of everything linked or bundled: PySide6/Qt (LGPLv3/GPLv3: is "GPLv2 only" code importing LGPLv3 Qt a problem to state plainly? what do the notices say?), pypdf, cryptography, the bundled llama.cpp binaries (MIT; their own third-party parts), the python-wasi runtime, office-uno bridge, fonts (Inter OFL, IBM Plex OFL, Special Elite, Parisienne: are the licence texts and copyright lines present for each bundled font file?), any icon sets, sounds, images. List every bundled third-party file group with its licence and whether its notice is present; list anything with NO clear licence.
- RIGHTS.md "says what is kept back (Stacy's artwork, the names and the game copy)". What exactly in the tree is NOT free to redistribute (branding/kasandra/art, hologram.webp, plates, the game, names/trademarks)? 1.0 no longer shows any picture of Kas: could those files leave the tree so the whole package is redistributable? What would a distribution's package have to exclude today, and does tools/package_graphite.py exclude it?
- The models are not shipped (Qwen files downloaded by the user): what licence do the named model files carry, and what must the docs say? Debian packages on the USB stick (redistribution of unmodified .debs: source-offer obligations for GPL packages carried on a stick).
- Debian-policy view: what would block this from being a proper .deb in a third-party repository (bundled binaries without source, vendored wheels, embedded code copies, missing debian/copyright)? What is the smallest honest path: a third-party .deb with a complete debian/copyright file.
- Source headers: do the Python files carry licence headers or SPDX identifiers? Is there a single authors/copyright holder line that does not name the owner personally (the owner's name must stay out of the tree: say how copyright can be stated without it, e.g. "the Graphite authors").
Return findings ranked by legal risk, each with the fix.`,
  },
]

phase('Audit')
const audits = (await parallel(AUDITS.map(a => () =>
  agent(COMMON + '\n' + a.prompt, { label: 'audit:' + a.key, phase: 'Audit', schema: FINDINGS_SCHEMA })
    .then(r => (r ? { key: a.key, ...r } : null))
))).filter(Boolean)

log(audits.length + ' of ' + AUDITS.length + ' audits returned; ' + audits.reduce((n, a) => n + a.findings.length, 0) + ' findings')
const missing = AUDITS.map(a => a.key).filter(k => !audits.some(a => a.key === k))
if (missing.length) log('NOT RETURNED (to rerun): ' + missing.join(', '))

phase('Critic')
const digest = audits.map(a => '## ' + a.key + '\nVERDICT: ' + a.verdict + '\nFEASIBILITY: ' + (a.feasibility || '-') + '\n' +
  a.findings.map((f, i) => (i + 1) + '. [' + f.severity + '/' + f.effort + (f.needs_real_hardware ? '/hw' : '') + '] ' + f.title + ' -> ' + f.fix).join('\n')).join('\n\n')

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    missed: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          title: { type: 'string' }, severity: { type: 'string', enum: ['blocker', 'major', 'minor'] },
          why: { type: 'string' }, fix: { type: 'string' }, effort: { type: 'string', enum: ['S', 'M', 'L'] },
        },
        required: ['title', 'severity', 'fix', 'effort'],
      },
    },
    contradictions: { type: 'array', items: { type: 'string' }, description: 'findings that contradict each other or look wrong, with the check that would settle each' },
    build_order: { type: 'array', items: { type: 'string' }, description: 'the slices to build, in order, each one line: a name, what it contains (finding titles), what it must not collide with' },
    cannot_be_done_here: { type: 'array', items: { type: 'string' } },
    definition_of_ready: { type: 'array', items: { type: 'string' }, description: 'a checkable definition of "distribution candidate" in at most 15 points' },
  },
  required: ['missed', 'build_order', 'definition_of_ready'],
}

const critic = await agent(`You are the COMPLETENESS CRITIC of an audit of Graphite 1.0 (a PySide6 desktop for Debian 13 with an agent, Kasandra) against the goal "fully distribution ready", for an owner who says: "this is meant to be MY full gui for Debian. I'm mostly comfortable in windows and dos." Eight auditors each took one dimension; their verdicts and findings are below (the detail is in ${S}/work/dist/<key>/NOTES.md; the repository is ${REPO}, read only; you may read both to check a claim, and you must not edit the repository).

Your job: (1) WHAT IS MISSING: a dimension nobody took (think: updates and how a new version arrives; data safety, backup and migration between versions; crash handling and logs a stranger can send; performance on weak machines; accessibility; internationalisation; support and documentation; reproducible builds and release signing; the model download experience; uninstall; multi-user), or an obvious gap inside a dimension. (2) CONTRADICTIONS or findings that look wrong: spot-check up to six of the highest-severity claims against the code and say which hold. (3) A BUILD ORDER: group the work into slices that separate agents can build in parallel without editing the same files (name the shared files to watch: workbench/shell2.py, her_column_qt.py, qt_app.py, engineering_kernel.py, menus2.py, PREPARE_DEBIAN.sh), most valuable and most unblocking first; testing and security fixes come before new features; say what must wait for real hardware. Aim for 12 to 20 slices. (4) What cannot be done in a cloud container at all. (5) A checkable definition of "distribution candidate".

THE AUDITS:

${digest}`, { label: 'critic', phase: 'Critic', schema: CRITIC_SCHEMA })

return { audits, missing, critic }
