#ifndef LBR_BROKER_H
#define LBR_BROKER_H

#include <stddef.h>
#include <stdint.h>
#include <sys/socket.h>

#define LBR_PACKET_BYTES 352u
#define LBR_HASH_DEADLINE_NS UINT64_C(2000000000)

enum lbr_error {
    LBR_OK = 0, LBR_AGAIN = 1, LBR_PROTOCOL = 2, LBR_PEER = 3,
    LBR_UNSEALED = 4, LBR_BOUNDS = 5, LBR_HASH = 6, LBR_CLOCK = 7
};

struct lbr_input {
    unsigned char packet[LBR_PACKET_BYTES];
    int fd[3];
};

/* The enclosing broker owns PIDFD/unit authorization. This is input custody
 * only: exactly one pending packet, no listener, launch or caller-path access. */
int lbr_decode(const unsigned char *, size_t);
int lbr_receive(int, const struct ucred *, struct lbr_input *);
void lbr_dispose(struct lbr_input *);

#endif
