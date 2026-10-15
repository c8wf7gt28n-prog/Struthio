#include "arc1_protocol.h"

#include <limits.h>
#include <string.h>

static const uint8_t magic[4] = {'A', 'R', 'C', '1'};

static uint16_t read16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static uint32_t read32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static void write16(uint8_t *p, uint16_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
}
static void write32(uint8_t *p, uint32_t v) {
    p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8);
    p[2] = (uint8_t)(v >> 16); p[3] = (uint8_t)(v >> 24);
}

uint32_t arc1_crc32(const uint8_t *data, size_t length) {
    uint32_t crc = UINT32_MAX;
    size_t i;
    unsigned bit;
    if (data == NULL && length != 0u) return 0u;
    for (i = 0; i < length; ++i) {
        crc ^= data[i];
        for (bit = 0; bit < 8u; ++bit)
            crc = (crc >> 1) ^ (0xedb88320u & (0u - (crc & 1u)));
    }
    return crc ^ UINT32_MAX;
}

size_t arc1_frame_size(size_t length) {
    return length <= ARC1_MAX_PAYLOAD ? length + ARC1_HEADER_SIZE + ARC1_CRC_SIZE : 0u;
}

static int shape(uint8_t type, uint32_t epoch, uint32_t sequence, size_t length) {
    if (length > ARC1_MAX_PAYLOAD) return ARC1_ERR_LENGTH;
    switch (type) {
    case ARC1_HELLO:
        return epoch != 0u && sequence == 0u && length == 0u ? ARC1_OK : ARC1_ERR_SHAPE;
    case ARC1_JOB:
        return epoch != 0u && sequence != 0u && length != 0u ? ARC1_OK : ARC1_ERR_SHAPE;
    case ARC1_STATUS:
        return length == 8u ? ARC1_OK : ARC1_ERR_SHAPE;
    case ARC1_RESULT:
        return epoch != 0u && sequence != 0u ? ARC1_OK : ARC1_ERR_SHAPE;
    default:
        return ARC1_ERR_TYPE;
    }
}

static int header(const uint8_t *data) {
    if (memcmp(data, magic, sizeof magic) != 0) return ARC1_ERR_MAGIC;
    if (data[4] != ARC1_PROTOCOL_VERSION) return ARC1_ERR_VERSION;
    if (read16(data + 6) != 0u) return ARC1_ERR_FLAGS;
    if (read16(data + 10) != ARC1_HEADER_SIZE) return ARC1_ERR_HEADER;
    return shape(data[5], read32(data + 12), read32(data + 16), read16(data + 8));
}

int arc1_encode(uint8_t type, uint32_t epoch, uint32_t sequence,
                const uint8_t *payload, size_t length,
                uint8_t *out, size_t capacity, size_t *written) {
    size_t size;
    int error;
    if (written == NULL) return ARC1_ERR_ARGUMENT;
    *written = 0u;
    if (out == NULL || (payload == NULL && length != 0u)) return ARC1_ERR_ARGUMENT;
    error = shape(type, epoch, sequence, length);
    if (error != ARC1_OK) return error;
    size = arc1_frame_size(length); /* Bound checked before addition. */
    if (capacity < size) return ARC1_ERR_CAPACITY;
    /* Move before writing the header, so overlapping input/output also works. */
    if (length != 0u) memmove(out + ARC1_HEADER_SIZE, payload, length);
    memcpy(out, magic, sizeof magic);
    out[4] = ARC1_PROTOCOL_VERSION; out[5] = type;
    write16(out + 6, 0u); write16(out + 8, (uint16_t)length);
    write16(out + 10, ARC1_HEADER_SIZE);
    write32(out + 12, epoch); write32(out + 16, sequence);
    write32(out + ARC1_HEADER_SIZE + length, arc1_crc32(out, ARC1_HEADER_SIZE + length));
    *written = size;
    return ARC1_OK;
}

int arc1_decode(const uint8_t *data, size_t length, arc1_packet *packet) {
    size_t payload_length, expected;
    int error;
    if (packet == NULL) return ARC1_ERR_ARGUMENT;
    memset(packet, 0, sizeof *packet);
    if (data == NULL) return ARC1_ERR_ARGUMENT;
    if (length < ARC1_HEADER_SIZE) return ARC1_ERR_TRUNCATED;
    error = header(data);
    if (error != ARC1_OK) return error;
    payload_length = read16(data + 8);
    expected = arc1_frame_size(payload_length);
    if (length < expected) return ARC1_ERR_TRUNCATED;
    if (length > expected) return ARC1_ERR_TRAILING;
    if (read32(data + ARC1_HEADER_SIZE + payload_length) !=
        arc1_crc32(data, ARC1_HEADER_SIZE + payload_length)) return ARC1_ERR_CRC;
    packet->type = data[5]; packet->epoch = read32(data + 12);
    packet->sequence = read32(data + 16);
    packet->payload = data + ARC1_HEADER_SIZE; packet->payload_length = payload_length;
    return ARC1_OK;
}

