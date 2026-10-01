// STRUTHIO HANDHELD · scene-builder check (host).
// Replays each golden trace through the C sim, then the C scene builder exactly
// as the browser session does (events -> feel/popups/banners, camera, scene),
// and compares every tick's instance-list hash with the browser's own
// (handheld/build/reference/<trace>.ihash, from tools/reference/capture.mjs).
//   scene_check [--dump TICK out.json] trace...
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "struthio_core.h"
#include "struthio_replay.h"
#include "struthio_scene.h"

typedef struct {
    st_scene_t sc;
    st_camera_t cam;
    st_pre_tick_t pre;
    st_quads_t quads;
    const uint32_t *want;
    long n_want, first_bad, checked, dump_tick;
    const char *dump_path;
    st_gameover_info_t info;
} ctx_t;

static void pre(void *c_, long t, const st_state_t *s) { (void)t; ctx_t *c = c_; c->pre = st_scene_pre_tick(s); }
static void dump(const st_quads_t *q, const char *path) {
    FILE *o = fopen(path, "w");
    if (!o) return;
    fprintf(o, "[");
    for (int i = 0; i < q->n; i++) {
        const st_quad_t *e = &q->q[i];
        fprintf(o, "%s[%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%.17g,%d]", i ? "," : "", e->x, e->y, e->w, e->h, e->sx, e->sy, e->sw, e->sh, e->z, e->flags);
    }
    fprintf(o, "]\n");
    fclose(o);
}
static void post(void *c_, long t, const st_state_t *s, const st_events_t *ev) {
    ctx_t *c = c_;
    st_scene_on_events(&c->sc, s, ev, &c->pre);
    for (int i = 0; i < ev->n; i++)
        if (ev->e[i].type == ST_EV_GAMEOVER) c->info = (st_gameover_info_t){s->sim.score, s->tower.round, s->sim.score, s->sim.score > 0, true};
    static const char *const ITEMS[2] = {"NEW RUN", "TITLE"};
    st_menu_t menu = {ITEMS, 2, 0, c->info};
    int32_t top = st_camera_resolve(&c->cam, s);
    st_scene_build(&c->sc, s, top, &menu, &c->quads);
    uint32_t h = st_quads_hash(&c->quads);
    if (t == c->dump_tick && c->dump_path) dump(&c->quads, c->dump_path);
    if (t < c->n_want) {
        c->checked++;
        if (h != c->want[t] && c->first_bad < 0) c->first_bad = t;
    }
}
static void *slurp(const char *path, size_t *size) {
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, 0, SEEK_SET);
    void *d = malloc((size_t)n);
    if (fread(d, 1, (size_t)n, f) != (size_t)n) { fclose(f); free(d); return NULL; }
    fclose(f);
    *size = (size_t)n;
    return d;
}
int main(int argc, char **argv) {
    long dump_tick = -1;
    const char *dump_path = NULL, *ref_dir = "../build/reference";
    int fails = 0, files = 0;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "--dump") && i + 2 < argc) { dump_tick = strtol(argv[i + 1], NULL, 10); dump_path = argv[i + 2]; i += 2; continue; }
        if (!strcmp(argv[i], "--ref") && i + 1 < argc) { ref_dir = argv[++i]; continue; }
        size_t size, hsize;
        uint8_t *data = slurp(argv[i], &size);
        const char *base = strrchr(argv[i], '/') ? strrchr(argv[i], '/') + 1 : argv[i];
        char name[64], hp[512];
        snprintf(name, sizeof name, "%.*s", (int)(strlen(base) - 6), base);
        snprintf(hp, sizeof hp, "%s/%s.ihash", ref_dir, name);
        uint32_t *want = slurp(hp, &hsize);
        if (!data || !want) { printf("SKIP %-7s (no %s: run tools/reference/capture.mjs)\n", name, hp); continue; }
        static ctx_t c;
        memset(&c, 0, sizeof c);
        st_scene_init(&c.sc);
        st_camera_reset(&c.cam);
        c.want = want; c.n_want = (long)(hsize / 4); c.first_bad = -1; c.dump_tick = dump_tick; c.dump_path = dump_path;
        st_replay_hooks_t hooks = {&c, pre, post};
        st_replay_result_t r;
        st_replay(data, size, false, &hooks, &r);
        bool ok = c.first_bad < 0 && c.checked == r.ran;
        printf("%s %-7s %6ld ticks: instance lists %s", ok ? "PASS" : "FAIL", name, c.checked, ok ? "equal the browser's on every tick\n" : "");
        if (!ok) printf("first differ at tick %ld (dump: --dump %ld c.json; browser: capture.mjs --list=%s:%ld)\n", c.first_bad, c.first_bad, name, c.first_bad);
        fails += !ok;
        files++;
        free(data); free(want);
    }
    if (!files) return 2;
    printf(fails ? "SCENE CHECK: %d trace(s) FAILED\n" : "SCENE CHECK: all %d traces equal the browser\n", fails ? fails : files);
    return fails ? 1 : 0;
}
