/*
 STRUTHIO ESP32-S3 HANDHELD — A1.5 (Build Manual 1.5 hardware lock)
 R.A. Peddycoart
 Units: mm. x right, y up, z from the front face back (into the handheld).

 Derived from A0.8.4 (cad/a1/STRUTHIO084.scad, kept as the historical baseline).
 Everything above the controls is unchanged: crown, screen opening, lens land,
 board datums, top screws, rear identity mark.

 A1.5 LOCKS (Build Manual 1.5)
 -----------------------------
 - Controls: STRUTHIO-CM1 one-piece conductive-silicone mat over STRUTHIO-CP1
   four-contact ENIG PCB. LEFT / RIGHT WING keys (~28 x 18.5 mm faces) and a
   44 x 9 mm two-end DART rocker below them; DART contacts 24.0 mm apart.
   Wing travel 1.5 mm / 125 g, rocker-end travel 1.3 mm / 150 g, 6 mm pills.
 - Inputs: GPIO17 LEFT, GPIO18 RIGHT, GPIO21 DART LEFT, GPIO38 DART RIGHT, GND.
 - Speaker: PUI AS02808MR-R, 28 mm, 5.2 mm high; pocket >= 29.2 dia x >= 5.8;
   gasketed front baffle, isolated rear cavity.
 - Battery: THOR-503450 1000 mAh, cavity >= 36 x 54 x 6.2.
 - Power: E-Switch 500SSP1S1M7QEA in BAT+ (body 12.7 x 6.6 x 6.71, actuator
   4.72, travel 2.16; pin geometry: CONFIRM against the E-Switch drawing).

 A1.5 GEOMETRY DECISIONS (2026-10-02)
 ------------------------------------
 - Owner decision: keep every locked control size and grow the body at the
   bottom only. The rocker below the wings, plus the speaker clearing the
   board's USB-C plug, needs 6.0 mm (BOTTOM_EXT): centre line y +64 .. -70.
 - Owner decision (later the same day): "sleek and stylish, not a block".
   The shell is sculpted (SHELL_STYLE, see the parameters): a 1991-handheld
   silhouette with concave top and bottom, a waist and flared hips, a
   rounded front edge and a pillow back. 88 x 137.4 x 23 mm overall (the
   corners lift 2.0 / drop 1.8 beyond the unchanged centre line). The four
   screws move in to x +-35 and now actually clamp: back-post counterbores
   into front-shell bosses. Front and back STLs come from build_shell.py.
 - The wings sit as high as the board allows (their silicone skirts end
   1 mm below the board's lower edge); the rocker is centred below them.
 - The speaker is mounted behind CP1 (CP1 + the printed carrier are the rigid
   front baffle), gasketed front and back, firing through a 13 mm window in
   CP1 and the mat into the grille between the wings. Its rear cavity is a
   closed tube up into the speaker blister.
 - USB-C: the board connector position is NOT confirmed. Assumed bottom
   centre (as A0): a RIGHT-ANGLE plug turns +x into a channel at x 16.5..22
   and a panel jack in the bottom wall at x = +19.25 (USB_*). If the board's
   connector is elsewhere, move USB_PLUG_* and re-run check_a15.py.
 - Power switch: left side wall at y = 12 (the right side keeps the A0
   service slot for BOOT / RESET).

 Stack in the control zone (z):
   0.0 .. 3.0   front shell; key holes = key outline + 0.30
   -1.8 / -1.5  wing / rocker key tops (proud)
   3.0 .. 3.6   key flanges (preloaded against the shell)
   3.0 .. 4.6   printed carrier (part of the front shell): seals the speaker
                window, holds the mat; key wells = outline + skirt
   4.6 .. 5.6   CM1 web on CP1
   5.6 .. 6.6   CP1 (1.0 mm FR-4); pill faces rest 1.5 (wing) / 1.3 (rocker) above it
   6.6 .. 7.2   front speaker gasket; 7.2 .. 12.4 PUI speaker; 12.4 .. 12.9 rear gasket
*/

$fn = 72;
part = "assembly"; // assembly, design_front, front, back, mat, cp1_outline, mat_outline, reference, sticker, front_fit_coupon, side_section

// ============================================================================
// LOCKED A0 DATUMS — change only after physical evidence
// ============================================================================
BODY_W = 88;
BODY_H = 128;
BODY_D = 25; // legacy A0 maximum envelope, retained as a comparison datum
BOTTOM_EXT = 6.0;          // A1.5: body grows at the bottom only (88 x 134)
BODY_BOTTOM = -BODY_H/2 - BOTTOM_EXT;   // -70
FRONT_T = 3.0;
BACK_D = BODY_D - FRONT_T; // legacy only
FRONT_SCREW_THROUGH = false; // same screw datums, clean heritage face by default
WALL = 2.4;
BACK_WALL = 2.2;

// A0.8 preserves the v0.7 hardware-following thickness map.
BASE_TOTAL_D = 18.6;       // board-only regions: front face to rear skin
BATTERY_TOTAL_D = 23.0;    // current 6.2 mm battery reference sets the max
SPEAKER_TOTAL_D = 22.5;    // current ~5 mm speaker reference
BASE_INNER_TOP_Z = BASE_TOTAL_D - BACK_WALL;
SUPPORT_TOP_Z = BASE_INNER_TOP_Z + 0.55;
FIT = 0.35;

// Waveshare 3.5B bare assembly, rotated portrait.
BOARD_W = 61.00;
BOARD_H = 92.44;
BOARD_D = 11.50;
BOARD_X = 0;
BOARD_TOP_GAP = 4.0;
BOARD_Y = BODY_H/2 - BOARD_TOP_GAP - BOARD_H/2; // 13.78
BOARD_Z_FRONT = FRONT_T + 0.35;

LCD_W = 48.96;
LCD_H = 73.44;
LCD_X = BOARD_X;
LCD_Y = BOARD_Y;
LCD_BEZEL_OVERLAP = 0.55;
LCD_OPEN_W = LCD_W - 2*LCD_BEZEL_OVERLAP;
LCD_OPEN_H = LCD_H - 2*LCD_BEZEL_OVERLAP;

// A1.5 wing key centres (A0.8.4: +-21.5, -47.5)
BTN_Y = -46.0;
BTN_X = 24.0;

SWITCH_BODY = 12.5;
SWITCH_PCB = 18.0;
SWITCH_PCB_T = 1.6;
SWITCH_PCB_PLANE_Z = 13.7; // tune with shim only after physical cap/switch measurement
SWITCH_H = 7.3;            // B3F-4050 overall height including the projected plunger
SWITCH_TRAVEL = 0.25;      // B3F operating travel

SPKR_D = 28.0;   // PUI AS02808MR-R
SPKR_T = 5.2;
SPKR_Y = -52.6;  // A1.5: behind CP1, clear of the board USB-C plug keep-out
SPKR_X = 0;

BAT_W = 36.0;
BAT_H = 54.0;   // THOR-503450 with PCM
BAT_T = 6.2;
BAT_Y = 13.5;

SCREW_X = 35.0;          // A1.5 sculpted: in from 37 so the counterbores stay on the back face
SCREW_Y = 55.5;
SCREW_Y_BOT = -63.0;     // A1.5 lower pair, below the wing skirts
SCREW_D = 2.2;
POST_OD = 6.0;

