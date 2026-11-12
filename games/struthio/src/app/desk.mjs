// STRUTHIO ARCADE · desk mode, opt-in by address (?desk or ?desk=1): the game
// played at a desk with a keyboard. No touch controller and no title screen; a
// new run waits on the pause screen at tick 0. Desk runs save to their own
// slots, so a run the web game left mid-climb is never touched (high scores
// are shared). Pure: no DOM. index.html sets the body class from the same rule
// before the first paint (tests/desk.mjs checks that the two agree).
import{SAVE_NAMESPACE,KEYS}from '../save/checkpoint.mjs';

export const deskMode=(search='')=>/^(|1|true|on|yes)$/i.test(new URLSearchParams(search??'').get('desk')??'x');
// A new run held before its first tick: tick 0, score 0, the opening position.
// The first flap key (or a controller's Start) sets the shell to PLAY, and that
// key flaps; Esc does not leave this start pause.
export function startPaused(game){const events=game.start();game.state.sim.shell='PAUSE';return events;}
// Storage seen through desk mode: the run slots and the save warning live under
// `struthio.arcade.v1.desk.*`; the high-score table is the web game's own.
const RUN_PREFIX=`${SAVE_NAMESPACE}.`,DESK_PREFIX=`${SAVE_NAMESPACE}.desk.`;
const own=(k)=>k===KEYS.RECORDS||!String(k).startsWith(RUN_PREFIX)?k:DESK_PREFIX+String(k).slice(RUN_PREFIX.length);
export function deskStorage(storage){
return{
getItem:(k)=>storage.getItem(own(k)),
setItem:(k,v)=>storage.setItem(own(k),v),
removeItem:(k)=>storage.removeItem(own(k)),
// The keys desk mode can see, under the names the game uses.
keys:()=>storage.keys().flatMap((k)=>k===KEYS.RECORDS?[k]:k.startsWith(DESK_PREFIX)?[RUN_PREFIX+k.slice(DESK_PREFIX.length)]:[]),
};
}
// The canvas's accessible label in desk mode: keys, not taps.
export const DESK_LABEL='STRUTHIO game arena. Left and Right arrows, or A and D, flap left and right; Up, W or Space flaps hard; Down or S darts; Escape pauses, and a flap key starts or resumes.';
