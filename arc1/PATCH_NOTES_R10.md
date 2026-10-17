# R10.5 — ARC-1 colours everywhere; Clip uses Google Gemini (free key)

- **ARC-1 colours** (owner decision): the whole UI now uses the logo's
  palette, replacing R10's light ivory.
  - Black surfaces, brushed-steel text and chrome, and ARC-1 orange
    (`#ff5a1a`) accents.
  - Covered: the Qt window (`workbench/qt_theme.py`), the editor gutter and
    highlights, the Resources charts, the Clip bubbles, and the classic Tk
    window (`workbench/app.py`).
  - The layout is unchanged.
- **Clip answers with Google Gemini only**, using a free key from any Google
  account. Local AI, OpenAI and copy & paste were removed.
- **Key setup inside the bubbles:** a **Get a free key** button opens
  aistudio.google.com/apikey; you paste the key into Clip.
  - **Checked straight away:** Clip lists the key's models and gets one real
    answer. Failures are explained in plain words: invalid key, blocked key,
    region, free limit, or no connection.
  - **Never on screen:** the key is not shown in any bubble and is stored
    encrypted for your Windows account.
- **No hard-coded model:** Clip uses `gemini-flash-latest` or the newest
  stable Flash model from the key's own list.
  - It falls back to the next Flash or Flash-Lite model when a model is
    refused or its free limit is used up.
  - It retries once when Google is busy.
- **Checked against Google's documentation (October 2026):**
  - the `x-goog-api-key` header, `generateContent` and `systemInstruction`;
  - "thought" parts are skipped, and blocked answers are explained.
- **Checked against the live endpoint:** a request with an invalid key
  reaches Google, and Google's real `API_KEY_INVALID` answer becomes Clip's
  plain message. No call with a valid key was made: none is available
  here. The owner's first paste is that test, and Clip reports the result.
- **Tests:** `tests/test_r10_clip.py` has 11 tests.
  - A fake Google that answers in the documented formats, including the
    real invalid-key body: model choice, fallback on a free-limit error, a
    retry when Google is busy, plain-word errors, and a full key check.
  - A real Qt test of first use: get-key button → paste → check → answer
    the question asked before the key.
- **Screenshots:** `tests/capture_r10_screens.py` regenerates all R10
  screenshots in the new colours.
- **Changed test:** `tests/test_r08_qt_contract.py` now checks the ARC-1
  palette instead of the R10 ivory. The owner changed the look; the rest of
  the test is unchanged.

# R10.4 — Clip floats over Workbench and needs no key

- **Chat bubbles instead of a window:** `ClipOverlay` in
  `workbench/qt_app.py` replaces R10.3's `ClipChat`.
  - The bubbles float over the Workbench window under the paperclip and
    fade in as they arrive.
  - Only the bubbles catch the mouse: a mask covers them and the message
    field, so the editor around them stays clickable.
  - Esc or another click on Clip hides them; a new reply pops them back up.
- **Free local AI is the default:** Ollama with `qwen2.5-coder:7b`. It needs
  no account or key and nothing leaves the PC.
  - First use: Clip offers to install Ollama (winget), starts it, and
    downloads the model with progress shown in a bubble. It then answers the
    message you already sent.
- **Google Gemini option:** works with a free API key.
- **Still available:** OpenAI API and ChatGPT copy & paste.
- **Settings:** schema `arc1.clip-settings/2`. R10.3 settings are ignored,
  so Clip starts with Local AI.
- **Tests:** `tests/test_r10_clip.py` has 9 tests.
  - Settings, keys, all three cloud/local request formats, and setup
    detection.
  - Model download progress.
  - A real Qt test of the bubbles: on the window, masked, setup → answer,
    toggling.
  - Not run: on Windows, or against a real Ollama, Gemini or OpenAI.

# R10.3 — Clip chats with ChatGPT

- **Clip opens a chat window** in the style of Messages: your messages
  are blue bubbles on the right, replies are grey on the left. Click the
  paperclip at the right end of the toolbar.
  - Code: `ClipChat` in `workbench/qt_app.py`; the Qt-free logic is in
    `workbench/clip.py`.