// ============================================================================
// TUNABLE INDUSTRIAL-DESIGN PARAMETERS — edit these first
// ============================================================================
// Outer silhouette: 1990s dedicated-handheld taper/flare language while keeping
// the exact 88 x 128 mm A0 bounding box. The construction uses local hull
// segments instead of one global hull so the waist remains visible.
// Rounded crown uses a superellipse rather than a hull between equal-height
// circles. This removes the 61 mm dead-flat top edge in v0.8 while keeping
// the same y=64 maximum and ample carrier clearance.
TOP_CROWN_RX = 42.0;
TOP_CROWN_RY = 12.0;
TOP_CROWN_Y = 52.0;
TOP_CROWN_N = 3.2;
UPPER_CENTER_X = 34.0;
UPPER_CENTER_Y = 25.0;
UPPER_R = 7.5;
WAIST_CENTER_X = 33.5;
WAIST_CENTER_Y = -12.0;
WAIST_R = 6.5;
LOWER_CENTER_X = 35.5;
LOWER_CENTER_Y = -45.0;   // A1.5 (A0.8.4: -42)
LOWER_R = 7.5;
FOOT_CENTER_X = 34.0;
FOOT_CENTER_Y = -60.0;    // A1.5 (A0.8.4: -54): feet reach BODY_BOTTOM
FOOT_R = 10.0;

// Shallow concave bottom arch, retained as a heritage cue but deliberately
// reduced from v0.8.1. The prior 4 mm centre rise plus 23.9 mm button holes
// produced weak lower ligaments. v0.8.2 keeps a broad structural bottom rail.
BOTTOM_ARCH_Y = -72.2; // shallower 1.8 mm centre rise; v0.8.1 rose ~4 mm and thinned the lower rail
BOTTOM_ARCH_RX = 31.0; // narrower arch preserves broad structural feet and lower bridge
BOTTOM_ARCH_RY = 10.0;
BOTTOM_ARCH = false;    // A1.5: flat lower rail
BOTTOM_EDGE_CENTER_Y = BOTTOM_ARCH ? BOTTOM_ARCH_Y + BOTTOM_ARCH_RY : BODY_BOTTOM;

// A1.5 SCULPTED SHELL (owner, 2026-10-02: "sleek and stylish, not a block").
// Front view: a 1991 dedicated-handheld silhouette: concave top and bottom
// with lifted corners, broad shoulders around the screen, a waist below it
// and flared hips around the wings. Side view: the front edge is rounded,
// the side wall runs straight to SHELL_ZS and then rolls into a pillow back
// (a quarter ellipse, SHELL_RB across x SHELL_ZB-SHELL_ZS deep). The outer
// and inner surfaces are the same core outline grown by a revolved profile
// (minkowski), so the wall stays ~WALL thick through the roll.
// "a0" restores the A0.8.4 slab (vertical walls, flat back + blisters).
SHELL_STYLE = "sleek";
TOP_LIFT = 2.0;       // concave top: corners rise this far above the centre (y +64)
BOTTOM_DROP = 1.8;    // concave bottom: corners drop this far below the centre (y -70)
SHELL_RF = 1.6;       // front edge radius
SHELL_ZS = 9.0;       // side wall straight from SHELL_RF to here ...
SHELL_ZB = 23.0;      // ... then rolls to the back face (= BATTERY_TOTAL_D)
SHELL_RB = 12.0;      // how far the roll moves in; also the smallest corner radius in plan
// Catmull-Rom control points, right half, top centre clockwise to bottom centre
function sleek_half() = [
  [0, 64.0], [16, 64.0+0.25*TOP_LIFT], [29, 64.0+0.85*TOP_LIFT], [37.2, 64.0+TOP_LIFT-0.2], [41.4, 61.2],
  [42.6, 52], [42.3, 38], [41.8, 26], [41.6, 14], [41.4, 4], [40.0, -7], [37.8, -16], [38.6, -26],
  [41.2, -36], [43.6, -46], [44.0, -56], [43.3, -64.5], [40.2, -69.0-BOTTOM_DROP], [33, -70.0-BOTTOM_DROP],
  [20, -70.0-0.35*BOTTOM_DROP], [0, -70.0]];
function cr_pt(p0,p1,p2,p3,t) = 0.5*((2*p1) + (-p0+p2)*t + (2*p0-5*p1+4*p2-p3)*t*t + (-p0+3*p1-3*p2+p3)*t*t*t);
function sleek_ctrl() = let(h=sleek_half(), n=len(h)) concat(h, [for(i=[n-2:-1:1]) [-h[i][0], h[i][1]]]);
function sleek_pts(k=12) = let(c=sleek_ctrl(), n=len(c))
  [for(i=[0:n-1], j=[0:k-1]) cr_pt(c[(i-1+n)%n], c[i], c[(i+1)%n], c[(i+2)%n], j/k)];
module sleek_raw2d(){ polygon(sleek_pts()); }
// side profiles (r, z) revolved around the core outline
function shell_prof_out() = concat(
  [for(i=[0:8]) let(a=90*i/8) [SHELL_RB-SHELL_RF+SHELL_RF*sin(a), SHELL_RF-SHELL_RF*cos(a)]],
  [for(i=[0:24]) let(a=90*i/24) [SHELL_RB*cos(a), SHELL_ZS+(SHELL_ZB-SHELL_ZS)*sin(a)]],
  [[0,0]]);
function shell_prof_in() = let(rw=SHELL_RB-WALL, zt=SHELL_ZB-BACK_WALL) concat(
  [[rw, FRONT_T-1.0]],
  [for(i=[0:24]) let(a=90*i/24) [rw*cos(a), SHELL_ZS+(zt-SHELL_ZS)*sin(a)]],
  [[0, FRONT_T-1.0]]);
CEIL_Z = SHELL_ZB - BACK_WALL;   // 20.8: inner back face over the flat part of the back
// screws: four rear M2 thread-forming screws through counterbored posts in the
// back shell into bosses on the front shell
JOIN_Z = 8.0;          // front bosses end here; back posts start 0.1 above
FRONT_BOSS_OD = 5.0;
PILOT_D = 1.7;         // M2 thread-forming into PETG / ASA (confirm with the screw maker's chart)
CLEAR_D = 2.4;
CBORE_D = 4.2;         // M2 socket head (3.8 mm)
SCREW_POST_OD = 7.2;   // back posts: ~1.5 mm round the counterbore
CBORE_Z = 13.0;        // head seat: M2 x 10 reaches z 3.0, 5 mm into the boss

// Screen lens / bezel cosmetics. Opening itself remains locked above.
LENS_LAND_W = 56.5;
LENS_LAND_H = 81.0;
LENS_LAND_R = 5.4;
LENS_RECESS_D = 0.55;

// Lower sticker/control-art registration panel. Unlike v0.7, the molded shell
// remains visible around the LCD and the printed art starts below the display,
// matching the construction language of the user's heritage references.
STICKER_TOP = -27.2;      // A0.8.4: 0.5 mm below the lens land (-26.72); A0.8.2 -24.2 overlapped it
STICKER_BOTTOM = -68.0;   // A1.5: the art runs below the rocker   // A0.8.4: wings sit fully inside the art; body2d(-4) clips it to the bottom contour
STICKER_TOP_W = 82.0;     // A1.5: wings at +-24 need a wider art panel     // A0.8.4: wider so the wing tips stay inside the art (A0.8.2: 69)
STICKER_BOTTOM_W = 86.0;  // A1.5 (clipped by the body outline)  // A0.8.4 (A0.8.2: 74); body2d(-4) still bounds it
STICKER_R = 2.2;
STICKER_RECESS_D = 0.28;

// Cosmetic shell/button colors used only by OpenSCAD previews/renders.
// STRUTHIO palette (rules.mjs): navy #102838, gold #E2A93F, void #07131F, ring #20C4D7.
SHELL_RGB = [16,40,56]/255;         // navy; STL has no color
BUTTON_RGB = [226,169,63]/255;      // gold
PANEL_RGB = [7,19,31]/255;           // void
RING_RGB = [32,196,215]/255;          // ring cyan (lens-land accent in previews)

