/* Deterministic I01 facade, not an OS controller or an admission provider.
 * All observations and resource amounts are supplied assertions. */
#include "controller.h"
#include <limits.h>

#define NS UINT64_C(1000000000)
#define GAP UINT64_C(20000000)
#define WAIT UINT64_C(50000000)
#define DEADLINE UINT64_C(2000000000)
#define KILL_INTERVAL UINT64_C(250000000)
#define MARK UINT32_C(0x3143434e)

enum {
    ADMISSION = 1, COUNTER = 3, CPU = 4, TIMING = 5, TERMINATION = 7,
    PARENT = 9, PROTOCOL = 10, BOUNDS = 11, INTEGER = 12,
    OVERFLOW = 13, UNDERFLOW = 14, IDENTITY = 15, TRANSITION = 16,
    RELEASE = 17
};
enum {
    PREPARED, CONTAINED, RUNNING, STOP_REQUIRED, STOPPING, DRAINED,
    FINAL_NATIVE, RECEIPT_BOUND, ACK_CHECKED, RELEASE_ASSERTED, HELD
};

/* An internal representation, NEVER a wire format or public caller struct.
 * Byte copying avoids effective-type/unaligned aliasing of opaque storage. */
typedef struct {
    uint32_t mark, platform, lane, bound, started_bound;
    uint64_t diagnostic[NCC_SNAPSHOT_WORDS];
    uint64_t contained, started, stop_at, stop_reason;
    uint64_t native[3], active[3], final_native[3], final_at;
    unsigned char attempt[16], object[16], receipt[32];
} State;
_Static_assert(sizeof(State) <= NCC_STATE_BYTES, "fixed state bound");
_Static_assert(CHAR_BIT == 8, "byte wire requires octets");

static void copy_bytes(void *to, const void *from, size_t count)
{
    unsigned char *d = (unsigned char *)to;
    const unsigned char *s = (const unsigned char *)from;
    size_t i;
    for (i = 0; i < count; ++i) d[i] = s[i];
}

static uint32_t same_bytes(const unsigned char *a, const unsigned char *b,
                           size_t count)
{
    size_t i;
    unsigned char difference = 0;
    for (i = 0; i < count; ++i) difference |= (unsigned char)(a[i] ^ b[i]);
    return difference == 0;
}

static uint64_t little(const unsigned char *p, uint32_t count)
{
    uint64_t value = 0;
    uint32_t i;
    for (i = 0; i < count; ++i) value |= (uint64_t)p[i] << (8u * i);
    return value;
}

static uint32_t scalar_out(const void *out)
{
    return out == NULL ? PROTOCOL : 0;
}

NCC_API uint32_t ncc_windows_cpu(uint64_t user, uint64_t kernel, uint64_t *out)
{
    uint64_t sum;
    if (scalar_out(out)) return PROTOCOL;
    if (user > (uint64_t)INT64_MAX || kernel > (uint64_t)INT64_MAX) return INTEGER;
    if (kernel > (uint64_t)INT64_MAX - user) return OVERFLOW;
    sum = user + kernel;
    if (sum > (uint64_t)INT64_MAX / 100u) return OVERFLOW;
    *out = sum * 100u;
    return 0;
}

NCC_API uint32_t ncc_linux_cpu(uint64_t usage, uint64_t user, uint64_t system,
                              uint64_t *out)
{
    uint64_t sum, total;
    if (scalar_out(out)) return PROTOCOL;
    if (system > UINT64_MAX - user) return OVERFLOW;
    sum = user + system;
    total = usage > sum ? usage : sum;
    if (total > (uint64_t)INT64_MAX / 1000u) return OVERFLOW;
    *out = total * 1000u;
    return 0;
}

NCC_API uint32_t ncc_delta(uint64_t current, uint64_t previous, uint64_t *out)
{
    if (scalar_out(out)) return PROTOCOL;
    if (current > (uint64_t)INT64_MAX || previous > (uint64_t)INT64_MAX) return INTEGER;
    if (current < previous) return UNDERFLOW;
    *out = current - previous;
    return 0;
}

NCC_API uint32_t ncc_next_sequence(uint64_t previous, uint64_t supplied)
{
    if (previous == UINT64_MAX || supplied != previous + 1u) return TRANSITION;
    return 0;
}

