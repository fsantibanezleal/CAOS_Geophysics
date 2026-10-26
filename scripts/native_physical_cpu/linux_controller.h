#ifndef LC_CONTROLLER_H
#define LC_CONTROLLER_H

/* Standalone Linux qualification ABI. Not the I01/public bundle revision. */
#include <stddef.h>
#include <stdint.h>
#include <sys/types.h>

#define LC_CONTEXT_BYTES 32768u
#define LC_FRAME_BYTES 4160u
#define LC_SAMPLE_BYTES 96u
#define LC_STREAM_BYTES 65536u
#define LC_TRACE_SAMPLES 65536u
#define LC_QUERY_NS UINT64_C(20000000)
#define LC_POLL_NS UINT64_C(5000000)
#define LC_HEARTBEAT_NS UINT64_C(500000000)

enum lc_error {
    LC_OK = 0, LC_CONTEXT = 1, LC_TOPOLOGY = 2, LC_CREATE = 3,
    LC_CONFIGURE = 4, LC_BIRTH = 5, LC_SETUP = 6, LC_COUNTER = 7,
    LC_REGRESSION = 8, LC_GAP = 9, LC_BUDGET = 10, LC_WALL = 11,
    LC_CANCEL = 12, LC_CONTROL = 13, LC_HEARTBEAT = 14,
    LC_OUTPUT = 15, LC_DESCENDANTS = 16, LC_ROOT_EXIT = 17,
    LC_KILL = 18, LC_DRAIN = 19, LC_FINAL = 20, LC_CUSTODY = 21,
    LC_OOM = 22, LC_CLOCK = 23
};
enum lc_type {
    LC_START = 1, LC_HEARTBEAT_FRAME = 2, LC_CANCEL_FRAME = 3,
    LC_BIND = 4, LC_ACK = 5, LC_SAMPLE = 256, LC_FINAL_FRAME = 257,
    LC_DIGEST = 258, LC_RELEASE = 259
};
struct lc_context {
    uint32_t budget_class, uid, gid, argc, envc;
    unsigned char attempt[16], object[16];
    char strings[LC_CONTEXT_BYTES];
    char *executable, *argv0, *cwd, *argv[34], *envp[33];
};
struct lc_object {
    int unit_fd, science_fd, cpu_fd, events_fd, kill_fd, memory_fd;
    int executable_fd, cwd_fd, null_fd, pidfd, ready_fd, go_fd;
    int out_fd, err_fd, root_reaped, root_status;
    pid_t root_pid;
    uint64_t adopted_reaped, oracle_user_us, oracle_system_us;
    uint64_t oom_kills;
    uint64_t device, inode;
    uint32_t logical_cpus;
};
struct lc_sample {
    uint64_t start_ns, end_ns, usage_us, user_us, system_us, cpu_ns;
    uint64_t populated, root_reaped, adopted_reaped;
};
struct lc_sha {
    uint32_t h[8];
    uint64_t bytes;
    unsigned char block[64];
    size_t used;
};
uint16_t lc_u16(const unsigned char *);
uint32_t lc_u32(const unsigned char *);
uint64_t lc_u64(const unsigned char *);
void lc_put32(unsigned char *, uint32_t);
void lc_put64(unsigned char *, uint64_t);
int lc_parse_context(const unsigned char *, size_t, struct lc_context *);
int lc_load_context(const char *, struct lc_context *);
int lc_parse_cpu(const unsigned char *, size_t, struct lc_sample *);
int lc_parse_events(const unsigned char *, size_t, uint64_t *);
int lc_clock(uint64_t *);
int lc_prepare(struct lc_object *, const struct lc_context *);
int lc_birth(struct lc_object *, const struct lc_context *);
int lc_sample(struct lc_object *, struct lc_sample *);
int lc_stop(struct lc_object *);
int lc_reap(struct lc_object *);
int lc_oom(struct lc_object *, uint64_t *);
int lc_release(struct lc_object *);
void lc_sha_init(struct lc_sha *);
void lc_sha_update(struct lc_sha *, const unsigned char *, size_t);
void lc_sha_final(struct lc_sha *, unsigned char[32]);

#endif
