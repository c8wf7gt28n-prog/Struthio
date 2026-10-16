#include "arc1_mechanics.h"

size_t arc1_mech_matrix_bytes(unsigned count)
{
    return count > ARC1_MECH_MAX_BODIES ? 0u : (size_t)count * ((count + 7u) >> 3);
}

static int interval_overlap(int32_t amin, int32_t amax, int32_t bmin, int32_t bmax)
{
#ifdef ARC1_MECH_MUTANT_INCLUSIVE
    return amax >= bmin && bmax >= amin;
#else
    return amax > bmin && bmax > amin;
#endif
}

int arc1_mech_aabb_matrix(const arc1_aabb *bodies, unsigned count, uint8_t *matrix,
                          size_t matrix_capacity, arc1_mech_stats *stats)
{
    size_t bytes = arc1_mech_matrix_bytes(count), stride = (count + 7u) >> 3;
    unsigned i, j;
    arc1_mech_stats local = { 0, 0, 0 };
    if (!bodies || !matrix || count == 0u || bytes == 0u) return -1;
    if (matrix_capacity < bytes) return -2;
    for (i = 0; i < bytes; i++) matrix[i] = 0;
    for (i = 0; i < count; i++) for (j = i + 1u; j < count; j++) {
        const arc1_aabb *a = &bodies[i], *b = &bodies[j];
        int eligible;
        local.candidate_pairs++;
        eligible = (a->mask & b->group) != 0u && (b->mask & a->group) != 0u;
        if (!eligible) { local.filtered_pairs++; continue; }
        if (a->min_x >= a->max_x || a->min_y >= a->max_y ||
            b->min_x >= b->max_x || b->min_y >= b->max_y) continue;
        if (interval_overlap(a->min_x, a->max_x, b->min_x, b->max_x) &&
            interval_overlap(a->min_y, a->max_y, b->min_y, b->max_y)) {
            matrix[(size_t)i * stride + (j >> 3)] |= (uint8_t)(1u << (j & 7u));
            matrix[(size_t)j * stride + (i >> 3)] |= (uint8_t)(1u << (i & 7u));
            local.overlapping_pairs++;
        }
    }
    if (stats) *stats = local;
    return (int)bytes;
}