NCC_API uint32_t ncc_qpc_ns(uint64_t current, uint64_t previous,
                           uint64_t frequency, uint64_t *out)
{
    uint64_t delta, whole, remainder, original, fraction = 0, base;
    uint32_t bit;
    if (scalar_out(out)) return PROTOCOL;
    if (current > (uint64_t)INT64_MAX || previous > (uint64_t)INT64_MAX ||
        frequency == 0 || frequency > (uint64_t)INT64_MAX) return INTEGER;
    if (current < previous) return UNDERFLOW;
    delta = current - previous;
    whole = delta / frequency;
    if (whole > (uint64_t)INT64_MAX / NS) return OVERFLOW;
    base = whole * NS;
    original = delta % frequency;
    remainder = 0;
    /* Long division of original*1e9 by frequency without a wide product.
     * Each remainder is <frequency<=I64. Double/add fit U64 before reduction.
     * Quotient is <1e9. Thirty multiplier bits include every bit of 1e9. */
    for (bit = 30; bit > 0; --bit) {
        fraction *= 2u;
        remainder *= 2u;
        if (remainder >= frequency) {
            remainder -= frequency;
            ++fraction;
        }
        if ((NS >> (bit - 1u)) & 1u) {
            remainder += original;
            if (remainder >= frequency) {
                remainder -= frequency;
                ++fraction;
            }
        }
    }
    if (remainder != 0) ++fraction; /* conservative ceil, not nearest */
    if (fraction > (uint64_t)INT64_MAX - base) return OVERFLOW;
    *out = base + fraction;
    return 0;
}

NCC_API uint32_t ncc_time_ns(uint64_t seconds, uint64_t fraction,
                            uint64_t quantum, uint64_t *out)
{
    uint64_t base, tail;
    if (scalar_out(out)) return PROTOCOL;
    if ((quantum != 1u && quantum != 1000u) || seconds > (uint64_t)INT64_MAX)
        return INTEGER;
    if (fraction >= NS / quantum) return INTEGER;
    if (seconds > (uint64_t)INT64_MAX / NS) return OVERFLOW;
    base = seconds * NS;
    tail = fraction * quantum;
    if (tail > (uint64_t)INT64_MAX - base) return OVERFLOW;
    *out = base + tail;
    return 0;
}

static const uint64_t limits[2][8] = {
    {UINT64_C(60000000000), UINT64_C(57000000000), UINT64_C(3000000000),
     UINT64_C(120000000000), UINT64_C(805306368), UINT64_C(268435456),
     UINT64_C(67108864), UINT64_C(5000000000)},
    {UINT64_C(240000000000), UINT64_C(237000000000), UINT64_C(3000000000),
     UINT64_C(300000000000), UINT64_C(1610612736), UINT64_C(536870912),
     UINT64_C(67108864), UINT64_C(10000000000)}
};

NCC_API uint32_t ncc_limits(uint32_t lane, uint64_t *out, uint64_t count)
{
    size_t i;
    if (lane != 1 && lane != 2) return ADMISSION;
    if (count != 8) return BOUNDS;
    if (scalar_out(out)) return PROTOCOL;
    for (i = 0; i < 8; ++i) out[i] = limits[lane - 1u][i];
    return 0;
}

NCC_API uint32_t ncc_parent_cpu(uint32_t lane, uint64_t controller,
                               uint64_t worker, uint64_t reported)
{
    uint64_t total;
    if (lane != 1 && lane != 2) return ADMISSION;
    if (controller > (uint64_t)INT64_MAX || worker > (uint64_t)INT64_MAX ||
        reported > (uint64_t)INT64_MAX)
        return INTEGER;
    if (worker > (uint64_t)INT64_MAX - controller) return OVERFLOW;
    total = controller + worker;
    if (total != reported) return RELEASE;
    return total > limits[lane - 1u][7] ? PARENT : 0;
}

