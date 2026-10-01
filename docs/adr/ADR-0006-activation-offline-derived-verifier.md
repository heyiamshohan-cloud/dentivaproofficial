# ADR-0006 — Offline activation: derived-key verifier with obfuscated constants

- Status: **Accepted** (Phase 1)

## Context
A one-time activation code (`1516591935015165`) must gate the product, work fully
offline, and must **not** appear as a readable string in the source. A local fixed
code can never be made extraction-proof: the verifier and its secret run on the
attacker's machine. The goal is honest, sensible offline tamper resistance and
secure representation — not impossible-to-break DRM.

## Decision
1. The literal code is **never** stored. The accepted value is a
   **derived verifier**: `V = Argon2id(code, salt=S_app, m=64MiB, t=3, p=2)` where
   `S_app` is a compile-time constant assembled at runtime from several split,
   XOR-masked fragments held in different modules.
2. `V` itself is stored split across ≥3 obfuscated fragments recombined at runtime;
   comparison uses `hmac.compare_digest` (constant time).
3. On success the app stores an **activation record**:
   `token = HMAC-SHA256(machine_id || app_instance_salt, V)` written to the data
   directory *and* the database, plus activation timestamp, app version and code
   fingerprint. Startup requires a valid, self-consistent record.
4. No hardware lock-in: re-activation is always possible with the code (avoids
   false lockouts after hardware change), and reinstallation on new hardware simply
   asks for the code again.
5. **Optional hardening (Phase 17):** compile the activation module to a native
   extension with Cython (Apache-2.0) if the Windows CI toolchain builds it
   reliably; if it does not, ship the obfuscated pure-Python path and document the
   residual risk truthfully.

## Rejected
- Plain string comparison / base64 of the code — explicitly forbidden.
- Online/licence-server activation — explicitly forbidden (must work offline).
- Third-party licence/DRM SDK — paid/online dependencies are forbidden.

## Honest threat model (to be reproduced in user-facing docs)
A determined attacker with full control of the machine and reverse-engineering
skill can ultimately bypass any purely local check. This design removes casual
inspection of source/binaries and raises the effort required; it is not a
cryptographic guarantee.
