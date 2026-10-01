# ADR-0005 — Password hashing: Argon2id via argon2-cffi

- Status: **Accepted** (Phase 1)

## Decision
- `argon2-cffi` (MIT) `PasswordHasher` → **Argon2id**, measured parameters for a
  desktop: `time_cost=3`, `memory_cost=64 MiB`, `parallelism=2` (tuned in Phase 3
  to keep interactive login < 400 ms; measured 78 ms for m=64MiB/t=2 in the
  Phase 1 spike, so 64 MiB/t=3 is safe).
- Unique cryptographically random salt per hash (handled by the library).
- Stored format is the library's PHC string; parameters are stored with the hash so
  they can be raised later; `needs_rehash` triggers silent upgrade on next login.
- Constant-time verification; identical work factor for existing/non-existing users
  (dummy hash verification) to avoid user enumeration timing.

## Rejected
- PBKDF2/bcrypt/scrypt-only: weaker against GPU attacks than Argon2id (memory-hard).
- `hashlib.sha256`-style hashing: unacceptable.

## Consequences
- Login latency budget must account for Argon2id (~100–200 ms).
- Password policy + lockout policy defined in `docs/05`.