const char *arc1_error_string(int error) {
    static const char *const names[] = {
        "OK", "ARGUMENT", "CAPACITY", "TRUNCATED", "MAGIC", "VERSION", "FLAGS",
        "HEADER", "LENGTH", "TYPE", "SHAPE", "CRC", "TRAILING"
    };
    return error >= 0 && (size_t)error < sizeof names / sizeof names[0] ? names[error] : "UNKNOWN";
}

void arc1_parser_init(arc1_parser *parser) {
    if (parser != NULL) memset(parser, 0, sizeof *parser);
}
static void drop(arc1_parser *parser, size_t n) {
    parser->used -= n;
    if (parser->used != 0u) memmove(parser->bytes, parser->bytes + n, parser->used);
    parser->discarded_bytes += n;
}
static void process(arc1_parser *parser, arc1_packet_callback callback, void *context) {
    arc1_packet packet;
    size_t expected;
    for (;;) {
        if (parser->used < sizeof magic) return;
        if (memcmp(parser->bytes, magic, sizeof magic) != 0) { drop(parser, 1u); continue; }
        if (parser->used < ARC1_HEADER_SIZE) return;
        if (header(parser->bytes) != ARC1_OK) { ++parser->rejected; drop(parser, 1u); continue; }
        expected = arc1_frame_size(read16(parser->bytes + 8));
        if (parser->used < expected) return;
        if (arc1_decode(parser->bytes, expected, &packet) != ARC1_OK) {
            ++parser->rejected; drop(parser, 1u); continue;
        }
        ++parser->accepted;
        if (callback != NULL) callback(context, &packet);
        parser->used -= expected;
        if (parser->used != 0u) memmove(parser->bytes, parser->bytes + expected, parser->used);
    }
}
int arc1_parser_feed(arc1_parser *parser, const uint8_t *data, size_t length,
                     arc1_packet_callback callback, void *context) {
    size_t i;
    if (parser == NULL || parser->used > ARC1_MAX_FRAME ||
        (data == NULL && length != 0u)) return ARC1_ERR_ARGUMENT;
    for (i = 0; i < length; ++i) {
        if (parser->used == ARC1_MAX_FRAME) return ARC1_ERR_CAPACITY;
        parser->bytes[parser->used++] = data[i];
        process(parser, callback, context);
    }
    return ARC1_OK;
}
size_t arc1_parser_finish(arc1_parser *parser) {
    size_t incomplete;
    if (parser == NULL || parser->used > ARC1_MAX_FRAME) return 0u;
    incomplete = parser->used;
    if (incomplete != 0u) { ++parser->rejected; drop(parser, incomplete); }
    return incomplete;
}

