// STRUTHIO ARCADE · the jouster sheet layout: 192 poses in a 16x12 grid of
// 96 px cells (32 logical px at 3x).
const SPRITE_HD=3;
const SPRITE_CELL_PX=32*SPRITE_HD;
const SPRITE_DRAW_OFFSET=Object.freeze([1,4]);
const SPRITE_FRAME_COUNT=192;
const SPRITE_IDLE=0;
const SPRITE_RANGES=Object.freeze({
NEUTRAL:[0,7],FLAP:[8,31],IMPULSE:[32,43],GLIDE:[44,53],CLIMB:[54,63],
DESCENT:[64,73],BANK_LEFT:[74,83],BANK_RIGHT:[84,93],RUN:[94,113],
TAKEOFF:[114,123],LANDING:[124,133],AIR_TRANSITION:[134,149],
GROUND_AIR:[150,161],DART:[162,171],HIT:[172,177],DEATH:[178,185],VERTICAL_ASCENT:[186,191],
});
function spriteSourceOrigin(_origin,_classRow,frame){
const n=((frame%SPRITE_FRAME_COUNT)+SPRITE_FRAME_COUNT)%SPRITE_FRAME_COUNT;
return[(n%16)*SPRITE_CELL_PX,Math.floor(n/16)*SPRITE_CELL_PX];
}
function idleSourceOrigin(classRow){return spriteSourceOrigin([0,0],classRow,SPRITE_IDLE);}
function paintHdSprites(_surface,_origin,sheet){
if (!sheet||sheet.w!==1536||sheet.h!==1152) throw new Error('JOUSTER_ART_REQUIRED: expected 192 poses in a 1536x1152 RGBA sheet');
}
export{paintHdSprites,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_RANGES,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin};
