// Side view of the closed handheld (front face to the left). Preview only.
use <../struthio_handheld.scad>
rotate([0,-90,0]) physical() { front_shell(); back_shell(); cm1_mat(); }