size_t arc1_session_size(void) { return sizeof(arc1_session); }
int arc1_session_init(arc1_session *session, uint16_t capacity) {
    if (session == NULL) return ARC1_ERR_ARGUMENT;
    memset(session, 0, sizeof *session);
    if (capacity == 0u || capacity > ARC1_MAX_CREDITS) return ARC1_ERR_ARGUMENT;
    session->capacity = capacity;
    return ARC1_OK;
}
static int session_valid(const arc1_session *s) {
    return s != NULL && s->capacity != 0u && s->capacity <= ARC1_MAX_CREDITS &&
           s->outstanding <= s->capacity;
}
static uint16_t respond(const arc1_session *s, uint16_t status, uint32_t sequence, arc1_reply *reply) {
    reply->status = status; reply->available_credits = (uint16_t)(s->capacity - s->outstanding);
    reply->next_sequence = s->active ? s->next_sequence : 0u;
    reply->epoch = s->active ? s->epoch : 0u; reply->sequence = sequence;
    return status;
}
uint16_t arc1_session_request(arc1_session *s, const arc1_packet *p, arc1_reply *reply) {
    arc1_job_record *record = NULL;
    size_t i;
    if (reply == NULL) return ARC1_STATUS_INVALID_REQUEST;
    memset(reply, 0, sizeof *reply); reply->status = ARC1_STATUS_INVALID_REQUEST;
    if (!session_valid(s) || p == NULL) return ARC1_STATUS_INVALID_REQUEST;
    if ((p->payload == NULL && p->payload_length != 0u) ||
        shape(p->type, p->epoch, p->sequence, p->payload_length) != ARC1_OK ||
        (p->type != ARC1_HELLO && p->type != ARC1_JOB))
        return respond(s, ARC1_STATUS_INVALID_REQUEST, p->sequence, reply);
    if (p->type == ARC1_HELLO) {
        if (s->active && p->epoch < s->epoch) return respond(s, ARC1_STATUS_EPOCH, 0u, reply);
        if (s->active && p->epoch == s->epoch) return respond(s, ARC1_STATUS_OK, 0u, reply);
        if (s->outstanding != 0u) return respond(s, ARC1_STATUS_BUSY, 0u, reply);
        memset(s->records, 0, sizeof s->records);
        s->active = 1u; s->epoch = p->epoch; s->next_sequence = 1u; s->sequence_exhausted = 0u;
        return respond(s, ARC1_STATUS_OK, 0u, reply);
    }
    if (!s->active) return respond(s, ARC1_STATUS_NO_SESSION, p->sequence, reply);
    if (p->epoch != s->epoch) return respond(s, ARC1_STATUS_EPOCH, p->sequence, reply);
    for (i = 0; i < s->capacity; ++i) {
        arc1_job_record *r = &s->records[i];
        if (r->used && r->sequence == p->sequence) {
            if (r->payload_length != p->payload_length || memcmp(r->payload, p->payload, p->payload_length) != 0)
                return respond(s, ARC1_STATUS_DUPLICATE_CONFLICT, p->sequence, reply);
            return respond(s, r->complete ? ARC1_STATUS_DUPLICATE_DONE : ARC1_STATUS_DUPLICATE_PENDING,
                           p->sequence, reply);
        }
    }
    if (s->sequence_exhausted) return respond(s, ARC1_STATUS_SEQUENCE_EXHAUSTED, p->sequence, reply);
    if (p->sequence < s->next_sequence) return respond(s, ARC1_STATUS_REPLAY_TOO_OLD, p->sequence, reply);
    if (p->sequence != s->next_sequence) return respond(s, ARC1_STATUS_SEQUENCE, p->sequence, reply);
    if (s->outstanding == s->capacity) return respond(s, ARC1_STATUS_NO_CREDIT, p->sequence, reply);
    for (i = 0; i < s->capacity; ++i) {
        arc1_job_record *r = &s->records[i];
        if (!r->used) { record = r; break; }
        if (r->complete && (record == NULL || r->sequence < record->sequence)) record = r;
    }
    if (record == NULL) return respond(s, ARC1_STATUS_BUSY, p->sequence, reply);
    record->used = 1u; record->complete = 0u; record->sequence = p->sequence;
    record->payload_length = p->payload_length;
    memcpy(record->payload, p->payload, p->payload_length);
    ++s->outstanding;
    if (s->next_sequence == UINT32_MAX) { s->sequence_exhausted = 1u; s->next_sequence = 0u; }
    else ++s->next_sequence;
    return respond(s, ARC1_STATUS_ACCEPTED, p->sequence, reply);
}
uint16_t arc1_session_complete(arc1_session *s, uint32_t epoch, uint32_t sequence, arc1_reply *reply) {
    size_t i;
    if (reply == NULL) return ARC1_STATUS_INVALID_REQUEST;
    memset(reply, 0, sizeof *reply); reply->status = ARC1_STATUS_INVALID_REQUEST;
    if (!session_valid(s)) return ARC1_STATUS_INVALID_REQUEST;
    if (!s->active) return respond(s, ARC1_STATUS_NO_SESSION, sequence, reply);
    if (epoch != s->epoch) return respond(s, ARC1_STATUS_EPOCH, sequence, reply);
    for (i = 0; i < s->capacity; ++i) {
        arc1_job_record *r = &s->records[i];
        if (r->used && r->sequence == sequence) {
            if (r->complete) return respond(s, ARC1_STATUS_DUPLICATE_DONE, sequence, reply);
            r->complete = 1u; --s->outstanding;
            return respond(s, ARC1_STATUS_DONE, sequence, reply);
        }
    }
    return respond(s, ARC1_STATUS_UNKNOWN_JOB, sequence, reply);
}
static int known_status(uint16_t status) {
    return status <= ARC1_STATUS_DUPLICATE_DONE ||
           (status >= ARC1_STATUS_NO_SESSION && status <= ARC1_STATUS_UNKNOWN_JOB);
}
static int valid_reply(const arc1_reply *reply) {
    return known_status(reply->status) && reply->available_credits <= ARC1_MAX_CREDITS &&
           (reply->epoch != 0u ||
            ((reply->status == ARC1_STATUS_NO_SESSION || reply->status == ARC1_STATUS_INVALID_REQUEST) &&
             reply->next_sequence == 0u));
}
int arc1_status_payload(const arc1_reply *reply, uint8_t out[8]) {
    if (reply == NULL || out == NULL) return ARC1_ERR_ARGUMENT;
    if (!valid_reply(reply)) return ARC1_ERR_SHAPE;
    write16(out, reply->status); write16(out + 2, reply->available_credits);
    write32(out + 4, reply->next_sequence);
    return ARC1_OK;
}
int arc1_read_status(const arc1_packet *packet, arc1_reply *reply) {
    arc1_reply decoded;
    if (packet == NULL || reply == NULL) return ARC1_ERR_ARGUMENT;
    memset(reply, 0, sizeof *reply);
    if (packet->type != ARC1_STATUS || packet->payload == NULL || packet->payload_length != 8u)
        return ARC1_ERR_SHAPE;
    decoded.status = read16(packet->payload);
    decoded.available_credits = read16(packet->payload + 2);
    decoded.next_sequence = read32(packet->payload + 4);
    decoded.epoch = packet->epoch; decoded.sequence = packet->sequence;
    if (!valid_reply(&decoded)) return ARC1_ERR_SHAPE;
    *reply = decoded;
    return ARC1_OK;
}
