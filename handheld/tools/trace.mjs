// STRUTHIO HANDHELD · the golden trace format and its input replay, shared by
// the Node exporter (golden_export.mjs) and the browser reference harness
// (reference/reference.mjs). No Node or DOM dependencies.
//
// Trace format (little-endian), version 1:
//   "STRGOLD1"  u32 headerLen  header JSON (utf-8)
//   per tick:   u8 nOps, nOps x {u8 msOffset, u8 op}, u8 acceptFlap (bit1 in raw
//               traces: the dart has no side), u8 frame,
//               8 bytes of the tick digest (first 16 hex digits)
//   op: 1 LEFT_DOWN 2 LEFT_UP 3 RIGHT_DOWN 4 RIGHT_UP 5 DART_LEFT 6 DART_RIGHT
//       7 CLEANUP (the session's input.cleanup() after a death / game over)
//   frame: bit0 left, bit1 right, bit2 flapEdge, bit3 chordEdge, bit4 dartEdge,
//          bit5 dartSide RIGHT, bits6-7 flapKind (1 LEFT, 2 RIGHT, 3 STRAIGHT)
import { SHIMMER_TICKS } from '../../arcade/src/sim/state.mjs';

export const OP = { LEFT_DOWN: 1, LEFT_UP: 2, RIGHT_DOWN: 3, RIGHT_UP: 4, DART_LEFT: 5, DART_RIGHT: 6, CLEANUP: 7 };
const KIND = { LEFT: 1, RIGHT: 2, STRAIGHT: 3 };
const KIND_NAME = [null, 'LEFT', 'RIGHT', 'STRAIGHT'];

export function tickTimeMs(tick) { return Math.floor((tick * 1000) / 60); }

// Applies one recorded op to the browser InputNormalizer, as the session's
// touch-controller path would (one pointer per wing press).
export function applyOp(input, op, ptr) {
  switch (op) {
    case OP.LEFT_DOWN: ptr.L = ++ptr.n; input.controlPointerDown(ptr.L, 'LEFT_WING'); break;
    case OP.LEFT_UP: input.pointerUp(ptr.L); break;
    case OP.RIGHT_DOWN: ptr.R = ++ptr.n; input.controlPointerDown(ptr.R, 'RIGHT_WING'); break;
    case OP.RIGHT_UP: input.pointerUp(ptr.R); break;
    // a dart belongs to the wing's latest press (a physical wing has one pointer)
    case OP.DART_LEFT: if (!ptr.L) ptr.L = ++ptr.n; input.controlDart(ptr.L, 'LEFT_WING'); break;
    case OP.DART_RIGHT: if (!ptr.R) ptr.R = ++ptr.n; input.controlDart(ptr.R, 'RIGHT_WING'); break;
    case OP.CLEANUP: input.cleanup(); break;
  }
}
export function encodeFrame(f) {
  return (f.left ? 1 : 0) | (f.right ? 2 : 0) | (f.flapEdge ? 4 : 0) | (f.chordEdge ? 8 : 0) |
    (f.dartEdge ? 16 : 0) | (f.dartSide === 'RIGHT' ? 32 : 0) | ((f.flapEdge ? KIND[f.flapKind] || 0 : 0) << 6);
}
export function decodeFrame(b, sidelessDart = false) {
  const dartEdge = !!(b & 16), flapEdge = !!(b & 4);
  return {
    left: !!(b & 1), right: !!(b & 2), flapEdge, flapKind: flapEdge ? KIND_NAME[b >> 6] : null, chordEdge: !!(b & 8),
    flapHeld: false, dartEdge, dartSide: dartEdge && !sidelessDart ? (b & 32 ? 'RIGHT' : 'LEFT') : null,
  };
}
export function canAcceptBufferedFlap(s) {           // arcade/src/app/session.mjs
  if (!s || s.sim.shell !== 'PLAY') return true;
  return s.player.flapCooldown === 0 && s.player.wing > 0 && s.player.invulnerableTicks <= SHIMMER_TICKS;
}
export function applyCheats(s, header) {
  if (header.livesFloor && s.sim.lives < 3) s.sim.lives = 3;
  if (header.shield && s.player.invulnerableTicks < 2) s.player.invulnerableTicks = 2;
}
// Parses a trace (Uint8Array) into its header and per-tick records.
export function parseTrace(bytes) {
  const magic = String.fromCharCode(...bytes.subarray(0, 8));
  if (magic !== 'STRGOLD1') throw new Error('not a golden trace');
  const hl = bytes[8] | bytes[9] << 8 | bytes[10] << 16 | bytes[11] << 24;
  const header = JSON.parse(new TextDecoder().decode(bytes.subarray(12, 12 + hl)));
  const ticks = [];
  let o = 12 + hl;
  while (o < bytes.length) {
    const n = bytes[o++], ops = [];
    for (let i = 0; i < n; i++) { ops.push([bytes[o], bytes[o + 1]]); o += 2; }
    const acc = bytes[o++], frame = bytes[o++];
    ticks.push({ ops, accept: !!(acc & 1), sidelessDart: !!(acc & 2), frame, digest: bytes.subarray(o, o + 8) });
    o += 8;
  }
  return { header, ticks };
}
// Produces the input frame for one recorded tick, driving the normalizer the
// way the browser session does (raw traces carry the frame itself).
export function frameForTick(rec, tickIndex, state, input, ptr, header, clock) {
  if (header.raw) return decodeFrame(rec.frame, rec.sidelessDart);
  const base = tickTimeMs(tickIndex);
  for (const [ms, op] of rec.ops) { clock.now = base + ms; applyOp(input, op, ptr); }
  clock.now = base + 16;
  return input.frame({ acceptFlap: canAcceptBufferedFlap(state) });
}
