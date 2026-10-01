/*
 STRUTHIO ESP32-S3 HANDHELD — A0.8.3 (A0.8.2 ROBUST LOWER CHASSIS + FIT FIXES)
 R.A. Peddycoart
 Units: mm

 PURPOSE
 -------
 Editable OpenSCAD update of the v0.4 A0 fit enclosure, aligned to the
 STRUTHIO ESP32-S3 Handheld C Port Manual v0.6 plus a new hardware-following
 thin-back study. The front and locked XY datums are inherited from A0.6.

 IMPORTANT AUTHORITY RULE
 ------------------------
 This source preserves the v0.6 A0 engineering locks. The external form,
 sticker recess, button face and cosmetic details are a TUNABLE candidate.
 Do not change LOCKED datums unless a physical fit test proves they must move.

 LOCKED / CURRENT A0 REQUIREMENTS FROM v0.6
 -----------------------------------------
 - Envelope: 88 x 128 x 25 mm for A0 fit test.
 - Shrink target AFTER fit proof: 85 x 125 x 23 mm.
 - Carrier: Waveshare ESP32-S3-Touch-LCD-3.5B, rotated portrait.
 - Published bare-board envelope used by v0.4: 92.44 x 61.00 x 11.50 mm.
 - Active LCD: 48.96 x 73.44 mm, 320 x 480 portrait.
 - Two physical wing controls only; GPIO17 left, GPIO18 right.
 - Candidate switch: Omron B3F-4050 / B3F-4055 footprint class.
 - Switch daughterboards: about 18 x 18 mm.
 - Speaker reference: 8 ohm, ~1 W, ~28 mm mono.
 - Battery reference cavity: ~36 x 52 x 6.2 mm; battery not locked.
 - USB-C: short full-data male-to-female extension to bottom opening.
 - 4 x M2-class case screws.
 - No front START/SOUND/ACL/menu/touch controls.
 - DART uses the SAME two wing switches; no extra DART control.

 A0.8.2 ROBUST-BOTTOM CHANGES IN THIS FILE
 --------------------------------------
 - Keeps the 88 x 128 mm A0 footprint and all front/display/button XY datums.
 - Reduces the nominal upper/side body thickness from 25 mm to 18.6 mm.
 - Uses local tapered rear blisters only where the 6.2 mm battery and speaker
   require depth; maximum thickness remains a physically honest 23.0 mm.
 - Battery blister follows the current 36 x 52 x 6.2 mm reference cavity.
 - Speaker blister follows the current ~28 x 5 mm reference speaker.
 - Switch/board regions stay inside the 18.6 mm base envelope.
 - Rear shell now follows hardware Z-height rather than one constant slab.
 - This is an optimization candidate, NOT a replacement for physical fit proof.
 - v0.8.2 shallows/narrows the bottom arch to preserve a broad lower rail.
 - Adds a 1.8 mm internal lower backer plate and 31 mm button collars.
 - Reduces the speaker grille to four 0.9 mm slots with thicker webs.
 - Raises the provisional speaker reference 3.5 mm away from the lower edge.
 - Adds an internal U-boss around the bottom USB-C opening.

 A0.8.3 FIT FIXES (2026-10-01; everything else is A0.8.2 unchanged)
 ------------------------------------------------------------------
 Found by exporting all parts and probing the meshes (handheld/cad/a1/check_a1.py):
 - USB-C opening: the cut started from the old square bottom (y=-64), but the
   shallow arch puts the centre bottom edge at y=-62.2, so ~1.1 mm of wall was
   left across the port. The cut and the U-boss now follow the arch
   (BOTTOM_EDGE_CENTER_Y); the boss no longer pokes ~1 mm out of the arch.
 - Side service slot: cut at x=41.4, but the waist puts the outer wall at
   x~41.0 there, so the slot never opened. It now starts inside the cavity.
   Same for the optional power-switch aperture.
 - Button stem: the stem tip sat at z=7.3 while the B3F plunger tip is at
   SWITCH_PCB_PLANE_Z - SWITCH_H = 6.4, i.e. 0.9 mm into a switch with
   0.25 mm travel (held pressed). The tip now stops BTN_PRETRAVEL_GAP before
   the plunger and follows SWITCH_PCB_PLANE_Z when that is shimmed.
 - Battery reference started 0.15 mm inside the board envelope; it now sits on
   the board's back face (14.85 mm).

 NOTES FOR CLAUDE / FUTURE EDITS
 -------------------------------
 Change the TUNABLE block first. Avoid editing hard coordinates in modules.
 Keep the A0 fit datums until the board + front + one wing cap are physically tested.

 Export examples:
 openscad -o stl/struthio_a083_front.stl        -D 'part="front"'        STRUTHIO083.scad
 openscad -o stl/struthio_a083_back.stl         -D 'part="back"'         STRUTHIO083.scad
 openscad -o stl/struthio_a083_left_button.stl  -D 'part="left_button"'  STRUTHIO083.scad
 openscad -o stl/struthio_a083_right_button.stl -D 'part="right_button"' STRUTHIO083.scad
 openscad -o svg/struthio_a083_front_sticker.svg -D 'part="sticker"'     STRUTHIO083.scad
 (or run ./export_a1.sh)
*/

