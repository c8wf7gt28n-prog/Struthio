// STRUTHIO HANDHELD · the soundtrack for the handheld: 24 kHz mono s16le in,
// IMA ADPCM out (audio/struthio_audio.h, "STMU"). The loop restarts from the
// encoder's initial state, so the seam is exact; the initial step index is the
// one that codes the first 256 samples best.
//   ffmpeg -i tarmac-at-midnight-loop.mp3 -ac 1 -ar 24000 -f s16le music.raw
//   make_music music.raw build/assets/struthio_music.ima
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const int16_t STEP[89] = {
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
    130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060,
    1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484,
    7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767};
static const int8_t INDEX[16] = {-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8};

typedef struct { int pred, idx; } st_t;
static int encode(st_t *s, int x) {
    int step = STEP[s->idx], diff = x - s->pred, code = 0;
    if (diff < 0) { code = 8; diff = -diff; }
    if (diff >= step) { code |= 4; diff -= step; }
    if (diff >= step >> 1) { code |= 2; diff -= step >> 1; }
    if (diff >= step >> 2) code |= 1;
    // decode exactly as the device does
    int d = step >> 3;
    if (code & 4) d += step;
    if (code & 2) d += step >> 1;
    if (code & 1) d += step >> 2;
    s->pred += (code & 8) ? -d : d;
    if (s->pred > 32767) s->pred = 32767; else if (s->pred < -32768) s->pred = -32768;
    s->idx += INDEX[code];
    if (s->idx < 0) s->idx = 0; else if (s->idx > 88) s->idx = 88;
    return code;
}
int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "usage: make_music in.raw(s16le 24k mono) out.ima\n"); return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    fseek(f, 0, SEEK_END); long bytes = ftell(f); fseek(f, 0, SEEK_SET);
    uint32_t n = (uint32_t)(bytes / 2);
    int16_t *x = malloc((size_t)n * 2);
    if (fread(x, 2, n, f) != n) { perror(argv[1]); return 2; }
    fclose(f);
    int best = 0; double best_err = 1e300;
    for (int i = 0; i < 89; i++) {
        st_t s = {x[0], i}; double e = 0;
        for (uint32_t k = 0; k < 256 && k < n; k++) { encode(&s, x[k]); double d = s.pred - x[k]; e += d * d; }
        if (e < best_err) { best_err = e; best = i; }
    }
    st_t s = {x[0], best};
    uint8_t *code = calloc((n + 1) / 2, 1);
    double sig = 0, err = 0;
    for (uint32_t k = 0; k < n; k++) {
        int c = encode(&s, x[k]);
        code[k >> 1] |= (uint8_t)(k & 1 ? c << 4 : c);
        sig += (double)x[k] * x[k]; err += (double)(s.pred - x[k]) * (s.pred - x[k]);
    }
    FILE *o = fopen(argv[2], "wb");
    if (!o) { perror(argv[2]); return 2; }
    uint8_t h[20] = {'S', 'T', 'M', 'U', 1, 0, 1, 0};
    uint32_t rate = 24000;
    memcpy(h + 8, &rate, 4); memcpy(h + 12, &n, 4);
    int16_t p0 = x[0]; memcpy(h + 16, &p0, 2); h[18] = (uint8_t)best;
    fwrite(h, 1, 20, o); fwrite(code, 1, (n + 1) / 2, o); fclose(o);
    printf("wrote %s: %u samples (%.2f s at 24 kHz), %u bytes, coding SNR %.1f dB\n", argv[2], n, n / 24000.0,
           20 + (n + 1) / 2, 10 * log10(sig / (err > 0 ? err : 1)));
    return 0;
}
