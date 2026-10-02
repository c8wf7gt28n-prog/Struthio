// Cut-away at x = 0 through the control stack: shell, carrier, CM1 rocker and keys, CP1,
// PUI speaker between its gaskets and the closed rear cavity, board and battery. Preview only.
use <../STRUTHIO15.scad>
intersection(){
  union(){ front_shell(); back_shell(); cm1_mat(); cm1_pills(); cp1(); speaker_ref(); battery_ref(); board_envelope(0.9); }
  translate([0,-80,-10]) cube([60,160,60]);
}
