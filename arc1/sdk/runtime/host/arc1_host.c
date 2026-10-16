/*
 * ARC-1 host reference runtime (evidence class HOST_SIM).
 *
 * A deterministic, headless software model of the arc1/game.h contract. It
 * is NOT cycle accurate and says nothing about D213, 45F or 12F behaviour.
 *
 * Usage: <game> [--frames N] [--replay FILE] [--trace FILE]
 *               [--dump-dir DIR] [--dump F[,F...]]
 *
 *   --frames N    frames to run before arc1_running() returns 0 (default 60,
 *                 max 36000)
 *   --replay FILE mock controller script: lines "<frame> <BTN|BTN...|NONE>",
 *                 ascending frame numbers; state holds until the next line.
 *                 '#' starts a comment.
 *   --trace FILE  writes one line per presented frame:
 *                 "<frame> <held-hex> <fnv1a64-of-framebuffer>"
 *   --dump-dir D  directory for PPM frame dumps (default ".")
 *   --dump LIST   comma-separated frame indices to dump as frame_NNNNNN.ppm
 *
 * Exit status: the game's return value, or 70 if the runtime detected API
 * misuse (any call returning ARC1_E_STATE), 64 for bad arguments, 66 for an
 * unreadable replay, 73 if an output file could not be written.
 */
#include "arc1/game.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_FRAMES 36000
#define MAX_REPLAY 4096
#define MAX_DUMPS 64

/* Fixed ARC-1 0.2 palette (RGB888). Must match docs/API.md. */
static const uint8_t PALETTE[ARC1_PALETTE_SIZE][3] = {
    {0x00, 0x00, 0x00}, {0x1d, 0x2b, 0x53}, {0x7e, 0x25, 0x53},
    {0x00, 0x87, 0x51}, {0xab, 0x52, 0x36}, {0x5f, 0x57, 0x4f},
    {0xc2, 0xc3, 0xc7}, {0xff, 0xf1, 0xe8}, {0xff, 0x00, 0x4d},
    {0xff, 0xa3, 0x00}, {0xff, 0xec, 0x27}, {0x00, 0xe4, 0x36},
    {0x29, 0xad, 0xff}, {0x83, 0x76, 0x9c}, {0xff, 0x77, 0xa8},
    {0xff, 0xcc, 0xaa}};

typedef struct {
    int w, h;
    uint8_t px[ARC1_SPRITE_MAX_W * ARC1_SPRITE_MAX_H];
} sprite_slot;

typedef struct {
    uint32_t frame;
    uint32_t buttons;
} replay_entry;

static struct {
    int initialised;
    int in_frame;
    int misuse;
    uint32_t frame;
    uint32_t frames_total;
    uint32_t held, prev_held, pressed;
    uint8_t fb[ARC1_SCREEN_W * ARC1_SCREEN_H];
    sprite_slot sprites[ARC1_SPRITE_MAX_COUNT];
    int sprite_count;
    replay_entry replay[MAX_REPLAY];
    int replay_len;
    FILE *trace;
    const char *dump_dir;
    uint32_t dumps[MAX_DUMPS];
    int dump_count;
    int io_error;
} rt;

static arc1_status misuse(void) {
    rt.misuse = 1;
    return ARC1_E_STATE;
}

const char *arc1_status_str(arc1_status status) {
    switch (status) {
    case ARC1_OK: return "ARC1_OK";
    case ARC1_E_INVALID_ARG: return "ARC1_E_INVALID_ARG";
    case ARC1_E_NO_CAPACITY: return "ARC1_E_NO_CAPACITY";
    case ARC1_E_UNSUPPORTED: return "ARC1_E_UNSUPPORTED";
    case ARC1_E_STATE: return "ARC1_E_STATE";
    }
    return "ARC1_E_UNKNOWN";
}

arc1_status arc1_init(void) {
    if (rt.initialised) return misuse();
    rt.initialised = 1;
    return ARC1_OK;
}

int arc1_running(void) { return rt.initialised && rt.frame < rt.frames_total; }

uint32_t arc1_frame_index(void) { return rt.frame; }

int arc1_capability(arc1_cap cap) {
    return cap == ARC1_CAP_SPRITES_2D || cap == ARC1_CAP_RECT_FILL;
}

static uint32_t replay_buttons_at(uint32_t frame) {
    uint32_t b = 0;
    for (int i = 0; i < rt.replay_len && rt.replay[i].frame <= frame; i++)
        b = rt.replay[i].buttons;
    return b;
}

arc1_status arc1_input_poll(void) {
    if (!rt.initialised) return misuse();
    rt.prev_held = rt.held;
    rt.held = replay_buttons_at(rt.frame);
    rt.pressed = rt.held & ~rt.prev_held;
    return ARC1_OK;
}

