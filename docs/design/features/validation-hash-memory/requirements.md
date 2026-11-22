# Bounded validation hashing

VM-01 THE file inventory SHALL hash every original byte through one reusable
64KiB buffer while preserving original path/held identity checks and exact
digests. Gate: test_exact_streamed_record_uses_one_bounded_buffer.

VM-02 WHEN hashing allocation fails, THE driver SHALL refuse without retry,
partial inventory or leaked stream; top-level allocation refusal SHALL be a
fixed diagnostic, not a Python traceback. Gates: test_hash_allocation_failure
and test_top_level_allocation_refuses_without_traceback.

This reduces allocation churn; it does not establish the sole cause of the
retained MemoryError, a new memory admission, scientific PASS or deployment.
