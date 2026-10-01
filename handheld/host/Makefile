# STRUTHIO HANDHELD · host builds and tests (no ESP-IDF needed).
#   make -C handheld/host test
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
CORE = ../core/struthio_sim.c ../core/struthio_tower.c ../core/struthio_digest.c ../core/struthio_input.c ../core/struthio_replay.c
HDRS = ../core/struthio_core.h ../core/struthio_input.h ../core/struthio_replay.h ../core/struthio_rules.h
BUILD = build

RENDER = ../render/struthio_greybox.c ../render/struthio_scene.c ../render/struthio_scene_data.c
all: $(BUILD)/replay $(BUILD)/render_demo $(BUILD)/scene_check

$(BUILD)/replay: replay.c $(CORE) $(HDRS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core replay.c $(CORE) -o $@

$(BUILD)/render_demo: render_demo.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_greybox.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render render_demo.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/scene_check: scene_check.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_scene.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render scene_check.c $(CORE) $(RENDER) -lm -o $@

scene: $(BUILD)/scene_check
	./$(BUILD)/scene_check ../golden/*.trace

test: $(BUILD)/replay
	./$(BUILD)/replay ../golden/*.trace

clean:
	rm -rf $(BUILD)
.PHONY: all test clean scene
