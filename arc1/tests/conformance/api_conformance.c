/* ARC-1 ABI 0.2 conformance checks for the host reference runtime.
 * Linked with sdk/runtime/host/arc1_host.c and run with --frames 2.
 * Deliberate misuse means the harness exits 70 (ARC1_E_STATE observed);
 * the test runner requires both that exit code and "CONFORMANCE OK". */
#include <arc1/game.h>

#include <stdio.h>
#include <string.h>

static int checks, failures;

#define CHECK(cond)                                                         \
    do {                                                                    \
        checks++;                                                           \
        if (!(cond)) {                                                      \
            failures++;                                                     \
            printf("FAIL line %d: %s\n", __LINE__, #cond);                  \
        }                                                                   \
    } while (0)

int arc1_main(void) {
    static uint8_t px[ARC1_SPRITE_MAX_W * ARC1_SPRITE_MAX_H];
    arc1_sprite s = {0}, bad = {0};

    /* Lifecycle: nothing works before init. */
    CHECK(arc1_running() == 0);
    CHECK(arc1_input_poll() == ARC1_E_STATE);
    CHECK(arc1_sprite_create(px, 1, 1, &s) == ARC1_E_STATE);
    CHECK(arc1_init() == ARC1_OK);
    CHECK(arc1_init() == ARC1_E_STATE);
    CHECK(arc1_running() == 1);

    /* Capabilities: host provides 2D only. */
    CHECK(arc1_capability(ARC1_CAP_SPRITES_2D) == 1);
    CHECK(arc1_capability(ARC1_CAP_RECT_FILL) == 1);
    CHECK(arc1_capability(ARC1_CAP_RASTER_3D) == 0);
    CHECK(arc1_capability(ARC1_CAP_COPROC_12F) == 0);
    CHECK(arc1_capability(ARC1_CAP_AUDIO) == 0);
    CHECK(strcmp(arc1_status_str(ARC1_E_UNSUPPORTED), "ARC1_E_UNSUPPORTED") == 0);
    CHECK(arc1_status_str((arc1_status)99) != NULL);

    /* Sprite creation validates arguments and copies pixels. */
    CHECK(arc1_sprite_create(NULL, 1, 1, &s) == ARC1_E_INVALID_ARG);
    CHECK(arc1_sprite_create(px, 0, 1, &s) == ARC1_E_INVALID_ARG);
    CHECK(arc1_sprite_create(px, ARC1_SPRITE_MAX_W + 1, 1, &s) == ARC1_E_INVALID_ARG);
    px[0] = ARC1_PALETTE_SIZE;
    CHECK(arc1_sprite_create(px, 1, 1, &s) == ARC1_E_INVALID_ARG);
    px[0] = 7;
    CHECK(arc1_sprite_create(px, 1, 1, &s) == ARC1_OK && s.id != 0);
    px[0] = 0; /* caller buffer may change after create */
    for (int i = 1; i < ARC1_SPRITE_MAX_COUNT; i++) CHECK(arc1_sprite_create(px, 1, 1, &bad) == ARC1_OK);
    CHECK(arc1_sprite_create(px, 1, 1, &bad) == ARC1_E_NO_CAPACITY);

    /* Drawing is only valid inside a frame. */
    CHECK(arc1_sprite_draw(s, 0, 0) == ARC1_E_STATE);
    CHECK(arc1_frame_end() == ARC1_E_STATE);
    CHECK(arc1_frame_begin(ARC1_PALETTE_SIZE) == ARC1_E_INVALID_ARG);

    while (arc1_running()) {
        CHECK(arc1_input_poll() == ARC1_OK);
        CHECK(arc1_input_held(1) == 0 && arc1_input_pressed(1) == 0);
        uint32_t frame = arc1_frame_index();
        CHECK(arc1_frame_begin(1) == ARC1_OK);
        CHECK(arc1_frame_begin(1) == ARC1_E_STATE);
        CHECK(arc1_sprite_create(px, 1, 1, &bad) == ARC1_E_STATE);
        CHECK(arc1_sprite_draw(s, -5, -5) == ARC1_OK);        /* clipped, not an error */
        CHECK(arc1_sprite_draw(s, 100000, 100000) == ARC1_OK);
        CHECK(arc1_sprite_draw((arc1_sprite){0}, 0, 0) == ARC1_E_INVALID_ARG);
        CHECK(arc1_rect_fill(-10, -10, 1000, 1000, 2) == ARC1_OK);
        CHECK(arc1_rect_fill(0, 0, -1, 1, 2) == ARC1_E_INVALID_ARG);
        CHECK(arc1_frame_end() == ARC1_OK);
        CHECK(arc1_frame_index() == frame + 1);
    }
    CHECK(arc1_frame_index() == 2);
    CHECK(arc1_frame_begin(0) == ARC1_E_STATE); /* no frames after running() ends */

    printf("%s %d checks, %d failures\n", failures ? "CONFORMANCE FAILED" : "CONFORMANCE OK", checks, failures);
    return failures ? 1 : 0;
}
