// Renders the firmware's FIRST POWER-ON CHECK screen on the host with the real greybox text + present path
// (layout copied from firmware/main/selftest.c). Values are EXAMPLES: a ONE SLIM, every button pressed, a cell
// at 3.92 V, USB not plugged in.
// Build: cc -std=c11 -I../../core -I../../render selftest_shot.c ../../render/struthio_greybox.c ../../render/struthio_scene.c ../../render/struthio_scene_data.c ../../core/*.c -lm -o selftest_shot && ./selftest_shot > selftest.ppm
#include <stdio.h>
#include <string.h>
#include "struthio_rules.h"
#include "struthio_greybox.h"
int main(void) {
    static uint8_t fb[ST_FB_W * ST_FB_H];
    memset(fb, STR_PAL_INK, sizeof fb);
    int y = 10;
    st_draw_text(fb, 8, y, "STRUTHIO", STR_PAL_GOLD_LIGHT, 2); y += 22;
    st_draw_text(fb, 8, y, "FIRST POWER-ON CHECK", STR_PAL_GOLD, 1); y += 20;
    st_draw_text(fb, 8, y, "PRESS EACH BUTTON ONCE:", STR_PAL_IVORY, 1); y += 14;
    const char *rows[] = {"LEFT WING      OK", "RIGHT WING     OK", "DART LEFT END  OK", "DART RIGHT END OK", "POWER (SIDE)   OK"};
    for (int i = 0; i < 5; i++) { st_draw_text(fb, 16, y, rows[i], STR_PAL_GREEN, 1); y += 12; }
    y += 6;
    st_draw_text(fb, 8, y, "EACH PRESS CLICKS: THAT IS THE", STR_PAL_IVORY_DARK, 1); y += 12;
    st_draw_text(fb, 8, y, "SPEAKER. NO CLICK? CHECK ITS PLUG.", STR_PAL_IVORY_DARK, 1); y += 18;
    st_draw_text(fb, 8, y, "BATTERY 3.92V  OK", STR_PAL_GREEN, 1); y += 12;
    st_draw_text(fb, 8, y, "USB: NOT PLUGGED IN", STR_PAL_IVORY, 1); y += 18;
    st_draw_text(fb, 8, y, "UPSIDE DOWN? HOLD LEFT WING 2 S.", STR_PAL_IVORY_DARK, 1); y += 12;
    st_draw_text(fb, 8, y, "OFF: HOLD THE POWER BUTTON 4 S.", STR_PAL_IVORY_DARK, 1); y += 20;
    st_draw_text(fb, 8, y, "ALL GOOD!", STR_PAL_GREEN, 2); y += 22;
    st_draw_text(fb, 8, y, "PRESS BOTH WINGS TO PLAY.", STR_PAL_GREEN, 1);
    printf("P6\n%d %d\n255\n", ST_PANEL_W, ST_PANEL_H);
    uint16_t line[ST_PANEL_W];
    for (int yy = 0; yy < ST_PANEL_H; yy++) {
        st_present_line(fb, yy, line, false);
        for (int x = 0; x < ST_PANEL_W; x++) { uint16_t c = line[x];
            putchar(((c >> 11) & 31) * 255 / 31); putchar(((c >> 5) & 63) * 255 / 63); putchar((c & 31) * 255 / 31); }
    }
    return 0;
}
