"""`arc1 ui`: a DOS-style text console for the SDK — debug menu, frame viewer and flasher.

Everything is drawn into an 80x25 cell buffer (character, foreground, background
from the 16-colour DOS palette); a curses backend copies the buffer to the
terminal, and `--snapshot ITEM` prints it as plain text instead. Menu items run
the same code paths as the command line (`main.execute`), so the UI can never
show a result the CLI would not give. Flashing is plan-only (see device.py).
"""

import locale
import os
import sys
from pathlib import Path

from . import device
from .core import SDK_ROOT, SDK_VERSION, UsageError, display_path
from .jsonschema_lite import SchemaError

W, H = 80, 25
(BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, BROWN, LIGHTGRAY,
 DARKGRAY, LIGHTBLUE, LIGHTGREEN, LIGHTCYAN, LIGHTRED, LIGHTMAGENTA, YELLOW, WHITE) = range(16)

# Classic CGA/EGA text-mode palette, used for frame viewing and screenshots.
DOS_RGB = [(0, 0, 0), (0, 0, 170), (0, 170, 0), (0, 170, 170), (170, 0, 0), (170, 0, 170), (170, 85, 0),
           (170, 170, 170), (85, 85, 85), (85, 85, 255), (85, 255, 85), (85, 255, 255), (255, 85, 85),
           (255, 85, 255), (255, 255, 85), (255, 255, 255)]

ASCII_FALLBACK = str.maketrans({"═": "=", "║": "|", "╔": "+", "╗": "+", "╚": "+", "╝": "+", "─": "-", "│": "|",
                                "┌": "+", "┐": "+", "└": "+", "┘": "+", "▀": "#", "░": ":", "▒": ":", "▓": "#",
                                "█": "#", "▄": "_", "↑": "^", "↓": "v", "►": ">", "·": ".",
                                "✗": "x", "…": "~"})

PIXEL = "\x01"  # a frame-viewer cell: upper half = fg colour, lower half = bg colour (drawn as ▀)

VERDICT_COLOUR = {"PASS": LIGHTGREEN, "FAIL": LIGHTRED, "ERROR": LIGHTRED, "NOT_AVAILABLE": YELLOW, "NOT_RUN": YELLOW}

MENU = [
    ("1", "System check", "doctor"),
    ("2", "Hardware facts", "hardware"),
    ("3", "Build project", "build"),
    ("4", "Run simulator", "sim"),
    ("5", "Test project", "test"),
    ("6", "Frame viewer", "frames"),
    ("7", "Pass records", "passes"),
    ("8", "Detect console", "detect"),
    ("9", "Flasher", "flasher"),
    ("0", "About", "about"),
]


# --------------------------------------------------------------------- cell buffer

