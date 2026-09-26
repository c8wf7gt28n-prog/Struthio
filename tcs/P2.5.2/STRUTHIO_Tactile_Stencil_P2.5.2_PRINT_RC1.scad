// STRUTHIO TACTILE STENCIL — P2.5.2 PRINT RC1 — HIGH QUALITY QC
// Derived from P2.5.0 DUAL WING CONTROL and the locked P2.4.8 Cadillac-quality chassis.
// Goal: preserve the proven P2.4.8 Cadillac-quality chassis and fit while changing ONLY the physical control apertures to the new dual-wing circular layout measured from the current game screenshot.
// Changes from P2.4.6:
// - rear / bottom plate retained at the premium 2.80 mm thickness
// - preserves the thicker top rail and local FLAP reinforcement
// - rounds/softens exterior transitions and checker texture for a production-quality surface
// - preserves phone pocket width/depth, seat, visibility margin, preload pads, front/back thickness, checker texture, lettering, and exterior silhouette
// - replaces old pill + FLAP openings with two equal circular wing-button apertures; no center divider

$fn = 56;

// ---------- phone / fit ----------
phone_w = 64.21;
phone_d = 7.65;
pocket_w = 65.05;
pocket_d = 8.15;
overall_w = 77.0398404;
x_mesh_cal = 0.0199202;
overall_h = 51.29244;
phone_seat_y=1.60;
rear_wall = 2.80;
side = (overall_w-pocket_w)/2;
z_glass = rear_wall+pocket_d;

// ---------- front depth ----------
front_face_th = 2.15;
base_front_z = z_glass + front_face_th;
overall_d = z_glass + 2.80;

// ---------- UI geometry: DUAL WING CONTROL, measured from IMG_3761.jpeg ----------
// Screenshot: 709 x 1536 px. Gold outer rings measured at x=110..272 and x=436..598,
// y=1268..1431, giving centers (191, 1349.5) and (517, 1349.5).
// Mapped to the proven iPhone 13 mini / TCS coordinate frame.
left_wing_cx=25.22084;
right_wing_cx=51.73766;
wing_cy=20.04634;
ui_wing_d=13.29971;
visibility_margin=0.65;
wing_d=ui_wing_d+2*visibility_margin; // 14.59971 mm through opening

// Preserve P2.4.8 exterior silhouette exactly; these legacy values drive only the existing right-side reinforcement lobe.
legacy_flap_cx=57.82586+x_mesh_cal;
legacy_flap_cy=25.45927+phone_seat_y;
legacy_ui_flap_d=15.13;
legacy_flap_d=legacy_ui_flap_d+2*visibility_margin;
// ---------- shaping ----------
body_y0=0.0;
body_y1=38.40; // increased from 35.40 to thicken the bar above LEFT/RIGHT and FLAP openings
body_r=7.35;
waist_x0=27.2;
waist_w=22.6;
waist_h=4.8;
ear_w=8.55;
ear_root_y=27.3;
outer_round=2.10; // increased edge blend; outer silhouette remains essentially unchanged
bottom_port_w=36.0;
bottom_port_h=8.0;
entry_flare_each=0.50;
entry_flare_h=5.0;
flap_reinforce_web=3.55; // locally thickened above FLAP; preserves global rail and screen intrusion

// ---------- recessed hole layering ----------
layer1_extra = 0.34;
layer1_depth = 0.35;
layer2_extra = 0.12;
layer2_depth = 0.75;
contact_backstep = 0.40;
contact_ring_extra = 0.80;
flap_lobe_r=legacy_flap_d/2 + layer1_extra + flap_reinforce_web;

// ---------- texture / branding ----------
side_tex_depth=0.20;
side_tex_cell=2.55;
side_tex_square=1.65;
back_tex_depth=0.15;
back_tex_cell=3.05;
back_tex_square=2.05;
side_tex_radius=0.42;
back_tex_radius=0.50;
preload_pad_t=0.20;
preload_pad_w=18.5;
preload_pad_h=10.5;
word_h=0.55;
word_size=3.08;
word_y=9.4;
brand_font="DejaVu Sans:style=Bold Oblique";
brand_spacing=1.10;