NCC_API uint32_t ncc_frame_preflight(const void *bytes, uint64_t length,
                                    uint32_t *out_kind)
{
    static const uint32_t sizes[13] = {0, 8, 0, 0, 32, 32, 8, 8, 96, 16, 24, 16, 8};
    const unsigned char *p = (const unsigned char *)bytes;
    uint64_t payload, kind;
    size_t i;
    if (length > 4160u) return BOUNDS; /* BEFORE any pointer read */
    if (length < 64u || p == NULL || out_kind == NULL) return PROTOCOL;
    if (p[0] != 'N' || p[1] != 'C' || p[2] != '0' || p[3] != '1' ||
        little(p + 4, 2) != 1u) return PROTOCOL;
    payload = little(p + 8, 4);
    if (payload > 4096u) return BOUNDS;
    kind = little(p + 6, 2);
    if (kind == 0 || kind > 12 || payload != sizes[kind] ||
        length != 64u + payload) return PROTOCOL;
    for (i = 52; i < 64; ++i) if (p[i] != 0) return PROTOCOL;
    if (little(p + 12, 8) == 0) return TRANSITION;
    *out_kind = (uint32_t)kind;
    return 0;
}

static uint32_t load_state(const void *bytes, uint64_t capacity, State *s)
{
    if (capacity != NCC_STATE_BYTES) return BOUNDS;
    if (bytes == NULL || ((uintptr_t)bytes % 8u) != 0) return PROTOCOL;
    copy_bytes(s, bytes, sizeof(*s));
    if (s->mark != MARK) return TRANSITION;
    return 0;
}

static void store_state(void *bytes, const State *s)
{
    copy_bytes(bytes, s, sizeof(*s));
}

static uint32_t hold(State *s, uint32_t code)
{
    if (s->diagnostic[0] == HELD) return (uint32_t)s->diagnostic[1];
    s->diagnostic[0] = HELD;
    s->diagnostic[1] = code;
    s->diagnostic[2] = 1;
    s->diagnostic[3] = 1;
    return code;
}

NCC_API uint32_t ncc_state_init(void *bytes, uint64_t capacity,
                               const void *attempt, const void *object)
{
    State s = {0};
    const unsigned char *p = (const unsigned char *)bytes;
    const unsigned char *a = (const unsigned char *)attempt;
    const unsigned char *o = (const unsigned char *)object;
    unsigned char az = 0, oz = 0;
    size_t i;
    uint32_t code;
    if (capacity != NCC_STATE_BYTES) return BOUNDS;
    if (p == NULL || ((uintptr_t)p % 8u) != 0 || a == NULL || o == NULL)
        return PROTOCOL;
    if (load_state(bytes, capacity, &s) == 0) {
        code = hold(&s, TRANSITION);
        store_state(bytes, &s);
        return code;
    }
    for (i = 0; i < NCC_STATE_BYTES; ++i) if (p[i] != 0) return TRANSITION;
    for (i = 0; i < 16; ++i) { az |= a[i]; oz |= o[i]; }
    if (az == 0 || oz == 0) return IDENTITY;
    /* load_state read zero bytes above; s is still a zero representation. */
    s.mark = MARK;
    copy_bytes(s.attempt, a, 16);
    copy_bytes(s.object, o, 16);
    store_state(bytes, &s);
    return 0;
}

static void failed_observation(State *s, uint32_t code, uint32_t reason)
{
    s->diagnostic[2] = 1;
    if (s->diagnostic[1] == 0 || code == CPU) s->diagnostic[1] = code;
    if (s->diagnostic[0] == RUNNING || s->diagnostic[0] == STOP_REQUIRED) {
        s->diagnostic[0] = STOP_REQUIRED;
        s->diagnostic[3] = 1;
        if (s->diagnostic[18] == 0) s->diagnostic[18] = reason;
    }
}