// Large two-button dedicated-handheld controls. Electrical centers stay locked.
// Claude can set BUTTON_STYLE=\"wing\" without changing the switch datums.
BUTTON_STYLE = "wing";               // "wing" (STRUTHIO, A0.8.4) or "round" (A0.8.2/3)
BTN_ROUND_D = 23.0;
BTN_FACE_W = 28.0;                    // wing face (A0.8.2 fallback: 32)
BTN_FACE_H = 18.5;                    // wing face
BTN_CLEAR = 0.45;
BTN_OPEN_SCALE_X = 1.0;
BTN_OPEN_SCALE_Y = 1.0;
BTN_FLANGE = 1.0;
BTN_FLANGE_T = 1.2;
// v0.8 placed the oversize capture flange inside the 3 mm front shell, which
// geometrically intersected the shell. v0.8.1 keeps the switch contact tip at
// the same installed z=7.3 mm but puts the flange behind the shell and gives
// the player-facing cap a real 1.8 mm proud height.
BTN_PROTRUSION = 1.8;
BTN_CAPTURE_GAP = 0.20;
BTN_PRETRAVEL_GAP = 0.10;   // A0.8.3: free gap between stem tip and plunger at rest
BTN_CONTACT_Z = SWITCH_PCB_PLANE_Z - SWITCH_H - BTN_PRETRAVEL_GAP; // 6.30 (A0.8.2: 7.30, 0.9 mm into the switch)
BTN_NECK_H = BTN_PROTRUSION + FRONT_T + BTN_CAPTURE_GAP;
BTN_STEM_Z = (BTN_CONTACT_Z + BTN_PROTRUSION) - (BTN_NECK_H + BTN_FLANGE_T);
BTN_STEM_W = 5.2;
BTN_STEM_H = 5.2;
BUTTON_GROOVES = true;                // feather grooves on the wings
BUTTON_GROOVE_D = 0.45;

// Front speaker grille remains subtle and between the controls.
GRILL_W = 9.0;
GRILL_SLOT_H = 0.90; // thicker webs between slots
GRILL_PITCH = 3.20;
GRILL_COUNT = 4;

// Lower-front strength package. These ribs live BEHIND the cosmetic face and
// do not move the locked switch centres or active display. The button collars
// clear the 25 mm capture flanges while tying each opening into a broad lower
// backer plate.
LOWER_BACKER_T = 1.80;
LOWER_BACKER_TOP = -34.0;
LOWER_BACKER_BOTTOM = -62.0;
LOWER_BACKER_SIDE_INSET = 3.2;
BTN_COLLAR_OD = 31.0;                // round-style reference (A0.8.3)
BTN_COLLAR_ID = 26.4;                // round-style reference (A0.8.3)
BTN_COLLAR_CLEAR = 0.70;             // hole beyond the capture flange (26.4 = 23 + 2*(1.0+0.7))
BTN_COLLAR_WALL = 2.30;              // collar ring width (31 = 26.4 + 2*2.3)

// Rear identity mark, debossed into the battery blister apex.
REAR_MARK = true;
REAR_MARK_DEPTH = 0.50;
REAR_MARK_TEXT = "STRUTHIO";
REAR_MARK_FONT = "Liberation Sans:style=Bold";
REAR_MARK_SIZE = 5.6;
REAR_RING_D = 11.0;
REAR_RING_W = 1.4;
BTN_COLLAR_T = 2.00;
SPKR_BACKER_CLEAR_W = 14.0;
SPKR_BACKER_CLEAR_H = 18.0;
USB_BOSS_W = 24.0;
USB_BOSS_DEPTH = 3.0;
USB_BOSS_Z0 = 7.6;
USB_BOSS_H = 9.6;

// Optional future dedicated power-switch aperture. OFF by default because v0.6
// does not lock a separate switch part/BOM. Existing A0 service slot remains.
OPTIONAL_POWER_SWITCH = false;
POWER_SLOT_Y = 12.0;
POWER_SLOT_Z = 8.0;
POWER_SLOT_H = 14.0;


// ============================================================================
// A1.5 CONTROLS, SPEAKER, USB AND POWER (Build Manual 1.5 locks)
// ============================================================================
KEY_CLEAR = 0.30;          // key outline to shell hole
KEY_FLANGE = 1.00;         // flange beyond the key outline (captured behind the shell)
KEY_FLANGE_T = 0.60;
WING_PROUD = 1.80;
WING_TRAVEL = 1.50;        // locked: 1.5 mm / 125 g
WING_SKIRT = 2.00;         // skirt beyond the outline (carrier well = outline + this)
ROCKER_W = 44.0;           // locked visible target
ROCKER_H = 9.0;
ROCKER_R = 3.0;
ROCKER_Y = -61.2;
ROCKER_PROUD = 1.50;
ROCKER_TRAVEL = 1.30;      // locked: 1.3 mm / 150 g per end
ROCKER_SKIRT = 1.20;
ROCKER_STOP_TRAVEL = 1.10; // centre nub: a flat press stops before either pill
DART_PITCH = 24.0;         // locked: DART contact centres 24.0 mm apart
PILL_D = 6.0;              // locked: 6.0 x ~0.5 carbon pills
PILL_T = 0.5;
PLUNGER_D = 7.0;
CARRIER_Z0 = FRONT_T;      // printed carrier behind the shell
WEB_T = 1.0;
CP1_T = 1.0;
CP1_Z = FRONT_T + 1.6 + WEB_T;   // 5.6: CP1 front face
CP1_TOP_Y = -33.3;         // below the board (-32.44) + FIT
CP1_EDGE_INSET = WALL + 0.5;
MAT_EDGE = 0.5;            // mat outline inside CP1
CP1_PAD_D = 7.0;           // interdigitated ENIG pad, for the 6 mm pill
CP1_PIN_XY = [[-30,-36.5],[30,-36.5]];    // heat-stake pins from the carrier
CP1_PIN_D = 2.0;
CP1_POST_CLEAR = 3.3;      // CP1 / mat notch radius around the lower screw posts
WINDOW_D = 13.0;           // speaker window in CP1, mat and carrier
WINDOW_Y = -47.0;
WINDOW_SEAL = 1.0;         // carrier ring around the window
GRILL15_SLOT_H = 1.2;
GRILL15_PITCH = 2.4;
GRILL15_COUNT = 5;
SPKR_POCKET_D = 29.2;      // locked minimum
SPKR_GASKET_T = 0.6;
SPKR_Z = CP1_Z + CP1_T + SPKR_GASKET_T;      // 7.2: speaker front
SPKR_RING_WALL = 1.2;      // locating ring / rear tube wall
SPKR_TUBE_ID = 26.0;       // rear-cavity tube bears on the speaker's rear rim
// USB-C (board connector position NOT confirmed: see header)
USB_PLUG_X0 = -6.0; USB_PLUG_X1 = 16.0;      // right-angle plug at the board edge, turning +x
USB_PLUG_Y0 = -37.5; USB_PLUG_Y1 = -32.8;
USB_PLUG_Z0 = 7.5;   USB_PLUG_Z1 = 14.0;
USB_CH_X0 = 16.5;    USB_CH_X1 = 22.0;        // cable channel down the right side
USB_JACK_X = 19.25;                           // panel jack centre in the bottom wall
USB15_BOSS_W = 16.0;
USB_WALL_Y = -70.6;        // sculpted outline's bottom edge at x = USB_JACK_X (check_a15 measures it)
USB_CH_Y0 = USB_WALL_Y + WALL + USB_BOSS_DEPTH;   // the cable channel ends at the back of the jack boss
// E-Switch 500SSP1S1M7QEA, left side wall (pins: CONFIRM against the drawing)
PWR_Y = 12.0;
PWR_BODY_L = 12.7;   // along y (slide direction)
PWR_BODY_W = 6.6;    // into the handheld (x)
PWR_BODY_H = 6.71;   // z
PWR_ACT_L = 4.72;    // actuator beyond the body face
PWR_ACT_W = 2.0;     // CONFIRM
PWR_TRAVEL = 2.16;
PWR_Z = 10.2;        // body centre

