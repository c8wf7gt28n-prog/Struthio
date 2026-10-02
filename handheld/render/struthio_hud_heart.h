// STRUTHIO HANDHELD · the joust counter's red heart (the handheld's one HUD change from the browser).
// The browser's HUD writes a small "J" before the jousts-left count (x/11). On the handheld that J is a
// red heart. host/make_pak.c paints it into the static HUD layers; host/panel_check.c leaves its box out
// when it compares the HUD with the browser's frames. Panel coordinates (320 x 480).
#pragma once
enum { ST_HEART_X0 = 258, ST_HEART_X1 = 270, ST_HEART_Y0 = 17, ST_HEART_Y1 = 30 };   // the box: J out, heart in
#define ST_HEART_CX 263.5f                 // centre of the heart, level with the "11/11" digits
#define ST_HEART_CY 23.3f