// Rear identity details. QR payload is literal text: R.A. PEDDYCOART. QR error correction: Level M (~15% codeword restoration); retained because this exact polygon has been mesh-verified.
qr_module_pitch=0.70;
qr_quiet_modules=4;
qr_symbol_modules=21;
qr_total_modules=qr_symbol_modules+2*qr_quiet_modules;
qr_size=qr_total_modules*qr_module_pitch; // 20.30 mm
qr_center_x=overall_w/2;
qr_y0=11.30;
qr_depth=0.40;
qr_clear_pad=1.40;
sig_text="R.A. PEDDYCOART";
sig_font="DejaVu Sans:style=Book";
sig_size=2.15;
sig_spacing=1.10;
sig_y=6.70;
sig_depth=0.30;
sig_stroke_boost=0.06;

module rounded_rect_2d(w,h,r){
    rr=min(r,min(w,h)/2-0.001);
    hull(){
        translate([rr,rr]) circle(r=rr);
        translate([w-rr,rr]) circle(r=rr);
        translate([rr,h-rr]) circle(r=rr);
        translate([w-rr,h-rr]) circle(r=rr);
    }
}

module texture_round_square_2d(s,r){
    rr=min(r,s/2-0.001);
    hull(){
        translate([rr,rr]) circle(r=rr,$fn=12);
        translate([s-rr,rr]) circle(r=rr,$fn=12);
        translate([rr,s-rr]) circle(r=rr,$fn=12);
        translate([s-rr,s-rr]) circle(r=rr,$fn=12);
    }
}
module pill_2d(w,h){ rounded_rect_2d(w,h,h/2-0.001); }
module left_wing_opening(extra=0){ translate([left_wing_cx,wing_cy]) circle(d=wing_d+2*extra); }
module right_wing_opening(extra=0){ translate([right_wing_cx,wing_cy]) circle(d=wing_d+2*extra); }
module openings_2d(extra=0){ union(){ left_wing_opening(extra); right_wing_opening(extra); } }

module lower_body_2d(){
    difference(){
        translate([0,body_y0]) rounded_rect_2d(overall_w,body_y1-body_y0,body_r);
        translate([waist_x0,-0.2]) rounded_rect_2d(waist_w,waist_h+0.2,3.65);
    }
}
module left_ear_2d(){
    hull(){
        translate([ear_w/2,ear_root_y+ear_w/2]) circle(r=ear_w/2);
        translate([ear_w/2,overall_h-4.0]) circle(r=3.55);
        translate([6.15,overall_h-3.55]) circle(r=2.55);
        translate([5.35,41.1]) circle(r=3.1);
    }
}
module right_ear_2d(){ mirror([1,0,0]) translate([-overall_w,0]) left_ear_2d(); }
module flap_reinforcement_2d(){ translate([legacy_flap_cx,legacy_flap_cy]) circle(r=flap_lobe_r); }
module outer_profile_2d(){ union(){ lower_body_2d(); flap_reinforcement_2d(); left_ear_2d(); right_ear_2d(); } }

module rounded_outer_solid(){
    minkowski(){
        translate([0,0,outer_round])
            linear_extrude(height=base_front_z-2*outer_round)
                offset(delta=-outer_round) outer_profile_2d();
        sphere(r=outer_round,$fn=20);
    }
}

module phone_pocket_cut(){
    translate([side,phone_seat_y,rear_wall])
        linear_extrude(height=pocket_d+0.02)
            rounded_rect_2d(pocket_w,overall_h-phone_seat_y+2.0,2.1);
}

module layered_control_cuts(){
    translate([0,0,z_glass-contact_backstep])
        linear_extrude(height=base_front_z-(z_glass-contact_backstep)+0.02)
            openings_2d(0);
    translate([0,0,base_front_z-layer2_depth])
        linear_extrude(height=layer2_depth+0.02)
            openings_2d(layer2_extra);
    translate([0,0,base_front_z-layer1_depth])
        linear_extrude(height=layer1_depth+0.02)
            openings_2d(layer1_extra);
}

module bottom_port_cut(){
    translate([0,0,rear_wall-0.08])
        linear_extrude(height=pocket_d+0.16)
            translate([(overall_w-bottom_port_w)/2,-0.3])
                rounded_rect_2d(bottom_port_w,bottom_port_h,2.35);
}
module entry_flares(){
    translate([0,0,rear_wall-0.1]) linear_extrude(height=pocket_d+0.2)
        polygon([[side+0.10,overall_h-entry_flare_h],[side+0.10,overall_h+0.3],[side-entry_flare_each-0.20,overall_h+0.3]]);
    translate([0,0,rear_wall-0.1]) linear_extrude(height=pocket_d+0.2)
        polygon([[overall_w-side-0.10,overall_h-entry_flare_h],[overall_w-side-0.10,overall_h+0.3],[overall_w-side+entry_flare_each+0.20,overall_h+0.3]]);
}

