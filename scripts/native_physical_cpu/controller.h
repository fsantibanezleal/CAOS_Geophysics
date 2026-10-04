#ifndef NCC_CONTROLLER_H
#define NCC_CONTROLLER_H

/* I01 supplied-data consistency only. No native execution authority. */
#include <stdint.h>
#include <stddef.h>

#define NCC_STATE_BYTES 1024u
#define NCC_SNAPSHOT_WORDS 22u

#if defined(_WIN32)
#define NCC_API __declspec(dllexport)
#else
#define NCC_API
#endif

NCC_API uint32_t ncc_windows_cpu(uint64_t, uint64_t, uint64_t *);
NCC_API uint32_t ncc_linux_cpu(uint64_t, uint64_t, uint64_t, uint64_t *);
NCC_API uint32_t ncc_delta(uint64_t, uint64_t, uint64_t *);
NCC_API uint32_t ncc_next_sequence(uint64_t, uint64_t);
NCC_API uint32_t ncc_qpc_ns(uint64_t, uint64_t, uint64_t, uint64_t *);
NCC_API uint32_t ncc_time_ns(uint64_t, uint64_t, uint64_t, uint64_t *);
NCC_API uint32_t ncc_parent_cpu(uint32_t, uint64_t, uint64_t, uint64_t);
NCC_API uint32_t ncc_limits(uint32_t, uint64_t *, uint64_t);
NCC_API uint32_t ncc_frame_preflight(const void *, uint64_t, uint32_t *);
NCC_API uint32_t ncc_state_init(void *, uint64_t, const void *, const void *);
NCC_API uint32_t ncc_apply(void *, uint64_t, uint32_t, const void *, uint64_t);
NCC_API uint32_t ncc_account_bytes(void *, uint64_t, uint32_t, uint64_t);
NCC_API uint32_t ncc_queue(void *, uint64_t, uint32_t);
NCC_API uint32_t ncc_snapshot(const void *, uint64_t, uint64_t *, uint64_t);
NCC_API const char *ncc_error_text(uint32_t, uint32_t);

#endif
