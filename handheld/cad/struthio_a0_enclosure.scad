/*
 STRUTHIO ESP32-S3 Handheld - Prototype A0 enclosure
 v0.4 engineering envelope model
 Units: mm

 Based on Waveshare ESP32-S3-Touch-LCD-3.5B published bare-board envelope:
 92.44 x 61.00 x 11.50 mm, rotated portrait in this housing.
 Active LCD: 48.96 x 73.44 mm, centered in board glass.

 This is a FIT/ENGINEERING prototype, not final industrial-design surface authority.
 The official vendor 3D solid should replace board_envelope() before A1 detail freeze.

 Export examples:
 openscad -o stl/struthio_a0_front.stl -D 'part="front"' struthio_a0_enclosure.scad
 openscad -o stl/struthio_a0_back.stl -D 'part="back"' struthio_a0_enclosure.scad
 openscad -o stl/struthio_a0_left_button.stl -D 'part="left_button"' struthio_a0_enclosure.scad
 openscad -o stl/struthio_a0_right_button.stl -D 'part="right_button"' struthio_a0_enclosure.scad
*/

$fn = 64;
part = "assembly"; // assembly, front, back, left_button, right_button, reference

// ---- DEVICE ENVELOPE ----
BODY_W = 88;
BODY_H = 128;
BODY_D = 25;
BODY_R = 8;
FRONT_T = 3.0;
BACK_D = BODY_D - FRONT_T;
WALL = 2.4;
BACK_WALL = 2.6;
SUPPORT_TOP_Z = BODY_D - BACK_WALL + 0.60; // overlap rear wall so all internal supports fuse into one printable body
FIT = 0.35;

// ---- WAVESHARE 3.5B BARE ASSEMBLY (ROTATED PORTRAIT) ----
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

// ---- CONTROLS ----
BTN_Y = -47.5;
BTN_X = 21.5;
BTN_CLEAR = 0.45;
BTN_FLANGE = 1.25;
BTN_FACE_T = 3.0;
BTN_FLANGE_T = 1.0;
BTN_STEM_Z = 3.1;
BTN_STEM_W = 5.0;
BTN_STEM_H = 5.0;

// Candidate A0 switch: Omron B3F-4050 / B3F-4055 footprint class, 12 x 12 mm.
SWITCH_BODY = 12.5;
SWITCH_PCB = 18.0;
SWITCH_PCB_T = 1.6;
SWITCH_PCB_PLANE_Z = 13.7;  // tune with shim after physical switch/cap measurement

// ---- SPEAKER / BATTERY REFERENCE ----
SPKR_D = 28.0;
SPKR_T = 5.0;
SPKR_Y = -47.0;
BAT_W = 36.0;
BAT_H = 52.0;
BAT_T = 6.2;
BAT_Y = 13.5;

// ---- FASTENERS ----
SCREW_X = 37.0;
SCREW_Y = 55.5;
SCREW_D = 2.2;
POST_OD = 6.0;

module rr2d(w,h,r){
  hull(){
    for(x=[-w/2+r,w/2-r], y=[-h/2+r,h/2-r]) translate([x,y]) circle(r=r);
  }
}

module body2d(delta=0){ offset(delta=delta) rr2d(BODY_W,BODY_H,BODY_R); }

module wing2d(side=-1, delta=0){
  // side -1 = left, +1 = right
  pts=[[-11,-8],[7,-10],[11,4],[5,10],[-9,8],[-12,0]];
  if(side<0) offset(delta=delta) polygon(points=pts);
  else scale([-1,1]) offset(delta=delta) polygon(points=pts);
}

module button_cap(side=-1){
  // flange stays behind front plate, face projects through opening
  color([0.95,0.62,0.04]) union(){
    linear_extrude(BTN_FLANGE_T) wing2d(side, BTN_FLANGE);
    translate([0,0,BTN_FLANGE_T]) linear_extrude(BTN_FACE_T) wing2d(side, 0);
    translate([-BTN_STEM_W/2,-BTN_STEM_H/2,BTN_FLANGE_T+BTN_FACE_T])
      cube([BTN_STEM_W,BTN_STEM_H,BTN_STEM_Z]);
  }
}

