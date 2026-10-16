#include "arc1_mechanics.h"
#include <stdio.h>
#include <string.h>

static int checks, fails;
#define CHECK(x) do { checks++; if (!(x)) { fails++; printf("FAIL %s:%d %s\n", __FILE__, __LINE__, #x); } } while (0)
#define Q(x) ((int32_t)((x) * 65536))

static int bit(const uint8_t *m, unsigned n, unsigned i, unsigned j)
{
    size_t stride = (n + 7u) >> 3;
    return (m[(size_t)i * stride + (j >> 3)] >> (j & 7u)) & 1u;
}

static int scalar_hit(const arc1_aabb *a, const arc1_aabb *b)
{
    if (!(a->mask & b->group) || !(b->mask & a->group)) return 0;
    if (a->min_x >= a->max_x || a->min_y >= a->max_y || b->min_x >= b->max_x || b->min_y >= b->max_y) return 0;
    return a->max_x > b->min_x && b->max_x > a->min_x && a->max_y > b->min_y && b->max_y > a->min_y;
}

static uint32_t rnd_state = 0x21436587u;
static uint32_t rnd(void) { rnd_state = rnd_state * 1664525u + 1013904223u; return rnd_state; }

int main(void)
{
    arc1_aabb b[ARC1_MECH_MAX_BODIES];
    uint8_t matrix[ARC1_MECH_MAX_BODIES * (ARC1_MECH_MAX_BODIES / 8)];
    arc1_mech_stats st;
    unsigned i, j;
    int rc;
    memset(b, 0, sizeof b);
    b[0] = (arc1_aabb){ Q(0), Q(0), Q(2), Q(2), 1, 3 };
    b[1] = (arc1_aabb){ Q(1), Q(1), Q(3), Q(3), 2, 1 };
    b[2] = (arc1_aabb){ Q(2), Q(0), Q(4), Q(2), 1, 1 }; /* touches 0: not overlap */
    b[3] = (arc1_aabb){ Q(1), Q(1), Q(2), Q(2), 4, 4 }; /* geometrically inside, layer-filtered */
    rc = arc1_mech_aabb_matrix(b, 4, matrix, sizeof matrix, &st);
    CHECK(rc == 4);
    CHECK(bit(matrix, 4, 0, 1) && bit(matrix, 4, 1, 0));
    CHECK(!bit(matrix, 4, 0, 2));
    CHECK(!bit(matrix, 4, 0, 3));
    CHECK(st.candidate_pairs == 6 && st.filtered_pairs == 4 && st.overlapping_pairs == 1);
    CHECK(arc1_mech_aabb_matrix(b, 0, matrix, sizeof matrix, 0) == -1);
    CHECK(arc1_mech_aabb_matrix(b, 4, matrix, 3, 0) == -2);

    for (i = 0; i < ARC1_MECH_MAX_BODIES; i++) {
        int32_t x = (int32_t)(rnd() & 0x3ffff), y = (int32_t)(rnd() & 0x3ffff);
        int32_t w = (int32_t)(1u + (rnd() & 0xffff)), h = (int32_t)(1u + (rnd() & 0xffff));
        uint16_t group = (uint16_t)(1u << (rnd() & 7u));
        b[i] = (arc1_aabb){ x, y, x + w, y + h, group, (uint16_t)(rnd() & 0xffu) };
    }
    rc = arc1_mech_aabb_matrix(b, ARC1_MECH_MAX_BODIES, matrix, sizeof matrix, &st);
    CHECK(rc == 2048);
    CHECK(st.candidate_pairs == 8128);
    for (i = 0; i < ARC1_MECH_MAX_BODIES; i++) {
        CHECK(!bit(matrix, ARC1_MECH_MAX_BODIES, i, i));
        for (j = 0; j < ARC1_MECH_MAX_BODIES; j++) {
            CHECK(bit(matrix, ARC1_MECH_MAX_BODIES, i, j) == bit(matrix, ARC1_MECH_MAX_BODIES, j, i));
            if (i != j) CHECK(bit(matrix, ARC1_MECH_MAX_BODIES, i, j) == scalar_hit(&b[i], &b[j]));
        }
    }
    printf("INFO max batch: %u bodies, %u candidate pairs, %d-byte collision matrix, %u overlaps\n",
           ARC1_MECH_MAX_BODIES, st.candidate_pairs, rc, st.overlapping_pairs);
    printf("%d checks, %d failed\n", checks, fails);
    printf(fails ? "MECHANICS_TEST_FAIL\n" : "MECHANICS_TEST_PASS\n");
    return fails != 0;
}