module side_checker_cuts(){
    // Premium rounded-square checker recesses. Rounded corners avoid the cheap, machined-cube look
    // and reduce local stress concentration while preserving the centered tactile pattern.
    for (side_i=[0,1])
        for (row=[0:7])
            for (col=[0:2])
                if ((row+col)%2==0){
                    yy=9.4 + row*side_tex_cell;
                    side_field_h=(3-1)*side_tex_cell + side_tex_square;
                    side_z0=(overall_d-side_field_h)/2;
                    zz=side_z0 + col*side_tex_cell;
                    if (side_i==0)
                        translate([-0.02,yy,zz+side_tex_square])
                            rotate([0,90,0])
                                linear_extrude(height=side_tex_depth+0.04)
                                    texture_round_square_2d(side_tex_square,side_tex_radius);
                    else
                        translate([overall_w+0.02,yy,zz])
                            rotate([0,-90,0])
                                linear_extrude(height=side_tex_depth+0.04)
                                    texture_round_square_2d(side_tex_square,side_tex_radius);
                }
}
module back_checker_cuts(){
    // Geometrically centered rear checker field with a protected identity zone.
    // QC fix: clear by tile bounds, not tile center, so no texture can intrude into the QR quiet zone or signature field.
    back_cols=13;
    back_rows=7;
    back_field_w=(back_cols-1)*back_tex_cell + back_tex_square;
    back_field_h=(back_rows-1)*back_tex_cell + back_tex_square;
    back_x0=(overall_w-back_field_w)/2;
    back_y0=(body_y1-back_field_h)/2;
    qr_clear_x0=qr_center_x-qr_size/2-qr_clear_pad;
    qr_clear_x1=qr_center_x+qr_size/2+qr_clear_pad;
    qr_clear_y0=qr_y0-qr_clear_pad;
    qr_clear_y1=qr_y0+qr_size+qr_clear_pad;
    sig_clear_x0=overall_w/2-15.5;
    sig_clear_x1=overall_w/2+15.5;
    sig_clear_y0=sig_y-1.9;
    sig_clear_y1=sig_y+1.9;
    for (row=[0:back_rows-1])
        for (col=[0:back_cols-1])
            if ((row+col)%2==0){
                xx=back_x0 + col*back_tex_cell;
                yy=back_y0 + row*back_tex_cell;
                tile_x1=xx+back_tex_square;
                tile_y1=yy+back_tex_square;
                hits_qr = !(tile_x1 <= qr_clear_x0 || xx >= qr_clear_x1 || tile_y1 <= qr_clear_y0 || yy >= qr_clear_y1);
                hits_sig = !(tile_x1 <= sig_clear_x0 || xx >= sig_clear_x1 || tile_y1 <= sig_clear_y0 || yy >= sig_clear_y1);
                if (!hits_qr && !hits_sig)
                    translate([xx,yy,-0.02])
                        linear_extrude(height=back_tex_depth+0.04)
                            texture_round_square_2d(back_tex_square,back_tex_radius);
            }
}

module glass_contact_lands(){
    translate([0,0,z_glass-contact_backstep])
        linear_extrude(height=contact_backstep+0.04)
            difference(){ offset(delta=contact_ring_extra) openings_2d(0); openings_2d(0); }
}

module rear_preload_pads(){
    for (xc=[26.0, 50.5])
        translate([xc-preload_pad_w/2, 15.0, rear_wall-0.001])
            linear_extrude(height=preload_pad_t)
                rounded_rect_2d(preload_pad_w, preload_pad_h, 2.2);
}

module brand_text(){
    // Slanted geometric front wordmark: restrained, durable, and more distinctive than generic block text.
    translate([overall_w/2,word_y,base_front_z-0.06])
        linear_extrude(height=word_h+0.06)
            offset(delta=0.050)
                text("STRUTHIO", size=word_size, halign="center", valign="center", spacing=brand_spacing, font=brand_font);
}