// ============================================================================
// A0.8 THIN-CONTOUR PARAMETERS — hardware-following rear shell
// ============================================================================
BAT_BLISTER_MARGIN_X = 5.0;
BAT_BLISTER_MARGIN_Y = 5.0;
BAT_BLISTER_TOP_SHRINK = 2.4;
BAT_POCKET_CLEAR = 0.7;
BAT_REAR_WALL = 1.8;

SPKR_BLISTER_MARGIN = 3.8;
SPKR_BLISTER_TOP_SHRINK = 1.8;
SPKR_POCKET_CLEAR = 0.9;
SPKR_REAR_WALL = 1.8;

CONTOUR_RAMP_H = 2.2;      // vertical height used to blend blister into base rear
CONTOUR_SLICE = 0.20;      // thin hull slice thickness
// Rear perimeter chamfer occurs only in the 2.2 mm rear wall, after the
// internal cavity ends, so it improves the side silhouette without stealing
// carrier clearance.
REAR_EDGE_INSET = 1.20;
REAR_SCALE_X = (BODY_W - 2*REAR_EDGE_INSET) / BODY_W;
REAR_SCALE_Y = (BODY_H + BOTTOM_EXT - 2*REAR_EDGE_INSET) / (BODY_H + BOTTOM_EXT);

// ============================================================================
// 2D PRIMITIVES
// ============================================================================
module rr2d(w,h,r){
  hull(){
    for(x=[-w/2+r,w/2-r], y=[-h/2+r,h/2-r]) translate([x,y]) circle(r=r);
  }
}

module superellipse2d(rx,ry,n,cy=0,steps=144){
  polygon(points=[
    for(i=[0:steps-1])
      let(a=360*i/steps, c=cos(a), q=sin(a))
      [rx*(c<0?-1:1)*pow(abs(c),2/n),
       cy + ry*(q<0?-1:1)*pow(abs(q),2/n)]
  ]);
}

module heritage_side_pair(x,y,r){
  for(s=[-1,1]) translate([s*x,y]) circle(r=r);
}

module heritage_body_pre_arch2d(){
  // Local hulls preserve the narrow waist and lower flare. The crown is a
  // superellipse so the top is smoothly rounded instead of a long flat chord.
  union(){
    hull(){ superellipse2d(TOP_CROWN_RX,TOP_CROWN_RY,TOP_CROWN_N,TOP_CROWN_Y); heritage_side_pair(UPPER_CENTER_X,UPPER_CENTER_Y,UPPER_R); }
    hull(){ heritage_side_pair(UPPER_CENTER_X,UPPER_CENTER_Y,UPPER_R); heritage_side_pair(WAIST_CENTER_X,WAIST_CENTER_Y,WAIST_R); }
    hull(){ heritage_side_pair(WAIST_CENTER_X,WAIST_CENTER_Y,WAIST_R); heritage_side_pair(LOWER_CENTER_X,LOWER_CENTER_Y,LOWER_R); }
    hull(){ heritage_side_pair(LOWER_CENTER_X,LOWER_CENTER_Y,LOWER_R); heritage_side_pair(FOOT_CENTER_X,FOOT_CENTER_Y,FOOT_R); }
  }
}

module bottom_arch_cut2d(){
  translate([0,BOTTOM_ARCH_Y]) scale([BOTTOM_ARCH_RX,BOTTOM_ARCH_RY]) circle(r=1);
}

module heritage_body_raw2d(){
  if(SHELL_STYLE=="sleek") offset(r=SHELL_RB) offset(delta=-SHELL_RB) sleek_raw2d();
  else difference(){
    heritage_body_pre_arch2d();
    if(BOTTOM_ARCH) bottom_arch_cut2d();
  }
}

module body2d(delta=0){ offset(delta=delta) heritage_body_raw2d(); }

module wing_unit2d(side=-1){
  // A0.8.4: a STRUTHIO wing. Left cap defined once, right mirrored. The rounded
  // root faces the screen centre; three primaries sweep outward with scalloped
  // tips, the leading edge arcs over the top. Unit box [-0.5,0.5]^2.
  pts=[
    [ 0.36, 0.44], [ 0.47, 0.30], [ 0.50, 0.08], [ 0.45,-0.16], [ 0.34,-0.30],  // root
    [ 0.16,-0.36], [ 0.08,-0.24],                                              // notch 1
    [-0.08,-0.44], [-0.15,-0.27],                                              // primary 1, notch 2
    [-0.32,-0.50], [-0.38,-0.31],                                              // primary 2, notch 3
    [-0.50,-0.38],                                                             // wingtip
    [-0.47,-0.14], [-0.34, 0.12], [-0.12, 0.33], [ 0.10, 0.46], [ 0.24, 0.50]   // leading edge
  ];
  if(side<0) polygon(points=pts);
  else scale([-1,1]) polygon(points=pts);
}

module wing2d(side=-1, delta=0){
  // A0.8.4: offset AFTER scaling, so clearances are true mm in X and Y (A0.8.2
  // offset in unit space, giving only 18.5/32 of the clearance in Y).
  offset(delta=delta) scale([BTN_FACE_W, BTN_FACE_H]) wing_unit2d(side);
}

module button_face_2d(side=-1, delta=0){
  if(BUTTON_STYLE=="round") circle(d=BTN_ROUND_D + 2*delta);
  else wing2d(side, delta);
}

module lower_sticker_raw2d(){
  // Slight trapezoid with rounded corners, entirely below the LCD.
  offset(r=STICKER_R)
    polygon(points=[
      [-STICKER_TOP_W/2+STICKER_R, STICKER_TOP-STICKER_R],   // A0.8.4: top corners inset DOWN (A0.8.2 used +R,
      [ STICKER_TOP_W/2-STICKER_R, STICKER_TOP-STICKER_R],   // so the art ran 4.4 mm up over the screen)
      [ STICKER_BOTTOM_W/2-STICKER_R, STICKER_BOTTOM+STICKER_R],
      [-STICKER_BOTTOM_W/2+STICKER_R, STICKER_BOTTOM+STICKER_R]
    ]);
}

module sticker_panel_2d(delta=0){
  intersection(){
    body2d(-2.0 + delta);
    offset(delta=delta) lower_sticker_raw2d();
  }
}

// ============================================================================
// THIN-CONTOUR REAR HELPERS
// ============================================================================
module rr_prism(w,h,r,z0,hz){
  translate([0,0,z0]) linear_extrude(hz) rr2d(w,h,r);
}

module tapered_rr_blister(cx,cy,base_w,base_h,top_w,top_h,z_base,z_top,r=5){
  // Convex tapered shell volume. The first slice overlaps the base shell so
  // the export is one fused solid.
  translate([cx,cy,0]) hull(){
    translate([0,0,z_base-CONTOUR_SLICE/2]) linear_extrude(CONTOUR_SLICE) rr2d(base_w,base_h,r);
    translate([0,0,z_top-CONTOUR_SLICE]) linear_extrude(CONTOUR_SLICE) rr2d(top_w,top_h,max(1,r-1));
  }
}

module battery_blister_outer(){
  intersection(){
    tapered_rr_blister(0,BAT_Y,
      BAT_W+2*BAT_BLISTER_MARGIN_X, BAT_H+2*BAT_BLISTER_MARGIN_Y,
      BAT_W+2*(BAT_BLISTER_MARGIN_X-BAT_BLISTER_TOP_SHRINK),
      BAT_H+2*(BAT_BLISTER_MARGIN_Y-BAT_BLISTER_TOP_SHRINK),
      BASE_TOTAL_D-CONTOUR_RAMP_H, BATTERY_TOTAL_D, 6.0);
    translate([0,0,BASE_TOTAL_D-CONTOUR_RAMP_H-0.5])
      linear_extrude(BATTERY_TOTAL_D-(BASE_TOTAL_D-CONTOUR_RAMP_H)+1.0) body2d();
  }
}