module screen_cut(){
  translate([LCD_X,LCD_Y,-0.2]) linear_extrude(FRONT_T+0.5) rr2d(LCD_OPEN_W,LCD_OPEN_H,1.6);
}

module button_cut(side=-1){
  translate([side*BTN_X,BTN_Y,-0.2]) linear_extrude(FRONT_T+0.5) wing2d(side, BTN_CLEAR);
}

module speaker_grill_cuts(){
  // visual/acoustic slots centered between wing buttons
  for(i=[-2.5:1:2.5]){
    translate([-8, SPKR_Y + i*3.0, -0.2]) cube([16,1.35,FRONT_T+0.5]);
  }
}

module front_shell(){
  color([0.12,0.12,0.115]) difference(){
    union(){
      // main face plate
      linear_extrude(FRONT_T) body2d();
      // shallow internal perimeter locating lip
      translate([0,0,FRONT_T]) linear_extrude(1.5)
        difference(){ body2d(-WALL-0.35); body2d(-WALL-1.8); }
      // board side locator pads, not mounting-hole authority
      for(x=[-BOARD_W/2-0.6, BOARD_W/2-1.4])
        translate([x, BOARD_Y-BOARD_H/2+5, FRONT_T]) cube([2.0,BOARD_H-10,1.5]);
    }
    screen_cut();
    button_cut(-1); button_cut(1);
    speaker_grill_cuts();
    // four assembly screw pass holes
    for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
      translate([x,y,-0.5]) cylinder(d=SCREW_D+0.45,h=FRONT_T+2.5);
  }
}

module board_envelope(alpha=0.55){
  // reference only: orientation/volume from official dimension drawing
  color([0.1,0.45,0.25,alpha]) translate([BOARD_X-BOARD_W/2,BOARD_Y-BOARD_H/2,BOARD_Z_FRONT])
    cube([BOARD_W,BOARD_H,BOARD_D]);
  // active display reference
  color([0.05,0.15,0.25,0.7]) translate([LCD_X-LCD_W/2,LCD_Y-LCD_H/2,FRONT_T+0.08])
    cube([LCD_W,LCD_H,0.25]);
}

module battery_ref(){
  color([0.75,0.72,0.68,0.65]) translate([-BAT_W/2,BAT_Y-BAT_H/2,14.7]) cube([BAT_W,BAT_H,BAT_T]);
}

module speaker_ref(){
  color([0.15,0.15,0.15,0.8]) translate([0,SPKR_Y,15.6]) cylinder(d=SPKR_D,h=SPKR_T);
}

module switch_ref(side=-1){
  color([0.1,0.35,0.15,0.8]) translate([side*BTN_X-SWITCH_PCB/2,BTN_Y-SWITCH_PCB/2,SWITCH_PCB_PLANE_Z])
    cube([SWITCH_PCB,SWITCH_PCB,SWITCH_PCB_T]);
  color([0.15,0.15,0.15,0.85]) translate([side*BTN_X-SWITCH_BODY/2,BTN_Y-SWITCH_BODY/2,SWITCH_PCB_PLANE_Z-SWITCH_BODY/8])
    cube([SWITCH_BODY,SWITCH_BODY,7.3]);
}

