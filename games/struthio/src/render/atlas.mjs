// STRUTHIO ARCADE · the texture atlas: sprites, swatches, the pixel font, ring
// effects, props and the island sheet, plus the world plates.
import{surface,color,rect,circle}from './surface.mjs';
import{ATLAS_SIZE,WORLD_PLATE_W,WORLD_TEX_W,WORLD_TEX_H}from './renderer.mjs';
import{measureIslands}from './islands.mjs';
import{visualPalette}from './visual-spec.mjs';
import{paintRingFx}from './ring-fx.mjs';
import{settle,depthGrade,ARCADE_DEPTH}from './grade.mjs';
import{paintHdProps}from './props.mjs';
import{paintHdSprites,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin}from './sprites.mjs';
const REGION=Object.freeze({
SPRITES:[0,0],
RING_DIM:[1536,520],
SWATCH:[1536,560],
ISLANDS:[0,1280],
ISLAND_BAKE:[0,0,1024,768],
});
const FONT_COLOURS=['white','cyanLight','lavaHot','goldLight','chromeDark'];
const MODERN_FONT=Object.freeze({x:1536,y:0,cols:16,cellW:18,cellH:24,rows:4,glyphW:15,glyphH:21});
function copyCanvas(s,canvas,dx,dy){
const pixels=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
for (let y=0;y<canvas.height;y++) s.p.set(
pixels.subarray(y*canvas.width*4,(y+1)*canvas.width*4),
((dy+y)*s.w+dx)*4,
);
}
function paintModernFont(s,A,C){
const canvas=document.createElement('canvas');
canvas.width=MODERN_FONT.cols*MODERN_FONT.cellW;
canvas.height=FONT_COLOURS.length*MODERN_FONT.rows*MODERN_FONT.cellH;
const ctx=canvas.getContext('2d',{willReadFrequently:true});
if (!ctx) throw new Error('TEXT_RASTER_UNAVAILABLE');
ctx.textBaseline='alphabetic';
ctx.textAlign='center';
ctx.font='700 23px Arial, Helvetica, sans-serif';
const chars=Object.keys(A.font_5x7).sort();
for (let tone=0;tone<FONT_COLOURS.length;tone++){
const[r,g,b]=C[FONT_COLOURS[tone]];
ctx.fillStyle=`rgb(${r} ${g} ${b})`;
chars.forEach((ch,i)=>{
if (ch===' ') return;
const x=(i%MODERN_FONT.cols)*MODERN_FONT.cellW+1+MODERN_FONT.glyphW/2;
const y=tone*MODERN_FONT.rows*MODERN_FONT.cellH+Math.floor(i/MODERN_FONT.cols)*MODERN_FONT.cellH+20;
ctx.fillText(ch,x,y,MODERN_FONT.glyphW);
});
}
copyCanvas(s,canvas,MODERN_FONT.x,MODERN_FONT.y);
}
function paintSpentRing(s,C){
const[x,y]=REGION.RING_DIM;
circle(s,x+12,y+12,10,C.cyanDeep,1);rect(s,x+9,y+11,7,2,C.earthDark);
}
function paintWorldPlates(atlas){
const stage=atlas.background,s=atlas.world;
for (const[layer,ox] of[[stage.rear,0],[stage.near,WORLD_PLATE_W]]){
const rowBytes=layer.w*4;
for (let y=0;y<layer.h;y++) s.p.set(layer.p.subarray(y*rowBytes,(y+1)*rowBytes),(y*s.w+ox)*4);
}
}
function paintArtSet(A,paletteRecord,fontRecord,islands,islandSpec,heroSprites,islandSettle){
const palette=visualPalette(paletteRecord);
const C=Object.fromEntries(Object.entries(palette).map(([k,v])=>[k,color(v)]));
const s=surface(ATLAS_SIZE,ATLAS_SIZE,[0,0,0,0]);
paintHdSprites(s,REGION.SPRITES,heroSprites);
const swatchNames=Object.keys(palette).sort();
const swatch={};
swatchNames.forEach((name,i)=>{const x=REGION.SWATCH[0]+i*8;rect(s,x,REGION.SWATCH[1],8,8,C[name]);swatch[name]=[x,REGION.SWATCH[1]];});
const extra={
shade:[0,0,0,176],
cyanGhost:[32,196,215,82],
cyanWhisper:[32,196,215,38],
lavaGhost:[242,74,34,70],
lavaBloom:[242,74,34,18],
whiteGhost:[255,253,243,90],
};
for (const[name,rgba] of Object.entries(extra)){
const i=Object.keys(swatch).length;
const x=REGION.SWATCH[0]+i*8;
rect(s,x,REGION.SWATCH[1],8,8,rgba);
swatch[name]=[x,REGION.SWATCH[1]];
}
const[ix,iy]=REGION.ISLANDS;
const islandArt=settle(islands,islandSettle);
for (let y=0;y<islandArt.h;y++) s.p.set(islandArt.p.subarray(y*islandArt.w*4,(y+1)*islandArt.w*4),((iy+y)*s.w+ix)*4);
paintModernFont(s,{font_5x7:fontRecord},C);
const fontChars=Object.keys(fontRecord).sort();
const set={surface:s,p:s.p,swatch,C,palette,fontIndex:new Map(fontChars.map((c,i)=>[c,i])),islands:Object.freeze({origin:REGION.ISLANDS,masters:measureIslands(islands,islandSpec),bakeRegion:REGION.ISLAND_BAKE})};
paintSpentRing(s,C);
paintRingFx(s,C);
paintHdProps(s,C);
return set;
}
// One art set: the Arcade palette, font, island sheet and jouster sheet, plus
// the depth-graded Arcade plates.
function buildAtlas(R,{rear,near,islands,islandSpec,bird}){
const set=paintArtSet(R,R.palette,R.font_5x7,islands,islandSpec,bird,0);
const background={rear:depthGrade(rear,ARCADE_DEPTH.REAR),near:depthGrade(near,ARCADE_DEPTH.NEAR)};
const atlas={surface:{w:set.surface.w,h:set.surface.h,p:set.p},world:surface(WORLD_TEX_W,WORLD_TEX_H,[0,0,0,0]),artSet:'ARCADE',
swatch:set.swatch,C:set.C,palette:set.palette,islands:set.islands,fontIndex:set.fontIndex,modernFont:MODERN_FONT,background};
paintWorldPlates(atlas);
return atlas;
}
function fnv(bytes){let h=0x811c9dc5;for (let i=0;i<bytes.length;i++){h^=bytes[i];h=Math.imul(h,0x01000193);}return (h>>>0).toString(16).padStart(8,'0');}
function atlasDigest(atlas){
return{artSet:atlas.artSet,world:fnv(atlas.world.p),atlas:fnv(atlas.surface.p),masters:atlas.islands.masters.map((m)=>m.id+':'+m.x+','+m.w+','+m.capTop+','+(m.topDecor||0)).join(' ')};
}
export{buildAtlas,atlasDigest,REGION,SPRITE_CELL_PX,SPRITE_FRAME_COUNT,SPRITE_DRAW_OFFSET,spriteSourceOrigin,SPRITE_IDLE,idleSourceOrigin};
