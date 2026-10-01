// STRUTHIO HANDHELD · host tests for the physical wing-button layer, plus a
// DART-trial report: the golden bots' real press timelines are played through
// each trial to count darts the player never asked for.
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_buttons.h"

static st_norm_t norm;
static st_buttons_t btn;
static uint32_t now;
static void run(uint32_t ms, bool l, bool r) { for (uint32_t i = 0; i < ms; i++, now++) st_buttons_sample(&btn, l, r, now); }
static void reset(st_dart_trial_t trial) {
    now = 1000;
    st_norm_init(&norm);
    st_norm_set_mode(&norm, ST_MODE_PLAY);
    st_buttons_init(&btn, &norm, trial, now);
}
static st_input_t frame(void) { return st_norm_frame(&norm, true); }

static void unit_tests(void) {
    st_input_t f;
    // 1. a bouncy press is one press, stamped at its first raw edge
    reset(ST_DART_OFF);
    run(20, false, false);
    for (int i = 0; i < 6; i++) run(1, i % 2 == 0, false);
    run(20, true, false);
    assert(btn.presses[0] == 1);
    f = frame();
    assert(f.flap_edge && f.flap_kind == ST_FLAP_LEFT && !f.chord_edge && f.left);
    // 2. opposite wing 40 ms later (same frame): the pending LEFT becomes STRAIGHT
    reset(ST_DART_OFF);
    run(5, true, false);
    run(40, true, true);
    f = frame();
    assert(f.flap_edge && f.flap_kind == ST_FLAP_STRAIGHT && f.chord_edge && !f.left && !f.right);
    f = frame();
    assert(!f.flap_edge);
    // 3. opposite wing 40 ms later after LEFT was consumed: a fresh STRAIGHT chord
    reset(ST_DART_OFF);
    run(12, true, false);
    f = frame();
    assert(f.flap_kind == ST_FLAP_LEFT);
    run(30, true, true);
    f = frame();
    assert(f.flap_edge && f.flap_kind == ST_FLAP_STRAIGHT && f.chord_edge);
    // 4. opposite wing 150 ms later: two directional flaps
    reset(ST_DART_OFF);
    run(150, true, false);
    run(20, true, true);
    f = frame();
    assert(f.flap_kind == ST_FLAP_LEFT);
    f = frame();
    assert(f.flap_kind == ST_FLAP_RIGHT && !f.chord_edge);
    // 5. trial A: one dart per long single-wing hold; none while both are held
    reset(ST_DART_TRIAL_A_HOLD);
    run(300, true, false);
    (void)frame();
    f = frame();
    assert(btn.darts == 1);
    run(300, true, false);
    assert(btn.darts == 1);
    run(20, false, false);
    run(400, true, true);
    assert(btn.darts == 1);
    // 6. trial B: tap, then press-and-hold within 220 ms darts; a long hold alone does not
    reset(ST_DART_TRIAL_B_TAP_HOLD);
    run(400, false, true);
    assert(btn.darts == 0);
    run(100, false, false);
    run(80, false, true);
    assert(btn.darts == 1);
    while ((f = frame()).flap_edge || f.dart_edge) if (f.dart_edge) break;
    assert(f.dart_edge && f.dart_side == ST_SIDE_RIGHT);
    // 7. trial C: both wings held 200 ms darts once toward facing; single holds never do
    reset(ST_DART_TRIAL_C_BOTH_HOLD);
    run(600, true, false);
    run(30, false, false);
    assert(btn.darts == 0);
    run(20, true, true);
    while ((f = frame()).flap_edge) {}
    run(250, true, true);
    assert(btn.darts == 1);
    f = frame();
    assert(f.dart_edge && f.dart_side == ST_SIDE_NONE);
    run(400, true, true);
    assert(btn.darts == 1);
    // 8. service mode needs both wings for 650 ms
    reset(ST_DART_OFF);
    run(500, true, true);
    assert(!st_buttons_service_requested(&btn, now));
    run(200, true, true);
    assert(st_buttons_service_requested(&btn, now));
    puts("PASS: wing buttons (debounce, chord, DART trials A/B/C, service)");
}

// ---- DART trial report ------------------------------------------------------------------
static void trial_report(const char *path) {
    FILE *fp = fopen(path, "rb");
    if (!fp) return;
    fseek(fp, 0, SEEK_END); long size = ftell(fp); fseek(fp, 0, SEEK_SET);
    uint8_t *d = malloc((size_t)size);
    if (fread(d, 1, (size_t)size, fp) != (size_t)size) { fclose(fp); free(d); return; }
    fclose(fp);
    uint32_t hl = d[8] | d[9] << 8 | d[10] << 16 | (uint32_t)d[11] << 24;
    if (memmem(d + 12, hl, "\"raw\":true", 10)) { free(d); return; }
    const char *name = strrchr(path, '/') ? strrchr(path, '/') + 1 : path;
    for (int trial = 0; trial < 3; trial++) {
        st_buttons_t b;
        st_buttons_init(&b, NULL, (st_dart_trial_t)trial, 0);
        bool L = false, R = false;
        long intended = 0, ticks = 0;
        uint32_t ms = 0;
        const uint8_t *p = d + 12 + hl, *end = d + size;
        for (long t = 0; p < end; t++, ticks++) {
            uint32_t base = (uint32_t)((t * 1000) / 60), next = (uint32_t)(((t + 1) * 1000) / 60);
            int nops = *p++;
            const uint8_t *ops = p;
            p += nops * 2 + 2 + 8;
            int k = 0;
            for (; ms < next; ms++) {
                while (k < nops && base + ops[2 * k] <= ms) {
                    uint8_t op = ops[2 * k + 1];
                    if (op == 1) L = true; else if (op == 2) L = false; else if (op == 3) R = true; else if (op == 4) R = false;
                    else if (op == 5 || op == 6) intended++;
                    k++;
                }
                st_buttons_sample(&b, L, R, ms);
            }
        }
        double minutes = ticks / 3600.0;
        printf("  %-12s trial %-10s %5u darts fired in %4.1f min (%5.1f/min); the bot asked for %ld (%4.1f/min)\n",
               name, st_dart_trial_name((st_dart_trial_t)trial), b.darts, minutes, b.darts / minutes, intended, intended / minutes);
    }
    free(d);
}

int main(int argc, char **argv) {
    unit_tests();
    if (argc > 1) {
        puts("DART trial report (bot press timelines played through each physical trial):");
        for (int i = 1; i < argc; i++) trial_report(argv[i]);
    }
    return 0;
}
