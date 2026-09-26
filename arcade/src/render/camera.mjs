// STRUTHIO ARCADE · the tower camera: one 8-screen climb from the grid floor to
// the moon, following the player up and down. Presentation y = 2 x sim y; the
// camera spans 2688 px (7 x 336) so the rear, near and island layers scroll at
// their own speeds over the whole climb.
import{floorDiv}from '../core/fixed.mjs';
import{SHIMMER_TICKS}from '../sim/state.mjs';

const SCALE_Y=2;
const SPAN=336;
const PLAYER_SPRITE_ANCHOR_Y=25;
const CAMERA_BOTTOM=SPAN;
const CAMERA_TOP=-7*SPAN;
const DEAD_ZONE=Object.freeze([150,290]);   // keep the player's feet in this band
const KEEP=Object.freeze([40,376]);         // and never outside this one
const SUMMIT_HOLD=330;                      // top screen: settle on the summit
const clamp=(n,lo,hi)=>Math.max(lo,Math.min(hi,n));

function feetOf(s){return (floorDiv(s.player.y,256)+PLAYER_SPRITE_ANCHOR_Y)*SCALE_Y;}
export function towerProfile(s){
const feet=feetOf(s);
return{
scaleY:SCALE_Y,baseY:0,initialTop:CAMERA_BOTTOM,summitTop:CAMERA_TOP,
targetTop:clamp(feet-Math.round((DEAD_ZONE[0]+DEAD_ZONE[1])/2),CAMERA_TOP,CAMERA_BOTTOM),
bounds:{bottom:CAMERA_BOTTOM,top:CAMERA_TOP},
};
}
export function withCamera(profile,cameraTop=profile?.targetTop??0){
if (!profile) return null;
const backgroundProgress=clamp((profile.bounds.bottom-cameraTop)/(profile.bounds.bottom-profile.bounds.top),0,1);
return{...profile,cameraTop,backgroundProgress};
}
export function projectY(view,localY){
return view?view.baseY+localY*view.scaleY-view.cameraTop:localY;
}
export function projectAnchoredY(view,localTop,anchorY){
return view?view.baseY+(localTop+anchorY)*view.scaleY-view.cameraTop-anchorY:localTop;
}
export class TowerCamera{
constructor(){this.reset();}
reset(){this.top=null;this.lastTick=null;}
resolve(s){
const profile=towerProfile(s);
const feet=feetOf(s);
const hidden=s.player.invulnerableTicks>SHIMMER_TICKS;
if (this.top===null) this.top=profile.targetTop;
let desired=this.top;
if (hidden) desired=profile.targetTop;
else if (feet-desired<DEAD_ZONE[0]) desired=feet-DEAD_ZONE[0];
else if (feet-desired>DEAD_ZONE[1]) desired=feet-DEAD_ZONE[1];
// In the top screen the camera settles on the summit so the gold ring sits
// on the moon (the rear plate only lines up with the world at the summit).
if (!hidden&&feet-CAMERA_TOP<SUMMIT_HOLD) desired=CAMERA_TOP;
desired=clamp(desired,CAMERA_TOP,CAMERA_BOTTOM);
const elapsed=this.lastTick===null?0:Math.max(0,Math.min(5,s.sim.tick-this.lastTick));
this.lastTick=s.sim.tick;
for (let i=0;i<elapsed;i++){
const delta=desired-this.top;
if (delta===0) break;
const step=Math.max(2,Math.min(40,Math.ceil(Math.abs(delta)*.16)));
this.top+=Math.sign(delta)*Math.min(Math.abs(delta),step);
}
if (!hidden) this.top=clamp(this.top,feet-KEEP[1],feet-KEEP[0]);
this.top=clamp(this.top,CAMERA_TOP,CAMERA_BOTTOM);
return{...withCamera(profile,Math.round(this.top)),cameraTarget:desired};
}
}
