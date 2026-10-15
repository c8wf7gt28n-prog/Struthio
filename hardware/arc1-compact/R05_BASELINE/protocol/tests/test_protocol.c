#include "arc1_protocol.h"

#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static uint32_t rng_state = 0xdeadbeefu;
static uint32_t random32(void) {
    rng_state ^= rng_state << 13; rng_state ^= rng_state >> 17; rng_state ^= rng_state << 5;
    return rng_state;
}
static size_t encode_job(uint8_t *out, const uint8_t *payload, size_t n, uint32_t seq) {
    size_t written = 0u;
    assert(arc1_encode(ARC1_JOB, 7u, seq, payload, n, out, ARC1_MAX_FRAME, &written) == ARC1_OK);
    return written;
}
static void codec_boundaries(void) {
    uint8_t payload[ARC1_MAX_PAYLOAD], out[ARC1_MAX_FRAME], damaged[ARC1_MAX_FRAME];
    arc1_packet packet;
    size_t i, bit, size, written;
    assert(arc1_crc32((const uint8_t *)"123456789", 9u) == 0xcbf43926u);
    assert(arc1_crc32(NULL, 0u) == 0u);
    assert(arc1_frame_size(SIZE_MAX) == 0u);
    for (i = 0; i < sizeof payload; ++i) payload[i] = (uint8_t)i;
    size = encode_job(out, payload, sizeof payload, UINT32_MAX);
    assert(size == ARC1_MAX_FRAME);
    assert(arc1_decode(out, size, &packet) == ARC1_OK);
    assert(packet.payload_length == sizeof payload && packet.sequence == UINT32_MAX);
    assert(memcmp(packet.payload, payload, sizeof payload) == 0);
    for (i = 0; i < size; ++i) {
        assert(arc1_decode(out, i, &packet) != ARC1_OK);
        assert(packet.payload == NULL && packet.payload_length == 0u);
    }
    assert(arc1_decode(out, SIZE_MAX, &packet) == ARC1_ERR_TRAILING);
    written = 99u;
    assert(arc1_encode(ARC1_JOB, 7u, 1u, payload, SIZE_MAX, out, sizeof out, &written) == ARC1_ERR_LENGTH);
    assert(written == 0u);
    assert(arc1_encode(ARC1_JOB, 7u, 1u, payload, 1u, out, 24u, &written) == ARC1_ERR_CAPACITY);
    assert(arc1_encode(ARC1_JOB, 7u, 1u, NULL, 1u, out, sizeof out, &written) == ARC1_ERR_ARGUMENT);
    assert(arc1_encode(ARC1_JOB, 7u, 1u, payload, 0u, out, sizeof out, &written) == ARC1_ERR_SHAPE);
    assert(arc1_encode(ARC1_HELLO, 0u, 0u, NULL, 0u, out, sizeof out, &written) == ARC1_ERR_SHAPE);
    assert(arc1_encode(0xffu, 7u, 1u, payload, 1u, out, sizeof out, &written) == ARC1_ERR_TYPE);
    assert(arc1_decode(NULL, 0u, &packet) == ARC1_ERR_ARGUMENT);
    assert(arc1_decode(out, 0u, NULL) == ARC1_ERR_ARGUMENT);
    size = encode_job(out, payload, 8u, 1u);
    for (i = 0; i < size; ++i) for (bit = 0; bit < 8u; ++bit) {
        memcpy(damaged, out, size); damaged[i] ^= (uint8_t)(1u << bit);
        assert(arc1_decode(damaged, size, &packet) != ARC1_OK);
    }
    /* Encoding an overlapping payload must not clobber its source. */
    memcpy(out, payload, 32u);
    assert(arc1_encode(ARC1_JOB, 7u, 1u, out, 32u, out, sizeof out, &written) == ARC1_OK);
    assert(arc1_decode(out, written, &packet) == ARC1_OK);
    assert(memcmp(packet.payload, payload, 32u) == 0);
    puts("PASS codec: CRC check, max/overflow/truncation/capacity, every single-bit corruption, overlap");
}

