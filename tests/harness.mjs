// Headless sim harness: loads the built-in DEV-00 authority into the real
// app.mjs sim modules (no browser needed).
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const mod = await import(path.join(ROOT, 'app.mjs'));
export const sim = mod.__sim;
const raw = JSON.parse(fs.readFileSync(path.join(ROOT, 'episodes/dev-00/authority.json'), 'utf8'));
const episode = JSON.parse(fs.readFileSync(path.join(ROOT, 'episodes/dev-00/episode.json'), 'utf8'));
sim.authority.configureCartridge({ id: episode.id, buildId: episode.buildId, saveNamespace: episode.saveNamespace });
export const A = await sim.authority.loadAuthority(async (name) => raw[name]);
export const EMPTY = Object.freeze({ left: false, right: false, flapEdge: false, flapHeld: false });
export function frame(o = {}) { return { ...EMPTY, ...o }; }
export { ROOT };
