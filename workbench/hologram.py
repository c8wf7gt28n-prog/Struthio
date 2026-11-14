"""Kasandra's hologram in the left column: where she stands, and how her picture moves. Pure: no Qt, so it is tested alone.

The owner, 14 November 2026: "We're going to move the kasandra picture to lower left column where it's boring looking."
and "I will attach the new kas picture that I want to be like a hologram in its new position. If you can animate the static
a hologram would have that would be very kool."

Where she stands (place): in the empty part of the left pane, under the tree's last row and above DELETE. Two stances:
on the stage, large and centred above the foot, when the space under the rows is tall; in the corner, beside DELETE and
standing on its floor, when it is short. She never covers a row or DELETE: when the tree scrolls, or the room is less than
HMIN, she is not shown at all.

How she moves (frame_plan): the static, the scan lines and a slow flicker are her picture's own life; a tear now and then
in her quiet states; her base breathes with the tree (pane_qt.BREATH). Each state of the work has its own word, colour and
pace (STATE_LOOK, MOTION). With Reduce motion, or the Clean glow, every frame is the same still frame: no flicker, no
drift, no tear; a change of state only changes the colour.
"""
import math

ASPECT = 608 / 822          # the picture's crop (kasandra_art.CROP): her width over her height
GAP = 16                    # between the tree's last row and the top of her stage, at 14 pt
SIDE = 8                    # her stage's margin each side of her
NEAR = 12                   # between her and DELETE, in the corner stance
HMIN = 120                  # shorter than this she is not shown
HMAX = 380                  # taller than this she is not drawn
ROOM = 16                   # the room for her base below her
FPS = 12                    # her frames a second (83 ms)
FRAME_MS = round(1000 / FPS)
BREATH = 2.8                # the tree's breath (pane_qt.breath): she breathes with it
TEAR_GAP = 4.0              # two tears are never closer than this (seconds)
TEAR_FRAMES = 2             # a tear lasts two frames
POWER = 0.36                # the power-up when she first appears (seconds)

# state -> (word, the palette's name for its colour)
STATE_LOOK = {
    'idle': ('quiet', 'VIOLET'),
    'working': ('at work', 'READY'),
    'awaiting_approval': ('waits for you', 'OWNER'),
    'completed': ('done', 'HONEY'),
    'blocked': ('stopped', 'RED'),
}
HOLD = {'completed': 20.0, 'blocked': 45.0}       # kasandra_art.HOLD

# opacity: her figure; static: the noise's opacity; drift: the scan lines, px a second downward; flicker: on or off;
# tears: the mean gap between tears (None: never); period, depth: her base's breath (None: steady)
MOTION = {
    'idle': dict(opacity=0.80, static=0.30, drift=6.0, flicker=True, tears=11.0, period=BREATH, depth=0.15),
    'working': dict(opacity=0.84, static=0.39, drift=14.0, flicker=True, tears=8.0, period=BREATH / 2, depth=0.20),
    'awaiting_approval': dict(opacity=0.86, static=0.19, drift=4.0, flicker=False, tears=None, period=BREATH, depth=0.25),
    'completed': dict(opacity=0.82, static=0.28, drift=6.0, flicker=True, tears=None, period=BREATH, depth=0.10),
    'blocked': dict(opacity=0.62, static=0.28, drift=3.0, flicker=False, tears=None, period=None, depth=0.0, grey=0.5),
}
FLICKER = (0.03, 0.02)      # the two parts of the flicker: never more than 5% either way
WRITE_PERIOD = 2.4          # working: a write band rises through her every 2.4 s
SWEEP = 0.6                 # completed: one lock sweep, top to bottom, in 0.6 s


def look(state):
    """(word, colour name) for a state of the work; 'viewing' and anything unknown are her quiet state."""
    return STATE_LOOK.get(state, STATE_LOOK['idle'])


def motion(state):
    return MOTION.get(state, MOTION['idle'])