class Screen:
    def __init__(self, w=W, h=H, bg=BLUE):
        self.w, self.h = w, h
        self.cells = [[[" ", LIGHTGRAY, bg] for _ in range(w)] for _ in range(h)]

    def put(self, x, y, text, fg=WHITE, bg=None):
        if not 0 <= y < self.h:
            return
        for i, ch in enumerate(text):
            if 0 <= x + i < self.w:
                cell = self.cells[y][x + i]
                cell[0], cell[1] = ch, fg
                if bg is not None:
                    cell[2] = bg

    def fill(self, x, y, w, h, bg, ch=" ", fg=LIGHTGRAY):
        for yy in range(y, y + h):
            self.put(x, yy, ch * w, fg, bg)

    def shadow(self, x, y, w, h):
        for yy in range(y + 1, y + h + 1):
            for xx in (x + w, x + w + 1):
                if 0 <= yy < self.h and 0 <= xx < self.w:
                    self.cells[yy][xx][1:] = [DARKGRAY, BLACK]
        for xx in range(x + 2, x + w + 2):
            if 0 <= y + h < self.h and 0 <= xx < self.w:
                self.cells[y + h][xx][1:] = [DARKGRAY, BLACK]

    def box(self, x, y, w, h, title="", fg=WHITE, bg=BLUE, shadow=True):
        self.fill(x, y, w, h, bg)
        self.put(x, y, "╔" + "═" * (w - 2) + "╗", fg, bg)
        for yy in range(y + 1, y + h - 1):
            self.put(x, yy, "║", fg, bg)
            self.put(x + w - 1, yy, "║", fg, bg)
        self.put(x, y + h - 1, "╚" + "═" * (w - 2) + "╝", fg, bg)
        if title:
            t = " %s " % title[:w - 6]
            self.put(x + (w - len(t)) // 2, y, t, BLACK, LIGHTGRAY)
        if shadow:
            self.shadow(x, y, w, h)

    def to_text(self, ascii_only=False):
        rows = []
        for row in self.cells:
            line = []
            for ch, fg, bg in row:
                if ch == PIXEL:  # no colour in plain text: shade the pixel pair by brightness
                    ch = _shade(fg, bg)
                line.append(ch)
            text = "".join(line)
            if ascii_only:
                text = "".join(ch if ord(ch) < 127 else "?" for ch in text.translate(ASCII_FALLBACK))
            rows.append(text)
        return "\n".join(rows) + "\n"


def _shade(fg, bg):
    lum = sum(sum(DOS_RGB[c]) for c in (fg, bg)) / (2 * 765.0)
    ramp = " .:-=+*#%@"
    return ramp[min(len(ramp) - 1, int(lum * len(ramp)))]


# --------------------------------------------------------------------- panels

class Panel:
    """Scrollable content: lines of (text, fg, bg) segments."""

    def __init__(self, title):
        self.title = title
        self.lines = []

    def add(self, text="", fg=LIGHTGRAY, bg=None):
        self.lines.append([(text, fg, bg)])
        return self

    def segs(self, *segments):
        self.lines.append([(t, f, b) for t, f, b in segments])
        return self

    def wrap(self, text, width, fg=LIGHTGRAY, indent="  "):
        words, line = text.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > width:
                self.add(line, fg)
                line = indent + w
            else:
                line = (line + " " + w) if line else w
        if line:
            self.add(line, fg)
        return self


def run_cli(argv):
    """Runs an arc1 command through the shared execute path."""
    from .main import build_parser, execute
    args = build_parser().parse_args(argv)
    try:
        data, _ = execute(args)
        return data, None
    except (UsageError, SchemaError) as e:
        return None, str(e)


def result_panel(title, data, err, width, extra=None):
    p = Panel(title)
    if err:
        p.add("ERROR", LIGHTRED)
        p.wrap(err, width, LIGHTRED)
        return p
    p.segs(("Verdict  ", LIGHTGRAY, None), (data["verdict"], VERDICT_COLOUR.get(data["verdict"], WHITE), None))
    p.segs(("Evidence ", LIGHTGRAY, None), (data["evidence_level"], LIGHTCYAN, None))
    if "test_count" in data:
        p.segs(("Tests    ", LIGHTGRAY, None), ("%d run, %d failed" % (data["test_count"], data["failed_count"]),
                                                WHITE, None))
    for f in data["failure_reasons"]:
        p.wrap("%s %s" % (f["code"], f["message"]), width, LIGHTRED)
    for w in data["warnings"]:
        p.wrap("! " + w, width, YELLOW)
    if extra:
        p.add()
        extra(p)
    if data["artifacts"]:
        p.add()
        p.add("Artifacts", WHITE)
        for a in data["artifacts"][:20]:
            p.add("  %s %s" % (a["sha256"][:8], a["path"][-(width - 12):]), LIGHTGRAY)
    return p


class App:
    def __init__(self, project="examples/hello_arc1"):
        self.project = project
        self.selected = 0
        self.scroll = 0
        self.frame = 60
        self.flash_sel = 2  # F1MA: the first partition the updater may write
        self.flash_image = ""
        self.panel = self.about()
        self.mode = "menu"  # menu | flasher | viewer
        self.pixels = None
        self.last = "-"

    @property
    def content_w(self):
        return 47

    # ---- actions -------------------------------------------------------
    def act(self, key):
        handler = getattr(self, "do_" + key)
        self.scroll = 0
        self.panel = handler()

    def do_doctor(self):
        data, err = run_cli(["doctor"])
        self._remember(data)

        def extra(p):
            for c in data["details"]["checks"]:
                colour = LIGHTGREEN if c["status"] in ("ok", "found") else YELLOW
                p.segs(("  %-22s " % c["check"][:22], LIGHTGRAY, None), (c["status"], colour, None))
        return result_panel("System check", data, err, self.content_w, extra if data else None)

    def do_hardware(self):
        data, err = run_cli(["hw", "inspect"])
        self._remember(data)
        if err or data["verdict"] != "PASS":
            return result_panel("Hardware facts", data, err, self.content_w)
        f = data["details"]["facts"]
        p = Panel("Hardware facts: %s" % f["revision"])
        p.segs(("Fabrication ", LIGHTGRAY, None), (f["fabrication_status"], YELLOW, None),
               ("   evidence ", LIGHTGRAY, None), ("DESIGN", LIGHTCYAN, None))
        p.add()
        p.add("CHIPS", WHITE)
        pools = {m["owner"]: m for m in f["memory_pools"]}
        for c in f["chips"]:
            m = pools.get(c["id"])
            p.segs(("  %-7s" % c["id"], YELLOW, None), ("%-19s" % c["part"][:19], WHITE, None),
                   ("%4d MiB" % (m["capacity_bytes"] // 1048576) if m else "", LIGHTCYAN, None))
        p.add("  %d MiB total, no unified address space" % (f["memory_total_bytes"] // 1048576), LIGHTGRAY)
        p.add()
        p.add("PERIPHERALS", WHITE)
        for per in f["peripherals"]:
            p.segs(("  %-15s" % per["id"][:15], YELLOW, None), (per["part"][:30], LIGHTGRAY, None))
        p.add()
        p.add("LINKS (all unverified)", WHITE)
        for l in f["links"]:
            p.segs(("  %-18s" % l["id"][:18], YELLOW, None), (" ".join(l["endpoints"])[:28], LIGHTGRAY, None))
        p.add()
        p.add("OPEN QUESTIONS", WHITE)
        for u in f["uncertainties"]:
            p.wrap("- " + u, self.content_w, LIGHTGRAY)
        return p

    def do_build(self):
        data, err = run_cli(["build", self.project])
        self._remember(data)
        return result_panel("Build " + self.project, data, err, self.content_w)

    def do_sim(self):
        data, err = run_cli(["sim", self.project, "--frames", "120", "--dump", "0,60,119"])
        self._remember(data)

        def extra(p):
            d = data["details"]
            p.add("Frames %d, last frame hash %s" % (d["frames"], d["last_frame_fnv1a64"]), WHITE)
            p.add("Open the frame viewer (6) to look at them.", LIGHTGRAY)
        return result_panel("Simulator " + self.project, data, err, self.content_w,
                            extra if data and data["verdict"] == "PASS" else None)

    def do_test(self):
        data, err = run_cli(["test", self.project])
        self._remember(data)

        def extra(p):
            for t in data["details"]["tests"]:
                p.segs(("  %-4s " % t["verdict"], VERDICT_COLOUR[t["verdict"]], None),
                       ("%-12s %s" % (t["kind"], t["id"]), LIGHTGRAY, None))
        return result_panel("Tests " + self.project, data, err, self.content_w,
                            extra if data and "tests" in data.get("details", {}) else None)

    def do_frames(self):
        data, err = run_cli(["sim", self.project, "--frames", str(self.frame + 1), "--dump", str(self.frame)])
        self._remember(data)
        if err or data["verdict"] != "PASS":
            return result_panel("Frame viewer", data, err, self.content_w)
        ppm = [a["path"] for a in data["artifacts"] if a["path"].endswith(".ppm")]
        path = Path(ppm[0]) if Path(ppm[0]).is_absolute() else SDK_ROOT / ppm[0]
        self.pixels = read_ppm(path)
        self.mode = "viewer"
        p = Panel("Frame %d" % self.frame)
        p.add("Frame %d of %s (HOST_SIM)." % (self.frame, self.project), WHITE)
        p.add("[ and ] step 10 frames, any other key returns.", LIGHTGRAY)
        return p

    def do_passes(self):
        p = Panel("Pass records")
        for rec in sorted((SDK_ROOT / "passes").glob("ARC1-PASS-*/pass.json")):
            data, err = run_cli(["pass", "validate", str(rec)])
            v = "ERROR" if err else data["verdict"]
            state = "?" if err else (data.get("details") or {}).get("state", "?")
            p.segs(("  %-15s" % rec.parent.name, YELLOW, None), ("%-6s" % v, VERDICT_COLOUR.get(v, WHITE), None),
                   (state, LIGHTGRAY, None))
            if data:
                for f in data["failure_reasons"][:3]:
                    p.wrap("    %s %s" % (f["code"], f["message"]), self.content_w, LIGHTRED)
        p.add()
        p.wrap("REVIEW means waiting for an independent reviewer; the owner of a pass cannot accept it.",
               self.content_w, LIGHTGRAY)
        return p

    def do_detect(self):
        data, err = run_cli(["device", "detect"])
        self._remember(data)

        def extra(p):
            p.add("How to connect (R10, bench-unproven):", WHITE)
            for line in ("1. Rear USB-C to the PC. A blank or corrupt NOR",
                         "   makes the F133 boot ROM fall through to FEL.",
                         "2. Forced FEL needs the internal fixture pads.",
                         "3. Install xfel on the PC, then detect again."):
                p.add(line, LIGHTGRAY)
        return result_panel("Detect console (USB-C / FEL)", data, err, self.content_w, extra)

    def do_flasher(self):
        self.mode = "flasher"
        return self.flasher_panel()

    def do_about(self):
        return self.about()

    def about(self):
        p = Panel("About")
        # "ARC-1" in a 3-row block font; the dash is red like the logo's orange bar.
        art = [("▄▀▀▄ █▀▀▄ ▄▀▀▀", "    ", " ▄█"),
               ("█▀▀█ █▀▀▄ █   ", " ▀▀ ", "  █"),
               ("▀  ▀ ▀  ▀  ▀▀▀", "    ", " ▀▀▀")]
        for letters, dash, one in art:
            p.segs(("  " + letters, WHITE, None), (dash, LIGHTRED, None), (one, WHITE, None))
        p.segs(("  ", None, None), ("──", LIGHTRED, None), (" Adaptive RISC-V Console ", LIGHTGRAY, None),
               ("──", LIGHTRED, None))
        p.add()
        p.add("SDK %s  debug console" % SDK_VERSION, WHITE)
        p.add()
        p.wrap("Host tools only. The R10 board is on fabrication HOLD: nothing here has run on ARC-1 hardware. "
               "Flashing is plan-only until FEL recovery is bench-proven, a board is identified and the owner "
               "approves.", self.content_w)
        p.add()
        p.add("Pick an item with 0-9 or the arrows + Enter.", YELLOW)
        return p

    # ---- flasher --------------------------------------------------------
    def flasher_panel(self, plan_result=None):
        p = Panel("Flasher: 64 MiB system NOR")
        p.add("ID   OFFSET     SIZE   PROTECTION", WHITE)
        for i, part in enumerate(device.partitions()):
            sel = i == self.flash_sel
            lock = "locked" if device.locked(part) else "updater"
            bg = CYAN if sel else None
            fg = BLACK if sel else (DARKGRAY if device.locked(part) else LIGHTGRAY)
            p.add("%s%-4s 0x%08X %3d MiB %-8s %s" % ("►" if sel else " ", part["id"], part["offset"],
                                                     part["size"] // 1048576, lock, part["name"][:12]), fg, bg)
        p.add()
        p.segs(("Image: ", LIGHTGRAY, None),
               (Path(self.flash_image).name[:38] if self.flash_image else "(none: press I)", WHITE, None))
        p.add("↑↓ partition  I image  Enter plan  Esc back", YELLOW)
        if plan_result is not None:
            data, err = plan_result
            p.add()
            if err:
                p.wrap("ERROR " + err, self.content_w, LIGHTRED)
                return p
            plan = data["details"]["plan"]
            p.segs(("Plan ", WHITE, None), (data["verdict"], VERDICT_COLOUR.get(data["verdict"], WHITE), None))
            p.wrap(plan["operation"], self.content_w, LIGHTGRAY)
            p.add("Fits: %s (%s%% of slot)" % ("yes" if plan["fits"] else "NO", plan["fill_percent"]),
                  LIGHTGREEN if plan["fits"] else LIGHTRED)
            p.add("sha256 %s" % plan["image"]["sha256"][:40], LIGHTGRAY)
            for f in data["failure_reasons"]:
                if f["code"] != "SEC-004" or "write disabled" not in f["message"]:
                    p.wrap("%s %s" % (f["code"], f["message"]), self.content_w, LIGHTRED)
            p.add()
            p.add(" " * 12 + "█▀▀ WRITE DISABLED ▀▀█", LIGHTRED)
            for g in plan["gates"]:
                p.wrap("✗ %s: %s" % (g["gate"], g["reason"]), self.content_w, YELLOW)
            p.wrap("Rollback: " + plan["rollback"], self.content_w, YELLOW)
            p.add()
            p.add("Commands the write would use (not run):", WHITE)
            for c in plan["commands"]:
                p.add("  " + c.split("#")[0].rstrip()[:self.content_w - 2], LIGHTCYAN)
        return p

    def flasher_plan(self):
        part = device.partitions()[self.flash_sel]
        if not self.flash_image:
            return None, "choose an image first (press I)"
        return run_cli(["device", "flash", "--partition", part["id"], "--image", self.flash_image])

    def _remember(self, data):
        if data:
            self.last = "%s %s" % (data["verdict"], data["evidence_level"])

    # ---- drawing ----------------------------------------------------------
    def draw(self):
        s = Screen()
        s.fill(0, 0, W, 1, CYAN)
        s.put(1, 0, "ARC-1 ", BLACK, CYAN)
        s.put(7, 0, "Adaptive RISC-V Console", BLUE, CYAN)
        s.put(31, 0, "│ SDK Debug Console %s" % SDK_VERSION, BLACK, CYAN)
        s.put(W - 12, 0, " R10: HOLD ", WHITE, RED)
        s.fill(0, 1, W, H - 2, BLUE, "░", LIGHTBLUE)

        s.box(1, 2, 25, len(MENU) + 4, "Main Menu")
        for i, (key, label, _) in enumerate(MENU):
            y = 4 + i
            sel = i == self.selected and self.mode == "menu"
            bg = CYAN if sel else BLUE
            s.put(2, y, " " * 23, WHITE, bg)
            s.put(3, y, key, YELLOW if not sel else RED, bg)
            s.put(5, y, label, BLACK if sel else WHITE, bg)

        y0 = len(MENU) + 7
        s.box(1, y0, 25, H - y0 - 2, "Session")
        s.put(3, y0 + 1, "Project ", LIGHTCYAN)
        shown = display_path(self.project)
        s.put(3, y0 + 2, shown if len(shown) <= 21 else "…" + shown[-20:], WHITE)
        s.put(3, y0 + 3, "Last ", LIGHTCYAN)
        s.put(8, y0 + 3, self.last[:16], WHITE)
        s.put(3, y0 + 4, "Board ", LIGHTCYAN)
        s.put(9, y0 + 4, "none (HOLD)", YELLOW)

        if self.mode == "viewer" and self.pixels:
            self.draw_viewer(s)
        else:
            bx, by, bw, bh = 28, 2, 50, H - 4
            s.box(bx, by, bw, bh, self.panel.title, WHITE, BLUE)
            rows = bh - 2
            lines = self.panel.lines
            self.scroll = max(0, min(self.scroll, max(0, len(lines) - rows)))
            for i, line in enumerate(lines[self.scroll:self.scroll + rows]):
                x = bx + 2
                for text, fg, bg in line:
                    text = text[:bx + bw - 2 - x]
                    s.put(x, by + 1 + i, text, fg if fg is not None else LIGHTGRAY, bg if bg is not None else BLUE)
                    x += len(text)
            if len(lines) > rows:
                s.put(bx + bw - 1, by + 1, "↑", YELLOW)
                s.put(bx + bw - 1, by + bh - 2, "↓", YELLOW)

        s.fill(0, H - 1, W, 1, LIGHTGRAY)
        keys = [("F1", "Help"), ("↑↓", "Move"), ("Enter", "Run"), ("PgUp/Dn", "Scroll"), ("P", "Project"),
                ("Q", "Quit")]
        x = 1
        for k, label in keys:
            s.put(x, H - 1, k, RED, LIGHTGRAY)
            s.put(x + len(k) + 1, H - 1, label, BLACK, LIGHTGRAY)
            x += len(k) + len(label) + 3
        return s

    def draw_viewer(self, s):
        w, h, rgb = self.pixels
        bx, by, bw, bh = 1, 1, W - 2, H - 2
        s.box(bx, by, bw, bh, "Frame %d · %s · HOST_SIM · [ ] step · any key: back"
              % (self.frame, Path(self.project).name[:20]), WHITE, BLACK, shadow=False)
        cols, rows = bw - 2, bh - 2
        for cy in range(rows):
            for cx in range(cols):
                top = _sample(rgb, w, h, cx, cy * 2, cols, rows * 2)
                bot = _sample(rgb, w, h, cx, cy * 2 + 1, cols, rows * 2)
                s.cells[by + 1 + cy][bx + 1 + cx] = [PIXEL, nearest_dos(top), nearest_dos(bot)]


def read_ppm(path):
    data = Path(path).read_bytes()
    parts, pos = [], 0
    while len(parts) < 4:
        while data[pos:pos + 1].isspace():
            pos += 1
        start = pos
        while not data[pos:pos + 1].isspace():
            pos += 1
        parts.append(data[start:pos])
    if parts[0] != b"P6" or parts[3] != b"255":
        raise ValueError("not an 8-bit P6 PPM")
    w, h = int(parts[1]), int(parts[2])
    return w, h, data[pos + 1:pos + 1 + w * h * 3]


def _sample(rgb, w, h, cx, py, cols, prows):
    x = min(w - 1, int((cx + 0.5) * w / cols))
    y = min(h - 1, int((py + 0.5) * h / prows))
    i = (y * w + x) * 3
    return rgb[i], rgb[i + 1], rgb[i + 2]


_nearest_cache = {}


def nearest_dos(c):
    if c not in _nearest_cache:
        _nearest_cache[c] = min(range(16), key=lambda k: sum((a - b) ** 2 for a, b in zip(c, DOS_RGB[k])))
    return _nearest_cache[c]


# --------------------------------------------------------------------- snapshot (tests, docs)

def snapshot(project, item):
    """Renders the screen after running one menu item. ITEM is a menu key or
    name, `flasher:<partition>:<image>` for a plan, or `menu`."""
    app = App(project)
    names = {k: n for k, _, n in MENU}
    names.update({n: n for _, _, n in MENU})
    if item.startswith("flasher:"):
        _, pid, image = item.split(":", 2)
        ids = [p["id"] for p in device.partitions()]
        if pid not in ids:
            raise UsageError("unknown partition %r" % pid)
        app.mode = "flasher"
        app.flash_sel = ids.index(pid)
        app.flash_image = image
        app.selected = 8
        app.panel = app.flasher_panel(app.flasher_plan())
    elif item != "menu":
        if item not in names:
            raise UsageError("unknown item %r; use one of %s, flasher:<id>:<image> or menu"
                             % (item, ", ".join(n for _, _, n in MENU)))
        app.selected = [n for _, _, n in MENU].index(names[item])
        app.act(names[item])
    return app.draw()


# --------------------------------------------------------------------- curses backend

class CursesUI:
    def __init__(self, stdscr, app):
        import curses
        self.c = curses
        self.scr = stdscr
        self.app = app
        self.pairs = {}
        self.colours = 16 if curses.COLORS >= 16 else 8
        # Ask the C library, not Python: Python's UTF-8 mode reports UTF-8 even in
        # the C locale, where ncurses can only draw ASCII.
        try:
            codeset = locale.nl_langinfo(locale.CODESET)
        except (AttributeError, ValueError):
            codeset = locale.getpreferredencoding(False) or ""
        self.unicode = codeset.lower().replace("-", "") == "utf8"
        self.cursor(0)
        stdscr.keypad(True)
        if curses.has_colors():
            curses.start_color()
        # DOS colour index -> curses colour (curses order: black red green yellow blue magenta cyan white).
        self.cmap = [curses.COLOR_BLACK, curses.COLOR_BLUE, curses.COLOR_GREEN, curses.COLOR_CYAN, curses.COLOR_RED,
                     curses.COLOR_MAGENTA, curses.COLOR_YELLOW, curses.COLOR_WHITE]

    def cursor(self, visible):
        try:  # some terminals (e.g. vt100) cannot hide the cursor
            self.c.curs_set(visible)
        except self.c.error:
            pass

    def attr(self, fg, bg):
        c = self.c
        if not c.has_colors():
            return c.A_REVERSE if bg in (CYAN, LIGHTGRAY) else c.A_NORMAL
        bold = 0
        if self.colours >= 16:
            cf = self.cmap[fg % 8] + (8 if fg >= 8 else 0)
            cb = self.cmap[bg % 8] + (8 if bg >= 8 else 0)
        else:
            cf, cb = self.cmap[fg % 8], self.cmap[bg % 8]
            bold = c.A_BOLD if fg >= 8 else 0
        key = (cf, cb)
        if key not in self.pairs:
            n = len(self.pairs) + 1
            if n >= c.COLOR_PAIRS:
                return bold
            c.init_pair(n, cf, cb)
            self.pairs[key] = n
        return c.color_pair(self.pairs[key]) | bold

    def blit(self, screen):
        rows, cols = self.scr.getmaxyx()
        self.scr.erase()
        if rows < H or cols < W:
            self.scr.addstr(0, 0, "ARC-1 debug console needs an 80x25 terminal (now %dx%d). Q quits."[:cols - 1]
                            % (cols, rows))
            self.scr.refresh()
            return
        ox, oy = (cols - W) // 2, (rows - H) // 2
        for y, row in enumerate(screen.cells):
            for x, (ch, fg, bg) in enumerate(row):
                if ch == PIXEL:
                    ch = "▀"
                if not self.unicode:
                    ch = ch.translate(ASCII_FALLBACK)
                    if ord(ch) > 126:  # anything else non-ASCII (e.g. from report text)
                        ch = "?"
                if y == H - 1 and x == W - 1 and oy + y == rows - 1 and ox + x == cols - 1:
                    continue  # writing the bottom-right cell would scroll the terminal
                try:
                    self.scr.addstr(oy + y, ox + x, ch, self.attr(fg, bg))
                except self.c.error:
                    pass
        self.scr.refresh()

    def prompt(self, label, initial=""):
        """One-line editor on the status bar. Scrolls horizontally, so long paths
        fit; Enter accepts, Esc cancels (keeps `initial`), Backspace deletes."""
        c = self.c
        rows, cols = self.scr.getmaxyx()
        y, x = (rows - H) // 2 + H - 1, (cols - W) // 2
        field_x = x + len(label) + 2
        field_w = W - len(label) - 4
        text = initial
        self.cursor(1)
        try:
            while True:
                shown = text[-(field_w - 1):]
                self.scr.addstr(y, x, (" " + label + " ").ljust(W - 1)[:W - 1], self.attr(BLACK, LIGHTGRAY))
                self.scr.addstr(y, field_x, shown.ljust(field_w - 1), self.attr(WHITE, BLUE))
                self.scr.move(y, field_x + len(shown))
                self.scr.refresh()
                k = self.scr.get_wch()
                if k in ("\n", "\r", c.KEY_ENTER):
                    return text.strip() or initial
                if k == "\x1b":
                    return initial
                if k in (c.KEY_BACKSPACE, "\x7f", "\b"):
                    text = text[:-1]
                elif isinstance(k, str) and k.isprintable() and len(text) < 1024:
                    text += k
        finally:
            self.cursor(0)

    def loop(self):
        c, app = self.c, self.app
        while True:
            self.blit(app.draw())
            k = self.scr.getch()
            if app.mode == "viewer":
                if k in (ord("["), ord("]")):
                    app.frame = max(0, app.frame + (-10 if k == ord("[") else 10))
                    app.panel = app.do_frames()
                else:
                    app.mode = "menu"
                continue
            if app.mode == "flasher":
                n = len(device.partitions())
                if k == c.KEY_UP:
                    app.flash_sel = (app.flash_sel - 1) % n
                    app.panel = app.flasher_panel()
                elif k == c.KEY_DOWN:
                    app.flash_sel = (app.flash_sel + 1) % n
                    app.panel = app.flasher_panel()
                elif k in (ord("i"), ord("I")):
                    app.flash_image = os.path.expanduser(self.prompt("Image file:", app.flash_image))
                    app.panel = app.flasher_panel()
                elif k in (10, 13, c.KEY_ENTER):
                    app.panel = app.flasher_panel(app.flasher_plan())
                elif k in (c.KEY_PPAGE, c.KEY_NPAGE):
                    app.scroll += -10 if k == c.KEY_PPAGE else 10
                elif k in (27, ord("q"), ord("Q")):
                    app.mode = "menu"
                continue
            if k in (ord("q"), ord("Q"), c.KEY_F10):  # not Esc: a stray escape sequence must not quit
                return 0
            if k == c.KEY_UP:
                app.selected = (app.selected - 1) % len(MENU)
            elif k == c.KEY_DOWN:
                app.selected = (app.selected + 1) % len(MENU)
            elif k in (c.KEY_PPAGE, c.KEY_NPAGE):
                app.scroll += -10 if k == c.KEY_PPAGE else 10
            elif k in (ord("p"), ord("P")):
                app.project = self.prompt("Project directory:", app.project)
            elif k == c.KEY_F1:
                app.panel = help_panel(app.content_w)
            elif k in (10, 13, c.KEY_ENTER) or (0 <= k < 256 and chr(k) in "0123456789"):
                if k not in (10, 13, c.KEY_ENTER):
                    app.selected = [m[0] for m in MENU].index(chr(k))
                self.busy(MENU[app.selected][1])
                app.act(MENU[app.selected][2])

    def busy(self, label):
        s = self.app.draw()
        s.box(24, 10, 32, 5, "Working", BLACK, LIGHTGRAY)
        s.put(27, 12, ("Running: " + label)[:27], BLACK, LIGHTGRAY)
        self.blit(s)


def help_panel(width):
    p = Panel("Help")
    for k, text in (("0-9", "run a menu item"), ("↑↓ Enter", "move and run"), ("PgUp PgDn", "scroll this window"),
                    ("P", "change the project directory"), ("F1", "this help"), ("Q F10", "quit (Esc backs out of a sub-screen)")):
        p.segs(("  %-11s" % k, YELLOW, None), (text, LIGHTGRAY, None))
    p.add()
    p.wrap("Every item runs the same code as the arc1 command line and shows its verdict and evidence level. "
           "Flasher: ↑↓ picks a NOR partition, I sets the image, Enter builds the write plan. Writing is disabled.",
           width)
    return p


def main(project, snapshot_item=None):
    # The default project is relative to the SDK root; others to the current directory.
    if not Path(project).exists() and (SDK_ROOT / project).exists():
        project = display_path(SDK_ROOT / project)
        if not Path(project).is_absolute():
            project = str(SDK_ROOT / project)
    if snapshot_item:
        sys.stdout.write(snapshot(project, snapshot_item).to_text(
            ascii_only=(sys.stdout.encoding or "").lower().replace("-", "") != "utf8"))
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        sys.stderr.write("arc1 ui needs an interactive terminal; use --snapshot ITEM for text output\n")
        return 2
    try:
        import curses
    except ImportError:
        sys.stderr.write("arc1 ui needs Python's curses module (on Windows: pip install windows-curses, or use WSL)\n")
        return 3
    locale.setlocale(locale.LC_ALL, "")
    os.environ.setdefault("ESCDELAY", "25")
    return curses.wrapper(lambda scr: CursesUI(scr, App(project)).loop())