$fn = 72;
part = "assembly"; // assembly, design_front, front, back, left_button, right_button, reference, sticker, front_fit_coupon

// ============================================================================
// LOCKED A0 DATUMS — change only after physical evidence
// ============================================================================
BODY_W = 88;
BODY_H = 128;
BODY_D = 25; // legacy A0 maximum envelope, retained as a comparison datum
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

// Electrical button centers retained from v0.4 until the switch-plane fit print.
BTN_Y = -47.5;
BTN_X = 21.5;

SWITCH_BODY = 12.5;
SWITCH_PCB = 18.0;
SWITCH_PCB_T = 1.6;
SWITCH_PCB_PLANE_Z = 13.7; // tune with shim only after physical cap/switch measurement
SWITCH_H = 7.3;            // B3F-4050 overall height including the projected plunger
SWITCH_TRAVEL = 0.25;      // B3F operating travel

SPKR_D = 28.0;
SPKR_T = 5.0;
SPKR_Y = -43.5; // raised 3.5 mm: speaker location is provisional; increases lower-shell ligament

BAT_W = 36.0;
BAT_H = 52.0;
BAT_T = 6.2;
BAT_Y = 13.5;

SCREW_X = 37.0;
SCREW_Y = 55.5;
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
LOWER_CENTER_Y = -42.0;
LOWER_R = 7.5;
FOOT_CENTER_X = 34.0;
FOOT_CENTER_Y = -54.0;
FOOT_R = 10.0;

// Shallow concave bottom arch, retained as a heritage cue but deliberately
// reduced from v0.8.1. The prior 4 mm centre rise plus 23.9 mm button holes
// produced weak lower ligaments. v0.8.2 keeps a broad structural bottom rail.
BOTTOM_ARCH_Y = -72.2; // shallower 1.8 mm centre rise; v0.8.1 rose ~4 mm and thinned the lower rail
BOTTOM_ARCH_RX = 31.0; // narrower arch preserves broad structural feet and lower bridge
BOTTOM_ARCH_RY = 10.0;
BOTTOM_EDGE_CENTER_Y = BOTTOM_ARCH_Y + BOTTOM_ARCH_RY; // -62.2: outer bottom edge at x=0 (A0.8.3)

// Screen lens / bezel cosmetics. Opening itself remains locked above.
LENS_LAND_W = 56.5;
LENS_LAND_H = 81.0;
LENS_LAND_R = 5.4;
LENS_RECESS_D = 0.55;

// Lower sticker/control-art registration panel. Unlike v0.7, the molded shell
// remains visible around the LCD and the printed art starts below the display,
// matching the construction language of the user's heritage references.
STICKER_TOP = -24.2;
STICKER_BOTTOM = -56.0;
STICKER_TOP_W = 69.0;
STICKER_BOTTOM_W = 74.0;
STICKER_R = 2.2;
STICKER_RECESS_D = 0.28;

// Cosmetic shell/button colors used only by OpenSCAD previews/renders.
SHELL_RGB = [0.02,0.45,0.19];       // heritage green; STL has no color
BUTTON_RGB = [0.96,0.63,0.04];      // STRUTHIO gold
PANEL_RGB = [0.03,0.05,0.07];

