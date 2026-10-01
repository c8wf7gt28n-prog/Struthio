// STRUTHIO HANDHELD · two-core band hand-off vs the AXS15231B's QSPI write
// model (host, pthreads).
//
// The panel gets no row address over QSPI: a band at y 0 starts a frame
// (RAMWR), every other band continues at the write pointer (RAMWRC). This test
// runs the real st_panel_render_bands on two threads (even / odd bands, as the
// firmware's two cores do) into a simulated panel with exactly that model, with
// random delays, and counts bands that would land on the wrong rows:
//   - "mutex" scheme (firmware before this fix): any finished band goes next
//   - "turn" scheme (firmware main.c band_out): band k waits for band k-1
//   band_order_test [frames]
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "struthio_panel.h"

static int frames = 200, scheme;                      // 0 mutex, 1 turn
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static sem_t turn[2];
static int write_ptr;                                 // the panel's row pointer
static long misplaced, sent;
static unsigned seed_base;

static void jitter(unsigned *s) { struct timespec t = {0, (long)(rand_r(s) % 200) * 1000}; nanosleep(&t, NULL); }

// The simulated panel: what board_display_lines sends, as the controller sees it.
static void panel_write(int y0, int rows) {
    int at = y0 == 0 ? 0 : write_ptr;                 // RAMWR resets, RAMWRC continues
    if (at != y0) misplaced++;
    write_ptr = (at + rows) % ST_PANEL_H;
    sent++;
}
static void band_out(void *ctx, int y0, int rows, const uint16_t *px) {
    (void)px;
    unsigned *s = ctx;
    jitter(s);                                         // the other core may finish first
    if (scheme == 0) {
        pthread_mutex_lock(&lock); panel_write(y0, rows); pthread_mutex_unlock(&lock);
    } else {
        int k = y0 / ST_BAND_ROWS, next = (k + 1) % ST_PANEL_BANDS;
        sem_wait(&turn[k & 1]);
        panel_write(y0, rows);
        sem_post(&turn[next & 1]);
    }
}

static st_panel_textures_t tx;
static st_panel_luts_t luts;
static st_quads_t q;
static st_frame_params_t fp;
static st_hud_t hud;
typedef struct { int core; st_panel_work_t w; unsigned seed; } worker_t;
static void *worker(void *arg) {
    worker_t *w = arg;
    for (int f = 0; f < frames; f++)
        st_panel_render_bands(&tx, NULL, &hud, &luts, &q, &fp, w->core, 2, &w->w, band_out, &w->seed);
    return NULL;
}
static long run(int sch) {
    scheme = sch; misplaced = sent = 0; write_ptr = 0;
    sem_init(&turn[0], 0, 1); sem_init(&turn[1], 0, 0);
    static worker_t w[2];
    pthread_t t[2];
    for (int c = 0; c < 2; c++) { memset(&w[c], 0, sizeof w[c]); w[c].core = c; w[c].seed = seed_base + (unsigned)c; pthread_create(&t[c], NULL, worker, &w[c]); }
    for (int c = 0; c < 2; c++) pthread_join(t[c], NULL);
    sem_destroy(&turn[0]); sem_destroy(&turn[1]);
    return misplaced;
}
int main(int argc, char **argv) {
    if (argc > 1) frames = atoi(argv[1]);
    seed_base = (unsigned)time(NULL);
    st_panel_luts_init(&luts);
    st_frame_params_default(&fp, 0, 0, 0);
    q.n = 0;                                           // an empty scene: the hand-off is what is under test
    long bad_mutex = run(0), sent_mutex = sent;
    long bad_turn = run(1), sent_turn = sent;
    printf("  mutex scheme (before): %ld of %ld bands would land on the wrong rows\n", bad_mutex, sent_mutex);
    printf("  turn scheme (main.c):  %ld of %ld bands misplaced\n", bad_turn, sent_turn);
    int ok = bad_turn == 0 && sent_turn == (long)frames * ST_PANEL_BANDS;
    printf(ok ? "BAND ORDER: in-order hand-off holds over %d frames\n" : "BAND ORDER: FAIL over %d frames\n", frames);
    return ok ? 0 : 1;
}