static uint32_t consume_sample(State *s, const unsigned char *p, uint32_t *retain)
{
    uint64_t v[12], cpu = 0, previous, phase = s->diagnostic[0];
    uint32_t code;
    size_t i;
    for (i = 0; i < 12; ++i) v[i] = little(p + 8u * i, 8);
    if (!s->started_bound) return TRANSITION;
    if (v[0] > (uint64_t)INT64_MAX || v[1] > (uint64_t)INT64_MAX || v[8] > (uint64_t)INT64_MAX)
        return INTEGER;
    if (v[11] != 0) return PROTOCOL;
    if (phase == DRAINED) {
        if (v[9] != 3 || v[10] != s->diagnostic[6] + 1u || v[10] > 3)
            return TRANSITION;
    } else {
        if (phase != RUNNING && phase != STOP_REQUIRED && phase != STOPPING)
            return TRANSITION;
        if (v[9] != (phase == RUNNING ? 1u : 2u) || v[10] != 0)
            return TRANSITION;
    }
    if (s->platform == 1) {
        if (v[4] != 0) return COUNTER;
        code = ncc_windows_cpu(v[2], v[3], &cpu);
        if (code != 0) return code;
        if (v[5] > 32 || v[6] > UINT32_MAX || v[7] > UINT32_MAX ||
            v[5] > v[6] || v[7] > v[6]) return COUNTER;
    } else {
        code = ncc_linux_cpu(v[2], v[3], v[4], &cpu);
        if (code != 0) return code;
        if (v[5] > 1 || v[6] > 1 || v[7] > 1) return COUNTER;
    }
    if (cpu != v[8]) return COUNTER;
    previous = s->diagnostic[5] == 0 ? s->started : s->diagnostic[8];
    if (v[0] <= previous || v[0] < s->started) return COUNTER;
    if (s->diagnostic[5] != 0) {
        for (i = 0; i < 3; ++i) if (v[i + 2] < s->native[i]) return COUNTER;
        for (i = 1; i < 3; ++i) if (v[i + 5] < s->active[i]) return COUNTER;
    }
    if (phase == DRAINED) {
        if (v[0] < s->diagnostic[20] || v[5] != 0 ||
            (s->platform == 2 && (v[6] != 1 || v[7] != 1))) return COUNTER;
        if (s->diagnostic[6] != 0)
            for (i = 0; i < 3; ++i)
                if (v[i + 2] != s->final_native[i]) return COUNTER;
    }
    if (s->diagnostic[5] >= 32768u) return BOUNDS;
    /* Validation complete. A bad *observed* timing/budget is retained. */
    ++s->diagnostic[5];
    s->diagnostic[7] = cpu;
    s->diagnostic[8] = v[0];
    for (i = 0; i < 3; ++i) { s->native[i] = v[i + 2]; s->active[i] = v[i + 5]; }
    *retain = 1;
    if (phase == DRAINED) {
        if (v[1] > GAP || v[0] - s->diagnostic[20] > DEADLINE ||
            (s->diagnostic[6] == 0 ? v[0] - s->diagnostic[20] < WAIT
                                   : v[0] - s->final_at < GAP)) return TIMING;
        if (v[0] > limits[s->lane - 1u][3]) return COUNTER;
        if (cpu > limits[s->lane - 1u][0]) failed_observation(s, CPU, 1);
        if (s->diagnostic[6] == 0)
            for (i = 0; i < 3; ++i) s->final_native[i] = v[i + 2];
        s->final_at = v[0];
        ++s->diagnostic[6];
        if (s->diagnostic[6] == 3) s->diagnostic[0] = FINAL_NATIVE;
    } else {
        if (cpu >= limits[s->lane - 1u][1]) failed_observation(s, CPU, 1);
        else if (v[1] > GAP || v[0] - previous > GAP)
            failed_observation(s, TIMING, 12);
        else if (v[0] > limits[s->lane - 1u][3]) failed_observation(s, COUNTER, 2);
    }
    return 0;
}

