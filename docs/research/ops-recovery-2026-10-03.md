# Official operations primary sources, 2026-10-03

Scope: SQLite, age and systemd only. Read before implementation. These sources establish API and command semantics; none establishes that a host drill occurred.

| Primary source | Verified fact and resulting design |
| --- | --- |
| [SQLite backup API](https://www.sqlite.org/backup.html) | SQLite can copy a consistent database while clients continue to write. This is not a transaction over external asset files; require all writers stopped for the entire capture. |
| [SQLite WAL](https://www.sqlite.org/wal.html) | The WAL is part of persistent database state. Refuse nonempty sidecars; after stopping every writer an operator must close/checkpoint through the supported SQLite interface before capture. Do not unlink WAL. |
| [SQLite pragmas](https://www.sqlite.org/pragma.html) | Integrity checking does not replace foreign-key checking; run both, validate the schema adapter and exact file receipts. |
| [SQLite VACUUM](https://www.sqlite.org/lang_vacuum.html) | VACUUM rebuilds the new database and removes deleted content from unused pages. Apply only to the newly restored copy after deleting tombstoned project rows. |
| [age maintained upstream](https://github.com/FiloSottile/age) and [v1.3.1 release](https://github.com/FiloSottile/age/releases/tag/v1.3.1) | Native recipient/identity files and executable encryption/decryption avoid product-owned crypto. Local installed executable reports v1.3.1. Version is captured and minimum checked, executable integrity remains the operator's supply-chain responsibility. |
| [age official command manual, pinned v1.3.1](https://github.com/FiloSottile/age/blob/v1.3.1/doc/age.1) | Use recipient encryption and identity-file decryption without plugins or interactive passwords. Do not expose decrypted material or identity content in logs. |
| [systemd official systemctl source](https://github.com/systemd/systemd/blob/main/man/systemctl.xml) | Masking prevents activation; stopping alone can leave activation paths. Read machine properties with show; require inactive/dead service and masked units. Freedesktop rendered manual was inaccessible here (403), so its official upstream source is used. |
| [systemd official kill source](https://github.com/systemd/systemd/blob/main/man/systemd.kill.xml) | Stop semantics depend on KillMode; require the actual service cgroup empty, and operator accounting for manually launched writers. MainPID zero alone is insufficient. |

Security inference: authenticated ciphertext is not a freshness oracle. Maintain the latest authority ciphertext hash and observation watermark independently of rollback-prone snapshots. A source loss before external replication of a deletion cannot be repaired by a backup utility alone. This is an explicit deployment gate.
