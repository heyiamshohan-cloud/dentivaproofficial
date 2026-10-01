"""Second half of the activation verifier material (ADR-0006, REQ-ACT-*).

See :mod:`dentiva.security._activation_part_a`; the two halves are joined at
runtime and never exist together anywhere else in the source tree.
"""

from __future__ import annotations

#: Second half of the application salt.
SALT_PART_B = "::868ffccb88ef56e148a58d589da66699"

#: Second half of the Argon2id verifier (PHC string).
VERIFIER_PART_B = "w5G7g$Z03PUsbtJ4RM6spR3mq4gsUgwHnKDS3SrhhQutvG9ow"
