#ifndef ARC1_PROTOCOL_H
#define ARC1_PROTOCOL_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define ARC1_PROTOCOL_VERSION 1u
#define ARC1_HEADER_SIZE 20u
#define ARC1_CRC_SIZE 4u
#define ARC1_MAX_PAYLOAD 4096u
#define ARC1_MAX_FRAME (ARC1_HEADER_SIZE + ARC1_MAX_PAYLOAD + ARC1_CRC_SIZE)
#define ARC1_MAX_CREDITS 8u

enum arc1_type {
    ARC1_HELLO = 0x01,
    ARC1_JOB = 0x10,
    ARC1_STATUS = 0x80,
    ARC1_RESULT = 0x81
};

enum arc1_error {
    ARC1_OK = 0,
    ARC1_ERR_ARGUMENT = 1,
    ARC1_ERR_CAPACITY = 2,
    ARC1_ERR_TRUNCATED = 3,
    ARC1_ERR_MAGIC = 4,
    ARC1_ERR_VERSION = 5,
    ARC1_ERR_FLAGS = 6,
    ARC1_ERR_HEADER = 7,
    ARC1_ERR_LENGTH = 8,
    ARC1_ERR_TYPE = 9,
    ARC1_ERR_SHAPE = 10,
    ARC1_ERR_CRC = 11,
    ARC1_ERR_TRAILING = 12
};

/* A decoded payload borrows the input buffer; it is never a native wire struct. */
typedef struct arc1_packet {
    uint8_t type;
    uint32_t epoch;
    uint32_t sequence;
    const uint8_t *payload;
    size_t payload_length;
} arc1_packet;

uint32_t arc1_crc32(const uint8_t *data, size_t length);
size_t arc1_frame_size(size_t payload_length);
int arc1_encode(uint8_t type, uint32_t epoch, uint32_t sequence,
                const uint8_t *payload, size_t payload_length,
                uint8_t *output, size_t capacity, size_t *written);
int arc1_decode(const uint8_t *data, size_t length, arc1_packet *packet);
const char *arc1_error_string(int error);

/* Callback payload is valid only during the callback. No heap allocation. */
typedef void (*arc1_packet_callback)(void *context, const arc1_packet *packet);
typedef struct arc1_parser {
    uint8_t bytes[ARC1_MAX_FRAME];
    size_t used;
    uint64_t accepted;
    uint64_t rejected;
    uint64_t discarded_bytes;
} arc1_parser;

void arc1_parser_init(arc1_parser *parser);
int arc1_parser_feed(arc1_parser *parser, const uint8_t *data, size_t length,
                     arc1_packet_callback callback, void *context);
/* A known transaction boundary discards an incomplete tail; returns its size. */
size_t arc1_parser_finish(arc1_parser *parser);

enum arc1_status {
    ARC1_STATUS_OK = 0,
    ARC1_STATUS_ACCEPTED = 1,
    ARC1_STATUS_DONE = 2,
    ARC1_STATUS_DUPLICATE_PENDING = 3,
    ARC1_STATUS_DUPLICATE_DONE = 4,
    ARC1_STATUS_NO_SESSION = 16,
    ARC1_STATUS_EPOCH = 17,
    ARC1_STATUS_SEQUENCE = 18,
    ARC1_STATUS_NO_CREDIT = 19,
    ARC1_STATUS_REPLAY_TOO_OLD = 20,
    ARC1_STATUS_DUPLICATE_CONFLICT = 21,
    ARC1_STATUS_BUSY = 22,
    ARC1_STATUS_SEQUENCE_EXHAUSTED = 23,
    ARC1_STATUS_INVALID_REQUEST = 24,
    ARC1_STATUS_UNKNOWN_JOB = 25
};

typedef struct arc1_reply {
    uint16_t status;
    uint16_t available_credits;
    uint32_t next_sequence; /* Zero means UINT32_MAX was accepted: reset required. */
    uint32_t epoch;         /* Current receiver epoch, zero before HELLO. */
    uint32_t sequence;      /* Echo of the request/completion sequence. */
} arc1_reply;

typedef struct arc1_job_record {
    uint8_t used;
    uint8_t complete;
    uint32_t sequence;
    size_t payload_length;
    uint8_t payload[ARC1_MAX_PAYLOAD];
} arc1_job_record;

/* Single-owner state: caller serializes requests/completions. No thread safety. */
typedef struct arc1_session {
    uint8_t active;
    uint8_t sequence_exhausted;
    uint16_t capacity;
    uint16_t outstanding;
    uint32_t epoch;
    uint32_t next_sequence;
    arc1_job_record records[ARC1_MAX_CREDITS];
} arc1_session;

size_t arc1_session_size(void);
int arc1_session_init(arc1_session *session, uint16_t capacity);
/* Only ACCEPTED authorizes exactly one application dispatch. */
uint16_t arc1_session_request(arc1_session *session,
                             const arc1_packet *packet, arc1_reply *reply);
/* Completion releases one credit once. It does not validate application output. */
uint16_t arc1_session_complete(arc1_session *session, uint32_t epoch,
                              uint32_t sequence, arc1_reply *reply);
int arc1_status_payload(const arc1_reply *reply, uint8_t output[8]);
/* Typed STATUS validation is separate from generic frame decoding. */
int arc1_read_status(const arc1_packet *packet, arc1_reply *reply);

#ifdef __cplusplus
}
#endif
#endif
