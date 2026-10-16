/* ARC-1 R10 -- optional 12F adaptive-mechanics service and bit-exact F133 fallback. */
#ifndef ARC1_MECHANICS_H
#define ARC1_MECHANICS_H
#include <stddef.h>
#include <stdint.h>

#define ARC1_MECH_ABI_MAJOR 1u
#define ARC1_MECH_ABI_MINOR 0u
#define ARC1_MECH_OP_AABB_MATRIX 0x0030u
#define ARC1_MECH_MAX_BODIES 128u

/* Coordinates are signed Q16.16 world units. group and mask are bit sets: A/B are eligible only when each body's
 * mask accepts at least one group bit of the other body. min edges are inclusive and max edges are exclusive. */
typedef struct {
    int32_t min_x, min_y, max_x, max_y;
    uint16_t group, mask;
} arc1_aabb;

typedef struct {
    uint32_t candidate_pairs;
    uint32_t filtered_pairs;
    uint32_t overlapping_pairs;
} arc1_mech_stats;

size_t arc1_mech_matrix_bytes(unsigned count);

/* Writes a symmetric row-major bit matrix.  Row stride is ceil(count/8); bit j of row i means body i overlaps j.
 * The diagonal is always zero. Returns bytes written, or -1 for bad count/pointers and -2 for insufficient output. */
int arc1_mech_aabb_matrix(const arc1_aabb *bodies, unsigned count, uint8_t *matrix,
                          size_t matrix_capacity, arc1_mech_stats *stats);

#endif