module back_shell(){
  color([0.10,0.10,0.095]) difference(){
    union(){
      // rear tray, z=FRONT_T to BODY_D
      translate([0,0,FRONT_T]) linear_extrude(BACK_D) body2d();
      // screw posts from back interior surface toward front
      for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
      // board rear support pads outside central battery footprint
      for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
        translate([x-3,y-3,14.6]) cube([6,6,SUPPORT_TOP_Z-14.6]);
      // switch PCB support islands
      for(side=[-1,1]) translate([side*BTN_X-SWITCH_PCB/2-1.2,BTN_Y-SWITCH_PCB/2-1.2,SWITCH_PCB_PLANE_Z+SWITCH_PCB_T])
        difference(){
          cube([SWITCH_PCB+2.4,SWITCH_PCB+2.4,SUPPORT_TOP_Z-(SWITCH_PCB_PLANE_Z+SWITCH_PCB_T)]);
          translate([1.2,1.2,-0.1]) cube([SWITCH_PCB,SWITCH_PCB,BODY_D]);
        }
      // battery side rails on back floor
      for(x=[-BAT_W/2-1.4, BAT_W/2+0.4])
        translate([x,BAT_Y-BAT_H/2-1, SUPPORT_TOP_Z-7.4]) cube([1.0,BAT_H+2,7.4]);
    }
    // hollow main cavity, leaving WALL perimeter and BACK_WALL floor
    translate([0,0,FRONT_T-0.2]) linear_extrude(BACK_D-BACK_WALL+0.25) body2d(-WALL);
    // recreate board/battery/switch support features by subtracting only from cavity above;
    // screw through-holes
    for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
      translate([x,y,FRONT_T+3]) cylinder(d=SCREW_D-0.25,h=BODY_D);
    // bottom USB-C panel-extension cutout (for short male-female extension; board port is internal)
    translate([-7.0,-BODY_H/2-0.2,10.0]) cube([14.0,WALL+0.6,8.0]);
    // side service slot for onboard PWR/BOOT/RESET access during A0
    translate([BODY_W/2-WALL-0.2,1.0,7.0]) cube([WALL+0.6,24.0,8.0]);
  }
  // Add supports back after main cavity boolean so they actually exist.
  color([0.10,0.10,0.095]){
    for(x=[-SCREW_X,SCREW_X], y=[-SCREW_Y,SCREW_Y])
      difference(){
        translate([x,y,FRONT_T+4]) cylinder(d=POST_OD,h=SUPPORT_TOP_Z-(FRONT_T+4));
        translate([x,y,FRONT_T+3.8]) cylinder(d=SCREW_D-0.25,h=BACK_D);
      }
    // board support pads to locate rear component plane without flexing glass
    for(x=[-27,27], y=[BOARD_Y-38, BOARD_Y+38])
      translate([x-3,y-3,14.6]) cube([6,6,SUPPORT_TOP_Z-14.6]);
    // battery side rails re-added after cavity subtraction; overlap rear wall for a single printable body
    for(x=[-BAT_W/2-1.4, BAT_W/2+0.4])
      translate([x,BAT_Y-BAT_H/2-1, SUPPORT_TOP_Z-7.4]) cube([1.0,BAT_H+2,7.4]);
    // individual switch PCB ledges, center left open for speaker
    for(side=[-1,1])
      translate([side*BTN_X-SWITCH_PCB/2-1.0,BTN_Y-SWITCH_PCB/2-1.0,SWITCH_PCB_PLANE_Z+SWITCH_PCB_T])
        difference(){
          cube([SWITCH_PCB+2.0,SWITCH_PCB+2.0,SUPPORT_TOP_Z-(SWITCH_PCB_PLANE_Z+SWITCH_PCB_T)]);
          translate([1.0,1.0,-0.1]) cube([SWITCH_PCB,SWITCH_PCB,BODY_D]);
        }
  }
}

module assembly(){
  front_shell();
  back_shell();
  board_envelope();
  battery_ref();
  speaker_ref();
  switch_ref(-1); switch_ref(1);
  translate([-BTN_X,BTN_Y,0.1]) button_cap(-1);
  translate([ BTN_X,BTN_Y,0.1]) button_cap( 1);
}

if(part=="front") front_shell();
else if(part=="back") back_shell();
else if(part=="left_button") button_cap(-1);
else if(part=="right_button") button_cap(1);
else if(part=="reference"){ board_envelope(0.8); battery_ref(); speaker_ref(); switch_ref(-1); switch_ref(1); }
else if(part=="presentation") rotate([180,0,0]) assembly();
else assembly();
