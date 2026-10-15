#include "arc1_transform.h"
#include <inttypes.h>
#include <stdio.h>

static int32_t signed_word(uint32_t value)
{
    return value <= INT32_MAX ? (int32_t)value : -(int32_t)(UINT32_MAX - value) - 1;
}

int main(int argc, char **argv)
{
    FILE *stream;
    unsigned count = 0, i;
    uint32_t v[18];
    if (argc != 2 || !(stream = fopen(argv[1], "r"))) return 2;
    while (fscanf(stream, "%" SCNx32, &v[0]) == 1) {
        arc1_transform_job job;
        arc1_transform_result result;
        for (i = 1; i < 18; ++i)
            if (fscanf(stream, "%" SCNx32, &v[i]) != 1) return 3;
        job.xmin = signed_word(v[0]); job.ymin = signed_word(v[1]);
        job.xmax = signed_word(v[2]); job.ymax = signed_word(v[3]);
        job.m00 = signed_word(v[4]); job.m01 = signed_word(v[5]); job.m02 = signed_word(v[6]);
        job.m10 = signed_word(v[7]); job.m11 = signed_word(v[8]); job.m12 = signed_word(v[9]);
        job.viewport_width = (uint16_t)v[10]; job.viewport_height = (uint16_t)v[11]; job.tag = v[12];
        arc1_transform_rectangle(&job, &result);
        if (result.tag != v[12] || result.minx != signed_word(v[13]) ||
            result.miny != signed_word(v[14]) || result.maxx != signed_word(v[15]) ||
            result.maxy != signed_word(v[16]) || result.flags != v[17]) {
            fprintf(stderr, "Mismatch at vector %u\n", count);
            return 1;
        }
        ++count;
    }
    if (ferror(stream) || !feof(stream)) return 4;
    fclose(stream);
    if (!count) return 5;
    printf("PASS C vector runner: %u cases\n", count);
    return 0;
}
