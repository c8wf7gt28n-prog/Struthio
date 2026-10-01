# STRUTHIO HANDHELD · host builds and tests (no ESP-IDF needed).
#   make -C handheld/host test
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
CORE = ../core/struthio_sim.c ../core/struthio_tower.c ../core/struthio_digest.c ../core/struthio_input.c ../core/struthio_replay.c
HDRS = ../core/struthio_core.h ../core/struthio_input.h ../core/struthio_replay.h ../core/struthio_rules.h
BUILD = build

RENDER = ../render/struthio_greybox.c ../render/struthio_scene.c ../render/struthio_scene_data.c ../render/struthio_raster.c ../render/struthio_panel.c
all: $(BUILD)/replay $(BUILD)/render_demo $(BUILD)/scene_check $(BUILD)/raster_check $(BUILD)/panel_check $(BUILD)/bake_textures

$(BUILD)/replay: replay.c $(CORE) $(HDRS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core replay.c $(CORE) -o $@

$(BUILD)/render_demo: render_demo.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_greybox.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render render_demo.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/scene_check: scene_check.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_scene.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render scene_check.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/raster_check: raster_check.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_raster.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render raster_check.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/panel_check: panel_check.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_panel.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render panel_check.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/bake_textures: bake_textures.c ../render/struthio_raster.c ../render/struthio_raster.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render bake_textures.c ../render/struthio_raster.c -lm -o $@

# panel-density textures from the browser's exported textures
bake: $(BUILD)/bake_textures
	@mkdir -p ../build/bake
	./$(BUILD)/bake_textures ../build/reference/textures ../build/bake

scene: $(BUILD)/scene_check
	./$(BUILD)/scene_check ../golden/*.trace

test: $(BUILD)/replay
	./$(BUILD)/replay ../golden/*.trace

clean:
	rm -rf $(BUILD)
.PHONY: all test clean scene bake
