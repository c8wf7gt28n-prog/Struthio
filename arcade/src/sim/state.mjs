// STRUTHIO ARCADE · the authoritative game state (it is also the save payload).
// Positions and velocities are integer subpixels (256 per pixel).
import{seedState}from '../core/rng.mjs';
import{px}from '../core/fixed.mjs';

export const STATE_VERSION=1;
export const BIRD_BOX=Object.freeze({l:8,r:21,t:14,b:25});
export const RIDER_BOX=Object.freeze({l:11,r:17,t:15,b:25});
export const EGG_BOX=Object.freeze({l:11,r:18,t:17,b:25});
export const LANCE_Y_SUB=(BIRD_BOX.t-5)*256;
export const FLAP_COOLDOWN_TICKS=7;
export const RESPAWN_HIDDEN_TICKS=84;
export const SHIMMER_TICKS=90;

export function emptyPlayer(x,y){
return{x:px(x),y:px(y),vx:0,vy:0,groundedPlatformId:null,facing:1,wing:64,flapCooldown:0,footingTicks:0,lavaPhase:'SAFE',lavaTicks:0,invulnerableTicks:0};
}
// tower: round, rings taken (bits 0-5, bit 6 = gold ring taken), rivals
// defeated, the island the player respawns on, whether rivals have started
// arriving (the player has moved), the round-clear hold, and the arrival
// cooldown in ticks.
export function emptyTower(round=1){
return{round,ringMask:0,kills:0,check:0,go:false,hold:0,cooldown:0};
}
export function newState(seed,R){
return{
version:STATE_VERSION,
sim:{tick:0,shell:'ATTRACT',nextActorId:1,eventSerial:0,score:0,lives:R.scoring.startLives},
rng:{gameplayState:seedState(seed)},
player:emptyPlayer(32,311),
actors:[],
world:{lavaY:px(R.sim.lavaY),platforms:[]},
tower:emptyTower(1),
run:{eggChain:0,clean:true,deaths:0,lifeBands:0},
};
}
export function entityBox(x,y,box){
return{l:x+box.l*256,r:x+box.r*256,t:y+box.t*256,b:y+box.b*256};
}