static uint32_t event(State *s, uint32_t kind, const unsigned char *p,
                      uint32_t *retain)
{
    uint64_t phase = s->diagnostic[0], at, reason, stopped, drained;
    uint32_t code, platform, lane;
    switch (kind) {
    case 1:
        if (phase != PREPARED || s->bound) return TRANSITION;
        platform = (uint32_t)little(p, 4); lane = (uint32_t)little(p + 4, 4);
        if (platform != 1 && platform != 2) return ADMISSION;
        if (lane != 1 && lane != 2) return ADMISSION;
        s->platform = platform; s->lane = lane; s->bound = 1;
        return 0;
    case 2:
        return phase == CONTAINED || phase == RUNNING ||
               phase == STOP_REQUIRED || phase == STOPPING ? 0 : TRANSITION;
    case 3:
        if (phase != CONTAINED && phase != RUNNING) return TRANSITION;
        s->diagnostic[0] = STOP_REQUIRED;
        s->diagnostic[1] = COUNTER; s->diagnostic[2] = 1;
        s->diagnostic[3] = 1; s->diagnostic[18] = 5;
        return 0;
    case 4:
        if (phase != RECEIPT_BOUND) return TRANSITION;
        if (!same_bytes(s->receipt, p, 32)) return RELEASE;
        s->diagnostic[0] = ACK_CHECKED;
        return 0;
    case 5:
        if (phase != FINAL_NATIVE) return TRANSITION;
        copy_bytes(s->receipt, p, 32); s->diagnostic[0] = RECEIPT_BOUND;
        return 0;
    case 6:
        if (phase != PREPARED || !s->bound) return TRANSITION;
        at = little(p, 8);
        if (at > (uint64_t)INT64_MAX) return INTEGER;
        s->contained = at; s->diagnostic[0] = CONTAINED;
        return 0;
    case 7:
        if (phase != CONTAINED) return TRANSITION;
        at = little(p, 8);
        if (at > (uint64_t)INT64_MAX) return INTEGER;
        if (at < s->contained) return COUNTER;
        s->started = at; s->started_bound = 1; s->diagnostic[0] = RUNNING;
        return 0;
    case 8:
        return consume_sample(s, p, retain);
    case 9:
        reason = little(p, 4); at = little(p + 8, 8);
        if (little(p + 4, 4) != 0 || reason == 0 || reason > 16) return PROTOCOL;
        if (at > (uint64_t)INT64_MAX) return INTEGER;
        if (phase != RUNNING && phase != STOP_REQUIRED) return TRANSITION;
        if (reason == 16 && (phase != RUNNING || s->diagnostic[18] != 0))
            return TRANSITION;
        if (s->diagnostic[18] != 0 && reason != s->diagnostic[18]) return TRANSITION;
        if (at < s->started || at < s->diagnostic[8]) return COUNTER;
        s->stop_at = at; s->stop_reason = reason; s->diagnostic[19] = at;
        s->diagnostic[0] = STOPPING;
        if (reason != 16) {
            code = reason == 1 ? CPU : reason == 12 ? TIMING : COUNTER;
            failed_observation(s, code, (uint32_t)reason);
            s->diagnostic[3] = 1;
        }
        return 0;
    case 10:
        if (phase != RUNNING && phase != STOPPING) return TRANSITION;
        if (little(p + 4, 4) != 0) return PROTOCOL;
        stopped = little(p + 8, 8); drained = little(p + 16, 8);
        if (stopped > (uint64_t)INT64_MAX || drained > (uint64_t)INT64_MAX) return INTEGER;
        if (stopped < s->started || drained < stopped || drained < s->diagnostic[8])
            return COUNTER;
        if (phase == STOPPING && stopped != s->stop_at) return COUNTER;
        if (s->stop_reason != 0 && s->stop_reason != 16 &&
            drained - stopped > KILL_INTERVAL) return TERMINATION;
        s->diagnostic[19] = stopped; s->diagnostic[20] = drained;
        s->diagnostic[21] = little(p, 4);
        if (s->diagnostic[21] != 0) failed_observation(s, COUNTER, 11);
        s->diagnostic[0] = DRAINED; s->diagnostic[3] = 0;
        return 0;
    case 11:
        if (little(p, 4) < 1 || little(p, 4) > 8 || little(p + 12, 4) != 0)
            return PROTOCOL;
        code = (uint32_t)little(p + 4, 4);
        if (code < 1 || code > 17) return PROTOCOL;
        *retain = 1; /* fixed enum only, never retain errno or raw frame */
        return code;
    case 12:
        if (phase != ACK_CHECKED) return TRANSITION;
        if (little(p, 8) > (uint64_t)INT64_MAX) return INTEGER;
        s->diagnostic[0] = RELEASE_ASSERTED; /* NOT parent closure/OS release */
        return 0;
    default:
        return PROTOCOL;
    }
}

NCC_API uint32_t ncc_apply(void *bytes, uint64_t capacity, uint32_t direction,
                          const void *frame, uint64_t length)
{
    State before, next;
    const unsigned char *p = (const unsigned char *)frame;
    uint32_t code, kind = 0, retain = 0;
    uint64_t sequence;
    size_t slot;
    code = load_state(bytes, capacity, &before);
    if (code != 0) return code;
    if (before.diagnostic[0] == HELD) return (uint32_t)before.diagnostic[1];
    next = before;
    code = ncc_frame_preflight(frame, length, &kind);
    if (code == 0 && direction != 1 && direction != 2) code = PROTOCOL;
    if (code == 0 && ((direction == 1 && kind > 5) ||
                     (direction == 2 && kind < 6))) code = PROTOCOL;
    if (code == 0 && (!same_bytes(p + 20, before.attempt, 16) ||
                     !same_bytes(p + 36, before.object, 16))) code = IDENTITY;
    if (code == 0) {
        slot = direction == 1 ? 9u : 10u;
        sequence = little(p + 12, 8);
        code = ncc_next_sequence(before.diagnostic[slot], sequence);
        if (code == 0) {
            code = event(&next, kind, p + 64, &retain);
            if (code == 0 || retain) next.diagnostic[slot] = sequence;
        }
    }
    if (code != 0) {
        if (!retain) next = before;
        code = hold(&next, code);
    }
    store_state(bytes, &next);
    return code;
}