module qr_shape_base_062(){
    union(){
        polygon(points=[[3.7100,8.0500],[2.4700,8.0500],[2.4700,9.3100],[3.1100,9.3100],[3.1100,8.6900],[3.7100,8.6900],[3.7100,9.2900],[3.7100,9.3100],[3.7100,9.9300],[4.9700,9.9300],[4.9700,9.3100],[4.9700,9.2900],[4.9700,8.6900],[5.5700,8.6900],[5.5700,9.3100],[7.4500,9.3100],[7.4500,8.6900],[8.0700,8.6900],[8.0700,8.0700],[8.0700,8.0500],[8.0700,7.4500],[8.6700,7.4500],[8.6700,8.0700],[9.2900,8.0700],[9.2900,8.6700],[8.6700,8.6700],[8.6700,9.2900],[8.0500,9.2900],[8.0500,9.9100],[7.4300,9.9100],[7.4300,11.1500],[7.4300,11.1700],[7.4300,11.7900],[8.0500,11.7900],[8.0500,12.3900],[8.0500,12.4100],[8.0500,13.0100],[7.4300,13.0100],[7.4300,13.6300],[7.4300,13.6500],[7.4300,14.8900],[8.0500,14.8900],[8.0500,15.5100],[9.2900,15.5100],[9.3100,15.5100],[9.9300,15.5100],[9.9300,14.8900],[10.5500,14.8900],[10.5500,14.2500],[9.9100,14.2500],[9.9100,14.8700],[9.3100,14.8700],[9.3100,13.6500],[9.9300,13.6500],[9.9300,13.0300],[10.5500,13.0300],[10.5500,12.3900],[9.9300,12.3900],[9.9300,11.7900],[10.5500,11.7900],[10.5500,11.1500],[9.9100,11.1500],[9.9100,11.7700],[9.3100,11.7700],[9.3100,11.1500],[8.6900,11.1500],[8.6900,10.5500],[9.2900,10.5500],[9.3100,10.5500],[9.9300,10.5500],[9.9300,9.9300],[10.5300,9.9300],[10.5300,10.5500],[11.1500,10.5500],[11.1700,10.5500],[11.7900,10.5500],[11.7900,9.3100],[11.7900,9.2900],[11.7900,8.6900],[12.3900,8.6900],[12.4100,8.6900],[13.0100,8.6900],[13.0100,9.2900],[12.3900,9.2900],[12.3900,9.9300],[13.0100,9.9300],[13.0100,10.5500],[13.6300,10.5500],[13.6500,10.5500],[14.8900,10.5500],[14.8900,9.9300],[15.5100,9.9300],[15.5100,9.3100],[15.5100,9.2900],[15.5100,8.0500],[14.8700,8.0500],[14.8700,9.2900],[13.6500,9.2900],[13.6500,8.0700],[14.2700,8.0700],[14.2700,7.4300],[13.6300,7.4300],[13.6300,8.0500],[12.4100,8.0500],[12.4100,7.4500],[13.0300,7.4500],[13.0300,6.8300],[13.6300,6.8300],[13.6500,6.8300],[15.5100,6.8300],[15.5100,6.1900],[14.8900,6.1900],[14.8900,4.9500],[13.6500,4.9500],[13.6300,4.9500],[12.4100,4.9500],[12.4100,4.3500],[13.0300,4.3500],[13.0300,3.7300],[13.6300,3.7300],[13.6500,3.7300],[14.2500,3.7300],[14.2500,4.3500],[15.5100,4.3500],[15.5100,3.0900],[14.8700,3.0900],[14.8700,3.7100],[14.2700,3.7100],[14.2700,2.4700],[13.6500,2.4700],[13.6300,2.4700],[13.0100,2.4700],[13.0100,3.7100],[12.4100,3.7100],[12.3900,3.7100],[11.7900,3.7100],[11.7900,3.0900],[11.1700,3.0900],[11.1700,2.4700],[9.9100,2.4700],[9.9100,3.7100],[9.3100,3.7100],[9.3100,2.4700],[8.0700,2.4700],[8.0500,2.4700],[7.4300,2.4700],[7.4300,3.1100],[8.0500,3.1100],[8.0500,4.3500],[8.6700,4.3500],[8.6700,4.9500],[8.0500,4.9500],[8.0500,5.5900],[8.6700,5.5900],[8.6700,6.8100],[8.0700,6.8100],[8.0500,6.8100],[7.4300,6.8100],[7.4300,8.0500],[6.8300,8.0500],[6.8300,7.4300],[5.5700,7.4300],[5.5700,8.0500],[4.3500,8.0500],[4.3500,7.4300],[3.7100,7.4300],[4.3300,8.0700],[4.3300,8.6700],[3.7300,8.6700],[3.7300,8.0700],[6.8100,8.0700],[6.8100,8.6700],[6.2100,8.6700],[6.2100,8.0700],[8.6900,5.5700],[8.6900,4.9700],[9.2900,4.9700],[9.2900,5.5700],[8.6900,4.3300],[8.6900,3.7300],[9.2900,3.7300],[9.2900,4.3300],[11.1500,3.7300],[11.1500,4.3300],[10.5500,4.3300],[10.5500,3.7300],[11.1700,4.3500],[11.7700,4.3500],[11.7700,4.9500],[11.1700,4.9500],[11.1700,6.8300],[11.7900,6.8300],[11.7900,5.5900],[12.3900,5.5900],[12.4100,5.5900],[13.6300,5.5900],[13.6500,5.5900],[14.2500,5.5900],[14.2500,6.1900],[13.6500,6.1900],[13.6300,6.1900],[13.0100,6.1900],[13.0100,6.8100],[12.3900,6.8100],[12.3900,7.4300],[11.1700,7.4300],[11.1500,8.0700],[11.1500,9.2900],[10.5500,9.2900],[10.5500,8.0700],[9.3100,7.4300],[9.3100,6.8300],[9.9100,6.8300],[9.9100,7.4300],[9.3100,6.1900],[9.3100,5.5900],[9.9300,5.5900],[9.9300,4.9700],[10.5300,4.9700],[10.5300,6.8100],[9.9300,6.8100],[9.9300,6.1900],[9.3100,4.9500],[9.3100,4.3500],[9.9100,4.3500],[9.9100,4.9500],[8.0700,11.7700],[8.0700,11.1700],[8.6700,11.1700],[8.6700,11.7700],[8.0700,10.5300],[8.0700,9.9300],[8.6700,9.9300],[8.6700,10.5300],[8.0700,14.8700],[8.0700,14.2700],[8.6700,14.2700],[8.6700,14.8700],[8.0700,13.6300],[8.0700,13.0300],[8.6700,13.0300],[8.6700,13.6300],[9.3100,13.0100],[9.3100,12.4100],[9.9100,12.4100],[9.9100,13.0100],[9.3100,9.2900],[9.3100,8.6900],[9.9100,8.6900],[9.9100,9.2900],[13.0300,9.9100],[13.0300,9.3100],[13.6300,9.3100],[13.6300,9.9100]], paths=[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89,90,91,92,93,94,95,96,97,98,99,100,101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,121,122,123,124,125,126,127,128,129,130,131,132,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,159,160,161,162,163,164,165],[166,167,168,169],[170,171,172,173],[174,175,176,177],[178,179,180,181],[182,183,184,185],[186,187,188,189],[190,191,192,193,194,195,196,197,198,199,200,201,202,203,204,205],[206,207,208,209],[210,211,212,213],[214,215,216,217,218,219,220,221],[222,223,224,225],[226,227,228,229],[230,231,232,233],[234,235,236,237],[238,239,240,241],[242,243,244,245],[246,247,248,249],[250,251,252,253]], convexity=10);
        polygon(points=[[11.1500,12.3900],[11.1500,12.4100],[11.1500,13.6300],[11.1500,13.6500],[11.1500,15.5100],[12.3900,15.5100],[12.4100,15.5100],[13.6300,15.5100],[13.6500,15.5100],[15.5100,15.5100],[15.5100,13.6500],[15.5100,13.6300],[15.5100,12.4100],[15.5100,12.3900],[15.5100,11.1500],[13.6500,11.1500],[13.6300,11.1500],[12.4100,11.1500],[12.3900,11.1500],[11.1500,11.1500],[12.3900,11.7900],[12.4100,11.7900],[13.6300,11.7900],[13.6500,11.7900],[14.8700,11.7900],[14.8700,12.3900],[14.8700,12.4100],[14.8700,13.6300],[14.8700,13.6500],[14.8700,14.8700],[13.6500,14.8700],[13.6300,14.8700],[12.4100,14.8700],[12.3900,14.8700],[11.7900,14.8700],[11.7900,13.6500],[11.7900,13.6300],[11.7900,12.4100],[11.7900,12.3900],[11.7900,11.7900]], paths=[[0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19],[20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39]], convexity=10);
        polygon(points=[[12.3900,13.6300],[12.3900,13.6500],[12.3900,14.2700],[13.6300,14.2700],[13.6500,14.2700],[14.2700,14.2700],[14.2700,13.6500],[14.2700,13.6300],[14.2700,12.3900],[13.6500,12.3900],[13.6300,12.3900],[12.3900,12.3900]], paths=[[0,1,2,3,4,5,6,7,8,9,10,11]], convexity=10);
        polygon(points=[[2.4700,6.8300],[6.8300,6.8300],[6.8300,2.4700],[2.4700,2.4700],[3.1100,6.1900],[3.1100,3.1100],[6.1900,3.1100],[6.1900,6.1900]], paths=[[0,1,2,3],[4,5,6,7]], convexity=10);
        polygon(points=[[2.4700,11.1500],[2.4700,12.3900],[2.4700,12.4100],[2.4700,13.6300],[2.4700,13.6500],[2.4700,15.5100],[6.8300,15.5100],[6.8300,13.6500],[6.8300,13.6300],[6.8300,12.4100],[6.8300,12.3900],[6.8300,11.1500],[6.1900,12.3900],[6.1900,12.4100],[6.1900,13.6300],[6.1900,13.6500],[6.1900,14.8700],[3.1100,14.8700],[3.1100,13.6500],[3.1100,13.6300],[3.1100,12.4100],[3.1100,12.3900],[3.1100,11.7900],[6.1900,11.7900]], paths=[[0,1,2,3,4,5,6,7,8,9,10,11],[12,13,14,15,16,17,18,19,20,21,22,23]], convexity=10);
        polygon(points=[[6.8300,9.9100],[6.1900,9.9100],[6.1900,10.5500],[6.8300,10.5500]], paths=[[0,1,2,3]], convexity=10);
        polygon(points=[[3.7100,5.5900],[5.5900,5.5900],[5.5900,3.7100],[3.7100,3.7100]], paths=[[0,1,2,3]], convexity=10);
        polygon(points=[[3.7100,13.6300],[3.7100,13.6500],[3.7100,14.2700],[5.5900,14.2700],[5.5900,13.6500],[5.5900,13.6300],[5.5900,12.3900],[3.7100,12.3900]], paths=[[0,1,2,3,4,5,6,7]], convexity=10);
        polygon(points=[[3.1100,9.9100],[2.4700,9.9100],[2.4700,10.5500],[3.1100,10.5500]], paths=[[0,1,2,3]], convexity=10);
    }
}
module qr_shape_2d(){
    // Mesh-validated Version-1 / Level-M QR polygon, scaled from 0.62 to 0.70 mm modules.
    scale([qr_module_pitch/0.62, qr_module_pitch/0.62]) qr_shape_base_062();
}