module battery_pocket_cut(){
  // The existing battery reference ends at z=20.9. This pocket leaves an
  // approximately 1.8 mm rear skin at the 23.0 mm blister apex.
  translate([0,BAT_Y,14.15]) linear_extrude(BATTERY_TOTAL_D-BAT_REAR_WALL-14.15+0.2)
    rr2d(BAT_W+2*BAT_POCKET_CLEAR,BAT_H+2*BAT_POCKET_CLEAR,1.5);   // A1.5: tighter corners for the THOR pouch
}

module rear_mark_cut(){
  // Seen from behind (+z) model X already runs left to right: no mirror.
  translate([0,BAT_Y,BATTERY_TOTAL_D-REAR_MARK_DEPTH]) linear_extrude(REAR_MARK_DEPTH+0.2) {
    translate([0,-9]) text(REAR_MARK_TEXT, size=REAR_MARK_SIZE, font=REAR_MARK_FONT, halign="center", valign="center");
    translate([0,6]) difference(){ circle(d=REAR_RING_D); circle(d=REAR_RING_D-2*REAR_RING_W); }
  }
}

// ============================================================================
// BUTTONS
// ============================================================================
module button_groove_cut(side=-1){
  // A0.8.4: one groove per primary feather, from the root toward its tip,
  // kept 1.6 mm inside the face edge. Cosmetic, BUTTON_GROOVE_D deep.
  tips = [[0.00,-0.30], [-0.24,-0.38], [-0.42,-0.28]];   // unit coords, left wing
  root = [0.22,-0.02];
  translate([0,0,-0.01]) linear_extrude(BUTTON_GROOVE_D+0.01)
    intersection(){
      wing2d(side, -1.6);
      scale([side<0 ? 1 : -1, 1])
        for(t=tips) hull(){
          translate([root[0]*BTN_FACE_W, root[1]*BTN_FACE_H]) circle(d=0.9, $fn=16);
          translate([t[0]*BTN_FACE_W, t[1]*BTN_FACE_H]) circle(d=0.9, $fn=16);
        }
    }
}

module button_cap(side=-1){
  // Local z=0 is the player-facing button surface. Installed at
  // z=-BTN_PROTRUSION: the 23 mm neck passes through the opening, the 25 mm
  // flange is captured just behind the 3 mm front shell, and the stem ends at
  // the same switch-contact datum as v0.8.
  color(BUTTON_RGB) difference(){
    union(){
      linear_extrude(BTN_NECK_H) button_face_2d(side, 0);
      translate([0,0,BTN_NECK_H])
        linear_extrude(BTN_FLANGE_T) button_face_2d(side, BTN_FLANGE);
      translate([-BTN_STEM_W/2,-BTN_STEM_H/2,BTN_NECK_H+BTN_FLANGE_T])
        cube([BTN_STEM_W,BTN_STEM_H,BTN_STEM_Z]);
    }
    if(BUTTON_GROOVES && BUTTON_STYLE=="wing") button_groove_cut(side);
  }
}

// ============================================================================
// FRONT DETAILS
// ============================================================================
module screen_cut(){
  translate([LCD_X,LCD_Y,-0.2]) linear_extrude(FRONT_T+0.5) rr2d(LCD_OPEN_W,LCD_OPEN_H,1.6);
}

module lens_recess_cut(){
  // Shallow front-side pocket for a lens/overlay land; does not move LCD datum.
  translate([LCD_X,LCD_Y,-0.01]) linear_extrude(LENS_RECESS_D+0.02) rr2d(LENS_LAND_W,LENS_LAND_H,LENS_LAND_R);
}

module sticker_recess_cut(){
  translate([0,0,-0.01]) linear_extrude(STICKER_RECESS_D+0.02) sticker_panel_2d();
}

// ============================================================================
// ENGINEERING REFERENCE VOLUMES
// ============================================================================
module board_envelope(alpha=0.55){
  color([0.1,0.45,0.25,alpha]) translate([BOARD_X-BOARD_W/2,BOARD_Y-BOARD_H/2,BOARD_Z_FRONT])
    cube([BOARD_W,BOARD_H,BOARD_D]);
  color([0.05,0.15,0.25,0.75]) translate([LCD_X-LCD_W/2,LCD_Y-LCD_H/2,FRONT_T+0.08])
    cube([LCD_W,LCD_H,0.25]);
}

module battery_ref(){
  color([0.75,0.72,0.68,0.65]) translate([-BAT_W/2,BAT_Y-BAT_H/2,BOARD_Z_FRONT+BOARD_D]) cube([BAT_W,BAT_H,BAT_T]);
}

// ============================================================================
// BACK SHELL / INTERNAL SUPPORTS
// ============================================================================
module thinness_reference(){
  // Transparent hardware + three witness planes: nominal base, speaker apex,
  // and battery/max apex. Useful for Claude/CAD review; not printable.
  assembly();
  color([0.2,0.8,1.0,0.18]) translate([-BODY_W/2,BODY_BOTTOM,BASE_TOTAL_D-0.10]) cube([BODY_W,BODY_H+BOTTOM_EXT,0.20]);
  color([1.0,0.7,0.1,0.18]) translate([-BODY_W/2,BODY_BOTTOM,SPEAKER_TOTAL_D-0.10]) cube([BODY_W,BODY_H+BOTTOM_EXT,0.20]);
  color([1.0,0.2,0.2,0.18]) translate([-BODY_W/2,BODY_BOTTOM,BATTERY_TOTAL_D-0.10]) cube([BODY_W,BODY_H+BOTTOM_EXT,0.20]);
}

module side_section(){
  // Longitudinal center section showing the contoured rear over the current
  // battery/speaker references. For render/engineering review only.
  intersection(){
    assembly();
    translate([-2.0,BODY_BOTTOM-2,-1]) cube([4.0,BODY_H+BOTTOM_EXT+4,BATTERY_TOTAL_D+3]);
  }
}

// ============================================================================
// 2D STICKER TEMPLATE / FIT COUPON
// ============================================================================
module front_fit_coupon(){
  // Small print to validate screen-lens opening + one wing opening without
  // committing to the full shell. 80 x 108-ish segment of the real front.
  intersection(){
    front_shell();
    translate([-40,-50,-1]) cube([80,108,FRONT_T+4]);
  }
}

// ============================================================================
// PRESENTATION / ASSEMBLY
// ============================================================================



// ============================================================================
// A1.5 CONTROL FACE: outlines (2D), shared by the shell, CM1, CP1 and sticker
// ============================================================================
module rocker2d(delta=0){ offset(delta=delta) rr2d(ROCKER_W, ROCKER_H, ROCKER_R); }
module wing_at2d(side, delta=0){ translate([side*BTN_X, BTN_Y]) wing2d(side, delta); }
module rocker_at2d(delta=0){ translate([0, ROCKER_Y]) rocker2d(delta); }
module keys2d(dw, dr){ wing_at2d(-1, dw); wing_at2d(1, dw); rocker_at2d(dr); }
module window2d(delta=0){ translate([SPKR_X, WINDOW_Y]) circle(d=WINDOW_D + 2*delta); }
// CP1 board outline: the lower cavity below the board, minus the speaker
// window, the lower screw posts and the carrier pins
module cp1_outline2d(){
  difference(){
    intersection(){
      body2d(-CP1_EDGE_INSET);
      translate([-BODY_W/2, BODY_BOTTOM-BOTTOM_DROP-1]) square([BODY_W, CP1_TOP_Y - BODY_BOTTOM+BOTTOM_DROP+1]);
    }
    window2d();
    for(x=[-SCREW_X,SCREW_X]) translate([x,SCREW_Y_BOT]) circle(r=CP1_POST_CLEAR);
    for(p=CP1_PIN_XY) translate(p) circle(d=CP1_PIN_D+0.2);
  }
}
module mat_outline2d(){ offset(delta=-MAT_EDGE) cp1_outline2d(); }
module dart_pills_xy(){ for(s=[-1,1]) translate([s*DART_PITCH/2, ROCKER_Y]) children(); }
module wing_pills_xy(){ for(s=[-1,1]) translate([s*BTN_X, BTN_Y]) children(); }