def rows_bottom(visible_rows, row_h, content_top, viewport_h):
    """Where the tree's rows end, in pane coordinates, or None when they do not fit its viewport (the tree scrolls: she
    stands aside). Worked out from the count, so she can move before the tree lays itself out."""
    used = int(visible_rows) * int(row_h)
    if used > int(viewport_h):return None
    return int(content_top) + used


def place(rows_end, foot_top, delete, P, I, s=1.0):
    """(stance, figure, stage) in the left pane's coordinates, or None. rows_end: where the tree's rows end (None when it
    scrolls); foot_top: the foot's top; delete: DELETE's box (x, y, w, h); P: the pane's width; I: its inset; s: the scale.
    figure is her picture's box, stage the box she paints (her and her base): it never meets a row or DELETE, and never
    passes the pane's bottom."""
    if rows_end is None:return None
    gap, side, near, hmin, hmax, room = (round(v * float(s)) for v in (GAP, SIDE, NEAR, HMIN, HMAX, ROOM))
    dx, dy, dw, dh = (int(v) for v in delete)
    top = int(rows_end) + gap

    def fit(left, right, base):
        width = right - left
        if width <= 0:return 0, left, width, base
        h = min(hmax, base - top, int(width / ASPECT));h -= h % 4
        return h, left, width, base

    stage = fit(I + side, P - I - side, dy - room)          # above the foot, the pane's width
    corner = fit(I + side, dx - near, dy + dh)              # beside DELETE, on its floor
    stance, (h, left, width, base) = ('stage', stage) if stage[0] >= corner[0] else ('corner', corner)
    if h < hmin:return None
    w = round(h * ASPECT);x = left + (width - w) // 2;y = base - h
    return stance, (x, y, w, h), (x - side, y, w + 2 * side, h + room)


def mix(a, b, share):
    """Two '#rrggbb' colours mixed: share 0 is a, 1 is b. Returns (r, g, b)."""
    share = max(0.0, min(1.0, float(share)))
    pa = [int(a[i:i + 2], 16) for i in (1, 3, 5)];pb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return tuple(round(x + (y - x) * share) for x, y in zip(pa, pb))


def base_colour(state, palette, since_state=0.0):
    """Her base's colour now: the state's colour; done fades from honey back to violet over its hold."""
    name = look(state)[1]
    if state == 'completed':
        return mix(palette['HONEY'], palette['VIOLET'], float(since_state) / HOLD['completed'])
    return mix(palette[name], palette[name], 0)


def flicker(state, t):
    if not motion(state)['flicker']:return 1.0
    a, b = FLICKER
    return 1.0 + a * math.sin(2 * math.pi * 0.7 * t) + b * math.sin(2 * math.pi * 1.9 * t + 1.3) * math.sin(2 * math.pi * 0.23 * t)


def breath(state, t):
    m = motion(state)
    if not m['period']:return 1.0
    return 1.0 + m['depth'] * math.sin(2 * math.pi * t / m['period'])


def frame_number(t):
    return int(math.floor(float(t) * FPS))


def noise_offset(n):
    """Where the static's tile starts in frame n: a fixed shuffle of the frame's number, so a frame is drawn the same twice."""
    n = int(n) & 0xFFFFFFFF
    v = (n * 2654435761 + 40503) & 0xFFFFFFFF
    return (v >> 8) % 64, (v >> 20) % 64


def _tear(rng, glitch_rows, touch=False):
    """A tear: a band of her picture moved sideways for two frames. y as a share of her height (a glitch line already in
    the picture 60% of the time, else anywhere in her top 80%), h and dx in pixels at 14 pt."""
    if touch:
        y = rng.uniform(0.1, 0.7);return dict(y=y, h=5, dx=rng.choice((-1, 1)) * 4, touch=True)
    if glitch_rows and rng.random() < 0.6:y = rng.choice(list(glitch_rows))
    else:y = rng.uniform(0.0, 0.8)
    return dict(y=y, h=rng.randint(2, 5), dx=rng.choice((-1, 1)) * rng.randint(3, 7), touch=False)