module qr_cut(){
    // Mirrored in X so the debossed code reads correctly from the exterior rear face.
    translate([qr_center_x,qr_y0,-0.02])
        mirror([1,0,0])
            translate([-qr_size/2,0,0])
                linear_extrude(height=qr_depth+0.04)
                    qr_shape_2d();
}

module signature_cut(){
    // Discreet rear maker signature, mirrored for correct outside-back reading.
    translate([overall_w/2,sig_y,-0.02])
        mirror([1,0,0])
            linear_extrude(height=sig_depth+0.04)
                offset(delta=sig_stroke_boost)
                    text(sig_text,size=sig_size,halign="center",valign="center",spacing=sig_spacing,font=sig_font);
}

module base_shell(){
    difference(){
        rounded_outer_solid();
        phone_pocket_cut();
        layered_control_cuts();
        bottom_port_cut();
        entry_flares();
        side_checker_cuts();
        back_checker_cuts();
        qr_cut();
        signature_cut();
    }
}

module stencil(){
    union(){
        base_shell();
        glass_contact_lands();
        rear_preload_pads();
        brand_text();
    }
}

// P2.5.2 PRINT RC1: QC fixes are limited to printable identity details. Fit-critical P2.5.0/P2.5.1 geometry remains locked.
stencil();