module speaker_blister_outer(){
  intersection(){
    translate([SPKR_X,SPKR_Y,0]) hull(){
      translate([0,0,BASE_TOTAL_D-CONTOUR_RAMP_H-CONTOUR_SLICE/2])
        linear_extrude(CONTOUR_SLICE) circle(d=SPKR_POCKET_D+2*SPKR_BLISTER_MARGIN);
      translate([0,0,SPEAKER_TOTAL_D-CONTOUR_SLICE])
        linear_extrude(CONTOUR_SLICE) circle(d=SPKR_POCKET_D+2*(SPKR_BLISTER_MARGIN-SPKR_BLISTER_TOP_SHRINK));
    }
    translate([0,0,BASE_TOTAL_D-CONTOUR_RAMP_H-0.5])
      linear_extrude(SPEAKER_TOTAL_D-(BASE_TOTAL_D-CONTOUR_RAMP_H)+1.0) body2d();
  }
}
// the closed rear cavity: tube interior from the speaker's rear rim into the blister
module speaker_rear_cavity_cut(){
  translate([SPKR_X,SPKR_Y,SPKR_Z+SPKR_T+0.5]) cylinder(d=SPKR_TUBE_ID, h=SPEAKER_TOTAL_D-SPKR_REAR_WALL-(SPKR_Z+SPKR_T+0.5));
}

// ============================================================================
// SCULPTED OUTER / INNER SOLIDS
// ============================================================================
module shell_core2d(){ offset(delta=-SHELL_RB) heritage_body_raw2d(); }
module shell_outer(){
  if(SHELL_STYLE=="sleek")
    minkowski(){ linear_extrude(0.002, center=true) shell_core2d(); rotate_extrude($fn=48) polygon(shell_prof_out()); }
  else linear_extrude(BATTERY_TOTAL_D) body2d();
}
module shell_inner(){
  minkowski(){ linear_extrude(0.002, center=true) shell_core2d(); rotate_extrude($fn=48) polygon(shell_prof_in()); }
}
module zslab(z0, z1){ translate([-80,-100,z0]) cube([160,200,z1-z0]); }
module screw_xy(){ for(x=[-SCREW_X,SCREW_X], y=[SCREW_Y_BOT,SCREW_Y]) translate([x,y]) children(); }

// ============================================================================
// FRONT SHELL (with the printed silicone carrier)
// ============================================================================
module key_holes_cut(){
  translate([0,0,-0.2]) linear_extrude(FRONT_T+0.4) keys2d(KEY_CLEAR, KEY_CLEAR);
}
module speaker_grill15_cuts(){
  translate([SPKR_X, WINDOW_Y, -0.2]) linear_extrude(FRONT_T+0.4)
    intersection(){
      circle(d=WINDOW_D-1.0);
      for(i=[-(GRILL15_COUNT-1)/2:1:(GRILL15_COUNT-1)/2])
        translate([0, i*GRILL15_PITCH]) square([WINDOW_D, GRILL15_SLOT_H], center=true);
    }
}
// Carrier plate behind the face: holds the mat web on CP1, seals the window
// path, carries the CP1 heat-stake pins. Wells around keys leave room for the
// skirts and the full travel.
module carrier(){
  translate([0,0,CARRIER_Z0-0.02]) linear_extrude(CP1_Z-WEB_T-CARRIER_Z0+0.02)
    difference(){
      union(){ mat_outline2d(); window2d(WINDOW_SEAL + MAT_EDGE); }   // full seal ring round the window
      keys2d(WING_SKIRT, ROCKER_SKIRT);
      window2d();
    }
  for(p=CP1_PIN_XY) translate([p[0],p[1],CARRIER_Z0-0.02]) cylinder(d=CP1_PIN_D, h=CP1_Z+CP1_T+0.8-CARRIER_Z0);
}
// The sculpted parts are built by build_shell.py (manifold3d): OpenSCAD 2021's
// CGAL takes far too long on the curved skin. It exports the pieces below,
// lofts the skin from shell_core2d() with the same profiles, and writes
// stl/struthio_a15_front.stl and _back.stl, which the views import.
module front_add(){
  if(SHELL_STYLE=="sleek") screw_xy() translate([0,0,FRONT_T-0.2]) cylinder(d=FRONT_BOSS_OD, h=JOIN_Z-FRONT_T+0.2);
  // perimeter locating lip, above the control zone only (the mat runs to the wall below)
  translate([0,0,FRONT_T-0.20]) linear_extrude(1.70)
    intersection(){
      difference(){ body2d(-WALL-0.35); body2d(-WALL-1.8); }
      translate([-BODY_W/2, CP1_TOP_Y]) square([BODY_W, BODY_H]);
    }
  for(x=[-BOARD_W/2-0.6, BOARD_W/2-1.4])
    translate([x, BOARD_Y-BOARD_H/2+5, FRONT_T-0.20]) cube([2.0,BOARD_H-10,1.70]);
  carrier();
}
module front_cut(){
  sticker_recess_cut();
  lens_recess_cut();
  screen_cut();
  key_holes_cut();
  speaker_grill15_cuts();
  if(SHELL_STYLE=="sleek") screw_xy() translate([0,0,1.5]) cylinder(d=PILOT_D, h=JOIN_Z, $fn=24);
}
module front_shell(){
  if(SHELL_STYLE=="sleek") color(SHELL_RGB) import("stl/struthio_a15_front.stl");
  else color(SHELL_RGB) difference(){
    union(){ linear_extrude(FRONT_T) body2d(); front_add(); }
    front_cut();
  }
}

// ============================================================================
// STRUTHIO-CM1 silicone mat (shape for the molder's drawing; preview / fit)
// ============================================================================
module cm1_wing(side){
  translate([side*BTN_X, BTN_Y, 0]) {
    translate([0,0,-WING_PROUD]) linear_extrude(WING_PROUD+FRONT_T) wing2d(side, 0);       // visible key through the shell
    translate([0,0,FRONT_T]) linear_extrude(KEY_FLANGE_T) wing2d(side, KEY_FLANGE);         // captured flange
    // skirt: a 0.5 mm membrane from the flange edge to the web
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01]) linear_extrude(CP1_Z-WEB_T-(FRONT_T+KEY_FLANGE_T)+0.02)
      difference(){ wing2d(side, WING_SKIRT); wing2d(side, WING_SKIRT-0.5); }
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01])
      linear_extrude(0.5) difference(){ wing2d(side, WING_SKIRT); wing2d(side, KEY_FLANGE-0.01); }
    // plunger, pill face WING_TRAVEL above CP1
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01]) cylinder(d=PLUNGER_D, h=CP1_Z-WING_TRAVEL-(FRONT_T+KEY_FLANGE_T)+0.01);
  }
}
module cm1_rocker(){
  translate([0, ROCKER_Y, 0]) {
    translate([0,0,-ROCKER_PROUD]) linear_extrude(ROCKER_PROUD+FRONT_T) rocker2d(0);
    translate([0,0,FRONT_T]) linear_extrude(KEY_FLANGE_T) rocker2d(KEY_FLANGE);
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01]) linear_extrude(CP1_Z-WEB_T-(FRONT_T+KEY_FLANGE_T)+0.02)
      difference(){ rocker2d(ROCKER_SKIRT); rocker2d(ROCKER_SKIRT-0.5); }
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01])
      linear_extrude(0.5) difference(){ rocker2d(ROCKER_SKIRT); rocker2d(KEY_FLANGE-0.01); }
    for(s=[-1,1]) translate([s*DART_PITCH/2,0,FRONT_T+KEY_FLANGE_T-0.01])
      cylinder(d=PLUNGER_D, h=CP1_Z-ROCKER_TRAVEL-(FRONT_T+KEY_FLANGE_T)+0.01);
    translate([0,0,FRONT_T+KEY_FLANGE_T-0.01]) cylinder(d=3.0, h=CP1_Z-ROCKER_STOP_TRAVEL-(FRONT_T+KEY_FLANGE_T)+0.01);
  }
}
module cm1_mat(){
  color(BUTTON_RGB) {
    translate([0,0,CP1_Z-WEB_T]) linear_extrude(WEB_T)
      difference(){ mat_outline2d(); keys2d(WING_SKIRT-0.5, ROCKER_SKIRT-0.5); }
    cm1_wing(-1); cm1_wing(1); cm1_rocker();
  }
}
module cm1_pills(){
  color([0.1,0.1,0.1]) {
    wing_pills_xy() translate([0,0,CP1_Z-WING_TRAVEL-PILL_T]) cylinder(d=PILL_D, h=PILL_T);
    dart_pills_xy() translate([0,0,CP1_Z-ROCKER_TRAVEL-PILL_T]) cylinder(d=PILL_D, h=PILL_T);
  }
}