// Large two-button dedicated-handheld controls. Electrical centers stay locked.
// Claude can set BUTTON_STYLE=\"wing\" without changing the switch datums.
BUTTON_STYLE = "round";              // "round" or "wing"
BTN_ROUND_D = 23.0;
BTN_FACE_W = 32.0;                    // wing-style fallback only
BTN_FACE_H = 18.5;                    // wing-style fallback only
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
BUTTON_GROOVES = false;               // round default is intentionally plain
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
BTN_COLLAR_OD = 31.0;
BTN_COLLAR_ID = 26.4;
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
REAR_SCALE_Y = (BODY_H - 2*REAR_EDGE_INSET) / BODY_H;

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
  difference(){
    heritage_body_pre_arch2d();
    bottom_arch_cut2d();
  }
}

module body2d(delta=0){ offset(delta=delta) heritage_body_raw2d(); }

module wing_unit2d(side=-1){
  // Left cap is defined once; right is mirrored. Wide, tactile, toy-like.
  pts=[
    [-0.50,-0.31], [0.27,-0.50], [0.50,-0.22], [0.48,0.25],
    [0.20,0.48], [-0.34,0.41], [-0.50,0.10]
  ];
  if(side<0) polygon(points=pts);
  else scale([-1,1]) polygon(points=pts);
}

module wing2d(side=-1, delta=0){
  scale([BTN_FACE_W, BTN_FACE_H]) offset(delta=delta/max(BTN_FACE_W,BTN_FACE_H)) wing_unit2d(side);
}

module button_face_2d(side=-1, delta=0){
  if(BUTTON_STYLE=="round") circle(d=BTN_ROUND_D + 2*delta);
  else wing2d(side, delta);
}

module lower_sticker_raw2d(){
  // Slight trapezoid with rounded corners, entirely below the LCD.
  offset(r=STICKER_R)
    polygon(points=[
      [-STICKER_TOP_W/2+STICKER_R, STICKER_TOP+STICKER_R],
      [ STICKER_TOP_W/2-STICKER_R, STICKER_TOP+STICKER_R],
      [ STICKER_BOTTOM_W/2-STICKER_R, STICKER_BOTTOM+STICKER_R],
      [-STICKER_BOTTOM_W/2+STICKER_R, STICKER_BOTTOM+STICKER_R]
    ]);
}

