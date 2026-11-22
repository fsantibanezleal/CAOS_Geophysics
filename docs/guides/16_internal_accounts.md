# Internal accounts and public computation

The full scientific application supports multiple accounts and projects. Its
initial owner-tested deployment uses a local SQLite account store rather than
external email services. Public course pages, permitted cases, visualization
and supported browser calculations remain available without signing in.
Server project storage, uploads and worker jobs require authentication.

## Account provisioning

Install the pinned runtime requirements into the repository `.venv`. Configure
the private data/database paths and run the committed Alembic migrations before
starting the API or provisioning an account. Provisioning refuses a missing or
unmigrated database; it does not create an unrelated new database or run a
migration implicitly.

Set `GEOPHYSICS_AUTH_MODE=local` (the default), a private random
`GEOPHYSICS_AUTH_SECRET` of at least 32 characters and the exact
`GEOPHYSICS_PUBLIC_ORIGIN`. Use Secure cookies behind HTTPS. No SMTP environment
variables are required. The account command needs only the declared private
storage/database paths, not the API authentication secret.

```powershell
# Set the private data/database environment from the operator configuration.
.venv/Scripts/python.exe -m alembic -c app/alembic.ini upgrade head
./scripts/provision-account.ps1 -Credentials /private/operator-account.json
# Or omit -Credentials for an identifier and non-echoing password prompt.
```

```bash
.venv/bin/python -m alembic -c app/alembic.ini upgrade head
./scripts/provision-account.sh --credentials /private/operator-account.json
```

The private JSON file has string `username` and `password` fields; it may also
carry operator metadata. It must never be placed in the product repository,
served by the application or committed publicly. Do not pass a password as a
command-line argument. Successful output gives a verdict and account ID only.
Malformed input and database failures do not print credentials or hashes.

Local project-deletion receipts report off-host integration as `not_configured`
and external erasure as `not_attempted`. This is not proof that no external copy
exists. Existing recorded local backup custody still prevents deletion and is
preserved for operator review; the application does not silently erase it.

Provisioning preserves the validated identifier, refuses an existing account
by default, uses the installed auth library's salted Argon2 hash and does not
claim that a mailbox has been verified. Accounts are active but not superusers.
The local test profile permits passwords of 8 to 1024 characters; this is not a
production password policy endorsement. Store a strong unique secret for any
later production use.

## Password rotation without email

Update the private credential file, then explicitly rotate:

```powershell
./scripts/provision-account.ps1 -Credentials /private/operator-account.json -RotatePassword
```

```bash
./scripts/provision-account.sh --credentials /private/operator-account.json --rotate-password
```

Rotation revokes this account's database sessions in the same write transaction
as the hash update. Its identity, projects and other accounts remain intact.
An inactive account cannot be silently reactivated. There is no public local
signup, verification or emailed reset endpoint. Operator administration is
separate from the scientific interface.

## Execution boundaries

Opening a compatible file for a browser tool does not upload it. A local export
downloads the browser's result. Browser computation never silently falls back
to a paid or server worker operation. The explicit server upload/run path
requires an authenticated session, same-origin CSRF and project ownership.
Server job limits concern actual worker memory, CPU, scratch, wall time and
stored bytes, not the scientific computation on a visitor's own device.

Client methods require parity with their canonical scientific implementation
and real browser failure/resource tests. [ONNX Runtime Web](https://onnxruntime.ai/docs/tutorials/web/)
executes exported neural inference, not arbitrary Python inversion engines.
Python-only/full local GPU methods retain complete reproducible pipelines and
honest execution-lane labels. This access model does not reduce method coverage
or substitute a prepared result for a submitted-data calculation.

The explicit `email` profile remains available for historical regression
coverage and requires its configured mail sender. It is not the current test
deployment and is never selected as an automatic fallback.

## Tests and source contracts

`tests/api/test_local_auth.py` exercises real migrated SQLite, library cookie
login, absent local mail/signup routes, exact identifiers, salted hashes,
rotation/session revocation, concurrent provisioning, multiple projects/users,
anonymous/foreign-owner rejection, CSRF and secret-safe CLI failures. The legacy
email suite uses an explicit email profile; it cannot accidentally assert that
email verification is required for local accounts.

The library's [password hashing](https://fastapi-users.github.io/fastapi-users/latest/configuration/password-hash/)
and [optional auth-router verification](https://fastapi-users.github.io/fastapi-users/latest/configuration/routers/auth/)
contracts are the implementation basis. Account identifiers are login names,
not proof of email delivery. No credentials are embedded in this guide.