// ============================================================================
// STRUTHIO-CP1 control PCB
// ============================================================================
module cp1(){
  color([0.12,0.42,0.22]) translate([0,0,CP1_Z]) linear_extrude(CP1_T) cp1_outline2d();
  color([0.85,0.70,0.30]) translate([0,0,CP1_Z-0.02]) linear_extrude(0.03) { wing_pills_xy() circle(d=CP1_PAD_D); dart_pills_xy() circle(d=CP1_PAD_D); }
}

// ============================================================================
// REFERENCE VOLUMES (A1.5)
// ============================================================================
module speaker_ref(){
  color([0.15,0.15,0.15,0.85]) translate([SPKR_X,SPKR_Y,SPKR_Z]) cylinder(d=SPKR_D,h=SPKR_T);
  color([0.3,0.3,0.3,0.6]) translate([SPKR_X,SPKR_Y,SPKR_Z-SPKR_GASKET_T]) difference(){ cylinder(d=SPKR_D,h=SPKR_GASKET_T); translate([0,0,-1]) cylinder(d=WINDOW_D+2,h=3); }
}
module usb_keepout(){
  color([0.9,0.2,0.9,0.35]) {
    translate([USB_PLUG_X0,USB_PLUG_Y0,USB_PLUG_Z0]) cube([USB_PLUG_X1-USB_PLUG_X0,USB_PLUG_Y1-USB_PLUG_Y0,USB_PLUG_Z1-USB_PLUG_Z0]);
    translate([USB_CH_X0,USB_CH_Y0,USB_PLUG_Z0]) cube([USB_CH_X1-USB_CH_X0,USB_PLUG_Y1-USB_CH_Y0,USB_PLUG_Z1-USB_PLUG_Z0]);
  }
}
module power_switch_ref(){
  // body against the left inner wall, actuator through the wall
  color([0.2,0.2,0.25,0.9]) translate([-pwr_wall_x()+0.0, PWR_Y-PWR_BODY_L/2, PWR_Z-PWR_BODY_H/2]) cube([PWR_BODY_W, PWR_BODY_L, PWR_BODY_H]);
  color([0.9,0.9,0.9]) translate([-pwr_wall_x()-PWR_ACT_L, PWR_Y-PWR_ACT_W/2, PWR_Z-PWR_ACT_W/2]) cube([PWR_ACT_L, PWR_ACT_W, PWR_ACT_W]);
}
// inner face of the left wall at PWR_Y (body half-width there, from the waist/upper hull)
function pwr_wall_x() = 38.25;   // left inner wall over y 5.65..18.35 (38.32 at the narrow end)

// ============================================================================
// BACK SHELL
// ============================================================================
module back_shell(){ if(SHELL_STYLE=="sleek") back_shell_sleek(); else back_shell_a0(); }
// internal features of the sculpted back shell (trimmed to the outer skin)
module back_features_sleek(){
  // screw posts from the joint to the back
  screw_xy() translate([0,0,JOIN_Z+0.1]) cylinder(d=SCREW_POST_OD, h=SHELL_ZB-JOIN_Z);
  // Features run on into the skin (they are trimmed to the outer surface), so
  // none ends tangent to the curved inner surface.
  // board hold-downs from the board back to the ceiling
  for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38]) translate([x-3,y-3,14.6]) cube([6,6,SHELL_ZB-14.6+1]);
  // USB-C panel-jack boss at the bottom wall
  translate([USB_JACK_X-USB15_BOSS_W/2,USB_WALL_Y+WALL-0.5,USB_BOSS_Z0])
    difference(){
      cube([USB15_BOSS_W,USB_BOSS_DEPTH+0.5,SHELL_ZB-USB_BOSS_Z0+1]);
      translate([1.5,-0.2,1.6]) cube([USB15_BOSS_W-3.0,USB_BOSS_DEPTH+0.9,USB_BOSS_H-3.2]);
    }
  // battery side ribs
  for(x=[-BAT_W/2-1.4, BAT_W/2+0.4]) translate([x,BAT_Y-BAT_H/2-1,14.0]) cube([1.0,BAT_H+2,SHELL_ZB-14.0+1]);
  // speaker locating ring (open over its top arc, where the USB-C plug passes)
  translate([SPKR_X,SPKR_Y,SPKR_Z]) difference(){
    cylinder(d=SPKR_POCKET_D+2*SPKR_RING_WALL, h=SPKR_T);
    translate([0,0,-0.1]) cylinder(d=SPKR_POCKET_D, h=SPKR_T+0.2);
    translate([USB_PLUG_X0-0.3-SPKR_X, USB_PLUG_Y0-0.3-SPKR_Y, -0.2]) cube([USB_PLUG_X1-USB_PLUG_X0+0.6, 20, SPKR_T+0.4]);
  }
  // rear-cavity tube from the speaker's rear rim to the back skin
  translate([SPKR_X,SPKR_Y,SPKR_Z+SPKR_T+0.5]) cylinder(d=SPKR_TUBE_ID+2*SPKR_RING_WALL, h=SHELL_ZB);
  // E-Switch cradle
  translate([-pwr_wall_x()-0.5, PWR_Y-PWR_BODY_L/2-1.2, PWR_Z+PWR_BODY_H/2])
    cube([PWR_BODY_W+0.5, PWR_BODY_L+2.4, SHELL_ZB-(PWR_Z+PWR_BODY_H/2)+1]);
  for(dy=[-PWR_BODY_L/2-1.2, PWR_BODY_L/2])
    translate([-pwr_wall_x()-0.5, PWR_Y+dy, PWR_Z-PWR_BODY_H/2]) cube([PWR_BODY_W+0.5, 1.2, PWR_BODY_H+0.02]);
}
module back_cut_sleek(){
  battery_pocket_cut();
  if(REAR_MARK) rear_mark_cut();
  // screw clearance + counterbore from the back
  screw_xy() { translate([0,0,JOIN_Z-0.5]) cylinder(d=CLEAR_D, h=CBORE_Z-JOIN_Z+0.6, $fn=24);
               translate([0,0,CBORE_Z]) cylinder(d=CBORE_D, h=SHELL_ZB, $fn=32); }
  // USB-C panel jack through the bottom wall and boss
  translate([USB_JACK_X-7.0,USB_WALL_Y-2.0,9.2]) cube([14.0,WALL+USB_BOSS_DEPTH+2.5,6.4]);
  // A0 side service access (BOOT / RESET), right side
  translate([BODY_W/2-8.0,1.0,7.0]) cube([10.0,24.0,7.5]);
  // E-Switch actuator slot, left wall
  translate([-BODY_W/2-2, PWR_Y-(PWR_ACT_W+PWR_TRAVEL)/2-0.3, PWR_Z-PWR_ACT_W/2-0.3])
    cube([BODY_W/2-pwr_wall_x()+2.5, PWR_ACT_W+PWR_TRAVEL+0.6, PWR_ACT_W+0.6]);
}
// the rear-cavity bore; build_shell.py trims it to the inner surface so the
// back skin closes the cavity
module speaker_bore(){ translate([SPKR_X,SPKR_Y,SPKR_Z+SPKR_T+0.5]) cylinder(d=SPKR_TUBE_ID, h=SHELL_ZB); }
module back_shell_sleek(){ color(SHELL_RGB) import("stl/struthio_a15_back.stl"); }

