// STRUTHIO HANDHELD · golden replay comparator (host).
// Replays each handheld/golden/*.trace through the C input normalizer and C
// simulation; every frame, every tick digest, the digest chain and the final
// state digest must equal the browser authority's.
//   replay [--dump TICK out.json] [--time] trace...
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "struthio_core.h"
#include "struthio_replay.h"

typedef struct { long tick; const char *path; } dump_t;
static void on_tick(void *ctx, long t, const st_state_t *s, const st_events_t *ev) {
    const dump_t *d = (const dump_t *)ctx;
    if (t != d->tick || !d->path) return;
    static char line[1 << 20];
    if (st_canonical_tick(s, ev, line, sizeof line) < 0) return;
    FILE *o = fopen(d->path, "w");
    if (o) { fprintf(o, "%s\n", line); fclose(o); }
}
static uint8_t *slurp(const char *path, size_t *size) {
    FILE *fp = fopen(path, "rb");
    if (!fp) { perror(path); return NULL; }
    fseek(fp, 0, SEEK_END);
    long n = ftell(fp);
    fseek(fp, 0, SEEK_SET);
    uint8_t *data = malloc((size_t)n);
    if (fread(data, 1, (size_t)n, fp) != (size_t)n) { fclose(fp); free(data); return NULL; }
    fclose(fp);
    *size = (size_t)n;
    return data;
}
int main(int argc, char **argv) {
    dump_t dump = {-1, NULL};
    bool timing = false;
    int fails = 0, files = 0;
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--dump") == 0 && i + 2 < argc) { dump.tick = strtol(argv[i + 1], NULL, 10); dump.path = argv[i + 2]; i += 2; continue; }
        if (strcmp(argv[i], "--time") == 0) { timing = true; continue; }
        size_t size;
        uint8_t *data = slurp(argv[i], &size);
        if (!data) { fails++; continue; }
        st_replay_result_t r;
        clock_t c0 = clock();
        bool ok = st_replay(data, size, true, on_tick, &dump, &r);
        double secs = (double)(clock() - c0) / CLOCKS_PER_SEC;
        printf("%s %-7s %6ld ticks  score %6d  round %2d  deaths %3ld  jousts %3ld  eggs %3ld  darts %3ld  chain %.16s\n",
               ok ? "PASS" : "FAIL", r.name, r.ran, r.score, r.round, r.event_counts[ST_EV_PLAYER_DEATH],
               r.event_counts[ST_EV_JOUST_WIN], r.event_counts[ST_EV_EGG], r.event_counts[ST_EV_DART], r.chain);
        if (!ok) printf("     first mismatch %s  (re-run with --dump %ld out.json; browser side: node handheld/tools/golden_export.mjs --dump %s %ld)\n",
                        r.why, r.first_bad_tick, r.name, r.first_bad_tick);
        if (timing) {
            c0 = clock();
            st_replay(data, size, false, NULL, NULL, &r);
            double sim = (double)(clock() - c0) / CLOCKS_PER_SEC;
            printf("     host: %.2f us/tick simulation, %.2f us/tick with digest\n", 1e6 * sim / r.ran, 1e6 * secs / r.ran);
        }
        fails += !ok;
        files++;
        free(data);
    }
    if (!files) { fprintf(stderr, "usage: replay [--dump TICK out.json] [--time] trace...\n"); return 2; }
    if (fails) printf("GOLDEN REPLAY: %d trace(s) FAILED\n", fails);
    else printf("GOLDEN REPLAY: all %d traces bit-exact\n", files);
    return fails ? 1 : 0;
}