typedef struct capture { size_t count; uint32_t last_sequence; } capture;
static void received(void *context, const arc1_packet *packet) {
    capture *c = context;
    assert(packet->type == ARC1_JOB && packet->epoch == 7u);
    ++c->count; c->last_sequence = packet->sequence;
}
static void stream_cases(void) {
    arc1_parser parser;
    capture c = {0u, 0u};
    uint8_t frame[ARC1_MAX_FRAME], bad[ARC1_MAX_FRAME], noise[193], largest[ARC1_MAX_PAYLOAD];
    const uint8_t payload[] = {'A','R','C','1', 0u, 0xffu, 2u};
    size_t n, split, i;
    n = encode_job(frame, payload, sizeof payload, 10u);
    for (split = 0; split <= n; ++split) {
        arc1_parser_init(&parser); c.count = 0u;
        assert(arc1_parser_feed(&parser, frame, split, received, &c) == ARC1_OK);
        assert(arc1_parser_feed(&parser, frame + split, n - split, received, &c) == ARC1_OK);
        assert(c.count == 1u && c.last_sequence == 10u && parser.used == 0u);
    }
    arc1_parser_init(&parser); c.count = 0u;
    for (i = 0; i < sizeof noise; ++i) noise[i] = (uint8_t)random32();
    memcpy(bad, frame, n); bad[n - 1u] ^= 0x80u;
    assert(arc1_parser_feed(&parser, noise, sizeof noise, received, &c) == ARC1_OK);
    assert(arc1_parser_feed(&parser, bad, n, received, &c) == ARC1_OK);
    assert(arc1_parser_feed(&parser, frame, n, received, &c) == ARC1_OK);
    assert(c.count == 1u && parser.rejected >= 1u && parser.discarded_bytes != 0u);
    assert(arc1_parser_feed(&parser, frame, 13u, received, &c) == ARC1_OK);
    assert(arc1_parser_finish(&parser) == 13u);
    assert(arc1_parser_feed(&parser, frame, n, received, &c) == ARC1_OK && c.count == 2u);
    assert(arc1_parser_feed(&parser, NULL, 0u, received, &c) == ARC1_OK);
    assert(arc1_parser_feed(&parser, NULL, 1u, received, &c) == ARC1_ERR_ARGUMENT);
    memset(largest, 0x5au, sizeof largest);
    n = encode_job(frame, largest, sizeof largest, 11u);
    arc1_parser_init(&parser); c.count = 0u;
    for (i = 0; i < n; ++i) {
        assert(arc1_parser_feed(&parser, frame + i, 1u, received, &c) == ARC1_OK);
        assert(parser.used <= ARC1_MAX_FRAME);
    }
    assert(c.count == 1u && c.last_sequence == 11u && parser.used == 0u);
    puts("PASS stream: every split, embedded magic, noise/CRC resync, explicit truncated-transaction boundary");
}

