#define _GNU_SOURCE
#include "linux_controller.h"
#include <inttypes.h>
#include <linux/magic.h>
#include <linux/sched.h>
#include <sched.h>
#include <signal.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>

#define SIZE(T) printf("sizeof." #T "=%zu\n",sizeof(T))
#define ALIGN(T) printf("alignof." #T "=%zu\n",_Alignof(T))
#define OFFSET(T,F) printf("offsetof." #T "." #F "=%zu\n",offsetof(T,F))
#define VALUE(N) printf("constant." #N "=%" PRIu64 "\n",(uint64_t)(N))
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "--sha-vectors")) {
        const char *vectors[] = {"", "abc",
            "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"};
        for (size_t i=0;i<3;++i) {
            struct lc_sha hash; unsigned char digest[32];
            lc_sha_init(&hash);lc_sha_update(&hash,(const unsigned char *)vectors[i],strlen(vectors[i]));
            lc_sha_final(&hash,digest);
            for (size_t j=0;j<32;++j) printf("%02x",(unsigned)digest[j]);
            puts("");
        }
        return 0;
    }
    if (argc != 1) return 2;
    SIZE(struct clone_args); ALIGN(struct clone_args);
    OFFSET(struct clone_args,flags); OFFSET(struct clone_args,pidfd);
    OFFSET(struct clone_args,child_tid); OFFSET(struct clone_args,parent_tid);
    OFFSET(struct clone_args,exit_signal); OFFSET(struct clone_args,stack);
    OFFSET(struct clone_args,stack_size); OFFSET(struct clone_args,tls);
    OFFSET(struct clone_args,set_tid); OFFSET(struct clone_args,set_tid_size);
    OFFSET(struct clone_args,cgroup);
    SIZE(pid_t); SIZE(uid_t); SIZE(gid_t); SIZE(time_t);
    SIZE(struct timespec); ALIGN(struct timespec);
    OFFSET(struct timespec,tv_sec); OFFSET(struct timespec,tv_nsec);
    SIZE(struct timeval); ALIGN(struct timeval);
    OFFSET(struct timeval,tv_sec); OFFSET(struct timeval,tv_usec);
    SIZE(struct rusage); ALIGN(struct rusage);
    OFFSET(struct rusage,ru_utime); OFFSET(struct rusage,ru_stime);
    SIZE(cpu_set_t); SIZE(struct lc_context); SIZE(struct lc_object); SIZE(struct lc_sample);
    VALUE(SYS_clone3); VALUE(SYS_close_range); VALUE(SYS_capget); VALUE(SYS_capset);
    VALUE(CLONE_INTO_CGROUP); VALUE(CLONE_PIDFD); VALUE(SIGCHLD); VALUE(SIGKILL);
    VALUE(CGROUP2_SUPER_MAGIC); VALUE(WNOHANG); VALUE(CLOCK_MONOTONIC);
    return ferror(stdout) ? 3 : 0;
}
