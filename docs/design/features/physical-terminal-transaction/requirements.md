# Caller-owned physical failure retirement

Status: implemented with local SQLite controls; host admission remains separate.
Extends the existing physical publication transaction lane;
it does not admit science, change a migration or remove private files.

PT-01 WHEN a caller-owned WAL transaction retires a failed physical job, THE operation SHALL keep stage and installed-copy custody, retire the intent and reservation atomically, and leave commit or rollback to the caller. Gate: `tests/api/test_physical_debt_transactions.py::test_terminal_visibility_and_copy_charge_belong_to_caller`.

PT-02 IF failure occurs after debt or terminal SQL, THEN the operation SHALL roll back only its own savepoint and preserve unrelated pending caller changes and all original reservations. Gate: `tests/api/test_physical_debt_transactions.py::test_failure_cut_preserves_caller_and_original_liability`.

PT-03 IF transaction, schema, ownership, inventory or SQLite representation is invalid, THEN the operation SHALL refuse without releasing custody. Gate: `tests/api/test_physical_debt_transactions.py::test_invalid_native_boundary_refuses_before_changes` and `tests/api/test_physical_debt_transactions.py::test_foreign_or_unknown_copy_keeps_custody`.

PT-04 THE original isolated entry SHALL retain its WAL and nested-transaction refusals. Gate: `tests/api/test_physical_debt_transactions.py::test_original_entry_does_not_gain_wal_admission` and `tests/api/test_physical_debt.py::test_nested_terminal_transaction_preserves_callers_work`.

PT-05 WHEN the asynchronous worker requests retirement, THE existing closed dispatcher SHALL use the same original connection and transaction. Gate: `tests/api/test_physical_debt_transactions.py::test_async_terminal_uses_original_session_transaction`.