- **Two ways to reach ChatGPT** (Clip › Settings):
  - **Copy & paste** (the default; no key needed): Clip copies your message
    and opens chatgpt.com. Paste it there with Ctrl+V. When ChatGPT
    answers, press its Copy button and the reply appears in Clip.
  - **OpenAI API:** Clip sends the conversation with your API key and shows
    the answer itself. API use is billed to the key, separately from a
    ChatGPT subscription.
    - **Key storage:** the key is stored encrypted for your Windows account
      (DPAPI), or read from `OPENAI_API_KEY`.
- **Include open file:** tick it to send the file in front of you with
  your message. It is off by default; nothing else leaves the PC.
- **Clip only passes messages along.** It changes no files and runs
  nothing.
- **Why Clip doesn't type into the browser window:** that breaks whenever
  the site changes, can't work while the window is minimized, and
  automated reading of ChatGPT's output is against OpenAI's terms.
- **Tests:** `tests/test_r10_clip.py` covers settings, message building and
  the API call against a fake server. The chat window was exercised
  offscreen, but not on Windows or against the live API.

# R10.2 — Windows installer second pass, and Clip

- **Clip:** a paperclip helper in the empty right-hand end of the toolbar
  (`ClipAssistant` in `workbench/qt_app.py`). It will become the go-between
  for you and the AI coder. For now it isn't connected to any agent and
  says so when clicked.
- **Windows installer fixes** (from a review; not yet run on Windows):
  - **Microsoft Store Python is refused.** It redirects files written in
    AppData to a private folder, so the shortcuts would point at nothing.
    `INSTALL_ARC1.cmd` skips it when looking for Python.
  - **Python 3.11–3.13 is preferred,** since PySide6 6.8.1 has no wheels for
    3.14. When Qt can't install, the message gives the actual reason:
    Python too new, paths too long, or no connection.
  - **Workbench left open:** upgrade and uninstall stop with "close
    Workbench" and change nothing, instead of crashing halfway through.
  - **Uninstaller:** `Uninstall ARC-1 Workbench.cmd` deletes itself while it
    runs. It now runs its last steps from one line, so it no longer ends
    with "batch file cannot be found".
  - **Backups follow OneDrive:** they go to the real Documents folder,
    even when OneDrive has moved it.
  - **Taskbar:** Workbench gets its own taskbar button and icon instead of
    Python's. The Tk fallback also asks Windows for sharp text on scaled
    displays.
  - **SmartScreen:** the installer explains the "Windows protected your PC"
    prompt, which appears because the file isn't signed.
  - Unexpected file errors now print a plain message, not a traceback.
- **Not tested:** tests were not run for this change, and no pass record was
  written.

# R10.1 — Installer and resource budgets

- **One-double-click installer:** `INSTALL_ARC1.cmd` replaces R09's
  drag-to-My-Apps installer (`workbench/installer.py`, removed). It finds or
  installs Python, then copies Workbench into place and installs Qt
  privately. It finds or installs a C compiler, creates shortcuts with a new
  ARC-1 icon and an Installed apps entry, runs `arc1 doctor`, and offers to
  start Workbench.
  - **Your work is safe:** upgrades and uninstalls back up any file you
    changed or added.
  - **Code:** `workbench/setup_arc1.py` (standard library only) and
    `workbench/launch.py`. The launcher opens the Qt window, falls back to
    Tk, and reports start-up errors.
  - **Line endings:** batch files are now stored with CRLF line endings
    (`.gitattributes`).
- **Resource budgets in the Hardware Inspector** (View › Resource Budgets),
  from the owner's frame-budget sketch:
  - Charts: frame time against 16.67 ms, link bandwidth against the 60 fps
    need, and memory pools.
  - Every figure quotes its R10 source. Missing quotes drop the number;
    unknowns are hatched "not measured".
  - Code: `workbench/resources.py`, `hardware/budgets/r10_resources.json`.
  - Agents get the same data with `inspect.resources`.
