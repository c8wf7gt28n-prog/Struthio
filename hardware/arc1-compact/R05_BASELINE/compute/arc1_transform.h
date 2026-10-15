#ifndef ARC1_TRANSFORM_H
#define ARC1_TRANSFORM_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ARC1_TRANSFORM_ABI_VERSION 1u
#define ARC1_TRANSFORM_VISIBLE 1u
#define ARC1_TRANSFORM_SATURATED 2u
#define ARC1_TRANSFORM_INVALID 4u

/* Native C record; the transport must explicitly serialize little-endian fields. */
typedef struct {
    int32_t xmin, ymin, xmax, ymax;
    int32_t m00, m01, m02, m10, m11, m12;
    uint16_t viewport_width, viewport_height;
    uint32_t tag;
} arc1_transform_job;

typedef struct {
    uint32_t tag;
    int32_t minx, miny, maxx, maxy;
    uint32_t flags;
} arc1_transform_result;

/* All coordinates/coefficients are signed Q16.16. See CONTRACT.md. */
void arc1_transform_rectangle(const arc1_transform_job *job,
                              arc1_transform_result *result);
/* Arrays must not overlap. A zero count performs no accesses. */
void arc1_transform_batch(const arc1_transform_job *jobs,
                         arc1_transform_result *results, size_t count);

#ifdef __cplusplus
}
#endif
#endif
