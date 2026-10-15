#include "arc1_transform.h"
#include <limits.h>

_Static_assert(sizeof(arc1_transform_job) == 48, "Unexpected native job layout");
_Static_assert(offsetof(arc1_transform_job, tag) == 44, "Unexpected tag offset");
_Static_assert(sizeof(arc1_transform_result) == 24, "Unexpected result layout");

static int add_overflows(int64_t a, int64_t b)
{
    return (b > 0 && a > INT64_MAX - b) ||
           (b < 0 && a < INT64_MIN - b);
}

static int32_t coordinate(int32_t a, int32_t b, int32_t t,
                          int32_t x, int32_t y, uint32_t *flags)
{
    const int64_t p0 = (int64_t)a * x;
    const int64_t p1 = (int64_t)b * y;
    const int64_t translation = (int64_t)t * INT64_C(65536);
    int64_t sum;
    uint64_t magnitude, rounded;
    int negative;

    /* Exact products fit int64_t. If their sum overflows, even the largest
       opposing 48-bit translation cannot bring it into the 32-bit output range.
       Return the proven saturation result without overflowing signed C. */
    if (add_overflows(p0, p1)) {
        *flags |= ARC1_TRANSFORM_SATURATED;
        return p0 < 0 ? INT32_MIN : INT32_MAX;
    }
    sum = p0 + p1;
    if (add_overflows(sum, translation)) {
        *flags |= ARC1_TRANSFORM_SATURATED;
        return sum < 0 ? INT32_MIN : INT32_MAX;
    }
    sum += translation;
    negative = sum < 0;
    /* Avoid abs(INT64_MIN), signed right-shift and negative left-shift. */
    magnitude = negative ? (uint64_t)(-(sum + 1)) + UINT64_C(1) : (uint64_t)sum;
    rounded = (magnitude >> 16) + ((magnitude & UINT64_C(65535)) >= UINT64_C(32768));
    if ((!negative && rounded > INT32_MAX) ||
        (negative && rounded > UINT64_C(2147483648))) {
        *flags |= ARC1_TRANSFORM_SATURATED;
        return negative ? INT32_MIN : INT32_MAX;
    }
    if (negative && rounded == UINT64_C(2147483648))
        return INT32_MIN;
    return negative ? -(int32_t)rounded : (int32_t)rounded;
}

void arc1_transform_rectangle(const arc1_transform_job *job,
                              arc1_transform_result *result)
{
    unsigned corner;
    result->tag = job->tag;
    result->minx = result->miny = result->maxx = result->maxy = 0;
    result->flags = 0;
    if (job->xmin > job->xmax || job->ymin > job->ymax ||
        job->viewport_width == 0 || job->viewport_height == 0) {
        result->flags = ARC1_TRANSFORM_INVALID;
        return;
    }
    for (corner = 0; corner < 4; ++corner) {
        const int32_t x = (corner & 1) ? job->xmax : job->xmin;
        const int32_t y = (corner & 2) ? job->ymax : job->ymin;
        const int32_t tx = coordinate(job->m00, job->m01, job->m02,
                                      x, y, &result->flags);
        const int32_t ty = coordinate(job->m10, job->m11, job->m12,
                                      x, y, &result->flags);
        if (corner == 0 || tx < result->minx) result->minx = tx;
        if (corner == 0 || tx > result->maxx) result->maxx = tx;
        if (corner == 0 || ty < result->miny) result->miny = ty;
        if (corner == 0 || ty > result->maxy) result->maxy = ty;
    }
    /* Closed viewport deliberately retains edge-touching rectangles. */
    if (result->maxx >= 0 && result->maxy >= 0 &&
        (int64_t)result->minx <= (int64_t)job->viewport_width * INT64_C(65536) &&
        (int64_t)result->miny <= (int64_t)job->viewport_height * INT64_C(65536))
        result->flags |= ARC1_TRANSFORM_VISIBLE;
}

void arc1_transform_batch(const arc1_transform_job *jobs,
                         arc1_transform_result *results, size_t count)
{
    size_t i;
    for (i = 0; i < count; ++i)
        arc1_transform_rectangle(jobs + i, results + i);
}
