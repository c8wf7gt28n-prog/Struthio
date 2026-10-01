// STRUTHIO HANDHELD · checks that the decomposed ambience (static per texel,
// per row, per frame) equals arcade_ambient() itself.
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include "struthio_raster.h"
float st_world_test_(const float in[3], float wx, float wy, const st_textures_t *tx, const st_frame_params_t *fp, float out[3]);
int main(void) {
    st_textures_t tx = {0};
    tx.globe_params[0] = 608; tx.globe_params[1] = 254; tx.globe_params[2] = -118;
    double worst = 0;
    srand(7);
    for (int f = 0; f < 40; f++) {
        st_frame_params_t fp;
        st_frame_params_default(&fp, rand() % 20000, 0, 0);
        st_amb_frame_t af;
        st_amb_frame(&af, &fp, &tx);
        for (int i = 0; i < 20000; i++) {
            float rgb[3] = {rand() / (float)RAND_MAX, rand() / (float)RAND_MAX, rand() / (float)RAND_MAX};
            if (i & 1) { rgb[0] *= .3f; rgb[1] *= .3f; rgb[2] *= .3f; }
            float wx = (float)(rand() % 153600) / 100.0f, wy = (float)(rand() % 230400) / 100.0f;
            if (wx >= 768 && wx < 770) continue;
            float ref[3];
            st_world_test_(rgb, wx, wy, &tx, &fp, ref);
            st_amb_texel_t x;
            st_amb_texel(rgb, wx, wy, &fp, &tx, &x);
            st_amb_row_t row;
            st_amb_row(&af, wy, x.rear, &row);
            float streak, g = st_amb_gain(&af, &row, &x, wx, wy, &streak);
            const float sc[3] = {0.85f, 0.92f, 1.0f};
            for (int c = 0; c < 3; c++) {
                double d = fabs(rgb[c] * g + streak * sc[c] - ref[c]);
                if (d > worst) {
                    worst = d;
                    if (getenv("DEBUG")) printf("t %.0f wx %.2f wy %.2f rgb %.3f %.3f %.3f: gain %.4f streak %.4f ref %.4f got %.4f | rear %d star %d k %.3f lit %.3f gold %.3f cyan %.3f grid %.4f city %.4f sn %.4f\n",
                        fp.ambient_tick, wx, wy, rgb[0], rgb[1], rgb[2], g, streak, ref[c], rgb[c] * g + streak * sc[c], x.rear, x.star, x.star_k, x.lit, x.gold, x.cyan, row.grid, row.city, row.sn10);
                }
            }
        }
    }
    printf("%s: decomposed ambience vs arcade_ambient, worst difference %.5f \n", worst < 0.02 ? "PASS" : "FAIL", worst);
    return worst < 0.02 ? 0 : 1;
}
