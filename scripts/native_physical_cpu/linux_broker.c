#define _GNU_SOURCE
#include "linux_broker.h"
#include "linux_controller.h"
#include <errno.h>
#include <fcntl.h>
#include <linux/magic.h>
#include <poll.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/vfs.h>
#include <unistd.h>

#ifndef SO_PEERPIDFD
#error "Linux SO_PEERPIDFD headers are required; no numeric-PID fallback"
#endif

static int nonnil(const unsigned char *p, size_t n) {
    unsigned char bits = 0;
    for (size_t i = 0; i < n; ++i) bits |= p[i];
    return bits != 0;
}

int lbr_decode(const unsigned char *p, size_t n) {
    static const size_t ids[] = {24, 40, 56, 72, 88, 288, 304, 320};
    static const size_t sizes[] = {200, 240, 280};
    static const uint64_t caps[] = {UINT64_C(5242880), UINT64_C(65536), UINT64_C(16384)};
    if (!p || n != LBR_PACKET_BYTES || memcmp(p, "LBR1", 4) ||
        lc_u16(p+4) != 1 || lc_u16(p+6) != 1 || lc_u32(p+8) != LBR_PACKET_BYTES ||
        lc_u32(p+12) || lc_u64(p+16) != 1 || nonnil(p+336, 16)) return LBR_PROTOCOL;
    for (size_t i = 0; i < sizeof(ids)/sizeof(ids[0]); ++i)
        if (!nonnil(p+ids[i], 16)) return LBR_PROTOCOL;
    for (size_t i = 0; i < 3; ++i) {
        uint64_t bytes = lc_u64(p+sizes[i]);
        if (!bytes || bytes > caps[i]) return LBR_BOUNDS;
    }
    return LBR_OK;
}

void lbr_dispose(struct lbr_input *in) {
    if (!in) return;
    for (size_t i = 0; i < 3; ++i) {
        if (in->fd[i] >= 0) close(in->fd[i]);
        in->fd[i] = -1;
    }
    memset(in->packet, 0, sizeof(in->packet));
}

void lbr_peer_dispose(struct lbr_peer *peer) {
    if (!peer) return;
    if (peer->pidfd >= 0) close(peer->pidfd);
    memset(&peer->credentials, 0, sizeof(peer->credentials));
    peer->pidfd = -1;
}

int lbr_peer_live(const struct lbr_peer *peer) {
    if (!peer || peer->pidfd < 0 || peer->credentials.pid <= 0) return LBR_PEER;
    struct pollfd handle = {.fd=peer->pidfd, .events=POLLIN};
    int ready = poll(&handle, 1, 0);
    return ready == 0 && !handle.revents ? LBR_OK : LBR_PEER;
}

int lbr_peer_open(int socket_fd, struct lbr_peer *out) {
    struct lbr_peer peer = {.pidfd=-1};
    int domain = 0, type = 0;
    socklen_t length = sizeof(domain);
    if (!out || out->pidfd != -1 || out->credentials.pid ||
        out->credentials.uid || out->credentials.gid) return LBR_PROTOCOL;
    if (getsockopt(socket_fd, SOL_SOCKET, SO_DOMAIN, &domain, &length) ||
        length != sizeof(domain) || domain != AF_UNIX) return LBR_PROTOCOL;
    length = sizeof(type);
    if (getsockopt(socket_fd, SOL_SOCKET, SO_TYPE, &type, &length) ||
        length != sizeof(type) || type != SOCK_SEQPACKET) return LBR_PROTOCOL;
    length = sizeof(peer.credentials);
    if (getsockopt(socket_fd, SOL_SOCKET, SO_PEERCRED, &peer.credentials, &length) ||
        length != sizeof(peer.credentials) || peer.credentials.pid <= 0) return LBR_PEER;
    length = sizeof(peer.pidfd);
    if (getsockopt(socket_fd, SOL_SOCKET, SO_PEERPIDFD, &peer.pidfd, &length)) {
        return errno == ENOPROTOOPT || errno == EINVAL || errno == ENOSYS ? LBR_KERNEL : LBR_PEER;
    }
    int flags = peer.pidfd >= 0 ? fcntl(peer.pidfd, F_GETFD) : -1;
    if (length != sizeof(peer.pidfd) || flags < 0 ||
        fcntl(peer.pidfd, F_SETFD, flags | FD_CLOEXEC) || lbr_peer_live(&peer)) {
        lbr_peer_dispose(&peer);
        return LBR_PEER;
    }
    *out = peer;
    return LBR_OK;
}

static int sealed(int fd, uint64_t bytes) {
    struct stat st;
    struct statfs fs;
    int seals = F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL;
    int actual = fcntl(fd, F_GET_SEALS);
    int access = fcntl(fd, F_GETFL);
    int flags = fcntl(fd, F_GETFD);
    if (actual < 0 || access < 0 || flags < 0 || fstat(fd, &st) || fstatfs(fd, &fs) ||
        !S_ISREG(st.st_mode) || fs.f_type != TMPFS_MAGIC || (actual & seals) != seals ||
        (access & O_ACCMODE) != O_RDONLY || !(flags & FD_CLOEXEC)) return LBR_UNSEALED;
    if (st.st_size < 0 || (uint64_t)st.st_size != bytes) return LBR_BOUNDS;
    return LBR_OK;
}

