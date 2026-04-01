from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib.staticfiles.storage import StaticFilesStorage
from django.core.files.storage import FileSystemStorage
from storages.backends.s3 import S3Storage


class LocalMediaStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", settings.MEDIA_ROOT)
        kwargs.setdefault("base_url", settings.MEDIA_URL)
        super().__init__(*args, **kwargs)


class LocalStaticStorage(StaticFilesStorage):
    pass


class PrivateMediaS3Storage(S3Storage):
    default_acl = "private"
    file_overwrite = False
    querystring_auth = True


def build_s3_storage_options(env) -> dict[str, Any]:
    return {
        "access_key": env("AWS_ACCESS_KEY_ID", default=""),
        "secret_key": env("AWS_SECRET_ACCESS_KEY", default=""),
        "bucket_name": env("AWS_STORAGE_BUCKET_NAME", default=""),
        "region_name": env("AWS_S3_REGION_NAME", default=""),
        "endpoint_url": env("AWS_S3_ENDPOINT_URL", default=""),
        "custom_domain": env("AWS_S3_CUSTOM_DOMAIN", default=""),
        "default_acl": env("AWS_DEFAULT_ACL", default="private"),
        "querystring_auth": env.bool("AWS_QUERYSTRING_AUTH", default=True),
        "file_overwrite": env.bool("AWS_FILE_OVERWRITE", default=False),
        "location": env("AWS_MEDIA_LOCATION", default="media"),
    }


def build_storage_settings(env) -> dict[str, dict[str, Any]]:
    storage_config: dict[str, dict[str, Any]] = {
        "default": {
            "BACKEND": "apps.core.storage.LocalMediaStorage",
        },
        "staticfiles": {
            "BACKEND": "apps.core.storage.LocalStaticStorage",
        },
    }

    if env.bool("USE_S3_STORAGE", default=False):
        storage_config["default"] = {
            "BACKEND": "apps.core.storage.PrivateMediaS3Storage",
            "OPTIONS": build_s3_storage_options(env),
        }

    return storage_config
