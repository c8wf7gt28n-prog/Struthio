// Dumps tower data as JSON for the offline map preview.
import { sim } from './harness.mjs';
const T = sim.tower;
console.log(JSON.stringify({ platforms: T.TOWER_PLATFORMS, sets: T.RING_SETS, gold: T.GOLD_RING, top: T.TOWER_TOP }));
