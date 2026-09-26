// STRUTHIO ARCADE · the bird ink palettes (player and rival classes) and their shader code.
const BIRD_INKS=Object.freeze([
{shadow:[6,34,48],mid:[14,132,166],light:[60,216,238],highlight:[214,250,255],body:[238,244,250],bodyMix:0.70,horn:[246,206,92],hornMix:1.00,hornRamp:0},
{shadow:[28,14,9],mid:[104,62,32],light:[158,96,44],highlight:[214,162,110],body:[164,134,104],bodyMix:0.62,horn:[192,54,40],hornMix:0.95,hornRamp:0},
{shadow:[52,12,10],mid:[188,28,28],light:[232,70,44],highlight:[252,168,140],body:[154,112,96],bodyMix:0.62,horn:[240,142,40],hornMix:0.95,hornRamp:0},
{shadow:[68,14,10],mid:[224,104,16],light:[255,162,40],highlight:[255,220,156],body:[182,144,108],bodyMix:0.62,horn:[120,78,44],hornMix:0.95,hornRamp:0},
{shadow:[58,22,10],mid:[192,148,26],light:[252,216,74],highlight:[255,246,196],body:[232,206,146],bodyMix:0.84,horn:[214,74,34],hornMix:0.90,hornRamp:0},
{shadow:[96,44,12],mid:[230,168,52],light:[255,226,110],highlight:[255,252,224],body:[255,240,190],bodyMix:0.92,horn:[236,110,40],hornMix:0.95,hornRamp:0},
{shadow:[34,18,8],mid:[128,74,28],light:[226,168,58],highlight:[110,236,255],body:[250,204,80],bodyMix:0.96,horn:[214,44,36],hornMix:1.00,hornRamp:0},
]);
const ARCADE_PLAYER_GLOW=[110,245,255];
const PLAYER_BLUES=Object.freeze([
{mid:[14,132,166],light:[60,216,238]},
{mid:[22,96,190],light:[86,170,255]},
{mid:[58,74,196],light:[130,146,255]},
]);
const BLUE_CYCLE_RATE=1/540;
const BLUE_CYCLE_TRAVEL=1/1400;
const JOUSTER_LOOK=Object.freeze([
{plume:[150,206,226],rim:[120,246,255]},
{plume:[150,106,66],rim:[255,146,56]},
{plume:[170,40,44],rim:[255,86,70]},
{plume:[112,66,172],rim:[224,128,255]},
{plume:[190,136,36],rim:[255,226,120]},
{plume:[190,136,36],rim:[255,226,120]},
{plume:[176,214,228],rim:[120,246,255]},
]);
const v3=(rgb)=>`vec3f(${rgb.map((n)=>`${n}.0`).join(',')})/255.0`;
const inkLiteral=(k)=>`Ink(${v3(k.shadow)},${v3(k.mid)},${v3(k.light)},${v3(k.highlight)},${v3(k.body)},${k.bodyMix.toFixed(2)},${v3(k.horn)},${k.hornMix.toFixed(2)},${k.hornRamp},${v3(JOUSTER_LOOK[BIRD_INKS.indexOf(k)].plume)},${v3(JOUSTER_LOOK[BIRD_INKS.indexOf(k)].rim)})`;
const WAR_BIRD_PALETTE_WGSL=`
struct Ink { shadow: vec3f, mid: vec3f, light: vec3f, highlight: vec3f, body: vec3f, bodyMix: f32, horn: vec3f, hornMix: f32, hornRamp: i32, plume: vec3f, rim: vec3f }
fn birdInkFor(classId:i32) -> Ink {
  var k = ${inkLiteral(BIRD_INKS[0])};
  ${BIRD_INKS.slice(1).map((k,i)=>`if(classId==${i+1}) { k = ${inkLiteral(k)}; }`).join('\n  ')}
  return k;
}
// Three stops on a seamless loop. Rendering only: the phase comes from the
// render tick, which no simulation reads.
fn cycle3(a:vec3f, b:vec3f, c:vec3f, phase:f32) -> vec3f {
  let u = fract(phase) * 3.0;
  let i = floor(u);
  let f = smoothstep(0.0, 1.0, u - i);
  var p = a; var q = b;
  if (i > 1.5) { p = c; q = a; }
  else if (i > 0.5) { p = b; q = c; }
  return mix(p, q, f);
}
fn birdRamp(k:Ink, t:f32) -> vec3f {
  let lowc = mix(k.shadow, k.mid, smoothstep(0.06, 0.5, t));
  let highc = mix(k.mid, k.light, smoothstep(0.5, 0.95, t));
  return select(highc, lowc, t < 0.5);
}
fn birdInk(c:vec3f, classId:i32, phase:f32, jouster:f32) -> vec3f {
  var k = birdInkFor(classId);
  if (classId == 0) {
    k.mid = cycle3(${v3(PLAYER_BLUES[0].mid)},${v3(PLAYER_BLUES[1].mid)},${v3(PLAYER_BLUES[2].mid)}, phase);
    k.light = cycle3(${v3(PLAYER_BLUES[0].light)},${v3(PLAYER_BLUES[1].light)},${v3(PLAYER_BLUES[2].light)}, phase);
  }
  let mx = max(c.r, max(c.g, c.b));
  let d = mx - min(c.r, min(c.g, c.b));
  let sat = select(0.0, d / max(mx, 0.0001), mx > 0.0001);
  let dd = max(d, 0.00001);
  var h = ((c.r - c.g) / dd + 4.0) * 60.0;
  if (mx == c.g) { h = ((c.b - c.r) / dd + 2.0) * 60.0; }
  if (mx == c.r) { h = ((c.g - c.b) / dd) * 60.0; }
  if (h > 180.0) { h = h - 360.0; }
  let wF = (1.0 - smoothstep(14.0, 26.0, abs(h))) * smoothstep(0.30, 0.55, sat);
  let hornHue = smoothstep(16.0, 24.0, h) * (1.0 - smoothstep(58.0, 70.0, h));
  let wH = hornHue * max(smoothstep(0.40, 0.55, c.r - c.b), smoothstep(0.24, 0.34, c.g - c.b)) * (1.0 - wF);
  let bodyHue = smoothstep(12.0, 20.0, h) * (1.0 - smoothstep(62.0, 72.0, h));
  let wB = smoothstep(0.06, 0.14, sat) * smoothstep(0.08, 0.16, mx) * bodyHue * (1.0 - wF) * (1.0 - wH);
  let L = dot(c, vec3f(0.2126, 0.7152, 0.0722));
  var o = c;
  if (k.bodyMix > 0.0) { o = mix(o, clamp(k.body * (L / 0.80), vec3f(0.0), vec3f(1.0)), wB * k.bodyMix); }
  if (k.hornRamp == 1) { o = mix(o, birdRamp(k, mx), wH); }
  else if (k.hornMix > 0.0) { o = mix(o, clamp(k.horn * (L / 0.55) * 0.85, vec3f(0.0), vec3f(1.0)), wH * k.hornMix); }
  let feather = mix(birdRamp(k, mx), k.highlight, smoothstep(0.2, 0.6, 1.0 - sat) * smoothstep(0.6, 1.0, mx));
  var res = mix(o, feather, wF);
  if (classId == 6) { res = mix(res, ${v3(ARCADE_PLAYER_GLOW)}, wF * smoothstep(0.985, 0.998, mx) * smoothstep(0.72, 0.80, sat)); }
  // 3.4 jouster marks (markJousterRims): plumage (0,0,v) takes the class
  // plume at shade v, the outer outline (0,1,0) the class rim.
  let pl = jouster * step(c.r + c.g, 0.002) * step(0.1, c.b);
  let rm = jouster * step(0.9, c.g) * step(c.r, 0.1) * step(c.b, 0.1);
  res = mix(mix(res, k.plume * (0.40 + 0.95 * c.b), pl), k.rim, rm);
  return clamp(res, vec3f(0.0), vec3f(1.0));
}
`;
export{WAR_BIRD_PALETTE_WGSL,BLUE_CYCLE_RATE,BLUE_CYCLE_TRAVEL};