static arc1_packet request(uint8_t type, uint32_t epoch, uint32_t seq, const uint8_t *p, size_t n) {
    arc1_packet result = {type, epoch, seq, p, n}; return result;
}
static void session_cases(void) {
    arc1_session s;
    arc1_reply r;
    arc1_packet p;
    uint8_t a[] = {1u, 2u}, b[] = {1u, 3u}, status[8];
    uint32_t sequence;
    assert(arc1_session_size() == sizeof s);
    assert(arc1_session_init(&s, 0u) == ARC1_ERR_ARGUMENT);
    assert(arc1_session_init(&s, 9u) == ARC1_ERR_ARGUMENT);
    assert(arc1_session_init(&s, 2u) == ARC1_OK);
    p = request(ARC1_JOB, 7u, 1u, a, sizeof a);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_NO_SESSION && r.epoch == 0u);
    p = request(ARC1_HELLO, 7u, 0u, NULL, 0u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_OK && r.available_credits == 2u);
    p = request(ARC1_JOB, 7u, 2u, a, sizeof a);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_SEQUENCE);
    p.sequence = 1u;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED && r.available_credits == 1u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_DUPLICATE_PENDING && r.next_sequence == 2u);
    p.payload = b;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_DUPLICATE_CONFLICT);
    p.payload = a; p.epoch = 6u;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_EPOCH);
    p.epoch = 7u; p.sequence = 2u;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED && r.available_credits == 0u);
    p.sequence = 3u;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_NO_CREDIT && r.next_sequence == 3u);
    p = request(ARC1_HELLO, 8u, 0u, NULL, 0u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_BUSY && r.epoch == 7u);
    p.epoch = 7u;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_OK && r.next_sequence == 3u);
    assert(arc1_session_complete(&s, 6u, 1u, &r) == ARC1_STATUS_EPOCH);
    assert(arc1_session_complete(&s, 7u, 99u, &r) == ARC1_STATUS_UNKNOWN_JOB);
    assert(arc1_session_complete(&s, 7u, 2u, &r) == ARC1_STATUS_DONE && r.available_credits == 1u);
    assert(arc1_session_complete(&s, 7u, 2u, &r) == ARC1_STATUS_DUPLICATE_DONE && r.available_credits == 1u);
    p = request(ARC1_JOB, 7u, 3u, a, sizeof a);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED);
    assert(arc1_session_complete(&s, 7u, 1u, &r) == ARC1_STATUS_DONE);
    assert(arc1_session_complete(&s, 7u, 3u, &r) == ARC1_STATUS_DONE);
    p.sequence = 4u; assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED);
    p.sequence = 1u; assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_REPLAY_TOO_OLD);
    assert(arc1_session_complete(&s, 7u, 4u, &r) == ARC1_STATUS_DONE);
    p = request(ARC1_HELLO, 8u, 0u, NULL, 0u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_OK && r.next_sequence == 1u);
    p.epoch = 7u; assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_EPOCH);
    p = request(ARC1_JOB, 8u, 1u, a, sizeof a);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED);
    assert(arc1_status_payload(&r, status) == ARC1_OK && status[0] == ARC1_STATUS_ACCEPTED && status[2] == 1u && status[4] == 2u);
    assert(arc1_session_complete(&s, 8u, 1u, &r) == ARC1_STATUS_DONE);
    /* Boundary-state fixture avoids executing 2^32 requests; not a native trace. */
    s.next_sequence = UINT32_MAX;
    p.sequence = UINT32_MAX;
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED && r.next_sequence == 0u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_DUPLICATE_PENDING);
    p.sequence = 2u; assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_SEQUENCE_EXHAUSTED);
    assert(arc1_session_complete(&s, 8u, UINT32_MAX, &r) == ARC1_STATUS_DONE);
    p = request(ARC1_HELLO, 9u, 0u, NULL, 0u);
    assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_OK);
    /* Long deterministic reuse cycle checks credits, eviction and no underflow. */
    for (sequence = 1u; sequence <= 10000u; ++sequence) {
        p = request(ARC1_JOB, 9u, sequence, a, sizeof a);
        assert(arc1_session_request(&s, &p, &r) == ARC1_STATUS_ACCEPTED && r.available_credits == 1u);
        assert(arc1_session_complete(&s, 9u, sequence, &r) == ARC1_STATUS_DONE && r.available_credits == 2u);
        assert(arc1_session_complete(&s, 9u, sequence, &r) == ARC1_STATUS_DUPLICATE_DONE && r.available_credits == 2u);
    }
    puts("PASS session: epoch/reset, exact duplicates/conflicts, sequence gaps, credits, out-of-order completion, eviction, wrap boundary, 10000 reuse cycles");
}

