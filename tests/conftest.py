from __future__ import annotations

import shutil
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _media_root(settings, tmp_path):
    media_root = Path(tmp_path) / "media"
    media_root.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = media_root
    yield
    shutil.rmtree(media_root, ignore_errors=True)
