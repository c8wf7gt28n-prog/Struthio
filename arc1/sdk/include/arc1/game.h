/*
 * arc1/game.h — ARC-1 game-facing C API, ABI 0.2 (PROPOSED).
 *
 * Status: host reference implementation only (sdk/runtime/host). No console
 * target mapping exists yet; see docs/API.md for the semantic contract and
 * the conformance tests that pin it. Nothing here implies that the F133,
 * D213, 45F and 12F share memory.
 *
 * Language: C11 subset. No dynamic allocation is required of the game, no
 * floating point is used by the API, and every call returns an explicit
 * status instead of failing silently.
 */
#ifndef ARC1_GAME_H
#define ARC1_GAME_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ARC1_ABI_VERSION_MAJOR 0
#define ARC1_ABI_VERSION_MINOR 2
#define ARC1_ABI_STATUS "proposed"

/* Logical screen. The host model presents exactly this many pixels. */
#define ARC1_SCREEN_W 320
#define ARC1_SCREEN_H 180

/* Sprite limits enforced by every implementation of this ABI. */
#define ARC1_SPRITE_MAX_W 64
#define ARC1_SPRITE_MAX_H 64
#define ARC1_SPRITE_MAX_COUNT 64

/* Colours are indices into the fixed 16-entry ARC-1 0.2 palette
 * (docs/API.md). In sprite pixel data index 0 is transparent. */
typedef uint8_t arc1_color;
#define ARC1_PALETTE_SIZE 16
#define ARC1_TRANSPARENT 0

typedef enum arc1_status {
    ARC1_OK = 0,
    ARC1_E_INVALID_ARG = -1, /* argument out of documented range */
    ARC1_E_NO_CAPACITY = -2, /* a documented resource limit was reached */
    ARC1_E_UNSUPPORTED = -3, /* capability not provided by this target */
    ARC1_E_STATE = -4        /* call not valid in the current lifecycle state */
} arc1_status;

/* Opaque sprite handle. id 0 is never a valid handle. */
typedef struct arc1_sprite {
    int32_t id;
} arc1_sprite;

/* Controller buttons (bit mask). Player 0 is the only player in ABI 0.2. */
#define ARC1_BTN_UP     (1u << 0)
#define ARC1_BTN_DOWN   (1u << 1)
#define ARC1_BTN_LEFT   (1u << 2)
#define ARC1_BTN_RIGHT  (1u << 3)
#define ARC1_BTN_A      (1u << 4)
#define ARC1_BTN_B      (1u << 5)
#define ARC1_BTN_START  (1u << 6)
#define ARC1_BTN_SELECT (1u << 7)

/* Capabilities a game may query before relying on them. */
typedef enum arc1_cap {
    ARC1_CAP_SPRITES_2D = 1, /* host: yes */
    ARC1_CAP_RECT_FILL = 2,  /* host: yes */
    ARC1_CAP_RASTER_3D = 3,  /* 45F dispatch; host: no */
    ARC1_CAP_COPROC_12F = 4, /* 12F kernels; host: no */
    ARC1_CAP_AUDIO = 5       /* host: no */
} arc1_cap;

/* Entry point implemented by the game. */
int arc1_main(void);

/* Lifecycle ------------------------------------------------------------ */

/* Must be called once before any other call. Second call: ARC1_E_STATE. */
arc1_status arc1_init(void);

/* Non-zero while the runtime wants more frames. */
int arc1_running(void);

/* Index of the frame currently being built (0-based, increments at
 * arc1_frame_end). */
uint32_t arc1_frame_index(void);

/* 1 if the capability is available on this target, 0 otherwise. */
int arc1_capability(arc1_cap cap);

/* Human-readable status name, never NULL. */
const char *arc1_status_str(arc1_status status);

/* Input ------------------------------------------------------------------ */

/* Latches controller state for the current frame. Call once per frame
 * before reading input; the latched value is stable until the next poll. */
arc1_status arc1_input_poll(void);

/* Buttons held at the last poll. Players other than 0 return 0. */
uint32_t arc1_input_held(int player);

/* Buttons that went from released to held between the previous and the
 * last poll. Players other than 0 return 0. */
uint32_t arc1_input_pressed(int player);

/* Frame building ---------------------------------------------------------- */

/* Starts a frame and clears it to the given palette index. */
arc1_status arc1_frame_begin(arc1_color clear);

/* Draw calls are composited in call order (painter's algorithm) and
 * clipped to the screen. Valid only between frame_begin and frame_end. */
arc1_status arc1_rect_fill(int x, int y, int w, int h, arc1_color color);
arc1_status arc1_sprite_draw(arc1_sprite sprite, int x, int y);

/* Presents the frame and advances arc1_frame_index(). */
arc1_status arc1_frame_end(void);

/* Resources --------------------------------------------------------------- */

/* Copies w*h palette indices (row-major) into runtime-owned storage. The
 * caller's buffer may be released after the call. Handles live until the
 * runtime shuts down; there is no free in ABI 0.2. */
arc1_status arc1_sprite_create(const uint8_t *pixels, int w, int h,
                               arc1_sprite *out);

#ifdef __cplusplus
}
#endif

#endif /* ARC1_GAME_H */