module back_shell_a0(){
  color(SHELL_RGB) difference(){
    union(){
      translate([0,0,FRONT_T])
        linear_extrude(BASE_INNER_TOP_Z-FRONT_T+0.02) body2d();
      translate([0,0,BASE_INNER_TOP_Z])
        linear_extrude(BACK_WALL, scale=[REAR_SCALE_X,REAR_SCALE_Y]) body2d();
      battery_blister_outer();
      speaker_blister_outer();
      for(x=[-SCREW_X,SCREW_X], y=[SCREW_Y_BOT,SCREW_Y])
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
      for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
        translate([x-3,y-3,14.6]) cube([6,6,max(0.8,SUPPORT_TOP_Z-14.6)]);
      // USB-C panel-jack boss at the bottom wall (x = USB_JACK_X)
      translate([USB_JACK_X-USB15_BOSS_W/2,BOTTOM_EDGE_CENTER_Y+0.3,USB_BOSS_Z0])
        difference(){
          cube([USB15_BOSS_W,USB_BOSS_DEPTH,USB_BOSS_H]);
          translate([1.5,-0.2,1.6]) cube([USB15_BOSS_W-3.0,USB_BOSS_DEPTH+0.4,USB_BOSS_H-3.2]);
        }
      for(x=[-BAT_W/2-1.4, BAT_W/2+0.4])
        translate([x,BAT_Y-BAT_H/2-1,14.0]) cube([1.0,BAT_H+2,6.8]);
    }
    translate([0,0,FRONT_T-0.2])
      linear_extrude(BASE_INNER_TOP_Z-(FRONT_T-0.2)+0.02) body2d(-WALL);
    battery_pocket_cut();
    if(REAR_MARK) rear_mark_cut();
    speaker_rear_cavity_cut();
    for(x=[-SCREW_X,SCREW_X], y=[SCREW_Y_BOT,SCREW_Y])
      translate([x,y,FRONT_T+3]) cylinder(d=SCREW_D-0.25,h=BASE_TOTAL_D);
    // USB-C panel jack through the bottom wall and boss
    translate([USB_JACK_X-7.0,BOTTOM_EDGE_CENTER_Y-2.0,9.2]) cube([14.0,WALL+USB_BOSS_DEPTH+2.5,6.4]);
    // A0 side service access (BOOT / RESET), right side
    translate([BODY_W/2-8.0,1.0,7.0]) cube([10.0,24.0,7.5]);
    // E-Switch actuator slot, left wall: actuator + travel + 0.3 all round
    translate([-BODY_W/2-1, PWR_Y-(PWR_ACT_W+PWR_TRAVEL)/2-0.3, PWR_Z-PWR_ACT_W/2-0.3])
      cube([BODY_W/2-pwr_wall_x()+1.5, PWR_ACT_W+PWR_TRAVEL+0.6, PWR_ACT_W+0.6]);
  }
  color(SHELL_RGB){
    for(x=[-SCREW_X,SCREW_X], y=[SCREW_Y_BOT,SCREW_Y])
      difference(){
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
        translate([x,y,FRONT_T+3.8]) cylinder(d=SCREW_D-0.25,h=BASE_TOTAL_D);
      }
    for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
      translate([x-3,y-3,14.6]) cube([6,6,max(0.8,SUPPORT_TOP_Z-14.6)]);
    // speaker locating ring around the speaker body (open over its top arc,
    // where the USB-C plug keep-out passes) ...
    translate([SPKR_X,SPKR_Y,SPKR_Z]) difference(){
      cylinder(d=SPKR_POCKET_D+2*SPKR_RING_WALL, h=SPKR_T);
      translate([0,0,-0.1]) cylinder(d=SPKR_POCKET_D, h=SPKR_T+0.2);
      translate([USB_PLUG_X0-0.3-SPKR_X, USB_PLUG_Y0-0.3-SPKR_Y, -0.2]) cube([USB_PLUG_X1-USB_PLUG_X0+0.6, 20, SPKR_T+0.4]);
    }
    // ... and the closed rear-cavity tube, bearing on the speaker's rear rim
    // through a 0.5 mm gasket, up to the rear wall / speaker blister
    translate([SPKR_X,SPKR_Y,SPKR_Z+SPKR_T+0.5]) difference(){
      cylinder(d=SPKR_TUBE_ID+2*SPKR_RING_WALL, h=BASE_INNER_TOP_Z-(SPKR_Z+SPKR_T+0.5)+0.02);
      translate([0,0,-0.1]) cylinder(d=SPKR_TUBE_ID, h=BASE_INNER_TOP_Z);
    }
    // E-Switch cradle: a U around the body against the left wall
    translate([-pwr_wall_x()-0.5, PWR_Y-PWR_BODY_L/2-1.2, PWR_Z+PWR_BODY_H/2])
      cube([PWR_BODY_W+0.5, PWR_BODY_L+2.4, BASE_INNER_TOP_Z-(PWR_Z+PWR_BODY_H/2)+0.02]);
    for(dy=[-PWR_BODY_L/2-1.2, PWR_BODY_L/2])
      translate([-pwr_wall_x()-0.5, PWR_Y+dy, PWR_Z-PWR_BODY_H/2])
        cube([PWR_BODY_W+0.5, 1.2, PWR_BODY_H+0.02]);
  }
}

// ============================================================================
// 2D STICKER TEMPLATE
// ============================================================================
module sticker_template_2d(){
  difference(){
    sticker_panel_2d();
    keys2d(KEY_CLEAR+0.7, KEY_CLEAR+0.7);
    translate([SPKR_X, WINDOW_Y]) intersection(){
      circle(d=WINDOW_D-1.0+1.6);
      for(i=[-(GRILL15_COUNT-1)/2:1:(GRILL15_COUNT-1)/2])
        translate([0, i*GRILL15_PITCH]) square([WINDOW_D+2, GRILL15_SLOT_H+0.8], center=true);
    }
  }
}

// ============================================================================
// PRESENTATION / ASSEMBLY
// ============================================================================
module design_front(){
  front_shell();
  color([0.02,0.08,0.16])
    translate([LCD_X-LCD_OPEN_W/2,LCD_Y-LCD_OPEN_H/2,-0.18]) cube([LCD_OPEN_W,LCD_OPEN_H,0.16]);
  color(PANEL_RGB) translate([0,0,-0.10]) linear_extrude(0.08) sticker_panel_2d();
  cm1_mat();
}
module assembly(){
  front_shell(); back_shell(); board_envelope(); battery_ref(); speaker_ref();
  cm1_mat(); cm1_pills(); cp1(); power_switch_ref();
}
module internals(){ board_envelope(0.8); battery_ref(); speaker_ref(); cm1_mat(); cm1_pills(); cp1(); power_switch_ref(); usb_keepout(); }

if(part=="design_front") design_front();
else if(part=="front") front_shell();
else if(part=="back") back_shell();
else if(part=="mat") cm1_mat();
else if(part=="cp1_outline") cp1_outline2d();
else if(part=="mat_outline") mat_outline2d();
else if(part=="body_outline") body2d();
else if(part=="core2d") shell_core2d();
else if(part=="front_add") front_add();
else if(part=="front_cut") front_cut();
else if(part=="back_add") back_features_sleek();
else if(part=="back_cut") back_cut_sleek();
else if(part=="speaker_bore") speaker_bore();
else if(part=="keys_outline") keys2d(0,0);
else if(part=="reference") internals();
else if(part=="sticker") sticker_template_2d();
else if(part=="front_fit_coupon") front_fit_coupon();
else if(part=="side_section") side_section();
else assembly();