static int hashed(int fd, uint64_t bytes, const unsigned char *expected, uint64_t start) {
    unsigned char buffer[65536], hash[32];
    uint64_t position = 0, now = 0;
    struct lc_sha state;
    lc_sha_init(&state);
    while (position < bytes) {
        if (lc_clock(&now) || now < start) return LBR_CLOCK;
        if (now-start > LBR_HASH_DEADLINE_NS) return LBR_BOUNDS;
        uint64_t remaining = bytes-position;
        size_t count = remaining < sizeof(buffer) ? (size_t)remaining : sizeof(buffer);
        ssize_t got = pread(fd, buffer, count, (off_t)position);
        if (got <= 0 || (size_t)got > count) return LBR_BOUNDS;
        lc_sha_update(&state, buffer, (size_t)got);
        position += (uint64_t)got;
    }
    if (lc_clock(&now) || now < start) return LBR_CLOCK;
    if (now-start > LBR_HASH_DEADLINE_NS) return LBR_BOUNDS;
    lc_sha_final(&state, hash);
    return memcmp(hash, expected, sizeof(hash)) ? LBR_HASH : LBR_OK;
}

int lbr_receive(int socket_fd, const struct ucred *expected, struct lbr_input *out) {
    struct lbr_input in = {.fd = {-1, -1, -1}};
    union {
        struct cmsghdr alignment;
        unsigned char bytes[CMSG_SPACE(3*sizeof(int))+CMSG_SPACE(sizeof(struct ucred))];
    } ancillary;
    struct iovec data = {.iov_base = in.packet, .iov_len = sizeof(in.packet)};
    struct msghdr message = {.msg_iov = &data, .msg_iovlen = 1,
        .msg_control = ancillary.bytes, .msg_controllen = sizeof(ancillary.bytes)};
    struct ucred sender = {0};
    unsigned rights = 0, credentials = 0, received = 0;
    int error = LBR_OK;
    uint64_t start = 0;
    if (!expected || !out || expected->pid <= 0) return LBR_PEER;
    if (out->fd[0] != -1 || out->fd[1] != -1 || out->fd[2] != -1 ||
        nonnil(out->packet, sizeof(out->packet))) return LBR_PROTOCOL;
    memset(ancillary.bytes, 0, sizeof(ancillary.bytes));
    /* Nonblocking prevents an absent or stalled packet from entering the
     * controller timer path. The enclosing loop owns handshake deadlines. */
    ssize_t bytes = recvmsg(socket_fd, &message, MSG_DONTWAIT | MSG_CMSG_CLOEXEC);
    if (bytes < 0) return errno == EAGAIN || errno == EWOULDBLOCK ? LBR_AGAIN : LBR_PROTOCOL;
    for (struct cmsghdr *c = CMSG_FIRSTHDR(&message); c; c = CMSG_NXTHDR(&message, c)) {
        size_t remaining = (size_t)((unsigned char *)message.msg_control+
            message.msg_controllen-(unsigned char *)c);
        if (c->cmsg_len < CMSG_LEN(0) || c->cmsg_len > remaining) {
            error = LBR_PROTOCOL; break;
        }
        size_t payload = c->cmsg_len-CMSG_LEN(0);
        if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_RIGHTS) {
            ++rights;
            if (payload % sizeof(int)) error = LBR_PROTOCOL;
            for (size_t i = 0; i < payload/sizeof(int); ++i) {
                int fd;
                memcpy(&fd, CMSG_DATA(c)+i*sizeof(int), sizeof(fd));
                if (received < 3) in.fd[received] = fd;
                else { close(fd); error = LBR_PROTOCOL; }
                ++received;
            }
        } else if (c->cmsg_level == SOL_SOCKET && c->cmsg_type == SCM_CREDENTIALS) {
            ++credentials;
            if (payload == sizeof(sender)) memcpy(&sender, CMSG_DATA(c), sizeof(sender));
            else error = LBR_PROTOCOL;
        } else error = LBR_PROTOCOL;
    }
    if ((message.msg_flags & (MSG_TRUNC | MSG_CTRUNC)) || bytes != LBR_PACKET_BYTES ||
        rights != 1 || credentials != 1 || received != 3) error = LBR_PROTOCOL;
    if (!error && (sender.pid != expected->pid || sender.uid != expected->uid ||
                   sender.gid != expected->gid)) error = LBR_PEER;
    if (!error) error = lbr_decode(in.packet, sizeof(in.packet));
    static const size_t sizes[] = {200, 240, 280}, hashes[] = {168, 208, 248};
    for (size_t i = 0; !error && i < 3; ++i)
        error = sealed(in.fd[i], lc_u64(in.packet+sizes[i]));
    if (!error && lc_clock(&start)) error = LBR_CLOCK;
    for (size_t i = 0; !error && i < 3; ++i)
        error = hashed(in.fd[i], lc_u64(in.packet+sizes[i]), in.packet+hashes[i], start);
    if (error) { lbr_dispose(&in); return error; }
    *out = in;
    return LBR_OK;
}

int lbr_receive_peer(int socket_fd, const struct lbr_peer *peer, struct lbr_input *out) {
    if (lbr_peer_live(peer)) return LBR_PEER;
    int result = lbr_receive(socket_fd, &peer->credentials, out);
    if (!result && lbr_peer_live(peer)) {
        lbr_dispose(out);
        return LBR_PEER;
    }
    return result;
}