module sticker_panel_2d(delta=0){
  intersection(){
    body2d(-4.0 + delta);
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

module speaker_blister_outer(){
  intersection(){
    translate([0,SPKR_Y,0]) hull(){
      translate([0,0,BASE_TOTAL_D-CONTOUR_RAMP_H-CONTOUR_SLICE/2])
        linear_extrude(CONTOUR_SLICE) circle(d=SPKR_D+2*SPKR_BLISTER_MARGIN);
      translate([0,0,SPEAKER_TOTAL_D-CONTOUR_SLICE])
        linear_extrude(CONTOUR_SLICE) circle(d=SPKR_D+2*(SPKR_BLISTER_MARGIN-SPKR_BLISTER_TOP_SHRINK));
    }
    translate([0,0,BASE_TOTAL_D-CONTOUR_RAMP_H-0.5])
      linear_extrude(SPEAKER_TOTAL_D-(BASE_TOTAL_D-CONTOUR_RAMP_H)+1.0) body2d();
  }
}

module battery_pocket_cut(){
  // The existing battery reference ends at z=20.9. This pocket leaves an
  // approximately 1.8 mm rear skin at the 23.0 mm blister apex.
  translate([0,BAT_Y,14.15]) linear_extrude(BATTERY_TOTAL_D-BAT_REAR_WALL-14.15+0.2)
    rr2d(BAT_W+2*BAT_POCKET_CLEAR,BAT_H+2*BAT_POCKET_CLEAR,3.0);
}

module speaker_pocket_cut(){
  translate([0,SPKR_Y,15.0]) cylinder(d=SPKR_D+2*SPKR_POCKET_CLEAR,
    h=SPEAKER_TOTAL_D-SPKR_REAR_WALL-15.0+0.2);
}

// ============================================================================
// BUTTONS
// ============================================================================
module button_groove_cut(side=-1){
  // Three shallow heritage wing-feather grooves, cosmetic only.
  for(k=[-1,0,1]){
    y = k*3.0;
    x0 = side<0 ? -7.5 : 1.0;
    // Grooves cut inward from the player-facing local z=0 surface.
    translate([x0,y,-0.01])
      rotate([0,0,side<0 ? -8 : 8])
      cube([8.0,0.9,BUTTON_GROOVE_D+0.2]);
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

module button_cut(side=-1){
  translate([side*BTN_X,BTN_Y,-0.2]) linear_extrude(FRONT_T+0.5)
    scale([BTN_OPEN_SCALE_X,BTN_OPEN_SCALE_Y]) button_face_2d(side, BTN_CLEAR);
}

module speaker_grill_cuts(){
  for(i=[-(GRILL_COUNT-1)/2:1:(GRILL_COUNT-1)/2]){
    translate([-GRILL_W/2, SPKR_Y + i*GRILL_PITCH, -0.2])
      cube([GRILL_W,GRILL_SLOT_H,FRONT_T+0.5]);
  }
}

module lower_front_reinforcement(){
  // Broad internal plate reinforces the lower shell across both button zones.
  // It is cut around button capture flanges and leaves an acoustic window.
  translate([0,0,FRONT_T-0.02])
    linear_extrude(LOWER_BACKER_T)
      difference(){
        intersection(){
          body2d(-LOWER_BACKER_SIDE_INSET);
          translate([-BODY_W/2,LOWER_BACKER_BOTTOM])
            square([BODY_W,LOWER_BACKER_TOP-LOWER_BACKER_BOTTOM]);
        }
        translate([-BTN_X,BTN_Y]) circle(d=BTN_COLLAR_ID);
        translate([ BTN_X,BTN_Y]) circle(d=BTN_COLLAR_ID);
        translate([-SPKR_BACKER_CLEAR_W/2,SPKR_Y-SPKR_BACKER_CLEAR_H/2])
          square([SPKR_BACKER_CLEAR_W,SPKR_BACKER_CLEAR_H]);
      }

  // Annular collars put material around each button opening without touching
  // the moving 25 mm capture flange.
  for(side=[-1,1])
    translate([side*BTN_X,BTN_Y,FRONT_T-0.02])
      linear_extrude(BTN_COLLAR_T)
        difference(){
          circle(d=BTN_COLLAR_OD);
          circle(d=BTN_COLLAR_ID);
        }
}

module front_shell(){
  color(SHELL_RGB) difference(){
    union(){
      linear_extrude(FRONT_T) body2d();
      // shallow internal perimeter locating lip
      translate([0,0,FRONT_T-0.20]) linear_extrude(1.70)
        difference(){ body2d(-WALL-0.35); body2d(-WALL-1.8); }
      // board side locator pads, inherited A0 fit datum
      for(x=[-BOARD_W/2-0.6, BOARD_W/2-1.4])
        translate([x, BOARD_Y-BOARD_H/2+5, FRONT_T-0.20]) cube([2.0,BOARD_H-10,1.70]);
      lower_front_reinforcement();
    }
    sticker_recess_cut();
    lens_recess_cut();
    screen_cut();
    button_cut(-1); button_cut(1);
    speaker_grill_cuts();
    if(FRONT_SCREW_THROUGH)
      for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
        translate([x,y,-0.5]) cylinder(d=SCREW_D+0.45,h=FRONT_T+2.5);
  }
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

module speaker_ref(){
  color([0.15,0.15,0.15,0.8]) translate([0,SPKR_Y,15.6]) cylinder(d=SPKR_D,h=SPKR_T);
}

module switch_ref(side=-1){
  // PCB plane is tunable. Switch is shown projecting TOWARD the front face.
  color([0.1,0.35,0.15,0.8])
    translate([side*BTN_X-SWITCH_PCB/2,BTN_Y-SWITCH_PCB/2,SWITCH_PCB_PLANE_Z])
      cube([SWITCH_PCB,SWITCH_PCB,SWITCH_PCB_T]);
  color([0.15,0.15,0.15,0.85])
    translate([side*BTN_X-SWITCH_BODY/2,BTN_Y-SWITCH_BODY/2,SWITCH_PCB_PLANE_Z-SWITCH_H])
      cube([SWITCH_BODY,SWITCH_BODY,SWITCH_H]);
}

// ============================================================================
// BACK SHELL / INTERNAL SUPPORTS
// ============================================================================
module back_shell(){
  // A0.8 outer shell: a thin 18.6 mm base body plus only the local depth
  // required by battery and speaker. This deliberately does NOT add cosmetic
  // rear thickness elsewhere.
  color(SHELL_RGB) difference(){
    union(){
      // Base cavity region keeps the full A0 outline. Only the final rear wall
      // tapers inward, so carrier clearance and the front seam remain unchanged.
      translate([0,0,FRONT_T])
        linear_extrude(BASE_INNER_TOP_Z-FRONT_T+0.02) body2d();
      translate([0,0,BASE_INNER_TOP_Z])
        linear_extrude(BACK_WALL, scale=[REAR_SCALE_X,REAR_SCALE_Y]) body2d();
      battery_blister_outer();
      speaker_blister_outer();

      // Screw posts and board locators terminate against the thin base rear.
      for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
      for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
        translate([x-3,y-3,14.6]) cube([6,6,max(0.8,SUPPORT_TOP_Z-14.6)]);

      // Switch-PCB cradles live completely inside the base thickness.
      for(side=[-1,1])
        translate([side*BTN_X-SWITCH_PCB/2-1.2,BTN_Y-SWITCH_PCB/2-1.2,SWITCH_PCB_PLANE_Z+SWITCH_PCB_T])
          difference(){
            cube([SWITCH_PCB+2.4,SWITCH_PCB+2.4,max(0.8,SUPPORT_TOP_Z-(SWITCH_PCB_PLANE_Z+SWITCH_PCB_T))]);
            translate([1.2,1.2,-0.1]) cube([SWITCH_PCB,SWITCH_PCB,20]);
          }

      // U-shaped internal reinforcement around the bottom USB-C opening.
      // Keeps the external port location but avoids two thin lower tabs.
      translate([-USB_BOSS_W/2,BOTTOM_EDGE_CENTER_Y+0.3,USB_BOSS_Z0])
        difference(){
          cube([USB_BOSS_W,USB_BOSS_DEPTH,USB_BOSS_H]);
          translate([5.0,-0.2,1.6]) cube([USB_BOSS_W-10.0,USB_BOSS_DEPTH+0.4,USB_BOSS_H-3.2]);
        }

      // Battery side rails bridge from the board plane into the local blister.
      for(x=[-BAT_W/2-1.4, BAT_W/2+0.4])
        translate([x,BAT_Y-BAT_H/2-1,14.0]) cube([1.0,BAT_H+2,6.8]);
    }

    // General board/switch cavity: stops at the thin-base rear wall.
    translate([0,0,FRONT_T-0.2])
      linear_extrude(BASE_INNER_TOP_Z-(FRONT_T-0.2)+0.02) body2d(-WALL);

    // Local pockets extend only where hardware needs the extra Z depth.
    battery_pocket_cut();
    speaker_pocket_cut();

    for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
      translate([x,y,FRONT_T+3]) cylinder(d=SCREW_D-0.25,h=BASE_TOTAL_D);

    // Bottom USB-C panel extension remains, shortened to the new thin base.
    translate([-7.0,BOTTOM_EDGE_CENTER_Y-2.0,9.2]) cube([14.0,WALL+USB_BOSS_DEPTH+2.5,6.4]); // A0.8.3: through arch wall and boss

    // Side A0 service access remains in a board-only thin region.
    translate([BODY_W/2-8.0,1.0,7.0]) cube([10.0,24.0,7.5]); // A0.8.3: starts inside the cavity (waist wall at x~41)

    if(OPTIONAL_POWER_SWITCH)
      translate([BODY_W/2-8.0,POWER_SLOT_Y-POWER_SLOT_H/2,POWER_SLOT_Z])
        cube([10.0,POWER_SLOT_H,6.2]);
  }

  // Re-add fused supports after the cavity subtraction.
  color(SHELL_RGB){
    for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
      difference(){
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
        translate([x,y,FRONT_T+3.8]) cylinder(d=SCREW_D-0.25,h=BASE_TOTAL_D);
      }
    for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
      translate([x-3,y-3,14.6]) cube([6,6,max(0.8,SUPPORT_TOP_Z-14.6)]);
    for(side=[-1,1])
      translate([side*BTN_X-SWITCH_PCB/2-1.0,BTN_Y-SWITCH_PCB/2-1.0,SWITCH_PCB_PLANE_Z+SWITCH_PCB_T])
        difference(){
          cube([SWITCH_PCB+2.0,SWITCH_PCB+2.0,max(0.8,SUPPORT_TOP_Z-(SWITCH_PCB_PLANE_Z+SWITCH_PCB_T))]);
          translate([1.0,1.0,-0.1]) cube([SWITCH_PCB,SWITCH_PCB,20]);
        }
  }
}

module thinness_reference(){
  // Transparent hardware + three witness planes: nominal base, speaker apex,
  // and battery/max apex. Useful for Claude/CAD review; not printable.
  assembly();
  color([0.2,0.8,1.0,0.18]) translate([-BODY_W/2,-BODY_H/2,BASE_TOTAL_D-0.10]) cube([BODY_W,BODY_H,0.20]);
  color([1.0,0.7,0.1,0.18]) translate([-BODY_W/2,-BODY_H/2,SPEAKER_TOTAL_D-0.10]) cube([BODY_W,BODY_H,0.20]);
  color([1.0,0.2,0.2,0.18]) translate([-BODY_W/2,-BODY_H/2,BATTERY_TOTAL_D-0.10]) cube([BODY_W,BODY_H,0.20]);
}

module side_section(){
  // Longitudinal center section showing the contoured rear over the current
  // battery/speaker references. For render/engineering review only.
  intersection(){
    assembly();
    translate([-2.0,-BODY_H/2-2,-1]) cube([4.0,BODY_H+4,BATTERY_TOTAL_D+3]);
  }
}

// ============================================================================
// 2D STICKER TEMPLATE / FIT COUPON
// ============================================================================
module sticker_template_2d(){
  difference(){
    sticker_panel_2d();
    translate([-BTN_X,BTN_Y]) button_face_2d(-1,BTN_CLEAR+0.7);
    translate([ BTN_X,BTN_Y]) button_face_2d( 1,BTN_CLEAR+0.7);
    for(i=[-(GRILL_COUNT-1)/2:1:(GRILL_COUNT-1)/2])
      translate([0,SPKR_Y+i*GRILL_PITCH]) square([GRILL_W+2.0,GRILL_SLOT_H+0.8],center=true);
  }
}

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

module design_front(){
  front_shell();
  // visual inserts only; not printable parts
  color([0.02,0.08,0.16])
    translate([LCD_X-LCD_OPEN_W/2,LCD_Y-LCD_OPEN_H/2,-0.18])
      cube([LCD_OPEN_W,LCD_OPEN_H,0.16]);
  color(PANEL_RGB) translate([0,0,-0.10]) linear_extrude(0.08) sticker_panel_2d();
  translate([-BTN_X,BTN_Y,-BTN_PROTRUSION]) button_cap(-1);
  translate([ BTN_X,BTN_Y,-BTN_PROTRUSION]) button_cap( 1);
}

module assembly(){
  front_shell();
  back_shell();
  board_envelope();
  battery_ref();
  speaker_ref();
  switch_ref(-1); switch_ref(1);
  translate([-BTN_X,BTN_Y,-BTN_PROTRUSION]) button_cap(-1);
  translate([ BTN_X,BTN_Y,-BTN_PROTRUSION]) button_cap( 1);
}

if(part=="design_front") design_front();
else if(part=="front") front_shell();
else if(part=="back") back_shell();
else if(part=="left_button") button_cap(-1);
else if(part=="right_button") button_cap(1);
else if(part=="reference"){ board_envelope(0.8); battery_ref(); speaker_ref(); switch_ref(-1); switch_ref(1); }
else if(part=="sticker") sticker_template_2d();
else if(part=="front_fit_coupon") front_fit_coupon();
else if(part=="thinness_reference") thinness_reference();
else if(part=="side_section") side_section();
else if(part=="presentation") rotate([180,0,0]) assembly();
else assembly();
