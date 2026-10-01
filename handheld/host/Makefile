# STRUTHIO HANDHELD · host builds and tests (no ESP-IDF needed).
#   make -C handheld/host test
CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
CORE = ../core/struthio_sim.c ../core/struthio_tower.c ../core/struthio_digest.c ../core/struthio_input.c ../core/struthio_replay.c
HDRS = ../core/struthio_core.h ../core/struthio_input.h ../core/struthio_replay.h ../core/struthio_rules.h
BUILD = build

RENDER = ../render/struthio_greybox.c ../render/struthio_scene.c ../render/struthio_scene_data.c ../render/struthio_raster.c ../render/struthio_panel.c ../render/struthio_pak.c
all: $(BUILD)/replay $(BUILD)/render_demo $(BUILD)/scene_check $(BUILD)/raster_check $(BUILD)/panel_check $(BUILD)/make_pak $(BUILD)/amb_test

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

$(BUILD)/panel_check: panel_check.c $(CORE) $(RENDER) $(HDRS) ../render/struthio_panel.h ../render/struthio_pak.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render panel_check.c $(CORE) $(RENDER) -lm -o $@

$(BUILD)/make_pak: make_pak.c ../render/struthio_raster.c ../render/struthio_raster.h ../render/struthio_pak.h ../render/struthio_panel.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render make_pak.c ../render/struthio_raster.c -lm -o $@

# the device's asset pack from the browser's exported textures and HUD capture
pak: $(BUILD)/make_pak
	@mkdir -p ../build/assets
	./$(BUILD)/make_pak ../build/reference ../build/assets/struthio.pak

$(BUILD)/amb_test: amb_test.c ../render/struthio_raster.c ../render/struthio_raster.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -I../core -I../render amb_test.c ../render/struthio_raster.c -lm -o $@

scene: $(BUILD)/scene_check
	./$(BUILD)/scene_check ../golden/*.trace

test: $(BUILD)/replay
	./$(BUILD)/replay ../golden/*.trace

clean:
	rm -rf $(BUILD)
.PHONY: all test clean scene pak