- **Not run on Windows:** the installer's Windows layer was checked with
  stand-ins. On Linux, a real install, launch and uninstall cycle passed:
  Qt downloaded, `ARC1_LAUNCH_OK qt`, uninstall removed everything.

# R10 — Familiar main screen (Qt "Classic")

Owner decision: Workbench should behave like File Manager and Word, with the
console-engineering tools appearing when the task needs them. See
[docs/WORKBENCH_R10.md](docs/WORKBENCH_R10.md).

## Changed

- **New main window** (`workbench/qt_app.py`, rewritten):
  - Layout: native Windows title bar, menu bar, one compact toolbar (Open,
    Save, Build ▾, Run, Tests, Target), a ~236 px logical project navigator,
    document tabs and a status bar.
  - Hidden until needed: Output/Problems (F10), the Hardware Inspector and the
    Cartridge Shelf.
  - Start page, Browse tab (File Manager listing, optional dual pane) and
    Preview tab for simulator frames.
- **Light Classic theme** (`workbench/qt_theme.py`): ivory and grey surfaces,
  restrained orange accents, subtle toolbar and button depth. It replaces
  R08/R09's dark graphite.
- **Editor:** line numbers, current-line band and problem-line marker. Undo,
  Redo, Cut, Copy, Paste, Find, Find Next, Replace (a single undo step) and
  Go to Line.
- **Build, Tests and Run follow the work in front of you:**
  - A file in a game project builds and tests that game.
  - Otherwise the selected Target is used.
  - Run (F5) builds the game and then runs the host simulator.
- **Compiler errors are navigable:**
  - The Problems list has severity, description, file and line.
  - Double-click or press F8 / Shift+F8 to jump to the line.
  - Game builds read the compiler log the CLI writes; firmware builds read
    the CLI failure text.
- **Session memory** (`workbench/session.py`): project, documents, cursor
  positions, active tab, target, recent files, output panel, panel sizes and
  window layout. **View › Reset Window Layout** restores the factory layout.
- **File operations** (`workbench/fileops.py`): New File, New Folder, Rename,
  Duplicate and Delete.
  - Windows naming rules, case-insensitive clash checks and no overwrites.
  - Recorded evidence is read-only.
- **Shared engine** (`workbench/engine.py`): the Qt window and the agent
  interface (`workbench/agent.py`) now use one command table, so the agent
  no longer keeps its own copy.

## Fixed (found by the R10 acceptance test)

- **Firmware errors were cut off.** `arc1 firmware build` and `arc1 firmware
  test` kept only the last 1,200–1,500 characters of compiler output, so the
  first error, usually the one you caused, was lost. The build then pointed
  at a knock-on error in another file.
- They now keep the beginning of the log, and the end too when it is long
  (`sdk/cli/arc1cli/firmware.py`, `compiler_excerpt`).

## Kept

The R09 backend, launcher, cartridge system, firmware tests, boot-diagnostic
model, agent protocol and the Tk desktop (`START_ARC1.cmd`) are unchanged.
The R09 Tk smoke test passes under Xvfb.

## Verified (see R10_VERIFICATION.json)

- **Qt acceptance workflow:** run with the offscreen platform, PySide6 6.8.1
  on Linux (`tests/test_r10_workbench.py`, 20 tests):
  - find a file, open it, edit it, save it
  - build the relevant target and read the compiler error
  - go back to the source line, fix it, rebuild clean, run the simulator
  - reopen to check what was remembered, and reset the layout
- **Earlier tests:** the SDK suite and the R08/R09 regression tests pass.

## Not done

- **Windows 11:** native run, installation, display scaling, and keyboard and
  accessibility qualification (R14).
- **Editing:** split editing, project-wide search and crash recovery (R11).
- **Workspaces:** per-activity saved workspaces (R12).
- **Agent Activity:** live streaming of agent requests.
- **Hardware:** everything that needs a board.
