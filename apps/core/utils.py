from __future__ import annotations

import secrets
from pathlib import Path
from uuid import uuid4


def build_upload_path(prefix: str, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"{prefix}/{uuid4().hex}{extension}"


def generate_public_token(length: int = 24) -> str:
    token = secrets.token_urlsafe(length)
    return token[:length]
