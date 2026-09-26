// STRUTHIO ARCADE · WebGPU renderer: a 256x384 logical scene drawn at 3x from
// instanced quads (atlas, bird sheet, world plates), then the post pass.
import{WAR_BIRD_PALETTE_WGSL,BLUE_CYCLE_RATE,BLUE_CYCLE_TRAVEL}from './bird-inks.mjs';
const LOGICAL_W=256,LOGICAL_H=384,SCENE_SCALE=3,SCENE_W=LOGICAL_W*SCENE_SCALE,SCENE_H=LOGICAL_H*SCENE_SCALE,LOGICAL_FORMAT='rgba8unorm',INSTANCE_STRIDE=40,ATLAS_SIZE=2048,MAX_INSTANCES=4096;
const WORLD_SCALE=3,WORLD_PLATE_W=256*WORLD_SCALE,WORLD_PLATE_H=768*WORLD_SCALE;
const WORLD_TEX_W=WORLD_PLATE_W*2,WORLD_TEX_H=WORLD_PLATE_H;
const MATERIAL_WORLD=8;
const MATERIAL_ARCADE_PLAYER=10;
const MATERIAL_ARCADE_ISLAND=11;
const GLOBE_MAP_W=1536,GLOBE_MAP_H=768;
// Island reds are drawn in the GAME OVER red and the yellow caps in the
// balanced gold the controller and HUD share (see islandPalette).
const ISLAND_RED_HUE='18.0',ISLAND_RED_DESAT='0.14',ISLAND_GOLD_SHIFT='8.0';
const SPRITE_WGSL=`struct Frame { logical: vec2f, invAtlas: vec2f, reserved0: vec2f, invWorld: vec2f, invBird: vec2f, reserved1: vec2f, tick: vec2f, globe: vec4f, fx: vec4f, look: vec4f }
struct VOut { @builtin(position) position: vec4f, @location(0) uv: vec2f, @location(2) @interpolate(flat) material: f32, @location(3) uvWorld: vec2f, @location(4) uvBird: vec2f }
@group(0) @binding(0) var<uniform> frame: Frame;
@group(0) @binding(1) var atlas: texture_2d<f32>;
@group(0) @binding(2) var nearestSampler: sampler;
@group(0) @binding(4) var world: texture_2d<f32>;
@group(0) @binding(7) var bird: texture_2d<f32>;
@group(0) @binding(9) var globeMap: texture_2d<f32>;
@vertex fn vs(@location(0) corner: vec2f, @location(1) uvCorner: vec2f, @location(2) dst: vec4f, @location(3) src: vec4f, @location(4) zAndFlags: vec2f) -> VOut {
  let pixel = dst.xy + corner * dst.zw;
  let ndc = vec2f(pixel.x / frame.logical.x * 2.0 - 1.0, 1.0 - pixel.y / frame.logical.y * 2.0);
  var out: VOut;
  out.position = vec4f(ndc, clamp(zAndFlags.x, 0.0, 1.0), 1.0);
  let texel = src.xy + uvCorner * src.zw + vec2f(0.5);
  out.uv = texel * frame.invAtlas;
  out.uvWorld = texel * frame.invWorld;
  out.uvBird = texel * frame.invBird;
  out.material = zAndFlags.y;
  return out;
}
${WAR_BIRD_PALETTE_WGSL}
// 2.3 ARCADE GLOBE: the battle station in the Arcade rear plate turns. The
// plate's own painted lighting (gold sun side, blue night side) stays fixed;
// only the surface detail -- grid, trench, dish -- rotates under it, read from
// a 360-degree longitude map built at boot from the same graded plate
// (buildArcadeGlobe). R = detail ratio / 4, GBA = the smooth painted light at
// the unrotated longitude. globe = (centre x, centre y, radius, radians/tick)
// in rear-plate texels; w = 0 disables it (any non-Arcade world).
// 3.1 COLOUR mode (radius negative): a neon wire globe has no smooth painted
// light to keep, and light x detail would grey its cyan and gold. The map's
// GBA then hold the plate's own colour at every longitude, and the whole
// surface -- lines, gold continent -- turns together.
fn globeSurface(base: vec3f, wp: vec2f, t: f32) -> vec3f {
  if (wp.x >= ${WORLD_PLATE_W}.0) { return base; }
  let colourMode = frame.globe.z < 0.0;
  let n = (wp - frame.globe.xy) / abs(frame.globe.z);
  if (dot(n, n) >= 1.0) { return base; }
  let lat = asin(clamp(n.y, -1.0, 1.0));
  let lon = asin(clamp(n.x / max(cos(lat), 0.0001), -1.0, 1.0));
  let dims = vec2f(textureDimensions(globeMap));
  let vy = clamp(i32((lat / ${Math.PI} + 0.5) * dims.y), 0, i32(dims.y) - 1);
  let spin = fract(frame.look.y);   // 3.5: the moon's turn, advanced by the music (moonPhase)
  let uL = clamp(i32((lon / ${2*Math.PI} + 0.5) * dims.x), 0, i32(dims.x) - 1);
  let uD = i32(fract(lon / ${2*Math.PI} + 0.5 - spin) * dims.x) % i32(dims.x);
  if (colourMode) { return textureLoad(globeMap, vec2i(uD, vy), 0).gba; }
  let light = textureLoad(globeMap, vec2i(uL, vy), 0).gba;
  let detail = textureLoad(globeMap, vec2i(uD, vy), 0).r * 4.0;
  return clamp(light * detail, vec3f(0.0), vec3f(1.0));
}
// 3.1 ARCADE AMBIENT (Pass 4 motion + light plan). fx = (on, rear horizon row,
// music beat 0..1, motion 0|1). Everything multiplies brightness only, never
// moves or adds geometry, and scales to nothing under Reduce Motion (w = 0).
//   rear sky  : ~15% of stars twinkle, 1.8-4.5 s, +-8-12%, calmer mid-corridor
//   rear floor: one broad energy band travels toward the viewer every 6.5 s, +13%
//   near      : a faint shimmer climbs the cyan edges every 8 s, +7%
//   islands   : red fissures and cyan cores pulse with the music, +4-12%
// Hash without trig (Hoskins hash12): cheap on every GPU.
fn fxHash(p: vec2f) -> f32 {
  var p3 = fract(vec3f(p.x, p.y, p.x) * 0.1031);
  p3 = p3 + dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}
// sin(pi x) on [0,1) as a parabola (within 6%), and a sine-shaped wave on a
// cycle: no trig in the per-texel path.
fn hump(x: f32) -> f32 { return 4.0 * x * (1.0 - x); }
fn wave1(x: f32) -> f32 { let f = fract(x); return select(-hump(f * 2.0 - 1.0), hump(f * 2.0), f < 0.5); }
fn arcadeAmbient(base: vec3f, wp: vec2f, t: f32) -> vec3f {
  // Branch-free: every term is weighted by a 0/1 mask, so every GPU (and
  // software rasteriser) runs it as one straight line. t is in ticks (60/s).
  let hi = max(base.r, max(base.g, base.b));
  let lit = clamp((hi - 0.16) * 3.0, 0.0, 1.0);          // painted lines and lights
  let horizon = frame.fx.y;
  let rear = step(wp.x, ${WORLD_PLATE_W}.0 - 1.0);
  let near = 1.0 - rear;
  // 1 GRID: light pulses slide along the painted grid toward the viewer, four
  //   bands in view, one band-spacing every 1.5 s.
  let dy = max(wp.y - horizon, 1.0);
  let gp = hump(fract(pow(dy, 0.62) / 12.0 - t / 90.0));
  let gp2 = gp * gp; let gp4 = gp2 * gp2; let band = gp4 * gp4 * gp2;
  let floorMask = rear * step(horizon + 2.0, wp.y) * smoothstep(horizon + 4.0, horizon + 70.0, wp.y);
  let gridGain = floorMask * band * (0.95 * lit + 0.10);
  // 2 STARS: about half the stars twinkle (1.2-3.4 s, 40%-160%), a few flash.
  let h = fxHash(floor(wp * 0.1));
  let g = wp - frame.globe.xy;
  let sky = rear * step(wp.y, horizon - 330.0);
  let star = sky * step(0.42, hi) * step(20000.0, dot(g, g)) * step(h, 0.55);
  let k = h / 0.55;
  let tw = wave1(t / ((1.2 + 2.2 * fract(k * 7.13)) * 60.0) + fract(k * 13.7));
  let flash = pow(max(wave1(t / ((7.0 + 9.0 * fract(k * 3.7)) * 60.0) + fract(k * 5.1)), 0.0), 14.0);
  let starGain = star * ((0.25 + 0.35 * k) * tw + 1.2 * flash * step(k, 0.3));
  // 3 CITY: the horizon glow breathes (5 s) and light climbs the spires (3.3 s).
  let city = rear * step(horizon - 540.0, wp.y) * step(wp.y, horizon + 6.0) * lit;
  let cp = hump(fract((horizon - wp.y) / 520.0 - t / 200.0));
  let cp2 = cp * cp; let cp4 = cp2 * cp2;
  let cityGain = city * (0.10 * sin(t * 0.020944) + 0.85 * cp4 * cp4 * cp4 * cp4);
  // 4 NEAR PILLARS: gold glints run up the vines (5 s); cyan edges shimmer (8 s).
  let gold = near * clamp((base.r - base.b - 0.20) * 3.0, 0.0, 1.0) * step(base.b, base.g) * step(0.35, hi);
  let gl = hump(fract(t / 300.0 + wp.y * 0.0009 + wp.x * 0.0004)); let gl2 = gl * gl; let gl4 = gl2 * gl2;
  let cyan = clamp((min(base.g, base.b) - base.r - 0.12) * 3.333, 0.0, 1.0);
  let sn = hump(fract(t * 0.0020833 + wp.y * 0.0011111)); let sn2 = sn * sn; let sn4 = sn2 * sn2;
  let nearGain = gold * 0.9 * gl4 * gl4 * gl4 + near * 0.22 * sn4 * sn4 * sn2 * cyan;
  // 5 SHOOTING STAR: most 7.5 s windows, a streak crosses the sky in 0.8 s
  //   (behind the moon, never across it).
  let epoch = floor(t / 450.0);
  let lt = t - epoch * 450.0;
  let h1 = fxHash(vec2f(epoch, 3.0)); let h2 = fxHash(vec2f(epoch, 7.0)); let h3 = fxHash(vec2f(epoch, 11.0));
  let dir = normalize(vec2f(select(-1.0, 1.0, h3 > 0.5), 0.42 + 0.3 * h2));
  let head = vec2f(80.0 + 608.0 * h1, 120.0 + 900.0 * h2) + dir * 14.0 * lt;
  let rel = wp - head;
  let along = -dot(rel, dir);
  let perp = abs(rel.x * dir.y - rel.y * dir.x);
  let tail = 1.0 - clamp(along / 120.0, 0.0, 1.0);
  let streak = sky * step(14000.0, dot(g, g)) * step(fxHash(vec2f(epoch, 1.0)), 0.7) * step(0.0, along) * tail * tail
    * (1.0 - smoothstep(0.6, 2.4, perp)) * smoothstep(0.0, 6.0, lt) * (1.0 - smoothstep(38.0, 50.0, lt));
  let m = frame.fx.w;
  return base * (1.0 + m * (gridGain + starGain + cityGain + nearGain)) + m * streak * 1.4 * vec3f(0.85, 0.92, 1.0);
}
// Island palette: crimson tips -> the GAME OVER red (hue 18, a little less
// saturated), and the lemon-yellow caps are turned toward the controller gold
// so the two yellows meet halfway. Blues are untouched.
fn islandPalette(c: vec3f) -> vec3f {
  let mx = max(c.r, max(c.g, c.b));
  let d = mx - min(c.r, min(c.g, c.b));
  if (d < 0.0001) { return c; }
  var h = 0.0;
  if (mx == c.r) { h = (c.g - c.b) / d * 60.0; }
  else if (mx == c.g) { h = ((c.b - c.r) / d + 2.0) * 60.0; }
  else { return c; }
  let s = d / mx;
  let lit = smoothstep(0.10, 0.20, mx);
  let wr = smoothstep(-48.0, -32.0, h) * (1.0 - smoothstep(20.0, 32.0, h)) * smoothstep(0.28, 0.45, s) * lit;
  let wy = smoothstep(34.0, 42.0, h) * (1.0 - smoothstep(66.0, 76.0, h)) * smoothstep(0.25, 0.40, s) * lit;
  h = mix(h, ${ISLAND_RED_HUE}, wr) - ${ISLAND_GOLD_SHIFT} * wy;
  let s2 = s * (1.0 - ${ISLAND_RED_DESAT} * wr);
  let k = (vec3f(5.0, 3.0, 1.0) + vec3f((h + 360.0) / 60.0)) % vec3f(6.0);
  return vec3f(mx) - mx * s2 * clamp(min(k, vec3f(4.0) - k), vec3f(0.0), vec3f(1.0));
}
fn arcadeIsland(c: vec3f, t: f32) -> vec3f {
  let c0 = islandPalette(c);
  let red = select(0.0, 1.0, c.r > 0.55 && c.g < 0.40 && c.r > c.b * 1.4);
  let core = clamp((min(c.g, c.b) - c.r - 0.15) / 0.35, 0.0, 1.0) * step(0.6, c.b);
  let amp = frame.fx.w * (0.04 + 0.08 * frame.fx.z) * (0.75 + 0.25 * wave1(t * 0.0079577));
  return c0 * (1.0 + amp * max(red, core));
}
@fragment fn fs(in: VOut) -> @location(0) vec4f {
  // 2.4: one texture read per fragment. Through 2.3 every fragment sampled
  // all three textures (atlas, bird, world) and then picked one,
  // so the two full-screen world plates alone paid for ten reads a texel.
  // Branching on the (flat, per-instance) material and reading only the
  // texture it names is bit-identical: every sampler is nearest and no texture
  // has mips, so textureSampleLevel(.., 0) returns exactly what textureSample
  // did -- and it is legal inside non-uniform control flow.
  var c: vec4f;
  if (in.material == 8.0) {
    // A world plate: painted art, lit by the turning moon and the horizon glow.
    var w = textureSampleLevel(world, nearestSampler, in.uvWorld, 0.0);
    if (frame.globe.w > 0.0) { w = vec4f(globeSurface(w.rgb, in.uvWorld * vec2f(${WORLD_TEX_W}.0, ${WORLD_TEX_H}.0), frame.tick.y), w.a); }
    if (frame.fx.x > 0.0) {
      let wp = in.uvWorld * vec2f(${WORLD_TEX_W}.0, ${WORLD_TEX_H}.0);
      w = vec4f(arcadeAmbient(w.rgb, wp, frame.tick.y), w.a);
    }
    c = w;
  } else if ((in.material > 1.5 && in.material < 7.5) || in.material == ${MATERIAL_ARCADE_PLAYER}.0) {
    // 2..7 are the six bird inks, 10 the Arcade jouster player (ink 6).
    let b = textureSampleLevel(bird, nearestSampler, in.uvBird, 0.0);
    let phase = frame.tick.y * ${BLUE_CYCLE_RATE} + in.position.y * ${BLUE_CYCLE_TRAVEL};
    let inkId = select(i32(in.material) - 2, 6, in.material == ${MATERIAL_ARCADE_PLAYER}.0);
    c = vec4f(birdInk(b.rgb, inkId, phase, frame.look.x), b.a);
  } else if (in.material == ${MATERIAL_ARCADE_ISLAND}.0) {
    c = textureSampleLevel(atlas, nearestSampler, in.uv, 0.0);
    if (frame.fx.x > 0.0) { c = vec4f(arcadeIsland(c.rgb, frame.tick.y), c.a); }
  } else {
    c = textureSampleLevel(atlas, nearestSampler, in.uv, 0.0);
  }
  if (c.a < 0.0039215686) { discard; }
  return vec4f(c.rgb * c.a, c.a);
}`;
const BLOOM_GAIN='1.8',BLOOM_BRIGHT_GAIN='1.0',BLOOM_BRIGHT_KNEE=Object.freeze(['0.40','0.90']);
const POST_EXPOSURE='1.8',POST_WHITE='1.6',POST_LOW_RUNG_GLOW='0.35';
// Cyan emitters bloom at 30% of their old strength; gradeArcade sets the final look.
const CYAN_BLOOM='0.3',BLUE_DESAT='0.30',BLUE_DIM='0.12',VIBRANCE='0.94';
const POST_WGSL=`struct Post { viewport: vec2f, scene: vec2f, logical: vec2f, quality: u32, tick: u32, fx: vec4f, music: vec4f }
// The post pass reads exclusively through textureLoad, so it declares no
// sampler. A declared-but-unused sampler is dropped from the 'auto' bind group
// layout, and supplying one anyway invalidates the bind group and every command
// buffer built from it. Binding 1 stays vacant to keep the uniform at 2.
@group(0) @binding(0) var logicalTexture: texture_2d<f32>;
@group(0) @binding(2) var<uniform> post: Post;
@group(0) @binding(3) var glowTex: texture_2d<f32>;
@group(0) @binding(4) var glowSampler: sampler;
struct VOut { @builtin(position) p: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@builtin(vertex_index) i:u32)->VOut { var pos=array<vec2f,3>(vec2f(-1.0,-1.0),vec2f(3.0,-1.0),vec2f(-1.0,3.0));var o:VOut;o.p=vec4f(pos[i],0.0,1.0);o.uv=vec2f((pos[i].x+1.0)*0.5,1.0-(pos[i].y+1.0)*0.5);return o; }
fn emission(c:vec3f,pulse:vec3f)->vec3f {
  let hi=max(c.r,max(c.g,c.b));
  let cyan=select(0.0,hi,c.b>0.34&&c.g>0.27&&c.b>c.r*1.20)*${CYAN_BLOOM};
  // The green ceiling excludes the gold platform caps from red/orange bloom.
  let lava=select(0.0,hi,c.r>0.42&&c.g<0.48&&c.r>c.g*1.25&&c.r>c.b*1.45);
  let violet=select(0.0,hi,c.b>0.35&&c.r>0.35&&c.g<c.r*0.78);
  return c*(cyan*pulse.x+lava*pulse.y+violet*pulse.z);
}
// Arcade grade: cyan and azure are pulled to a softer slate blue (hue 218,
// less saturation, a little less light); everything else only loses a touch
// of vibrance, so golds, reds and whites keep their look.
fn rgb2hsv(c:vec3f)->vec3f {
  let mx=max(c.r,max(c.g,c.b));let d=mx-min(c.r,min(c.g,c.b));
  var h=0.0;
  if(d>0.00001){
    if(mx==c.r){h=(c.g-c.b)/d;if(h<0.0){h+=6.0;}}
    else if(mx==c.g){h=(c.b-c.r)/d+2.0;}
    else{h=(c.r-c.g)/d+4.0;}
  }
  return vec3f(h*60.0,select(0.0,d/mx,mx>0.00001),mx);
}
fn hsv2rgb(q:vec3f)->vec3f {
  let k=(vec3f(5.0,3.0,1.0)+vec3f(q.x/60.0))%vec3f(6.0);
  return vec3f(q.z)-q.z*q.y*clamp(min(k,vec3f(4.0)-k),vec3f(0.0),vec3f(1.0));
}
fn gradeArcade(c:vec3f)->vec3f {
  var q=rgb2hsv(c);
  let w=smoothstep(160.0,178.0,q.x)*(1.0-smoothstep(228.0,245.0,q.x))*smoothstep(0.10,0.25,q.y);
  q.x=mix(q.x,218.0,w*0.85);
  q.y=q.y*(1.0-${BLUE_DESAT}*w)*${VIBRANCE};
  q.z=q.z*(1.0-${BLUE_DIM}*w);
  return hsv2rgb(q);
}
fn glowAt(p:vec2i,pulse:vec3f)->vec3f {
  let dims=vec2i(post.scene);
  let q=clamp(p,vec2i(0),dims-vec2i(1));
  let c=textureLoad(logicalTexture,q,0).rgb;
  return emission(c,pulse);
}
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let dims=vec2i(post.scene);
  let p=clamp(vec2i(floor(i.uv*post.scene)),vec2i(0),dims-vec2i(1));
  var c=textureLoad(logicalTexture,p,0);
  if(post.quality==0u){ let x0=c.rgb*${POST_EXPOSURE}; return vec4f(gradeArcade(clamp(x0*(vec3f(1.0)+x0/(${POST_WHITE}*${POST_WHITE}))/(vec3f(1.0)+x0),vec3f(0.0),vec3f(1.0))),c.a); }
  let t=f32(post.tick&511u)*0.012271846;
  let pulse=vec3f(post.fx.x*(0.84+0.16*sin(t+f32(p.x+p.y)*0.018)),post.fx.y*(0.82+0.18*sin(t*0.73+f32(p.y)*0.025)),post.fx.z*(0.84+0.16*sin(t*1.13)));
  // Multi-radius contour halation: reduced quality keeps the tight four-tap
  // halo; full quality adds mid, diagonal, far and atmospheric bloom fields.
  var glow=(glowAt(p+vec2i(2,0),pulse)+glowAt(p+vec2i(-2,0),pulse)+glowAt(p+vec2i(0,2),pulse)+glowAt(p+vec2i(0,-2),pulse))*0.068;
  // 2.4: the mid, diagonal, far and atmospheric fields were 16 more full-res
  // reads a pixel (21 in all, ~1.1 billion a second at 60 Hz). They are now
  // computed once at quarter resolution (POST_EMIT_WGSL, POST_GLOW_WGSL) and
  // read back here with one filtered sample.
  if(post.quality>1u){ glow+=textureSampleLevel(glowTex,glowSampler,i.uv,0.0).rgb*${BLOOM_GAIN}; }
  glow+=emission(c.rgb,pulse)*(0.10+post.fx.w*0.10);
  if(post.quality<=1u){ glow+=emission(c.rgb,pulse)*${POST_LOW_RUNG_GLOW}; }
  // 3.5: the bloom swells on the music's beats (music.x, 0..1, decays between).
  glow*=1.0+0.6*post.music.x;
  let scale=max(1u,u32(round(post.scene.y/post.logical.y)));
  let scan=select(1.0,0.93,(u32(p.y)%scale)==scale-1u);
  let centered=i.uv*2.0-vec2f(1.0);
  let vignette=1.0-0.10*smoothstep(0.38,1.12,dot(centered,centered));
  let x=(c.rgb+glow)*${POST_EXPOSURE};
  let toned=x*(vec3f(1.0)+x/(${POST_WHITE}*${POST_WHITE}))/(vec3f(1.0)+x);
  return vec4f(gradeArcade(clamp(toned*scan*vignette,vec3f(0.0),vec3f(1.0))),c.a);
}`;
const POST_SHARED_WGSL=POST_WGSL.slice(0,POST_WGSL.indexOf('@fragment'));
const POST_EMIT_WGSL=`${POST_SHARED_WGSL}
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let dims=vec2i(post.scene);
  let base=vec2i(floor(i.p.xy))*4;
  let pc=base+vec2i(2);
  let t=f32(post.tick&511u)*0.012271846;
  let pulse=vec3f(post.fx.x*(0.84+0.16*sin(t+f32(pc.x+pc.y)*0.018)),post.fx.y*(0.82+0.18*sin(t*0.73+f32(pc.y)*0.025)),post.fx.z*(0.84+0.16*sin(t*1.13)));
  var e=vec3f(0.0);
  for(var y=0;y<4;y++){ for(var x=0;x<4;x++){
    let c=textureLoad(logicalTexture,min(base+vec2i(x,y),dims-vec2i(1)),0).rgb;
    // 2.7 bright-pass: beyond the cyan/lava/violet emitters, anything lit --
    // gold rims, stars, sprites, the moon -- blooms too, weighted by how far
    // it rises above the threshold, with the post pulse riding on it.
    let L=dot(c,vec3f(0.2126,0.7152,0.0722));
    e+=emission(c,pulse)+c*smoothstep(${BLOOM_BRIGHT_KNEE[0]},${BLOOM_BRIGHT_KNEE[1]},L)*${BLOOM_BRIGHT_GAIN}*(0.85+0.15*pulse.x);
  } }
  return vec4f(e*0.0625,1.0);
}`;
const POST_GLOW_WGSL=`@group(0) @binding(0) var emitTex: texture_2d<f32>;
@group(0) @binding(1) var emitSampler: sampler;
struct VOut { @builtin(position) p: vec4f, @location(0) uv: vec2f }
@vertex fn vs(@builtin(vertex_index) i:u32)->VOut { var pos=array<vec2f,3>(vec2f(-1.0,-1.0),vec2f(3.0,-1.0),vec2f(-1.0,3.0));var o:VOut;o.p=vec4f(pos[i],0.0,1.0);o.uv=vec2f((pos[i].x+1.0)*0.5,1.0-(pos[i].y+1.0)*0.5);return o; }
fn tap(uv:vec2f,o:vec2f,px:vec2f)->vec3f { return textureSampleLevel(emitTex,emitSampler,uv+o*px,0.0).rgb; }
fn ring(uv:vec2f,r:f32,px:vec2f)->vec3f { return tap(uv,vec2f(r,0.0),px)+tap(uv,vec2f(-r,0.0),px)+tap(uv,vec2f(0.0,r),px)+tap(uv,vec2f(0.0,-r),px); }
@fragment fn fs(i:VOut)->@location(0) vec4f {
  let px=1.0/vec2f(textureDimensions(emitTex));
  let uv=i.p.xy*px;
  var g=ring(uv,1.5,px)*0.028;
  g+=(tap(uv,vec2f(1.25,1.25),px)+tap(uv,vec2f(-1.25,1.25),px)+tap(uv,vec2f(1.25,-1.25),px)+tap(uv,vec2f(-1.25,-1.25),px))*0.022;
  g+=ring(uv,3.75,px)*0.014;
  g+=ring(uv,8.25,px)*0.007;
  // 2.7: a wide atmospheric field, so the whole screen breathes with light.
  g+=(ring(uv,16.0,px)+tap(uv,vec2f(11.3,11.3),px)+tap(uv,vec2f(-11.3,11.3),px)+tap(uv,vec2f(11.3,-11.3),px)+tap(uv,vec2f(-11.3,-11.3),px))*0.0045;
  return vec4f(g,1.0);
}`;
const BLOOM_DIV=4,BLOOM_FORMAT='rgba16float';
class FatalError extends Error{constructor(code,detail){super(code);this.code=code;this.detail=detail;}}
async function createRenderer(canvas,{atlasPixels,birdPixels,onFatal,onRecovered,onLost}){
if (!globalThis.isSecureContext) throw new FatalError('FATAL_SECURE_CONTEXT','Insecure context');
if (!navigator.gpu) throw new FatalError('FATAL_WEBGPU_UNAVAILABLE','navigator.gpu is absent');
const context=canvas.getContext('webgpu');
if (!context) throw new FatalError('FATAL_WEBGPU_CONTEXT','canvas.getContext(webgpu) returned null');
let lossCount=0,device=null,adapter=null,R=null,state='init',canvasFormat=null,quality=2;
let instanceData=new Float32Array((MAX_INSTANCES*INSTANCE_STRIDE)/4);
let instanceCount=0;
let uploadPending=true;
let birdUploadPending=true;
let globeMap=null,globeUploadPending=false;
const globeData=new Float32Array(4);
const fxData=new Float32Array(4);
const lookData=new Float32Array(4);
let worldSurface=null,worldPending=false;
let tickSeen=0;
const overflow={count:0,worst:0,lastTick:-1};
const uniformData=new Float32Array(16);
const tickData=new Float32Array(2);
const postData=new ArrayBuffer(64);
const postF=new Float32Array(postData),postU=new Uint32Array(postData);
async function compile(d,code,label){
const m=d.createShaderModule({code,label});
const info=await m.getCompilationInfo();
const errors=info.messages.filter((x)=>x.type==='error');
if (errors.length) throw new FatalError('FATAL_SHADER',`${label}: ${errors.map((e)=>`${e.lineNum}:${e.linePos} ${e.message}`).join('; ')}`);
return m;
}
async function acquire(){
adapter=await navigator.gpu.requestAdapter({powerPreference:'high-performance'});
if (!adapter) throw new FatalError('FATAL_ADAPTER','requestAdapter returned null');
device=await adapter.requestDevice({requiredFeatures:[],requiredLimits:{}});
if (!device) throw new FatalError('FATAL_DEVICE','requestDevice returned null');
const acquiredDevice=device;
acquiredDevice.addEventListener('uncapturederror',(event)=>{
if (device!==acquiredDevice||state==='destroyed'||state==='fatal') return;
if (typeof event.preventDefault==='function') event.preventDefault();
state='fatal';
const detail=event.error&&event.error.message?event.error.message:'Uncaptured WebGPU validation error';
onFatal&&onFatal(new FatalError('FATAL_GPU_VALIDATION',detail));
});
canvasFormat=navigator.gpu.getPreferredCanvasFormat();
context.configure({device,format:canvasFormat,alphaMode:'premultiplied'});
device.lost.then(async (info)=>{
if (state==='destroyed'||state==='fatal') return;
lossCount+=1;
state='recovering';
onLost&&onLost({lossCount,reason:info.reason,message:info.message});
if (lossCount>1){state='fatal';onFatal&&onFatal(new FatalError('FATAL_GPU_LOST_TWICE',info.message));return;}
try{await acquire();await build();uploadPending=true;birdUploadPending=true;globeUploadPending=!!globeMap;state='ready';onRecovered&&onRecovered({lossCount});}
catch (e){state='fatal';onFatal&&onFatal(e instanceof FatalError?e:new FatalError('FATAL_RECOVERY',String(e)));}
});
}
async function build(){
const d=device;
d.pushErrorScope('validation');
let scopeOpen=true;
try{
const spriteModule=await compile(d,SPRITE_WGSL,'sprite.wgsl');
const postModule=await compile(d,POST_WGSL,'post.wgsl');
const emitModule=await compile(d,POST_EMIT_WGSL,'post-emit.wgsl');
const glowModule=await compile(d,POST_GLOW_WGSL,'post-glow.wgsl');
const logical=d.createTexture({size:[SCENE_W,SCENE_H,1],format:LOGICAL_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_SRC});
const depth=d.createTexture({size:[SCENE_W,SCENE_H,1],format:'depth24plus',usage:GPUTextureUsage.RENDER_ATTACHMENT});
const sampler=d.createSampler({magFilter:'nearest',minFilter:'nearest',mipmapFilter:'nearest'});
const quad=d.createBuffer({size:64,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
d.queue.writeBuffer(quad,0,new Float32Array([0,0,0,0,1,0,1,0,0,1,0,1,1,1,1,1]));
const instances=d.createBuffer({size:INSTANCE_STRIDE*MAX_INSTANCES,usage:GPUBufferUsage.VERTEX|GPUBufferUsage.COPY_DST});
const uniform=d.createBuffer({size:112,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
const postUniform=d.createBuffer({size:64,usage:GPUBufferUsage.UNIFORM|GPUBufferUsage.COPY_DST});
const atlas=d.createTexture({size:[ATLAS_SIZE,ATLAS_SIZE,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const birdTexture=d.createTexture({size:[1536,1152,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const globeTexture=d.createTexture({size:[GLOBE_MAP_W,GLOBE_MAP_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const world=d.createTexture({size:[WORLD_TEX_W,WORLD_TEX_H,1],format:'rgba8unorm',usage:GPUTextureUsage.TEXTURE_BINDING|GPUTextureUsage.COPY_DST});
const linearSampler=d.createSampler({magFilter:'linear',minFilter:'linear'});
const sprite=d.createRenderPipeline({
layout:'auto',
vertex:{module:spriteModule,entryPoint:'vs',buffers:[
{arrayStride:16,attributes:[{shaderLocation:0,offset:0,format:'float32x2'},{shaderLocation:1,offset:8,format:'float32x2'}]},
{arrayStride:INSTANCE_STRIDE,stepMode:'instance',attributes:[{shaderLocation:2,offset:0,format:'float32x4'},{shaderLocation:3,offset:16,format:'float32x4'},{shaderLocation:4,offset:32,format:'float32x2'}]}]},
fragment:{module:spriteModule,entryPoint:'fs',targets:[{format:LOGICAL_FORMAT,blend:{color:{srcFactor:'one',dstFactor:'one-minus-src-alpha',operation:'add'},alpha:{srcFactor:'one',dstFactor:'one-minus-src-alpha',operation:'add'}}}]},
primitive:{topology:'triangle-strip',stripIndexFormat:'uint16'},
depthStencil:{format:'depth24plus',depthWriteEnabled:true,depthCompare:'less-equal'},
});
const post=d.createRenderPipeline({layout:'auto',vertex:{module:postModule,entryPoint:'vs'},fragment:{module:postModule,entryPoint:'fs',targets:[{format:canvasFormat}]},primitive:{topology:'triangle-list'}});
const bloomSize=[Math.ceil(SCENE_W/BLOOM_DIV),Math.ceil(SCENE_H/BLOOM_DIV),1];
const emitTex=d.createTexture({size:bloomSize,format:BLOOM_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING});
const glowTex=d.createTexture({size:bloomSize,format:BLOOM_FORMAT,usage:GPUTextureUsage.RENDER_ATTACHMENT|GPUTextureUsage.TEXTURE_BINDING});
const emitPipe=d.createRenderPipeline({layout:'auto',vertex:{module:emitModule,entryPoint:'vs'},fragment:{module:emitModule,entryPoint:'fs',targets:[{format:BLOOM_FORMAT}]},primitive:{topology:'triangle-list'}});
const glowPipe=d.createRenderPipeline({layout:'auto',vertex:{module:glowModule,entryPoint:'vs'},fragment:{module:glowModule,entryPoint:'fs',targets:[{format:BLOOM_FORMAT}]},primitive:{topology:'triangle-list'}});
const spriteBind=d.createBindGroup({layout:sprite.getBindGroupLayout(0),entries:[{binding:0,resource:{buffer:uniform}},{binding:1,resource:atlas.createView()},{binding:2,resource:sampler},{binding:4,resource:world.createView()},{binding:7,resource:birdTexture.createView()},{binding:9,resource:globeTexture.createView()}]});
const postBind=d.createBindGroup({layout:post.getBindGroupLayout(0),entries:[{binding:0,resource:logical.createView()},{binding:2,resource:{buffer:postUniform}},{binding:3,resource:glowTex.createView()},{binding:4,resource:linearSampler}]});
const emitBind=d.createBindGroup({layout:emitPipe.getBindGroupLayout(0),entries:[{binding:0,resource:logical.createView()},{binding:2,resource:{buffer:postUniform}}]});
const glowBind=d.createBindGroup({layout:glowPipe.getBindGroupLayout(0),entries:[{binding:0,resource:emitTex.createView()},{binding:1,resource:linearSampler}]});
const validation=await d.popErrorScope();
scopeOpen=false;
if (validation) throw new FatalError('FATAL_GPU_VALIDATION',`renderer build: ${validation.message}`);
uniformData.set([LOGICAL_W,LOGICAL_H,1/ATLAS_SIZE,1/ATLAS_SIZE,0,0,1/WORLD_TEX_W,1/WORLD_TEX_H,1/1536,1/1152,0,0]);
d.queue.writeBuffer(uniform,0,uniformData);
d.queue.writeBuffer(uniform,64,globeData);
d.queue.writeBuffer(uniform,80,fxData);
d.queue.writeBuffer(uniform,96,lookData);
R={logical,depth,sampler,linearSampler,quad,instances,uniform,postUniform,atlas,birdTexture,globeTexture,world,sprite,post,spriteBind,postBind,emitTex,glowTex,emitPipe,glowPipe,emitBind,glowBind};
worldPending=!!worldSurface;
}catch (error){
if (scopeOpen) await d.popErrorScope().catch(()=>null);
throw error;
}
}
function uploadAtlas(pixels,x=0,y=0,w=ATLAS_SIZE,h=ATLAS_SIZE){
if (!device||!R) return;
device.queue.writeTexture({texture:R.atlas,origin:[x,y,0]},pixels,{bytesPerRow:w*4,rowsPerImage:h},[w,h,1]);
}
function uploadWorld(surface){
if (!surface||surface.w!==WORLD_TEX_W||surface.h!==WORLD_TEX_H) return false;
worldSurface=surface;worldPending=true;
return true;
}
function resize(cssW,cssH){
const fit=Math.min(cssW/LOGICAL_W,cssH/LOGICAL_H);
const displayW=Math.max(2,Math.floor(LOGICAL_W*fit/2)*2);
const displayH=displayW*LOGICAL_H/LOGICAL_W;
canvas.style.width=`${displayW}px`;
canvas.style.height=`${displayH}px`;
canvas.width=SCENE_W;
canvas.height=SCENE_H;
return fit;
}
function setInstances(list){
if (list.length>MAX_INSTANCES){
overflow.count+=1;
overflow.worst=Math.max(overflow.worst,list.length);
overflow.lastTick=tickSeen;
}
instanceCount=Math.min(list.length,MAX_INSTANCES);
for (let i=0;i<instanceCount;i++){
const o=i*10,it=list[i];
instanceData[o]=it.x;instanceData[o+1]=it.y;instanceData[o+2]=it.w;instanceData[o+3]=it.h;
if (it.sw>=0){instanceData[o+4]=it.sx;instanceData[o+6]=it.sw>1?it.sw-1:0;}
else{instanceData[o+4]=it.sx-1;instanceData[o+6]=-(-it.sw-1);}
instanceData[o+5]=it.sy;instanceData[o+7]=it.sh>1?it.sh-1:0;
instanceData[o+8]=it.z;instanceData[o+9]=it.flags||0;
}
}
function setGlobe(map,params=null){
if (map&&(map.w!==GLOBE_MAP_W||map.h!==GLOBE_MAP_H||!params)) return false;
if (map&&map!==globeMap){globeMap=map;globeUploadPending=true;}
globeData.set(map?params:[0,0,1,0]);
if (device&&R) device.queue.writeBuffer(R.uniform,64,globeData);
return true;
}
function setArcadeFx(horizon=null){fxData[0]=horizon===null?0:1;fxData[1]=horizon===null?0:horizon;return true;}
function setBird(pixels,jouster=false){
if (!pixels||pixels.w!==1536||pixels.h!==1152) return false;
birdPixels=pixels;birdUploadPending=true;
lookData[0]=jouster?1:0;
if (device&&R) device.queue.writeBuffer(R.uniform,96,lookData);
return true;
}
function frame(tick,effects={},clear=[0.027,0.075,0.122,1]){
if (state!=='ready'||!device||!R) return false;
tickSeen=tick;
const d=device;
if (uploadPending){uploadAtlas(atlasPixels.p);uploadPending=false;}
if (birdUploadPending){d.queue.writeTexture({texture:R.birdTexture},birdPixels.p,{bytesPerRow:1536*4,rowsPerImage:1152},[1536,1152,1]);birdUploadPending=false;}
if (globeUploadPending&&globeMap){d.queue.writeTexture({texture:R.globeTexture},globeMap.p,{bytesPerRow:GLOBE_MAP_W*4,rowsPerImage:GLOBE_MAP_H},[GLOBE_MAP_W,GLOBE_MAP_H,1]);globeUploadPending=false;}
if (worldPending&&worldSurface){
d.queue.writeTexture({texture:R.world},worldSurface.p,{bytesPerRow:WORLD_TEX_W*4,rowsPerImage:WORLD_TEX_H},[WORLD_TEX_W,WORLD_TEX_H,1]);

worldPending=false;
}
d.queue.writeBuffer(R.instances,0,instanceData,0,instanceCount*10);
tickData[0]=tick;
tickData[1]=Number.isFinite(effects.ambientTick)?effects.ambientTick:tick;
d.queue.writeBuffer(R.uniform,48,tickData);
fxData[2]=Number.isFinite(effects.beat)?Math.max(0,Math.min(1,effects.beat)):0;
fxData[3]=effects.motion===false?0:1;
d.queue.writeBuffer(R.uniform,80,fxData);
lookData[1]=Number.isFinite(effects.moonPhase)?effects.moonPhase%1:(tick*globeData[3]/(2*Math.PI))%1;
d.queue.writeBuffer(R.uniform,96,lookData);
postF[0]=canvas.width;postF[1]=canvas.height;postF[2]=SCENE_W;postF[3]=SCENE_H;postF[4]=LOGICAL_W;postF[5]=LOGICAL_H;postU[6]=quality;postU[7]=(Number.isFinite(effects.ambientTick)?effects.ambientTick:tick)>>>0;
postF[8]=Number.isFinite(effects.cyan)?effects.cyan:1;
postF[9]=Number.isFinite(effects.lava)?effects.lava:1;
postF[10]=Number.isFinite(effects.violet)?effects.violet:1;
postF[11]=Number.isFinite(effects.impact)?effects.impact:0;
postF[12]=Number.isFinite(effects.bloomBeat)?Math.max(0,Math.min(1,effects.bloomBeat)):0;
d.queue.writeBuffer(R.postUniform,0,postData);
const enc=d.createCommandEncoder();
const pass=enc.beginRenderPass({colorAttachments:[{view:R.logical.createView(),clearValue:{r:clear[0],g:clear[1],b:clear[2],a:1},loadOp:'clear',storeOp:'store'}],depthStencilAttachment:{view:R.depth.createView(),depthClearValue:1,depthLoadOp:'clear',depthStoreOp:'store'}});
pass.setPipeline(R.sprite);pass.setBindGroup(0,R.spriteBind);pass.setVertexBuffer(0,R.quad);pass.setVertexBuffer(1,R.instances);
if (instanceCount>0) pass.draw(4,instanceCount);
pass.end();
if (quality>1){
const e=enc.beginRenderPass({colorAttachments:[{view:R.emitTex.createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
e.setPipeline(R.emitPipe);e.setBindGroup(0,R.emitBind);e.draw(3,1);e.end();
const g=enc.beginRenderPass({colorAttachments:[{view:R.glowTex.createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
g.setPipeline(R.glowPipe);g.setBindGroup(0,R.glowBind);g.draw(3,1);g.end();
}
const post=enc.beginRenderPass({colorAttachments:[{view:context.getCurrentTexture().createView(),clearValue:{r:0,g:0,b:0,a:1},loadOp:'clear',storeOp:'store'}]});
post.setPipeline(R.post);post.setBindGroup(0,R.postBind);post.draw(3,1);post.end();
d.queue.submit([enc.finish()]);
return true;
}
async function readScene3x(){
if (state!=='ready') return null;
const d=device;
const bytesPerRow=SCENE_W*4;
const buf=d.createBuffer({size:bytesPerRow*SCENE_H,usage:GPUBufferUsage.COPY_DST|GPUBufferUsage.MAP_READ});
const enc=d.createCommandEncoder();
enc.copyTextureToBuffer({texture:R.logical},{buffer:buf,bytesPerRow,rowsPerImage:SCENE_H},[SCENE_W,SCENE_H,1]);
d.queue.submit([enc.finish()]);
await buf.mapAsync(GPUMapMode.READ);
const hi=new Uint8Array(buf.getMappedRange());
const out=hi.slice(0,SCENE_W*SCENE_H*4);
buf.unmap();buf.destroy();
return out;
}
async function readLogical(){
const hi=await readScene3x();
if (!hi) return null;
const out=new Uint8Array(LOGICAL_W*LOGICAL_H*4);
for (let y=0;y<LOGICAL_H;y++) for (let x=0;x<LOGICAL_W;x++){
const si=((y*SCENE_SCALE+1)*SCENE_W+x*SCENE_SCALE+1)*4;
out.set(hi.subarray(si,si+4),(y*LOGICAL_W+x)*4);
}
return out;
}
await acquire();
await build();
state='ready';
return{
get state(){return state;},get lossCount(){return lossCount;},get device(){return device;},get quality(){return quality;},
get instanceOverflow(){return{...overflow,cap:MAX_INSTANCES};},
get instanceCount(){return instanceCount;},
setQuality(q){quality=Math.max(0,Math.min(2,q|0));},
resize,setInstances,frame,readLogical,readScene3x,uploadAtlas,setBird,setGlobe,setArcadeFx,uploadWorld,
simulateDeviceLoss(){if (device) device.destroy();},get worldReady(){return!!worldSurface;},
markAtlasDirty(){uploadPending=true;},markWorldDirty(){worldPending=!!worldSurface;},
simulateLoss(){if (device) device.destroy();},
destroy(){state='destroyed';if (device) device.destroy();},
};
}
export{createRenderer,FatalError,ATLAS_SIZE,WORLD_SCALE,WORLD_PLATE_W,WORLD_PLATE_H,WORLD_TEX_W,WORLD_TEX_H,MATERIAL_WORLD,MATERIAL_ARCADE_PLAYER,MATERIAL_ARCADE_ISLAND,GLOBE_MAP_W,GLOBE_MAP_H};
