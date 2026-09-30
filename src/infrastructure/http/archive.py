"""
ZIP reading — the Assemblée nationale publishes everything as archives.
"""

import io
import zipfile
from collections.abc import Iterator


def iter_zip_members(
    payload: bytes,
    *,
    prefix: str = "",
    suffix: str = ".xml",
    limit: int | None = None,
) -> Iterator[tuple[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        yielded = 0
        for info in archive.infolist():
            if info.is_dir():
                continue
            if prefix and not info.filename.startswith(prefix):
                continue
            if suffix and not info.filename.endswith(suffix):
                continue

            yield info.filename, archive.read(info)

            yielded += 1
            if limit is not None and yielded >= limit:
                return
