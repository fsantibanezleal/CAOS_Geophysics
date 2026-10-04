#define _GNU_SOURCE
#include "linux_controller.h"
#include "controller.h"
#include <errno.h>
#include <fcntl.h>
#include <grp.h>
#include <limits.h>
#include <linux/audit.h>
#include <linux/capability.h>
#include <linux/filter.h>
#include <linux/magic.h>
#include <linux/sched.h>
#include <linux/seccomp.h>
#include <poll.h>
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/statfs.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error "This source requires the independently reviewed Linux x86_64 syscall ABI"
#endif

uint16_t lc_u16(const unsigned char *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
uint32_t lc_u32(const unsigned char *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
uint64_t lc_u64(const unsigned char *p) {
    return (uint64_t)lc_u32(p) | ((uint64_t)lc_u32(p + 4) << 32);
}
void lc_put32(unsigned char *p, uint32_t v) {
    for (size_t i = 0; i < 4; ++i) p[i] = (unsigned char)(v >> (i * 8));
}
void lc_put64(unsigned char *p, uint64_t v) {
    for (size_t i = 0; i < 8; ++i) p[i] = (unsigned char)(v >> (i * 8));
}
static int nonnil(const unsigned char *p, size_t n) {
    unsigned char a = 0;
    for (size_t i = 0; i < n; ++i) a |= p[i];
    return a != 0;
}
static int utf8(const unsigned char *p, size_t n) {
    size_t i = 0;
    while (i < n) {
        uint32_t cp = p[i++], minimum;
        size_t extra;
        if (cp == 0) return 0;
        if (cp < 128) continue;
        if (cp >= 194 && cp <= 223) { extra = 1; minimum = 128; cp &= 31; }
        else if (cp >= 224 && cp <= 239) { extra = 2; minimum = 2048; cp &= 15; }
        else if (cp >= 240 && cp <= 244) { extra = 3; minimum = 65536; cp &= 7; }
        else return 0;
        if (extra > n - i) return 0;
        for (size_t j = 0; j < extra; ++j) {
            if (p[i] < 128 || p[i] > 191) return 0;
            cp = (cp << 6) | (uint32_t)(p[i++] & 63);
        }
        if (cp < minimum || cp > 1114111 || (cp >= 55296 && cp <= 57343)) return 0;
    }
    return 1;
}
static int path_ok(const unsigned char *p, size_t n) {
    size_t start = 1;
    if (n < 2 || p[0] != '/') return 0;
    for (size_t i = 1; i <= n; ++i) {
        if (i != n && p[i] != '/') continue;
        size_t count = i - start;
        if (!count || (count == 1 && p[start] == '.') ||
            (count == 2 && p[start] == '.' && p[start + 1] == '.')) return 0;
        start = i + 1;
    }
    return 1;
}
static int env_key(const unsigned char *p, size_t n, size_t *key_len) {
    static const char *const keys[] = { "LANG", "LC_ALL", "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED" };
    const unsigned char *equal = memchr(p, '=', n);
    if (equal == NULL) return 0;
    *key_len = (size_t)(equal - p);
    for (size_t i = 0; i < sizeof(keys) / sizeof(keys[0]); ++i)
        if (strlen(keys[i]) == *key_len && !memcmp(keys[i], p, *key_len)) return 1;
    return 0;
}
int lc_parse_context(const unsigned char *p, size_t n, struct lc_context *c) {
    size_t offsets[67], sizes[67], key_sizes[32], offset = 64, arg_bytes = 0, env_bytes = 0;
    uint32_t argc, envc;
    if (p == NULL || c == NULL || n < 64 || n > LC_CONTEXT_BYTES ||
        memcmp(p, "LCX1", 4) || lc_u16(p + 4) != 1 ||
        (lc_u16(p + 6) != 1 && lc_u16(p + 6) != 2) ||
        lc_u32(p + 8) == 0 || lc_u32(p + 12) == 0 ||
        lc_u32(p + 8) == UINT32_MAX || lc_u32(p + 12) == UINT32_MAX ||
        lc_u32(p + 24) != n - 64 || lc_u32(p + 28) ||
        !nonnil(p + 32, 16) || !nonnil(p + 48, 16)) return LC_CONTEXT;
    argc = lc_u32(p + 16); envc = lc_u32(p + 20);
    if (argc < 1 || argc > 32 || envc > 32) return LC_CONTEXT;
    size_t count = 3u + argc + envc;
    /* First pass validates all lengths/UTF8/combined bounds/duplicates before copy. */
    for (size_t i = 0; i < count; ++i) {
        if (n - offset < 4) return LC_CONTEXT;
        size_t size = lc_u32(p + offset); offset += 4;
        if (!size || size > 1024 || size > n - offset || !utf8(p + offset, size)) return LC_CONTEXT;
        offsets[i] = offset; sizes[i] = size;
        if (i < 3 && !path_ok(p + offset, size)) return LC_CONTEXT;
        if (i >= 3 && i < 3u + argc) arg_bytes += size;
        if (i >= 3u + argc) {
            size_t e = i - 3u - argc;
            env_bytes += size;
            if (!env_key(p + offset, size, &key_sizes[e])) return LC_CONTEXT;
            for (size_t j = 0; j < e; ++j) {
                size_t prior = 3u + argc + j;
                if (key_sizes[j] == key_sizes[e] &&
                    !memcmp(p + offsets[prior], p + offset, key_sizes[e])) return LC_CONTEXT;
            }
        }
        offset += size;
    }
    if (offset != n || arg_bytes > 16384 || env_bytes > 4096) return LC_CONTEXT;
    memset(c, 0, sizeof(*c));
    c->budget_class = lc_u16(p + 6); c->uid = lc_u32(p + 8); c->gid = lc_u32(p + 12);
    c->argc = argc; c->envc = envc;
    memcpy(c->attempt, p + 32, 16); memcpy(c->object, p + 48, 16);
    size_t at = 0;
    for (size_t i = 0; i < count; ++i) {
        if (sizes[i] + 1 > sizeof(c->strings) - at) return LC_CONTEXT;
        char *value = c->strings + at;
        memcpy(value, p + offsets[i], sizes[i]); value[sizes[i]] = '\0';
        if (i == 0) c->executable = value;
        else if (i == 1) { c->argv0 = value; c->argv[0] = value; }
        else if (i == 2) c->cwd = value;
        else if (i < 3u + argc) c->argv[i - 2] = value;
        else c->envp[i - 3u - argc] = value;
        at += sizes[i] + 1;
    }
    return LC_OK;
}
/* Every component is opened by descriptor, no link/reparse traversal. */
static int open_path(const char *path, int directory, uid_t leaf_owner, int writable_leaf) {
    size_t n = strlen(path);
    if (!path_ok((const unsigned char *)path, n) || n > 1024) return -1;
    int fd = open("/", O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return -1;
    const char *part = path + 1;
    for (;;) {
        const char *slash = strchr(part, '/');
        size_t size = slash ? (size_t)(slash - part) : strlen(part);
        char name[1025]; struct stat st;
        memcpy(name, part, size); name[size] = '\0';
        /* The science-owned0700 cwd is not readable by the capability-limited
           observer. O_PATH on that leaf retains identity without adding DAC
           privilege; child fchdir checks search permission after credential drop. */
        int access = (!slash && directory && writable_leaf) ? O_PATH : O_RDONLY;
        int next = openat(fd, name, access | O_CLOEXEC | O_NOFOLLOW |
                          ((slash || directory) ? O_DIRECTORY : 0));
        close(fd); fd = next;
        if (fd < 0 || fstat(fd, &st) != 0 ||
            st.st_uid != (slash ? 0u : leaf_owner) ||
            (st.st_mode & (S_IWGRP | S_IWOTH)) ||
            (!slash && !directory && (!S_ISREG(st.st_mode) || st.st_nlink != 1))) {
            if (fd >= 0) close(fd);
            return -1;
        }
        if (!slash) {
            if (directory && writable_leaf && (st.st_mode & 0777u) != 0700u) { close(fd); return -1; }
            return fd;
        }
        part = slash + 1;
    }
}
static int read_fd(int fd, unsigned char *p, size_t cap, size_t *n) {
    ssize_t got;
    do { got = pread(fd, p, cap, 0); } while (got < 0 && errno == EINTR);
    if (got < 0) return -1;
    *n = (size_t)got;
    unsigned char extra;
    do { got = pread(fd, &extra, 1, (off_t)*n); } while (got < 0 && errno == EINTR);
    return got == 0 ? 0 : -1;
}
int lc_load_context(const char *path, struct lc_context *c) {
    unsigned char raw[LC_CONTEXT_BYTES]; size_t n; struct stat st;
    int fd = open_path(path, 0, 0, 0);
    if (fd < 0) return LC_CONTEXT;
    int bad = fstat(fd, &st) != 0 || (st.st_mode & 0777u) != 0600u ||
        st.st_size < 64 || st.st_size > (off_t)LC_CONTEXT_BYTES || read_fd(fd, raw, sizeof(raw), &n);
    close(fd);
    if (bad) return LC_CONTEXT;
    return lc_parse_context(raw, n, c);
}
static int decimal(const unsigned char *p, size_t n, uint64_t *v) {
    uint64_t value = 0;
    if (!n || n > 20) return -1;
    for (size_t i = 0; i < n; ++i) {
        if (p[i] < '0' || p[i] > '9') return -1;
        unsigned digit = (unsigned)(p[i] - '0');
        if (value > (UINT64_MAX - digit) / 10u) return -1;
        value = value * 10u + digit;
    }
    *v = value; return 0;
}
static int keyed(const unsigned char *p, size_t n, const char *const *keys,
                 size_t count, uint64_t *values, uint32_t *seen) {
    size_t at = 0, lines = 0;
    *seen = 0;
    if (!n || n > 4096 || p[n - 1] != '\n') return -1;
    while (at < n) {
        size_t start = at;
        while (at < n && p[at] != ' ' && at - start <= 64) ++at;
        if (at == n || at - start > 64 || ++lines > 32) return -1;
        size_t key_size = at++ - start, value_start = at;
        while (at < n && p[at] != '\n' && at - value_start <= 20) ++at;
        if (at == n) return -1;
        size_t key = count;
        for (size_t j = 0; j < count; ++j)
            if (strlen(keys[j]) == key_size && !memcmp(p + start, keys[j], key_size)) { key = j; break; }
        if (key == count || (*seen & (1u << key)) ||
            decimal(p + value_start, at - value_start, &values[key])) return -1;
        *seen |= 1u << key; ++at;
    }
    return 0;
}
int lc_parse_cpu(const unsigned char *p, size_t n, struct lc_sample *s) {
    static const char *const keys[] = { "usage_usec", "user_usec", "system_usec",
        "nr_periods", "nr_throttled", "throttled_usec", "nr_bursts", "burst_usec" };
    uint64_t v[8] = {0}; uint32_t seen;
    if (keyed(p, n, keys, 8, v, &seen) || (seen & 7u) != 7u ||
        ncc_linux_cpu(v[0], v[1], v[2], &s->cpu_ns) != 0) return LC_COUNTER;
    s->usage_us = v[0]; s->user_us = v[1]; s->system_us = v[2];
    return LC_OK;
}
int lc_parse_events(const unsigned char *p, size_t n, uint64_t *populated) {
    static const char *const keys[] = { "populated", "frozen" };
    uint64_t v[2] = {0}; uint32_t seen;
    if (keyed(p, n, keys, 2, v, &seen) || seen != 3 || v[0] > 1 || v[1] != 0) return LC_COUNTER;
    *populated = v[0]; return LC_OK;
}
int lc_clock(uint64_t *v) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) || t.tv_sec < 0 || t.tv_nsec < 0 ||
        t.tv_nsec >= 1000000000 || ncc_time_ns((uint64_t)t.tv_sec,
        (uint64_t)t.tv_nsec, 1u, v) != 0) return LC_CLOCK;
    return LC_OK;
}
static int child_file(int dir, const char *name, int flags) {
    return openat(dir, name, flags | O_CLOEXEC | O_NOFOLLOW);
}
static int exact_file(int dir, const char *name, const char *value, int write_it) {
    unsigned char actual[256]; size_t n;
    if (write_it) {
        int fd = child_file(dir, name, O_WRONLY);
        if (fd < 0) return -1;
        ssize_t written = write(fd, value, strlen(value)); close(fd);
        if (written < 0 || (size_t)written != strlen(value)) return -1;
    }
    int fd = child_file(dir, name, O_RDONLY);
    if (fd < 0) return -1;
    int bad = read_fd(fd, actual, sizeof(actual), &n); close(fd);
    return bad || n != strlen(value) || memcmp(actual, value, n) ? -1 : 0;
}
static int controller_set(int dir) {
    unsigned char p[256]; size_t n;
    int fd = child_file(dir, "cgroup.subtree_control", O_RDONLY);
    if (fd < 0) return -1;
    int bad = read_fd(fd, p, sizeof(p) - 1, &n); close(fd);
    if (bad) return -1;
    p[n] = 0;
    /* Exact delegated set, not substring matches or unexpected controllers. */
    return strcmp((const char *)p, "cpu memory pids\n") ? -1 : 0;
}
int lc_prepare(struct lc_object *o, const struct lc_context *c) {
    unsigned char proc[512]; size_t n; char unit_path[160], own_path[180], hex[33];
    struct stat st; struct statfs fs; cpu_set_t affinity;
    memset(o, 0, sizeof(*o));
    o->unit_fd = o->science_fd = o->cpu_fd = o->events_fd = o->kill_fd = o->memory_fd = -1;
    o->executable_fd = o->cwd_fd = o->null_fd = o->pidfd = o->ready_fd = o->go_fd = -1;
    o->out_fd = o->err_fd = -1;
    if (getuid() || geteuid() || getgid() || getegid() ||
        sched_getaffinity(0, sizeof(affinity), &affinity)) return LC_TOPOLOGY;
    int logical = CPU_COUNT(&affinity);
    long online = sysconf(_SC_NPROCESSORS_ONLN);
    if (logical < 1 || logical > 8 || online < logical || online > 8) return LC_TOPOLOGY;
    o->logical_cpus = (uint32_t)logical;
    for (size_t i = 0; i < 16; ++i) {
        static const char digits[] = "0123456789abcdef";
        hex[i * 2] = digits[c->attempt[i] >> 4]; hex[i * 2 + 1] = digits[c->attempt[i] & 15];
    }
    hex[32] = '\0';
    int length = snprintf(unit_path, sizeof(unit_path),
        "/sys/fs/cgroup/system.slice/geophysics-cpu-qual-%s.service", hex);
    if (length < 0 || (size_t)length >= sizeof(unit_path)) return LC_TOPOLOGY;
    length = snprintf(own_path, sizeof(own_path),
        "0::/system.slice/geophysics-cpu-qual-%s.service/observer\n", hex);
    if (length < 0 || (size_t)length >= sizeof(own_path)) return LC_TOPOLOGY;
    int fd = open("/proc/self/cgroup", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) return LC_TOPOLOGY;
    int bad = read_fd(fd, proc, sizeof(proc), &n); close(fd);
    if (bad || n != strlen(own_path) || memcmp(proc, own_path, n)) return LC_TOPOLOGY;
    o->unit_fd = open_path(unit_path, 1, 0, 0);
    if (o->unit_fd < 0 || fstatfs(o->unit_fd, &fs) ||
        fs.f_type != CGROUP2_SUPER_MAGIC || exact_file(o->unit_fd, "cgroup.procs", "", 0) ||
        exact_file(o->unit_fd, "cgroup.type", "domain\n", 0)) return LC_TOPOLOGY;
    fd = child_file(o->unit_fd, "cgroup.subtree_control", O_WRONLY);
    if (fd < 0) return LC_CONFIGURE;
    const char enable[] = "+cpu +memory +pids\n";
    ssize_t put = write(fd, enable, sizeof(enable) - 1); close(fd);
    if (put != (ssize_t)(sizeof(enable) - 1) || controller_set(o->unit_fd)) return LC_CONFIGURE;
    if (mkdirat(o->unit_fd, "science", 0700)) return LC_CREATE;
    o->science_fd = child_file(o->unit_fd, "science", O_RDONLY | O_DIRECTORY);
    if (o->science_fd < 0 || fstat(o->science_fd, &st) || st.st_uid ||
        exact_file(o->science_fd, "cgroup.type", "domain\n", 0) ||
        exact_file(o->science_fd, "cgroup.procs", "", 0)) return LC_CREATE;
    o->device = (uint64_t)st.st_dev; o->inode = (uint64_t)st.st_ino;
    if (exact_file(o->science_fd, "cpu.max", "100000 100000\n", 1) ||
        exact_file(o->science_fd, "cpu.max.burst", "0\n", 1) ||
        exact_file(o->science_fd, "pids.max", "256\n", 1) ||
        exact_file(o->science_fd, "memory.swap.max", "0\n", 1) ||
        exact_file(o->science_fd, "memory.max", c->budget_class == 1 ? "805306368\n" : "1073741824\n", 1))
        return LC_CONFIGURE;
    int observer = child_file(o->unit_fd, "observer", O_RDONLY | O_DIRECTORY);
    if (observer < 0) return LC_CONFIGURE;
    bad = exact_file(observer, "memory.max", "67108864\n", 1) ||
        exact_file(observer, "memory.swap.max", "0\n", 1) || exact_file(observer, "pids.max", "1\n", 1);
    close(observer);
    if (bad) return LC_CONFIGURE;
    o->cpu_fd = child_file(o->science_fd, "cpu.stat", O_RDONLY);
    o->events_fd = child_file(o->science_fd, "cgroup.events", O_RDONLY);
    o->kill_fd = child_file(o->science_fd, "cgroup.kill", O_WRONLY);
    o->memory_fd = child_file(o->science_fd, "memory.events", O_RDONLY);
    o->executable_fd = open_path(c->executable, 0, 0, 0);
    o->cwd_fd = open_path(c->cwd, 1, (uid_t)c->uid, 1);
    o->null_fd = open("/dev/null", O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (o->cpu_fd < 0 || o->events_fd < 0 || o->kill_fd < 0 || o->memory_fd < 0 ||
        o->executable_fd < 0 || o->cwd_fd < 0 || o->null_fd < 0 ||
        prctl(PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0)) return LC_SETUP;
    return LC_OK;
}
static void child_fail(int ready) {
    const unsigned char code = 'E';
    ssize_t unused = write(ready, &code, 1); (void)unused;
    _exit(126);
}
static int science_filter(void) {
    /* v255 RestrictNamespaces would block the controller's own clone3 because
       seccomp cannot dereference clone_args. Apply this AFTER accounted birth,
       to science only. ENOSYS permits libc's ordinary pthread clone fallback;
       no controller birth fallback exists. Namespace-bearing clone is denied. */
    const uint32_t namespaces = CLONE_NEWCGROUP | CLONE_NEWIPC | CLONE_NEWNET |
        CLONE_NEWNS | CLONE_NEWPID | CLONE_NEWUSER | CLONE_NEWUTS | CLONE_NEWTIME;
    struct sock_filter instructions[] = {
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS, offsetof(struct seccomp_data,arch)),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,AUDIT_ARCH_X86_64,1,0),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,nr)),
        BPF_JUMP(BPF_JMP|BPF_JSET|BPF_K,__X32_SYSCALL_BIT,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_KILL_PROCESS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_clone3,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|(uint32_t)ENOSYS),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_setns,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|(uint32_t)EPERM),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_unshare,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|(uint32_t)EPERM),
        BPF_JUMP(BPF_JMP|BPF_JEQ|BPF_K,SYS_clone,1,0),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
        BPF_STMT(BPF_LD|BPF_W|BPF_ABS,offsetof(struct seccomp_data,args[0])),
        BPF_JUMP(BPF_JMP|BPF_JSET|BPF_K,namespaces,0,1),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ERRNO|(uint32_t)EPERM),
        BPF_STMT(BPF_RET|BPF_K,SECCOMP_RET_ALLOW),
    };
    struct sock_fprog program = {(unsigned short)(sizeof(instructions)/sizeof(instructions[0])),instructions};
    return syscall(SYS_seccomp,SECCOMP_SET_MODE_FILTER,0u,&program) ? -1 : 0;
}
static void child_setup(const struct lc_object *o, const struct lc_context *c,
                        int ready, int go, int out, int err, pid_t expected_parent) {
    /* Duplicate to a disjoint high range before remapping fixed descriptors. */
    int originals[7] = {o->null_fd, out, err, ready, go, o->executable_fd, o->cwd_fd};
    int high[7];
    for (size_t i = 0; i < 7; ++i) {
        high[i] = fcntl(originals[i], F_DUPFD_CLOEXEC, 64);
        if (high[i] < 0) child_fail(ready);
    }
    for (int i = 0; i < 7; ++i)
        if (dup2(high[i], i) < 0) child_fail(ready);
    if (syscall(SYS_close_range, 7u, UINT_MAX, 0u)) child_fail(3);
    for (int capability = 0; capability < 64; ++capability) {
        int has = prctl(PR_CAPBSET_READ, capability, 0, 0, 0);
        if (has < 0) {
            if (errno == EINVAL && capability > CAP_LAST_CAP) break;
            child_fail(3);
        }
        if (has && prctl(PR_CAPBSET_DROP, capability, 0, 0, 0)) child_fail(3);
        if (prctl(PR_CAPBSET_READ, capability, 0, 0, 0) != 0) child_fail(3);
    }
    if (setgroups(0, NULL) || setresgid((gid_t)c->gid, (gid_t)c->gid, (gid_t)c->gid) ||
        setresuid((uid_t)c->uid, (uid_t)c->uid, (uid_t)c->uid)) child_fail(3);
    uid_t r, e, s; gid_t gr, ge, gs;
    if (getresuid(&r, &e, &s) || getresgid(&gr, &ge, &gs) ||
        r != c->uid || e != c->uid || s != c->uid || gr != c->gid || ge != c->gid || gs != c->gid ||
        getgroups(0, NULL) != 0) child_fail(3);
    struct __user_cap_header_struct header = {_LINUX_CAPABILITY_VERSION_3, 0};
    struct __user_cap_data_struct caps[2] = {{0}, {0}};
    if (syscall(SYS_capset, &header, caps) || syscall(SYS_capget, &header, caps) ||
        caps[0].effective || caps[0].permitted || caps[0].inheritable ||
        caps[1].effective || caps[1].permitted || caps[1].inheritable ||
        prctl(PR_CAP_AMBIENT, PR_CAP_AMBIENT_CLEAR_ALL, 0, 0, 0) ||
        prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) || prctl(PR_SET_DUMPABLE, 0, 0, 0, 0) ||
        prctl(PR_SET_PDEATHSIG, SIGKILL, 0, 0, 0) || getppid() != expected_parent ||
        science_filter() || fchdir(6)) child_fail(3);
    const unsigned char ready_byte = 'R';
    if (write(3, &ready_byte, 1) != 1) child_fail(3);
    unsigned char permission;
    ssize_t got;
    do { got = read(4, &permission, 1); } while (got < 0 && errno == EINTR);
    if (got != 1 || permission != 'G' || getppid() != expected_parent) child_fail(3);
    close(3); close(4); close(6);
    if (fcntl(5, F_SETFD, FD_CLOEXEC)) _exit(126);
    fexecve(5, c->argv, c->envp);
    _exit(127);
}
int lc_birth(struct lc_object *o, const struct lc_context *c) {
    int ready[2], go[2], out[2], err[2];
    if (pipe2(ready, O_CLOEXEC) || pipe2(go, O_CLOEXEC) ||
        pipe2(out, O_CLOEXEC) || pipe2(err, O_CLOEXEC)) return LC_BIRTH;
    struct clone_args args = {0};
    pid_t expected_parent = getpid();
    args.flags = CLONE_INTO_CGROUP | CLONE_PIDFD;
    args.pidfd = (uint64_t)(uintptr_t)&o->pidfd;
    args.exit_signal = SIGCHLD;
    args.cgroup = (uint64_t)(unsigned)o->science_fd;
    long result = syscall(SYS_clone3, &args, sizeof(args));
    int saved_errno = errno; /* No fallback, preserve the actual syscall outcome. */
    if (result == 0) child_setup(o, c, ready[1], go[0], out[1], err[1], expected_parent);
    close(ready[1]); close(go[0]); close(out[1]); close(err[1]);
    if (result < 0) {
        close(ready[0]); close(go[1]); close(out[0]); close(err[0]);
        errno = saved_errno; return LC_BIRTH;
    }
    if (result > INT_MAX || o->pidfd < 0) return LC_BIRTH;
    o->root_pid = (pid_t)result; o->ready_fd = ready[0]; o->go_fd = go[1];
    o->out_fd = out[0]; o->err_fd = err[0];
    int fds[5] = {o->ready_fd, o->go_fd, o->out_fd, o->err_fd, o->pidfd};
    for (size_t i = 0; i < 5; ++i) {
        int flags = fcntl(fds[i], F_GETFL);
        if (flags < 0 || fcntl(fds[i], F_SETFL, flags | O_NONBLOCK)) return LC_BIRTH;
    }
    return LC_OK;
}
int lc_reap(struct lc_object *o) {
    for (unsigned i = 0; i < 256; ++i) {
        int status; struct rusage ru;
        pid_t pid = wait4(-1, &status, WNOHANG, &ru);
        if (pid == 0 || (pid < 0 && errno == ECHILD)) return LC_OK;
        if (pid < 0) { if (errno == EINTR) continue; return LC_COUNTER; }
        if (ru.ru_utime.tv_sec < 0 || ru.ru_utime.tv_usec < 0 || ru.ru_stime.tv_sec < 0 || ru.ru_stime.tv_usec < 0)
            return LC_COUNTER;
        uint64_t user_ns, system_ns;
        if (ncc_time_ns((uint64_t)ru.ru_utime.tv_sec, (uint64_t)ru.ru_utime.tv_usec, 1000, &user_ns) ||
            ncc_time_ns((uint64_t)ru.ru_stime.tv_sec, (uint64_t)ru.ru_stime.tv_usec, 1000, &system_ns))
            return LC_COUNTER;
        uint64_t user = user_ns / 1000u, system = system_ns / 1000u;
        if (user > UINT64_MAX - o->oracle_user_us || system > UINT64_MAX - o->oracle_system_us)
            return LC_COUNTER;
        o->oracle_user_us += user; o->oracle_system_us += system;
        if (pid == o->root_pid) { o->root_reaped = 1; o->root_status = status; }
        else ++o->adopted_reaped;
    }
    return LC_OK;
}
int lc_sample(struct lc_object *o, struct lc_sample *s) {
    unsigned char p[4096]; size_t n;
    memset(s, 0, sizeof(*s));
    if (lc_clock(&s->start_ns)) return LC_CLOCK;
    if (read_fd(o->cpu_fd, p, sizeof(p), &n) || lc_parse_cpu(p, n, s) ||
        read_fd(o->events_fd, p, sizeof(p), &n) || lc_parse_events(p, n, &s->populated) ||
        lc_reap(o) || lc_oom(o, &o->oom_kills)) return LC_COUNTER;
    if (o->root_reaped) {
        struct pollfd root = {o->pidfd, POLLIN, 0};
        if (poll(&root, 1, 0) != 1 || !(root.revents & POLLIN)) return LC_COUNTER;
    }
    s->root_reaped = (uint64_t)(unsigned)o->root_reaped; s->adopted_reaped = o->adopted_reaped;
    if (lc_clock(&s->end_ns) || s->end_ns < s->start_ns) return LC_CLOCK;
    return LC_OK;
}
int lc_stop(struct lc_object *o) {
    if (o->kill_fd < 0 || write(o->kill_fd, "1\n", 2) != 2) return LC_KILL;
    return LC_OK;
}
int lc_oom(struct lc_object *o, uint64_t *kills) {
    static const char *const keys[] = {"low", "high", "max", "oom", "oom_kill", "oom_group_kill"};
    unsigned char p[4096]; size_t n; uint64_t values[6] = {0}; uint32_t seen;
    if (read_fd(o->memory_fd, p, sizeof(p), &n) || keyed(p, n, keys, 6, values, &seen) ||
        (seen & 31u) != 31u) return LC_COUNTER;
    *kills = values[4]; return LC_OK;
}
int lc_release(struct lc_object *o) {
    /* Caller has verified final sample/digest/custody ACK, never a timer release. */
    int fds[] = {o->cpu_fd, o->events_fd, o->kill_fd, o->memory_fd};
    for (size_t i = 0; i < sizeof(fds) / sizeof(fds[0]); ++i)
        if (fds[i] >= 0 && close(fds[i])) return LC_CUSTODY;
    if (close(o->science_fd) || unlinkat(o->unit_fd, "science", AT_REMOVEDIR)) return LC_CUSTODY;
    return LC_OK;
}