uint32_t arc1_input_held(int player) { return player == 0 ? rt.held : 0; }

uint32_t arc1_input_pressed(int player) { return player == 0 ? rt.pressed : 0; }

arc1_status arc1_frame_begin(arc1_color clear) {
    if (!rt.initialised || rt.in_frame || !arc1_running()) return misuse();
    if (clear >= ARC1_PALETTE_SIZE) return ARC1_E_INVALID_ARG;
    memset(rt.fb, clear, sizeof rt.fb);
    rt.in_frame = 1;
    return ARC1_OK;
}

arc1_status arc1_rect_fill(int x, int y, int w, int h, arc1_color color) {
    if (!rt.in_frame) return misuse();
    if (color >= ARC1_PALETTE_SIZE || w < 0 || h < 0) return ARC1_E_INVALID_ARG;
    int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    long x1 = (long)x + w, y1 = (long)y + h;
    if (x1 > ARC1_SCREEN_W) x1 = ARC1_SCREEN_W;
    if (y1 > ARC1_SCREEN_H) y1 = ARC1_SCREEN_H;
    for (long yy = y0; yy < y1; yy++)
        for (long xx = x0; xx < x1; xx++) rt.fb[yy * ARC1_SCREEN_W + xx] = color;
    return ARC1_OK;
}

arc1_status arc1_sprite_create(const uint8_t *pixels, int w, int h,
                               arc1_sprite *out) {
    if (!rt.initialised || rt.in_frame) return misuse();
    if (!pixels || !out || w < 1 || h < 1 || w > ARC1_SPRITE_MAX_W ||
        h > ARC1_SPRITE_MAX_H)
        return ARC1_E_INVALID_ARG;
    for (int i = 0; i < w * h; i++)
        if (pixels[i] >= ARC1_PALETTE_SIZE) return ARC1_E_INVALID_ARG;
    if (rt.sprite_count >= ARC1_SPRITE_MAX_COUNT) return ARC1_E_NO_CAPACITY;
    sprite_slot *s = &rt.sprites[rt.sprite_count];
    s->w = w;
    s->h = h;
    memcpy(s->px, pixels, (size_t)(w * h));
    out->id = ++rt.sprite_count;
    return ARC1_OK;
}

arc1_status arc1_sprite_draw(arc1_sprite sprite, int x, int y) {
    if (!rt.in_frame) return misuse();
    if (sprite.id < 1 || sprite.id > rt.sprite_count) return ARC1_E_INVALID_ARG;
    const sprite_slot *s = &rt.sprites[sprite.id - 1];
    for (int sy = 0; sy < s->h; sy++) {
        long yy = (long)y + sy;
        if (yy < 0 || yy >= ARC1_SCREEN_H) continue;
        for (int sx = 0; sx < s->w; sx++) {
            long xx = (long)x + sx;
            uint8_t c = s->px[sy * s->w + sx];
            if (xx < 0 || xx >= ARC1_SCREEN_W || c == ARC1_TRANSPARENT) continue;
            rt.fb[yy * ARC1_SCREEN_W + xx] = c;
        }
    }
    return ARC1_OK;
}

static uint64_t fb_hash(void) {
    uint64_t h = 0xcbf29ce484222325ull;
    for (size_t i = 0; i < sizeof rt.fb; i++) {
        h ^= rt.fb[i];
        h *= 0x100000001b3ull;
    }
    return h;
}

static int should_dump(uint32_t frame) {
    for (int i = 0; i < rt.dump_count; i++)
        if (rt.dumps[i] == frame) return 1;
    return 0;
}

static void dump_ppm(uint32_t frame) {
    char path[4096];
    int n = snprintf(path, sizeof path, "%s/frame_%06u.ppm", rt.dump_dir,
                     (unsigned)frame);
    if (n < 0 || (size_t)n >= sizeof path) {
        rt.io_error = 1;
        return;
    }
    FILE *f = fopen(path, "wb");
    if (!f) {
        rt.io_error = 1;
        return;
    }
    fprintf(f, "P6\n%d %d\n255\n", ARC1_SCREEN_W, ARC1_SCREEN_H);
    for (size_t i = 0; i < sizeof rt.fb; i++)
        fwrite(PALETTE[rt.fb[i]], 1, 3, f);
    if (fclose(f) != 0) rt.io_error = 1;
}

arc1_status arc1_frame_end(void) {
    if (!rt.in_frame) return misuse();
    if (rt.trace)
        fprintf(rt.trace, "%u %04x %016llx\n", (unsigned)rt.frame,
                (unsigned)rt.held, (unsigned long long)fb_hash());
    if (should_dump(rt.frame)) dump_ppm(rt.frame);
    rt.in_frame = 0;
    rt.frame++;
    return ARC1_OK;
}

/* Host harness ------------------------------------------------------------ */

