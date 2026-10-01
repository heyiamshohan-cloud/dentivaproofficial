"""Security primitives: credentials, local secrets, activation and sessions.

No module outside this package handles a password, a token or a key.
"""

from __future__ import annotations

__all__ = ["activation", "password", "secrets", "session"]
