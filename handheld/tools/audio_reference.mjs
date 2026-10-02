// STRUTHIO HANDHELD · the browser's own sound engine, offline: renders an event
// list (host/audio_check --events) through arcade/src/audio/conductor.mjs and
// synth.mjs, unmodified, with the delivery protocol host/audio_check --render
// uses, and compares the C render sample by sample.
//   node handheld/tools/audio_reference.mjs in.events c.pcm [ref.pcm]
import fs from 'node:fs';
import R from '../../arcade/src/data/rules.mjs';
import { Conductor, synthConfig } from '../../arcade/src/audio/conductor.mjs';
import { Mixer } from '../../arcade/src/audio/synth.mjs';

const [evPath, cPath, refOut] = process.argv.slice(2);
const RATE = R.audio.sampleRate, BLOCK = 128;
const events = fs.readFileSync(evPath, 'utf8').trim().split('\n').filter(Boolean).map((l) => {
  const [tick, type, a, b] = l.split(' ');
  return { tick: Number(tick), type, a: Number(a), b: Number(b) };
});
Math.random = () => 0.5;                                  // pitch jitter off, as in the C render
const mixer = new Mixer(synthConfig(R.audio), RATE);
const clock = { currentTime: 0, sampleRate: RATE };
const conductor = new Conductor(R.audio, {
  context: clock,
  send: (m) => { if (m.type === 'note') mixer.noteOn({ ...m, at: Math.max(mixer.frame, Math.round(m.atSeconds * RATE)) }); },
});
const tickFrame = (t) => Math.round(t / 60 * RATE);      // C: (uint32)(t / 60 * rate + 0.5)
const end = events.length ? tickFrame(events[events.length - 1].tick) + RATE : RATE;
const blocks = Math.ceil(end / BLOCK);
const ref = new Int16Array(blocks * BLOCK);
let k = 0;
for (let F = 0, b = 0; b < blocks; b++, F += BLOCK) {
  while (k < events.length && tickFrame(events[k].tick) < F + BLOCK) {
    const tick = events[k].tick;
    clock.currentTime = tick / 60;
    const batch = [];
    while (k < events.length && events[k].tick === tick && tickFrame(tick) < F + BLOCK) batch.push(events[k++]);
    conductor.onEvents(batch);
  }
  mixer.render(ref.subarray(F, F + BLOCK));
}
if (refOut) fs.writeFileSync(refOut, Buffer.from(ref.buffer));
const c = new Int16Array(fs.readFileSync(cPath).buffer.slice(0));
if (c.length !== ref.length) { console.log(`AUDIO CHECK: FAIL length ${c.length} vs ${ref.length}`); process.exit(1); }
let sig = 0, err = 0, maxd = 0, active = 0;
for (let i = 0; i < ref.length; i++) {
  const d = c[i] - ref[i];
  sig += ref[i] * ref[i]; err += d * d;
  if (Math.abs(d) > maxd) maxd = Math.abs(d);
  if (ref[i]) active++;
}
const snr = err ? 10 * Math.log10(sig / err) : Infinity;
const name = evPath.split('/').pop();
const ok = snr >= 60;
console.log(`${ok ? 'PASS' : 'FAIL'} ${name.padEnd(14)} ${(ref.length / RATE).toFixed(1).padStart(6)} s  ${conductor.scheduled} notes  ` +
  `SNR ${snr === Infinity ? 'inf' : snr.toFixed(1)} dB  max diff ${maxd} LSB  (${(100 * active / ref.length).toFixed(1)}% non-silent)`);
process.exit(ok ? 0 : 1);