static int parse_u32(const char *s, uint32_t max, uint32_t *out) {
    char *end;
    if (!s || !*s) return 0;
    unsigned long v = strtoul(s, &end, 10);
    if (*end || v > max || s[0] == '-') return 0;
    *out = (uint32_t)v;
    return 1;
}

static int button_bit(const char *name, uint32_t *bit) {
    static const struct {
        const char *name;
        uint32_t bit;
    } names[] = {{"UP", ARC1_BTN_UP},       {"DOWN", ARC1_BTN_DOWN},
                 {"LEFT", ARC1_BTN_LEFT},   {"RIGHT", ARC1_BTN_RIGHT},
                 {"A", ARC1_BTN_A},         {"B", ARC1_BTN_B},
                 {"START", ARC1_BTN_START}, {"SELECT", ARC1_BTN_SELECT},
                 {"NONE", 0}};
    for (size_t i = 0; i < sizeof names / sizeof names[0]; i++)
        if (strcmp(name, names[i].name) == 0) {
            *bit = names[i].bit;
            return 1;
        }
    return 0;
}

static int load_replay(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) {
        fprintf(stderr, "arc1-host: cannot open replay %s\n", path);
        return 0;
    }
    char line[512];
    int lineno = 0, ok = 1;
    while (ok && fgets(line, sizeof line, f)) {
        lineno++;
        char *hash = strchr(line, '#');
        if (hash) *hash = '\0';
        char *frame_tok = strtok(line, " \t\r\n");
        if (!frame_tok) continue;
        char *btn_tok = strtok(NULL, " \t\r\n");
        uint32_t frame, buttons = 0;
        if (!parse_u32(frame_tok, MAX_FRAMES, &frame) || !btn_tok ||
            strtok(NULL, " \t\r\n")) {
            ok = 0;
            break;
        }
        if (rt.replay_len > 0 && frame <= rt.replay[rt.replay_len - 1].frame) {
            ok = 0;
            break;
        }
        for (char *b = strtok(btn_tok, "|"); b; b = strtok(NULL, "|")) {
            uint32_t bit;
            if (!button_bit(b, &bit)) {
                ok = 0;
                break;
            }
            buttons |= bit;
        }
        if (!ok || rt.replay_len >= MAX_REPLAY) {
            ok = 0;
            break;
        }
        rt.replay[rt.replay_len].frame = frame;
        rt.replay[rt.replay_len].buttons = buttons;
        rt.replay_len++;
    }
    fclose(f);
    if (!ok) fprintf(stderr, "arc1-host: %s:%d: malformed replay line\n", path, lineno);
    return ok;
}

static int parse_dumps(char *list) {
    for (char *t = strtok(list, ","); t; t = strtok(NULL, ",")) {
        if (rt.dump_count >= MAX_DUMPS ||
            !parse_u32(t, MAX_FRAMES, &rt.dumps[rt.dump_count]))
            return 0;
        rt.dump_count++;
    }
    return 1;
}

int main(int argc, char **argv) {
    const char *replay = NULL, *trace = NULL;
    rt.frames_total = 60;
    rt.dump_dir = ".";
    for (int i = 1; i < argc; i += 2) {
        const char *a = argv[i];
        const char *v = i + 1 < argc ? argv[i + 1] : NULL;
        int ok = v != NULL;
        if (ok && strcmp(a, "--frames") == 0) ok = parse_u32(v, MAX_FRAMES, &rt.frames_total);
        else if (ok && strcmp(a, "--replay") == 0) replay = v;
        else if (ok && strcmp(a, "--trace") == 0) trace = v;
        else if (ok && strcmp(a, "--dump-dir") == 0) rt.dump_dir = v;
        else if (ok && strcmp(a, "--dump") == 0) ok = parse_dumps(argv[i + 1]);
        else ok = 0;
        if (!ok) {
            fprintf(stderr, "arc1-host: bad argument near '%s'\n", a);
            return 64;
        }
    }
    if (replay && !load_replay(replay)) return 66;
    if (trace && !(rt.trace = fopen(trace, "w"))) {
        fprintf(stderr, "arc1-host: cannot write trace %s\n", trace);
        return 73;
    }
    int rc = arc1_main();
    if (rt.trace && fclose(rt.trace) != 0) rt.io_error = 1;
    if (rt.io_error) {
        fprintf(stderr, "arc1-host: failed to write an output file\n");
        return 73;
    }
    if (rt.misuse) {
        fprintf(stderr, "arc1-host: API lifecycle misuse detected (ARC1_E_STATE)\n");
        return 70;
    }
    if (rt.frame != rt.frames_total && rc == 0) {
        fprintf(stderr, "arc1-host: game returned after %u of %u frames\n",
                (unsigned)rt.frame, (unsigned)rt.frames_total);
    }
    return rc;
}
