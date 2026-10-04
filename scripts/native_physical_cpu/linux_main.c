#define _GNU_SOURCE
#include "linux_controller.h"
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

/* Single-thread observer. No science imports, plugins, heap trace, or PID polling. */
struct queued { unsigned char bytes[LC_FRAME_BYTES]; size_t count, sent; };
struct loop {
    struct lc_context context;
    struct lc_object object;
    struct lc_sha sha;
    struct queued queue[4];
    unsigned char input[LC_FRAME_BYTES], digest[32], receipt[32];
    struct lc_sample previous, settled;
    size_t used;
    uint32_t error, queue_head, queue_size, samples, final_count;
    int started, born, go, stopping, available, finished, bound, acknowledged;
    int input_eof, out_eof, err_eof, counter_lost;
    uint64_t in_seq, out_seq, created_ns, heartbeat_ns, birth_ns;
    uint64_t stop_ns, kill_end_ns, drained_ns, last_final_ns, finished_ns;
    uint64_t max_gap_ns, max_query_ns, stdout_bytes, stderr_bytes;
};
static void latch(struct loop *l, uint32_t error) {
    if (!l->error) l->error = error;
}
static int nonzero(const unsigned char *p, size_t n) {
    unsigned char value = 0;
    for (size_t i = 0; i < n; ++i) value |= p[i];
    return value != 0;
}
static int queue_frame(struct loop *l, uint32_t type, const unsigned char *body, size_t n, int hashed) {
    if (l->queue_size == 4 || n > 4096 || l->out_seq == UINT64_MAX) return LC_OUTPUT;
    uint32_t slot = (l->queue_head + l->queue_size) % 4u;
    struct queued *q = &l->queue[slot];
    memset(q, 0, sizeof(*q));
    memcpy(q->bytes, "LCP1", 4); q->bytes[4] = 1;
    q->bytes[6] = (unsigned char)type; q->bytes[7] = (unsigned char)(type >> 8);
    lc_put32(q->bytes + 8, (uint32_t)n); lc_put64(q->bytes + 16, ++l->out_seq);
    uint64_t now;
    if (lc_clock(&now)) return LC_CLOCK;
    lc_put64(q->bytes + 24, now);
    memcpy(q->bytes + 32, l->context.attempt, 16); memcpy(q->bytes + 48, l->context.object, 16);
    if (n) memcpy(q->bytes + 64, body, n);
    q->count = 64 + n; ++l->queue_size;
    if (hashed) lc_sha_update(&l->sha, q->bytes, q->count);
    return LC_OK;
}
static int flush(struct loop *l) {
    /* At most four writes; I/O cannot turn this into a blocking drain loop. */
    for (unsigned i = 0; i < 4 && l->queue_size; ++i) {
        struct queued *q = &l->queue[l->queue_head];
        ssize_t n = write(STDOUT_FILENO, q->bytes + q->sent, q->count - q->sent);
        if (n < 0 && (errno == EAGAIN || errno == EINTR)) return LC_OK;
        if (n <= 0) return LC_OUTPUT;
        q->sent += (size_t)n;
        if (q->sent == q->count) { l->queue_head = (l->queue_head + 1) % 4u; --l->queue_size; }
    }
    return LC_OK;
}
static int input(struct loop *l, uint64_t now) {
    if (l->input_eof) return LC_CONTROL;
    ssize_t n = read(STDIN_FILENO, l->input + l->used, sizeof(l->input) - l->used);
    if (n < 0) return (errno == EAGAIN || errno == EINTR) ? LC_OK : LC_CONTROL;
    if (n == 0) { l->input_eof = 1; return LC_CONTROL; }
    l->used += (size_t)n;
    unsigned processed = 0;
    while (l->used >= 64 && processed++ < 4) {
        unsigned char *p = l->input;
        uint32_t size = lc_u32(p + 8), type = lc_u16(p + 6);
        uint64_t seq = lc_u64(p + 16);
        if (memcmp(p, "LCP1", 4) || lc_u16(p + 4) != 1 || lc_u32(p + 12) ||
            size > 4096 || seq != l->in_seq + 1 || l->in_seq == UINT64_MAX ||
            memcmp(p + 32, l->context.attempt, 16) || memcmp(p + 48, l->context.object, 16)) return LC_CONTROL;
        if (l->used < 64u + size) break;
        if (type == LC_START) {
            if (size || l->started || l->finished) return LC_CONTROL;
            l->started = 1; l->heartbeat_ns = now;
        } else if (type == LC_HEARTBEAT_FRAME) {
            if (size || !l->started || l->acknowledged) return LC_CONTROL;
            l->heartbeat_ns = now;
        } else if (type == LC_CANCEL_FRAME) {
            if (size || !l->started || l->finished) return LC_CONTROL;
            latch(l, LC_CANCEL);
        } else if (type == LC_BIND) {
            if (size != 64 || !l->finished || l->bound ||
                memcmp(p + 64, l->digest, 32) || !nonzero(p + 96, 32)) return LC_CUSTODY;
            memcpy(l->receipt, p + 96, 32); l->bound = 1;
        } else if (type == LC_ACK) {
            if (size != 32 || !l->bound || l->acknowledged || memcmp(p + 64, l->receipt, 32)) return LC_CUSTODY;
            l->acknowledged = 1;
        } else return LC_CONTROL;
        l->in_seq = seq;
        size_t consumed = 64u + size;
        l->used -= consumed;
        memmove(l->input, l->input + consumed, l->used);
    }
    return LC_OK;
}
static int stream(int fd, uint64_t *count, int *ended) {
    unsigned char bytes[4096];
    if (*ended || fd < 0) return LC_OK;
    /* Discard here only after counting; authored fixtures write their own oracle
       in their private cwd. This executable is not the app artifact interface. */
    ssize_t n = read(fd, bytes, sizeof(bytes));
    if (n < 0) return (errno == EAGAIN || errno == EINTR) ? LC_OK : LC_OUTPUT;
    if (!n) { *ended = 1; return LC_OK; }
    if ((uint64_t)n > LC_STREAM_BYTES - *count) return LC_OUTPUT;
    *count += (uint64_t)n; return LC_OK;
}
static int same(const struct lc_sample *a, const struct lc_sample *b) {
    return a->usage_us == b->usage_us && a->user_us == b->user_us && a->system_us == b->system_us;
}
static int observe(struct loop *l) {
    struct lc_sample s;
    int result = lc_sample(&l->object, &s);
    if (result) { l->counter_lost = 1; return result; }
    uint64_t previous_end = l->samples ? l->previous.end_ns : l->created_ns;
    if (s.start_ns < previous_end || s.end_ns < s.start_ns) return LC_CLOCK;
    uint64_t gap = s.start_ns - previous_end, query = s.end_ns - s.start_ns;
    if (gap > l->max_gap_ns) l->max_gap_ns = gap;
    if (query > l->max_query_ns) l->max_query_ns = query;
    if (gap > LC_QUERY_NS || query > LC_QUERY_NS) latch(l, LC_GAP);
    if (l->samples && (s.usage_us < l->previous.usage_us || s.user_us < l->previous.user_us ||
        s.system_us < l->previous.system_us || s.root_reaped < l->previous.root_reaped ||
        s.adopted_reaped < l->previous.adopted_reaped)) { l->counter_lost = 1; latch(l, LC_REGRESSION); }
    l->previous = s;
    if (++l->samples > LC_TRACE_SAMPLES) return LC_OUTPUT;
    uint64_t words[12] = {s.start_ns,s.end_ns,s.usage_us,s.user_us,s.system_us,s.cpu_ns,
        s.populated,s.root_reaped,s.adopted_reaped,l->max_gap_ns,l->max_query_ns,l->error};
    unsigned char body[LC_SAMPLE_BYTES];
    for (size_t i = 0; i < 12; ++i) lc_put64(body + i*8, words[i]);
    if (queue_frame(l, LC_SAMPLE, body, sizeof(body), 1)) return LC_OUTPUT;
    uint64_t stop = l->context.budget_class == 1 ? UINT64_C(57000000000) : UINT64_C(237000000000);
    uint64_t budget = stop + UINT64_C(3000000000);
    if (s.cpu_ns >= stop && !l->stopping) latch(l, LC_BUDGET);
    if (s.cpu_ns > budget) latch(l, LC_BUDGET);
    if (l->object.oom_kills) latch(l, LC_OOM);
    if (l->born && s.root_reaped) {
        if (!WIFEXITED(l->object.root_status) || WEXITSTATUS(l->object.root_status))
            latch(l, l->go ? LC_ROOT_EXIT : LC_SETUP);
        if (s.populated) latch(l, LC_DESCENDANTS);
    }
    if (l->born && !s.populated && s.root_reaped && l->out_eof && l->err_eof) {
        if (!l->drained_ns) {
            l->drained_ns = s.end_ns;
            if (l->stopping && l->drained_ns-l->stop_ns>UINT64_C(250000000)) latch(l,LC_KILL);
        }
        if (s.start_ns - l->drained_ns >= UINT64_C(50000000) &&
            (!l->last_final_ns || s.start_ns - l->last_final_ns >= UINT64_C(20000000))) {
            if (l->final_count && !same(&s, &l->settled)) { latch(l, LC_FINAL); l->final_count = 0; }
            l->settled = s; l->last_final_ns = s.end_ns; ++l->final_count;
            if (l->final_count == 3) l->available = !l->counter_lost;
        }
    } else if (l->drained_ns) { l->counter_lost = 1; latch(l, LC_FINAL); }
    return LC_OK;
}
static int stop(struct loop *l, uint64_t now) {
    if (l->stopping) return LC_OK;
    l->stopping = 1; l->stop_ns = now;
    int result = lc_stop(&l->object);
    uint64_t end;
    if (lc_clock(&end)) return LC_CLOCK;
    l->kill_end_ns = end;
    return result;
}
static int finish(struct loop *l, uint64_t now) {
    const struct lc_sample *s = &l->previous;
    uint64_t words[23] = {s->start_ns,s->end_ns,s->usage_us,s->user_us,s->system_us,s->cpu_ns,
        s->populated,s->root_reaped,s->adopted_reaped,l->max_gap_ns,l->max_query_ns,l->error,
        l->drained_ns,l->stop_ns,l->kill_end_ns,(uint64_t)(unsigned)l->available,
        l->object.oracle_user_us,l->object.oracle_system_us,l->stdout_bytes,l->stderr_bytes,
        l->object.oom_kills,(uint64_t)(unsigned)l->object.root_status,l->object.logical_cpus};
    unsigned char body[184];
    for (size_t i=0;i<23;++i) lc_put64(body+i*8,words[i]);
    int result = queue_frame(l, LC_FINAL_FRAME, body, sizeof(body), 1);
    if (result) return result;
    lc_sha_final(&l->sha, l->digest);
    result = queue_frame(l, LC_DIGEST, l->digest, 32, 0);
    if (result) return result;
    l->finished = 1; l->finished_ns = now;
    return LC_OK;
}
int main(int argc, char **argv) {
    struct loop l; uint64_t now;
    memset(&l, 0, sizeof(l));
    /* No context/error values are printed. Fixed safe pre-birth failure only. */
    if (argc != 2 || lc_load_context(argv[1], &l.context)) {
        fputs("linux_context_invalid\n", stderr); return LC_CONTEXT;
    }
    if (signal(SIGPIPE, SIG_IGN) == SIG_ERR || lc_clock(&l.created_ns)) return LC_CLOCK;
    lc_sha_init(&l.sha);
    int result = lc_prepare(&l.object, &l.context);
    if (result) { fputs("linux_prepare_failed\n", stderr); return result; }
    /* Setup cost is retained in outer accounting; observation clock starts now. */
    if (lc_clock(&l.created_ns)) return LC_CLOCK;
    for (int fd=0;fd<=1;++fd) {
        int flags=fcntl(fd,F_GETFL);
        if (flags<0 || fcntl(fd,F_SETFL,flags|O_NONBLOCK)) return LC_CONTROL;
    }
    for (;;) {
        if (lc_clock(&now)) { latch(&l,LC_CLOCK); break; }
        if (!l.finished) {
            result=observe(&l); if (result) latch(&l,(uint32_t)result);
            if (!l.started && now-l.created_ns>UINT64_C(2000000000)) latch(&l,LC_CONTROL);
            if (l.started && now-l.heartbeat_ns>LC_HEARTBEAT_NS) latch(&l,LC_HEARTBEAT);
            uint64_t wall=l.context.budget_class==1?UINT64_C(120000000000):UINT64_C(300000000000);
            if (now-l.created_ns>=wall) latch(&l,LC_WALL);
            if (l.started && !l.born && !l.error) {
                result=(l.previous.populated || l.previous.cpu_ns) ? LC_TOPOLOGY : lc_birth(&l.object,&l.context);
                if (result) latch(&l,(uint32_t)result);
                else { l.born=1; l.birth_ns=now; }
            }
            if (l.born && !l.go && !l.error) {
                unsigned char byte;
                ssize_t got=read(l.object.ready_fd,&byte,1);
                if (got==1) {
                    if (byte!='R' || write(l.object.go_fd,"G",1)!=1) latch(&l,LC_SETUP);
                    else { l.go=1; close(l.object.ready_fd); close(l.object.go_fd);
                        l.object.ready_fd=-1; l.object.go_fd=-1; }
                } else if (got==0 || (got<0 && errno!=EAGAIN && errno!=EINTR) ||
                    now-l.birth_ns>UINT64_C(2000000000)) latch(&l,LC_SETUP);
            }
            if (l.error) { result=stop(&l,now); if (result) latch(&l,(uint32_t)result); }
            if (l.final_count>=3 || (l.stopping && now-l.stop_ns>UINT64_C(2000000000))) {
                if (l.final_count<3) { l.available=0; latch(&l,LC_DRAIN); }
                result=finish(&l,now); if (result) { latch(&l,(uint32_t)result); break; }
            }
        }
        result=flush(&l); if (result) { latch(&l,(uint32_t)result); (void)stop(&l,now); break; }
        if (l.finished && l.acknowledged && l.queue_size==0) {
            /* A failed CPU verdict can release a truly empty sealed object, not publish science. */
            if (!l.available || lc_release(&l.object)) { latch(&l,LC_CUSTODY); break; }
            unsigned char body[8]; lc_put64(body,l.error);
            result=queue_frame(&l,LC_RELEASE,body,sizeof(body),0);
            if (result) { latch(&l,(uint32_t)result); break; }
            while (l.queue_size) {
                if (lc_clock(&now) || now-l.finished_ns>UINT64_C(5000000000) || flush(&l)) {
                    latch(&l,LC_CUSTODY); break;
                }
                struct pollfd fd={STDOUT_FILENO,POLLOUT,0};
                int ignored=poll(&fd,1,5); (void)ignored;
            }
            return (int)l.error;
        }
        if (l.finished && now-l.finished_ns>UINT64_C(5000000000)) { latch(&l,LC_CUSTODY); break; }
        struct pollfd fds[4]={{STDIN_FILENO,POLLIN,0},{STDOUT_FILENO,l.queue_size?POLLOUT:0,0},
            {l.out_eof ? -1 : l.object.out_fd,POLLIN,0},
            {l.err_eof ? -1 : l.object.err_fd,POLLIN,0}};
        int ready=poll(fds,4,5);
        if (ready<0 && errno!=EINTR) { latch(&l,LC_CONTROL); (void)stop(&l,now); break; }
        if (lc_clock(&now)) { latch(&l,LC_CLOCK); (void)stop(&l,l.previous.end_ns); break; }
        if (fds[0].revents&(POLLIN|POLLHUP|POLLERR|POLLNVAL)) {
            result=input(&l,now); if (result) latch(&l,(uint32_t)result);
        }
        result=stream(l.object.out_fd,&l.stdout_bytes,&l.out_eof); if (result) latch(&l,(uint32_t)result);
        result=stream(l.object.err_fd,&l.stderr_bytes,&l.err_eof); if (result) latch(&l,(uint32_t)result);
        if (l.error && !l.stopping) { result=stop(&l,now); if (result) latch(&l,(uint32_t)result); }
    }
    /* No implicit ACK/unlink on failure. PID1 kills remaining tasks; private
       captures retain HELD evidence. Kernel counters may vanish on unit death. */
    if (!l.stopping) (void)stop(&l,l.previous.end_ns);
    return (int)(l.error?l.error:LC_CUSTODY);
}