static void status_cases(void) {
    arc1_reply reply = {ARC1_STATUS_ACCEPTED, 8u, 2u, 7u, 1u}, decoded;
    uint8_t bytes[8], frame[ARC1_MAX_FRAME];
    size_t written;
    arc1_packet packet;
    assert(arc1_status_payload(&reply, bytes) == ARC1_OK);
    assert(arc1_encode(ARC1_STATUS, 7u, 1u, bytes, sizeof bytes, frame, sizeof frame, &written) == ARC1_OK);
    assert(arc1_decode(frame, written, &packet) == ARC1_OK);
    assert(arc1_read_status(&packet, &decoded) == ARC1_OK && decoded.available_credits == 8u && decoded.next_sequence == 2u);
    reply.available_credits = 9u; assert(arc1_status_payload(&reply, bytes) == ARC1_ERR_SHAPE);
    reply.available_credits = 1u; reply.status = 9u;
    assert(arc1_status_payload(&reply, bytes) == ARC1_ERR_SHAPE);
    packet.payload = bytes; bytes[0] = 0xffu; bytes[1] = 0xffu;
    assert(arc1_read_status(&packet, &decoded) == ARC1_ERR_SHAPE);
    bytes[0] = ARC1_STATUS_OK; bytes[1] = 0u; bytes[2] = 9u; bytes[3] = 0u;
    assert(arc1_read_status(&packet, &decoded) == ARC1_ERR_SHAPE);
    puts("PASS typed status: valid roundtrip, unknown code and excessive credit rejection");
}

static void session_capacity_and_bad_api(void) {
    arc1_session session;
    arc1_reply reply;
    const uint8_t payload[] = {1u};
    arc1_packet packet = request(ARC1_HELLO, 1u, 0u, NULL, 0u);
    uint32_t seq;
    assert(arc1_session_init(&session, ARC1_MAX_CREDITS) == ARC1_OK);
    assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_OK);
    packet = request(ARC1_STATUS, 1u, 1u, payload, 1u);
    assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_INVALID_REQUEST);
    packet = request(ARC1_JOB, 1u, 1u, NULL, 1u);
    assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_INVALID_REQUEST);
    packet = request(ARC1_JOB, 1u, 1u, payload, SIZE_MAX);
    assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_INVALID_REQUEST);
    assert(session.next_sequence == 1u && session.outstanding == 0u);
    for (seq = 1u; seq <= ARC1_MAX_CREDITS; ++seq) {
        packet = request(ARC1_JOB, 1u, seq, payload, sizeof payload);
        assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_ACCEPTED);
        assert(reply.available_credits == ARC1_MAX_CREDITS - seq);
    }
    packet.sequence = ARC1_MAX_CREDITS + 1u;
    assert(arc1_session_request(&session, &packet, &reply) == ARC1_STATUS_NO_CREDIT);
    for (seq = ARC1_MAX_CREDITS; seq > 0u; --seq)
        assert(arc1_session_complete(&session, 1u, seq, &reply) == ARC1_STATUS_DONE);
    assert(reply.available_credits == ARC1_MAX_CREDITS);
    puts("PASS full eight-slot window, reverse completion, invalid API input without sequence/credit mutation");
}

static void malformed_fuzz(void) {
    uint8_t data[ARC1_MAX_FRAME];
    arc1_packet packet;
    arc1_parser parser;
    size_t trial, length, i;
    arc1_parser_init(&parser);
    for (trial = 0; trial < 20000u; ++trial) {
        length = (size_t)(random32() % (ARC1_MAX_FRAME + 1u));
        for (i = 0; i < length; ++i) data[i] = (uint8_t)random32();
        (void)arc1_decode(data, length, &packet);
        assert(arc1_parser_feed(&parser, data, length, NULL, NULL) == ARC1_OK);
        assert(parser.used <= ARC1_MAX_FRAME);
        if ((trial & 127u) == 0u) (void)arc1_parser_finish(&parser);
    }
    puts("PASS deterministic malformed fuzz: 20000 bounded buffers through decoder and incremental parser");
}
int main(void) {
    codec_boundaries(); stream_cases(); session_cases(); status_cases(); session_capacity_and_bad_api(); malformed_fuzz();
    puts("ALL PORTABLE PROTOCOL CHECKS PASSED; no SPI or physical hardware exercised");
    return 0;
}