def frame_plan(state, t, rng, still, since_state, since_show, memo=None, glitch_rows=()):
    """What one frame of her shows at time t (seconds, time.monotonic()): a dict of
        opacity, flicker, noise_index, noise_offset, static, scan_offset, tear (or None), base_rgb, base_alpha,
        sweep_y (a share of her height, or None), write_y (the same), power (0..1, or None), grey (0..1).
    since_state: seconds since the state began; since_show: seconds since a power-up began (None: no power-up).
    memo: a dict kept between frames for the tears (None: no tears); rng: random.Random, for the tears only."""
    m = motion(state);t = float(t);since_state = max(0.0, float(since_state or 0.0))
    from . import boss_theme
    palette = boss_theme.PALETTES['kasandra']
    plan = dict(opacity=m['opacity'], flicker=1.0, noise_index=0, noise_offset=(0, 0), static=m['static'], scan_offset=0,
                tear=None, base_rgb=base_colour(state, palette, since_state), base_alpha=1.0, sweep_y=None, write_y=None,
                power=None, grey=m.get('grey', 0.0), drift=m['drift'])
    if still:return plan
    n = frame_number(t)
    plan.update(flicker=flicker(state, t), noise_index=n % 6, noise_offset=noise_offset(n), scan_offset=int(m['drift'] * t) % 3,
                base_alpha=breath(state, t))
    if state == 'working':plan['write_y'] = 1.0 - (t % WRITE_PERIOD) / WRITE_PERIOD
    if state == 'completed' and since_state < SWEEP:plan['sweep_y'] = since_state / SWEEP
    if since_show is not None and 0.0 <= float(since_show) < POWER:plan['power'] = float(since_show) / POWER
    if memo is not None:plan['tear'] = tears(memo, state, t, rng, since_state, glitch_rows)
    return plan


def tears(memo, state, t, rng, since_state, glitch_rows=()):
    """The tear showing at time t, or None. In the quiet states a tear comes at random (a Poisson clock with a floor: never
    two within TEAR_GAP seconds, on average one every MOTION[state]['tears']); blocked tears once, as it starts; a state
    that waits for the owner or has just finished never tears. A touch (memo['touch']) tears once, at once."""
    lasting = TEAR_FRAMES / FPS
    current = memo.get('tear')
    if current is not None and t < current['until'] and memo.get('state') == state:return current['tear']
    memo['tear'] = None
    if memo.get('state') != state:      # a new state: its own clock
        memo['state'] = state;memo['next'] = None;memo['once'] = False
    touch = memo.pop('touch', None)
    if touch is not None and state not in ('awaiting_approval', 'blocked'):
        tear = _tear(rng, glitch_rows, touch=True);memo['tear'] = dict(tear=tear, until=t + lasting);return tear
    if state == 'blocked':
        if not memo.get('once') and since_state < 0.2:
            memo['once'] = True;tear = _tear(rng, glitch_rows);memo['tear'] = dict(tear=tear, until=t + lasting);memo['last'] = t
            return tear
        return None
    mean = motion(state)['tears']
    if mean is None:return None
    if memo.get('next') is None:memo['next'] = t + TEAR_GAP + rng.expovariate(1.0 / (mean - TEAR_GAP))
    if t < memo['next']:return None
    memo['next'] = t + TEAR_GAP + rng.expovariate(1.0 / (mean - TEAR_GAP));memo['last'] = t
    tear = _tear(rng, glitch_rows);memo['tear'] = dict(tear=tear, until=t + lasting)
    return tear


def tear_starts(state, seconds, rng, fps=FPS, start=0.0):
    """The times tears begin over `seconds` of frames at fps, for a state that began at `start` (for the tests and the
    frames' notes)."""
    memo = {};found = [];showing = False
    for i in range(int(seconds * fps)):
        t = start + i / fps
        tear = tears(memo, state, t, rng, t - start)
        if tear is not None and not showing:found.append(t)
        showing = tear is not None
    return found