NCC_API uint32_t ncc_account_bytes(void *bytes, uint64_t capacity,
                                  uint32_t channel, uint64_t amount)
{
    State s;
    uint32_t code = load_state(bytes, capacity, &s);
    uint64_t cap = 0;
    size_t slot = 0;
    if (code != 0) return code;
    if (s.diagnostic[0] == HELD) return (uint32_t)s.diagnostic[1];
    if (!s.bound) code = TRANSITION;
    else if (channel >= 1 && channel <= 6) {
        slot = channel == 6 ? 12u : 12u + channel;
        cap = channel <= 3 ? UINT64_C(65536) :
              channel == 4 ? limits[s.lane - 1u][6] :
              channel == 5 ? limits[s.lane - 1u][5] : UINT64_C(16777216);
        if (s.diagnostic[slot] > cap || amount > cap - s.diagnostic[slot]) code = BOUNDS;
    } else code = PROTOCOL;
    if (code != 0) code = hold(&s, code);
    else s.diagnostic[slot] += amount;
    store_state(bytes, &s);
    return code;
}

NCC_API uint32_t ncc_queue(void *bytes, uint64_t capacity, uint32_t action)
{
    State s;
    uint32_t code = load_state(bytes, capacity, &s);
    if (code != 0) return code;
    if (s.diagnostic[0] == HELD) return (uint32_t)s.diagnostic[1];
    if (action == 1) { if (s.diagnostic[11] >= 4) code = BOUNDS; }
    else if (action == 2) { if (s.diagnostic[11] == 0) code = UNDERFLOW; }
    else code = PROTOCOL;
    if (code != 0) code = hold(&s, code);
    else if (action == 1) ++s.diagnostic[11];
    else --s.diagnostic[11];
    store_state(bytes, &s);
    return code;
}

NCC_API uint32_t ncc_snapshot(const void *bytes, uint64_t capacity,
                             uint64_t *out, uint64_t count)
{
    State s;
    uint32_t code;
    size_t i;
    if (count != NCC_SNAPSHOT_WORDS) return BOUNDS;
    if (out == NULL) return PROTOCOL;
    code = load_state(bytes, capacity, &s);
    if (code != 0) return code;
    for (i = 0; i < NCC_SNAPSHOT_WORDS; ++i) out[i] = s.diagnostic[i];
    return 0;
}

NCC_API const char *ncc_error_text(uint32_t code, uint32_t which)
{
    static const char *const codes[17] = {
        "accounting_admission_closed", "accounting_launch_failed",
        "accounting_counter_invalid", "accounting_cpu_limit",
        "accounting_observation_gap", "accounting_containment_failed",
        "accounting_termination_uncertain", "accounting_receipt_unavailable",
        "accounting_parent_limit", "accounting_protocol_invalid",
        "accounting_bounds_exceeded", "accounting_integer_invalid",
        "accounting_counter_overflow", "accounting_counter_underflow",
        "accounting_identity_mismatch", "accounting_transition_invalid",
        "accounting_release_invalid"
    };
    static const char *const messages[17] = {
        "Physical CPU accounting admission is closed",
        "Contained execution could not start", "CPU accounting could not be verified",
        "Aggregate CPU budget was reached", "CPU observation timing could not be verified",
        "Execution containment could not be verified", "Execution termination could not be verified",
        "Final CPU receipt is unavailable", "Controller resource budget was reached",
        "Private accounting protocol is invalid", "Private accounting record exceeds its bounds",
        "Accounting integer type or range is invalid", "Accounting counter conversion would overflow",
        "Accounting counter difference would underflow", "Accounting identity does not match the attempt",
        "Accounting protocol transition is invalid", "Accounting release acknowledgment is invalid"
    };
    if (code < 1 || code > 17) code = PROTOCOL;
    return which == 0 ? codes[code - 1u] : messages[code - 1u];
}
