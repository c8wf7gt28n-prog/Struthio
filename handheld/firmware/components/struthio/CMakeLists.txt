# The portable STRUTHIO core (bit-exact port of the 1.8.0 simulation, input
# normalizer, golden replay, digests) and the greybox renderer. The same
# sources are built and verified on the host by handheld/host.
set(H ${CMAKE_CURRENT_LIST_DIR}/../../..)
idf_component_register(
    SRCS ${H}/core/struthio_sim.c ${H}/core/struthio_tower.c ${H}/core/struthio_digest.c
         ${H}/core/struthio_input.c ${H}/core/struthio_replay.c ${H}/render/struthio_greybox.c
    INCLUDE_DIRS ${H}/core ${H}/render
)
target_compile_options(${COMPONENT_LIB} PRIVATE -O2)
