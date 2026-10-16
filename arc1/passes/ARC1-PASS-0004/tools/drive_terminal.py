# Evidence tool for ARC1-PASS-0004: drives `arc1 ui` in a pseudo-terminal and checks the
# screen with the pyte terminal emulator (pip install pyte==0.8.2; set PYTE_PATH if it is not on
# sys.path). Usage: python3 drive_terminal.py <image file>. Not part of the SDK.
import fcntl, os, pty, select, struct, subprocess, sys, termios, time
sys.path.insert(0, os.environ.get("PYTE_PATH", ""))
import pyte
ARC1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "arc1")
ROWS, COLS = 30, 100
m, s = pty.openpty()
fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
env = dict(os.environ, TERM="xterm-256color", LANG="C.UTF-8", LC_ALL="C.UTF-8")
p = subprocess.Popen([sys.executable, ARC1, "ui"], stdin=s, stdout=s, stderr=s, env=env, close_fds=True,
                     cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."), start_new_session=True)
os.close(s)
screen = pyte.Screen(COLS, ROWS); stream = pyte.ByteStream(screen)
def pump(t=1.5):
    end = time.time() + t
    while time.time() < end:
        r, _, _ = select.select([m], [], [], 0.05)
        if r:
            try: stream.feed(os.read(m, 65536))
            except OSError: return
def text(): return "\n".join(screen.display)
checks = []
def step(key, needle, t=2.0):
    os.write(m, key); pump(t); checks.append((repr(key)[:20], needle, needle in text()))
pump(2)
checks.append(("start", "Main Menu", "Main Menu" in text()))
step(b"1", "Verdict  PASS", 4)
step(b"2", "Hardware facts: R10-development")
step(b"\x1b[6~", "OPEN QUESTIONS")
step(b"3", "Build examples/hello_arc1", 4)
step(b"5", "4 run, 0 failed", 6)
step(b"6", "Frame 60", 3)
step(b"]", "Frame 70", 3)
step(b"x", "Main Menu")
step(b"9", "Flasher: 64 MiB system NOR")
step(b"\x1bOB", "►F1MB")
step(b"i", "Image file:")
step(sys.argv[1].encode() + b"\n", "Image: fw.bin")
step(b"\r", "Plan NOT_AVAILABLE", 3)
step(b"\x1b[6~", "WRITE DISABLED")
step(b"\x1b", "Main Menu")
step(b"7", "ARC1-PASS-0001", 6)
step(b"8", "NOT_AVAILABLE", 3)
step(b"\x1bOP", "Help")
pass
os.write(m, b"q"); pump(1)
try: rc = p.wait(timeout=10)
except subprocess.TimeoutExpired: p.kill(); rc = "TIMEOUT"
for k, n, ok in checks: print("%-6s %-22s %s" % ("ok" if ok else "MISS", k, n))
print("exit:", rc)
