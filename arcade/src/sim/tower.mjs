// STRUTHIO ARCADE · the tower: one hand-placed, 8-screen map from the grid
// floor to the moon, ten fixed ring placements, and the per-round rules.
// Sim coordinates keep the 256-wide wrap; y runs from the grid floor (GROUND
// top 336) up to the moon (TOWER_TOP). The camera presents y at 2x, so 1536
// sim px fill the 8 screens (3072 px) the Arcade background plates span.
import{mod}from '../core/fixed.mjs';
const TOWER_SCREENS=8,TOWER_SCREEN=192;
const TOWER_GROUND=336;
const TOWER_BOTTOM=360;
const TOWER_TOP=TOWER_BOTTOM-TOWER_SCREENS*TOWER_SCREEN;
const TOWER_PLAY_TOP=TOWER_TOP+20;
const DRIFT=(amplitude,period)=>Object.freeze({profile:'DRIFT_X_SOFT',amplitude,period,dwell:0});
const BOB=(amplitude,period)=>Object.freeze({profile:'BOB_Y_SOFT',amplitude,period,dwell:0});
// [id, x, y, width, island art, mirrored, motion, phase offset]. One fixed,
// hand-placed map: a zig-zag of stepping islands with a wide rest island about
// once a screen; the upper tower is sparser, smaller and starts to drift.
const ISLANDS=[
// 1 LAUNCH PAD: low perches either side of the grid floor.
['T01',14,284,56,'STD_05',0],['T02',182,280,54,'STD_04',1],
['T03',98,236,54,'STD_07',0],
['T04',222,196,50,'STD_02',1],['T05',34,188,52,'STD_01',0],
// 2 STAIRCASE: a rest island, then steps climbing left to right.
['T06',98,148,88,'STD_09',0],
['T07',16,106,50,'STD_03',1],['T08',200,98,50,'STD_07',1],
['T09',68,62,46,'STD_06',0],
['T10',128,20,52,'STD_02',0],
['T11',188,-24,54,'STD_04',1],
// 3 TWIN COLUMNS: two ladders of perches around an open central shaft.
['T12',18,-50,52,'STD_01',0],
['T13',196,-80,50,'STD_03',1],['T14',32,-106,48,'STD_06',0],
['T15',186,-136,54,'STD_07',1],['T16',14,-162,52,'STD_02',1],
['T17',200,-192,48,'STD_06',1],['T18',30,-218,50,'STD_03',0],
// 4 REST AND DRIFT: a wide landing, then two islands that move.
['T19',96,-256,96,'STD_09',1],
['T20',214,-306,50,'STD_02',0,DRIFT(12,420)],['T21',30,-314,54,'STD_05',1],
['T22',124,-360,54,'STD_04',0,BOB(6,460)],
['T23',30,-404,50,'STD_01',1],
// 5 STAIRCASE BACK: right to left, across the wrap seam.
['T24',200,-414,52,'STD_07',0],
['T25',138,-458,50,'STD_03',1],
['T26',76,-502,52,'STD_01',0],['T27',214,-506,76,'STD_08',1],
['T28',14,-546,54,'STD_04',0],
['T29',208,-590,48,'STD_06',1],
// 6 THE VOID: open sky with one rest island and one drifting stone.
['T30',92,-640,92,'STD_09',0],
['T31',196,-722,46,'STD_06',0,DRIFT(14,380)],['T32',24,-736,50,'STD_02',1],
// 7 CROWN: an arc of islands with a drifting keystone above.
['T33',6,-812,52,'STD_05',0],['T34',200,-816,52,'STD_04',1],
['T35',60,-862,50,'STD_07',0],['T36',146,-866,50,'STD_01',1],
['T37',92,-912,76,'STD_08',0],
['T38',210,-948,46,'STD_03',1,DRIFT(12,340)],
// 8 SUMMIT: side perches and the pedestal under the moon.
['T39',20,-990,52,'STD_02',0],
['T40',104,-1034,46,'STD_06',1,BOB(8,400)],
['T41',8,-1086,50,'STD_03',0],
['T42',150,-1066,92,'STD_09',1],
];
const TOWER_PLATFORMS=Object.freeze([
Object.freeze({id:'GROUND',motion:'STATIC',phaseOffset:0,rect:Object.freeze([0,TOWER_GROUND,256,16]),surface:'SAFE'}),
...ISLANDS.map(([id,x,y,w,look,mirror,motion='STATIC',phaseOffset=0])=>Object.freeze({
id,motion,phaseOffset,rect:Object.freeze([x,y,w,8]),surface:'SAFE',look,mirror:!!mirror,
})),
]);
const PLATFORM_INDEX=new Map(TOWER_PLATFORMS.map((p,i)=>[p.id,i]));
function towerSpawnFor(index){
const p=TOWER_PLATFORMS[index]||TOWER_PLATFORMS[0];
if (p.id==='GROUND') return[32,TOWER_GROUND-25];
return[mod(p.rect[0]+(p.rect[2]>>1)-14,256),p.rect[1]-25];
}
// Gold ring: in front of the moon at the top of the rear plate (the moon sits
// at rear-plate logical (203,85); at the summit the camera shows rows 0..384).
const GOLD_RING=Object.freeze({id:'TWR_GOLD',order:7,center:Object.freeze([203,TOWER_TOP+43]),radius:11,color:'GREEN'});
// Ten fixed ring placements, one per round, then the cycle repeats. Each set
// spreads six rings through the whole tower so every round is a full climb.
const RING_SETS_RAW=[
[[126,204],[160,70],[110,-150],[100,-316],[176,-560],[130,-760]],
[[240,240],[40,30],[230,-240],[170,-520],[60,-690],[240,-880]],
[[60,150],[150,-60],[20,-270],[170,-410],[120,-700],[30,-950]],
[[128,300],[2,60],[110,-200],[238,-272],[100,-560],[170,-1000]],
[[200,150],[90,-20],[150,-300],[20,-450],[236,-760],[128,-960]],
[[246,306],[150,56],[250,-108],[60,-470],[150,-790],[60,-1130]],
[[40,236],[210,40],[130,-220],[250,-470],[20,-780],[236,-1020]],
[[170,190],[4,-20],[128,-300],[176,-600],[120,-830],[90,-1100]],
[[96,300],[100,100],[216,-160],[60,-600],[240,-770],[110,-1130]],
[[180,236],[40,-80],[170,-330],[10,-620],[60,-1040],[250,-1000]],
];
const RING_SETS=Object.freeze(RING_SETS_RAW.map((set)=>Object.freeze(set.map(([x,y],i)=>Object.freeze({
id:`TWR_R${i+1}`,order:i+1,center:Object.freeze([x,y]),radius:11,color:'CYAN',
})))));
const TOWER_HAZARD=Object.freeze({kind:'STATIC',lavaY:352,period:0,warning:0,active:0,amplitude:0,phaseOffset:0});
const GHOSTS=Object.freeze(['BLINKY','PINKY','INKY','CLYDE']);
// The nearby zone: rivals exist within ZONE px above and below the player.
// Arrivals start ARRIVAL px away (more than a full screen plus a sprite, so
// they are always off screen when they appear) and fly in.
const TOWER_ZONE=288,TOWER_DESPAWN=300,TOWER_ARRIVAL=[220,252];
const TOWER_FIRST_ARRIVAL=45;
const ROUND_CLEAR_HOLD=75;
const ROUND_SWEEP_TICKS=60;
function towerRules(round){
const r=Math.max(1,round|0),k=r-1;
return{
round:r,
cap:Math.min(8,3+k),
fillGap:Math.max(40,90-8*k),
replaceDelay:Math.max(60,240-36*k),
classShift:Math.min(.5,.12*k),
tierBase:Math.min(4,1+(k>>1)),
eggTicks:Math.max(150,360-30*k),
ringSet:mod(k,RING_SETS.length),
clearBonus:Math.min(15000,5000+1000*k),
};
}
function towerAltitude(yPx){return Math.max(0,Math.min(1,(TOWER_GROUND-yPx)/(TOWER_GROUND-TOWER_TOP)));}
function towerBand(yPx){const a=towerAltitude(yPx);return a<1/3?0:a<2/3?1:2;}
function towerClassFor(yPx,rules,draw){
const eff=towerAltitude(yPx)+rules.classShift;
const w=eff<1/3?[80,20,0]:eff<2/3?[30,55,15]:eff<1?[10,45,45]:[0,40,60];
const pick=draw%100;
return pick<w[0]?'BOUNDER':pick<w[0]+w[1]?'HUNTER':'SHADOW';
}
export function towerContent(s){
const t=s.tower,rules=towerRules(t.round);
return{
kind:'TOWER',contentId:'TOWER',platforms:TOWER_PLATFORMS,playerSpawn:towerSpawnFor(t.check),
rings:RING_SETS[rules.ringSet],goldRing:GOLD_RING,hazard:TOWER_HAZARD,round:t.round,tower:t,rules,
};
}
export{
TOWER_PLATFORMS,PLATFORM_INDEX,RING_SETS,GOLD_RING,TOWER_TOP,TOWER_BOTTOM,TOWER_GROUND,TOWER_PLAY_TOP,TOWER_SCREEN,TOWER_SCREENS,
TOWER_ZONE,TOWER_DESPAWN,TOWER_ARRIVAL,TOWER_FIRST_ARRIVAL,ROUND_CLEAR_HOLD,ROUND_SWEEP_TICKS,GHOSTS,TOWER_HAZARD,
towerRules,towerSpawnFor,towerAltitude,towerBand,towerClassFor,
};
