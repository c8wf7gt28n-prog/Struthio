// Both wing caps as the player sees them (installed, viewed from the front). Preview only.
use <../STRUTHIO084.scad>
rotate([0,180,0]) for(s=[-1,1]) translate([s*17,0,0]) button_cap(s);
