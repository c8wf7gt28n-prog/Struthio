// Renders the firmware's SERVICE MODE screen on the host with the real greybox
// text + present path (layout copied from firmware/main/service.c). Values are EXAMPLES.
// Build: cc -std=c11 -I../../core -I../../render service_shot.c ../../render/struthio_greybox.c ../../render/struthio_scene.c ../../render/struthio_scene_data.c ../../core/*.c -lm -o service_shot && ./service_shot > service.ppm
#include <stdio.h>
#include <string.h>
#include "struthio_rules.h"
#include "struthio_greybox.h"
int main(void) {
    static uint8_t fb[ST_FB_W * ST_FB_H];
    memset(fb, STR_PAL_INK, sizeof fb);
    st_draw_text(fb, 8, 8, "STRUTHIO SERVICE", STR_PAL_GOLD_LIGHT, 2);
    st_draw_text(fb, 8, 30, "A0 / CORE 1.8.0 PORT / OCT  2 2026", STR_PAL_GOLD, 1);
    st_draw_text(fb, 8, 48, "RESET 1  PSRAM 8192K  RAM 312K", STR_PAL_IVORY, 1);
    st_draw_text(fb, 8, 72, "LEFT UP 12   RIGHT DOWN 9", STR_PAL_CYAN_LIGHT, 1);
    st_draw_text(fb, 8, 84, "DART B  FIRED 3", STR_PAL_CYAN_LIGHT, 1);
    st_draw_text(fb, 8, 108, "GOLDEN PASS 10011 TICKS", STR_PAL_GREEN, 1);
    st_draw_text(fb, 8, 120, "SIM 180 US/TICK  +DIGEST 420", STR_PAL_IVORY, 1);
    st_draw_text(fb, 8, 132, "PANEL 9.8 MS/FRAME 102 FPS", STR_PAL_IVORY, 1);
    st_draw_text(fb, 8, 160, "LEFT: NEXT DART TRIAL", STR_PAL_IVORY_DARK, 1);
    st_draw_text(fb, 8, 172, "RIGHT: RUN CHECKS AGAIN", STR_PAL_IVORY_DARK, 1);
    st_draw_text(fb, 8, 184, "POWER-CYCLE TO PLAY", STR_PAL_IVORY_DARK, 1);
    printf("P6\n%d %d\n255\n", ST_PANEL_W, ST_PANEL_H);
    uint16_t line[ST_PANEL_W];
    for (int y = 0; y < ST_PANEL_H; y++) {
        st_present_line(fb, y, line, false);
        for (int x = 0; x < ST_PANEL_W; x++) { uint16_t c = line[x];
            putchar(((c >> 11) & 31) * 255 / 31); putchar(((c >> 5) & 63) * 255 / 63); putchar((c & 31) * 255 / 31); }
    }
    return 0;
}
