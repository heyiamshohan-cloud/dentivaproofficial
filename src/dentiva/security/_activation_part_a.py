"""First half of the activation verifier material (ADR-0006, REQ-ACT-*).

The offline activation code is **never stored** in this repository. Only a
derived, salted Argon2id verifier is shipped, and it is split across two modules
so that neither file alone is usable and no single grep reveals the scheme.
"""

from __future__ import annotations

#: First half of the application salt, joined with
#: :data:`dentiva.security._activation_part_b.SALT_PART_B` at runtime.
SALT_PART_A = "dentiva-pro-offline-activation-v1"

#: First half of the Argon2id verifier (PHC string).
VERIFIER_PART_A = "$argon2id$v=19$m=65536,t=3,p=2$spB9G2+veYmI//tZ4"
