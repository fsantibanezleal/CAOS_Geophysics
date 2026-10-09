#define _GNU_SOURCE
/* Finite authored OS qualification only. Never linked into the controller. */
#include "linux_controller.h"
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <linux/sched.h>
#include <sched.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static uint64_t ns(clockid_t clock) {
    struct timespec t;
    if (clock_gettime(clock,&t) || t.tv_sec<0 || t.tv_nsec<0 || t.tv_nsec>=1000000000) _exit(100);
    return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec;
}
static void burn(uint64_t duration) {
    uint64_t start=ns(CLOCK_THREAD_CPUTIME_ID);
    volatile uint64_t x=1;
    while (ns(CLOCK_THREAD_CPUTIME_ID)-start<duration)
        for (unsigned i=0;i<1000;++i) x=x*UINT64_C(6364136223846793005)+1;
}
static int system_cpu(void) {
    uint64_t start=ns(CLOCK_THREAD_CPUTIME_ID);
    while (ns(CLOCK_THREAD_CPUTIME_ID)-start<UINT64_C(200000000)) {
        /* Real kernel transitions. No input/fixture supplied CPU counter. */
        for (unsigned i=0;i<1000;++i) if (syscall(SYS_gettid)<=0) return 110;
    }
    return 0;
}
static int marker(void) {
    char group[256],status[4096];
    int fd=open("/proc/self/cgroup",O_RDONLY|O_CLOEXEC);
    if (fd<0) return 101;
    ssize_t n=read(fd,group,sizeof(group)-1);close(fd);
    if (n<=0 || (size_t)n>=sizeof(group)-1) return 101;
    group[n]='\0';
    if (!strstr(group,"/science\n") || getuid()==0 || geteuid()==0 || getgid()==0) return 101;
    fd=open("/proc/self/status",O_RDONLY|O_CLOEXEC);
    if (fd<0) return 101;
    n=read(fd,status,sizeof(status)-1);close(fd);
    if (n<=0 || (size_t)n>=sizeof(status)-1) return 101;
    status[n]='\0';
    const char *caps[]={"CapInh:\t0000000000000000\n","CapPrm:\t0000000000000000\n",
        "CapEff:\t0000000000000000\n","CapBnd:\t0000000000000000\n",
        "CapAmb:\t0000000000000000\n","NoNewPrivs:\t1\n"};
    for (size_t i=0;i<sizeof(caps)/sizeof(caps[0]);++i) if (!strstr(status,caps[i])) return 101;
    if (getgroups(0,NULL)!=0) return 101;
    fd=open("birth.marker",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    if (fd<0) return 102;
    int result=dprintf(fd,"uid=%u\ngid=%u\ngroups=0\ncaps=0\nno_new_privs=1\n%s",
        (unsigned)getuid(),(unsigned)getgid(),group);
    if (result<0 || fsync(fd) || close(fd)) return 102;
    return 0;
}
static void *thread_load(void *unused) { (void)unused;burn(UINT64_C(20000000));return NULL; }
static int exited(void) {
    pid_t children[16];
    for (size_t i=0;i<16;++i) {
        children[i]=fork();
        if (children[i]<0) return 103;
        if (children[i]==0) {burn(UINT64_C(10000000));_exit(0);}
    }
    burn(UINT64_C(20000000));
    for (size_t i=0;i<16;++i) {
        int status;pid_t result;
        do {result=waitpid(children[i],&status,0);} while (result<0 && errno==EINTR);
        if (result!=children[i] || !WIFEXITED(status) || WEXITSTATUS(status)) return 103;
    }
    return 0;
}
static int grandchild(void) {
    int ready[2];
    if (pipe2(ready,O_CLOEXEC)) return 104;
    pid_t intermediate=fork();
    if (intermediate<0) return 104;
    if (intermediate==0) {
        pid_t descendant=fork();
        if (descendant<0) _exit(104);
        if (descendant==0) {
            close(ready[0]);
            if (write(ready[1],"R",1)!=1) _exit(104);
            close(ready[1]);burn(UINT64_C(100000000000));_exit(0);
        }
        _exit(0);
    }
    close(ready[1]);char byte;ssize_t got;
    do {got=read(ready[0],&byte,1);} while (got<0 && errno==EINTR);
    close(ready[0]);
    int status;
    if (got!=1 || byte!='R' || waitpid(intermediate,&status,0)!=intermediate ||
        !WIFEXITED(status) || WEXITSTATUS(status)) return 104;
    return 0; /* Deliberately leave an accounted reparented grandchild alive. */
}
static int escape(void) {
    char group[256],path[512];
    int fd=open("/proc/self/cgroup",O_RDONLY|O_CLOEXEC);
    if (fd<0) return 105;
    ssize_t n=read(fd,group,sizeof(group)-1);close(fd);
    if (n<=0) return 105;
    group[n]='\0';char *end=strchr(group,'\n');if (!end) return 105;*end='\0';
    static const char prefix[]="0::/system.slice/geophysics-cpu-qual-";
    if (strncmp(group,prefix,sizeof(prefix)-1)) return 105;
    int length=snprintf(path,sizeof(path),"/sys/fs/cgroup%s/cgroup.procs",group+3);
    if (length<0 || (size_t)length>=sizeof(path)) return 105;
    fd=open(path,O_WRONLY|O_CLOEXEC|O_NOFOLLOW);
    if (fd>=0) {close(fd);return 105;}
    if (errno!=EACCES && errno!=EPERM && errno!=EROFS) return 105;
    if (unshare(CLONE_NEWUSER)!=-1 || errno!=EPERM) return 105;
    struct clone_args args={0};
    if (syscall(SYS_clone3,&args,sizeof(args))!=-1 || errno!=ENOSYS) return 105;
    if (kill(getppid(),0)!=-1 || errno!=EPERM) return 105;
    if (ptrace(PTRACE_ATTACH,getppid(),NULL,NULL)!=-1 || errno!=EPERM) return 105;
    fd=open("escape.denied",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600);
    if (fd<0 || write(fd,"own_cgroup_write_denied\n",24)!=24 || fsync(fd) || close(fd)) return 105;
    return 0;
}
int main(int argc,char **argv) {
    if (argc!=2) return 99;
    if (!strcmp(argv[1],"--parent")) {sleep(600);return 0;}
    if (!strcmp(argv[1],"--parse-context") || !strcmp(argv[1],"--parse-counter")) {
        unsigned char bytes[LC_CONTEXT_BYTES+1];size_t count=0;
        while (count<sizeof(bytes)) {
            ssize_t n=read(0,bytes+count,sizeof(bytes)-count);
            if (n<0) {if (errno==EINTR) continue;return 109;}
            if (!n) break;
            count+=(size_t)n;
        }
        if (!strcmp(argv[1],"--parse-context")) {
            struct lc_context context;
            return lc_parse_context(bytes,count,&context);
        }
        struct lc_sample sample={0};
        int code=lc_parse_cpu(bytes,count,&sample);
        if (!code) printf("%" PRIu64 "\n",sample.cpu_ns);
        return code;
    }
    int result=marker();if (result) return result;
    if (!strcmp(argv[1],"--system-cpu")) return system_cpu();
    if (!strcmp(argv[1],"--nominal")) {burn(UINT64_C(50000000));return 0;}
    if (!strcmp(argv[1],"--exited")) return exited();
    if (!strcmp(argv[1],"--grandchild")) return grandchild();
    if (!strcmp(argv[1],"--escape")) return escape();
    if (!strcmp(argv[1],"--threads")) {
        pthread_t threads[4];
        for (size_t i=0;i<4;++i) if (pthread_create(&threads[i],NULL,thread_load,NULL)) return 106;
        for (size_t i=0;i<4;++i) if (pthread_join(threads[i],NULL)) return 106;
        return 0;
    }
    if (!strcmp(argv[1],"--upper") || !strcmp(argv[1],"--cancel")) {
        burn(UINT64_C(250000000000));return 0;
    }
    if (!strcmp(argv[1],"--output")) {
        char block[4096];memset(block,'x',sizeof(block));
        for (size_t i=0;i<17;++i) if (write(1,block,sizeof(block))!=(ssize_t)sizeof(block)) return 107;
        return 0;
    }
    if (!strcmp(argv[1],"--oom")) {
        size_t size=900u*1024u*1024u;
        unsigned char *p=mmap(NULL,size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
        if (p==MAP_FAILED) return 108;
        for (size_t i=0;i<size;i+=4096) p[i]=(unsigned char)i;
        if (munmap(p,size)) return 108;
        return 108; /* Completing allocation would contradict class1's memcg cap. */
    }
    return 99;
}
