# The portable STRUTHIO core (bit-exact port of the 1.8.0 simulation, input
# normalizer, golden replay, digests), the browser renderer's port (scene
# builder, panel renderer, asset pack loader), the greybox fallback and the
# port of the browser's sound (audio/: synth, conductor, music loop). The
# same sources are built and verified on the host by handheld/host.
set(H ${CMAKE_CURRENT_LIST_DIR}/../../..)
idf_component_register(
    SRCS ${H}/core/struthio_sim.c ${H}/core/struthio_tower.c ${H}/core/struthio_digest.c
         ${H}/core/struthio_input.c ${H}/core/struthio_replay.c ${H}/render/struthio_greybox.c
         ${H}/render/struthio_scene.c ${H}/render/struthio_scene_data.c ${H}/render/struthio_raster.c
         ${H}/render/struthio_panel.c ${H}/render/struthio_pak.c ${H}/audio/struthio_audio.c
    INCLUDE_DIRS ${H}/core ${H}/render ${H}/audio
)
target_compile_options(${COMPONENT_LIB} PRIVATE -O2)