/* SHA-256 (FIPS180-4/RFC6234): transcript identity only, not an authentication MAC. */
static uint32_t rotate(uint32_t x, unsigned n) { return (x >> n) | (x << (32u - n)); }
static void sha_block(struct lc_sha *s, const unsigned char *p) {
    static const uint32_t k[64] = {
        0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
        0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
        0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
        0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
        0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
        0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
        0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
        0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u};
    uint32_t w[64];
    for (size_t i = 0; i < 16; ++i) w[i] = ((uint32_t)p[4*i] << 24) |
        ((uint32_t)p[4*i+1] << 16) | ((uint32_t)p[4*i+2] << 8) | p[4*i+3];
    for (size_t i = 16; i < 64; ++i) {
        uint32_t x = w[i-15], y = w[i-2];
        w[i] = w[i-16] + (rotate(x,7)^rotate(x,18)^(x>>3)) + w[i-7] +
            (rotate(y,17)^rotate(y,19)^(y>>10));
    }
    uint32_t a=s->h[0],b=s->h[1],c=s->h[2],d=s->h[3],e=s->h[4],f=s->h[5],g=s->h[6],h=s->h[7];
    for (size_t i=0;i<64;++i) {
        uint32_t t1=h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[i]+w[i];
        uint32_t t2=(rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c));
        h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
    }
    s->h[0]+=a;s->h[1]+=b;s->h[2]+=c;s->h[3]+=d;s->h[4]+=e;s->h[5]+=f;s->h[6]+=g;s->h[7]+=h;
}
void lc_sha_init(struct lc_sha *s) {
    static const uint32_t initial[8] = {0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
        0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u};
    memset(s,0,sizeof(*s));memcpy(s->h,initial,sizeof(initial));
}
void lc_sha_update(struct lc_sha *s, const unsigned char *p, size_t n) {
    s->bytes += n;
    while (n) {
        size_t take = 64-s->used; if (take>n) take=n;
        memcpy(s->block+s->used,p,take);s->used+=take;p+=take;n-=take;
        if (s->used==64) {sha_block(s,s->block);s->used=0;}
    }
}
void lc_sha_final(struct lc_sha *s, unsigned char digest[32]) {
    uint64_t bits=s->bytes*8u;
    s->block[s->used++]=0x80;
    if (s->used>56) {memset(s->block+s->used,0,64-s->used);sha_block(s,s->block);s->used=0;}
    memset(s->block+s->used,0,56-s->used);
    for (size_t i=0;i<8;++i) s->block[63-i]=(unsigned char)(bits>>(i*8));
    sha_block(s,s->block);
    for (size_t i=0;i<8;++i) for (size_t j=0;j<4;++j)
        digest[i*4+j]=(unsigned char)(s->h[i]>>(24-j*8));
}
