"""Download the original sources into data/raw and record their provenance.

Usage: python -m src.download

Raw files are written once and never modified. A file already present keeps its
bytes; its checksum is recomputed and compared with the manifest.
"""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from datetime import date
from pathlib import Path

import requests

from src import config

CHUNK = 1 << 20
HEADERS = {"User-Agent": "Mozilla/5.0 (merida-urban-intelligence)"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    with requests.get(url, headers=HEADERS, stream=True, timeout=120) as response:
        response.raise_for_status()
        with partial.open("wb") as fh:
            for block in response.iter_content(CHUNK):
                fh.write(block)
    partial.replace(target)


def load_manifest() -> dict:
    if config.SOURCE_MANIFEST.exists():
        return json.loads(config.SOURCE_MANIFEST.read_text(encoding="utf-8"))
    return {}


def main() -> int:
    manifest = load_manifest()
    status = 0
    for key, source in config.SOURCES.items():
        folder = config.DATA_RAW / key
        archive = folder / source["url"].rsplit("/", 1)[-1]
        previous = manifest.get(key, {})

        if archive.exists():
            checksum = sha256(archive)
            if previous.get("sha256") and previous["sha256"] != checksum:
                print(f"[{key}] CHECKSUM MISMATCH: raw file differs from the manifest")
                status = 1
                continue
            print(f"[{key}] already present, checksum verified")
            downloaded = previous.get("download_date", date.today().isoformat())
        elif source.get("manual"):
            print(f"[{key}] not found. Open {source['url']} in a web browser and save the file "
                  f"as {archive.relative_to(config.ROOT)}; then run this step again.")
            continue
        else:
            print(f"[{key}] downloading {source['url']}")
            fetch(source["url"], archive)
            checksum = sha256(archive)
            downloaded = date.today().isoformat()

        extracted = folder / "extracted"
        if archive.suffix == ".zip" and not extracted.exists():
            with zipfile.ZipFile(archive) as zf:
                zf.extractall(extracted)

        manifest[key] = {
            "name": source["name"],
            "provider": source["provider"],
            "edition": source["edition"],
            "url": source["url"],
            "original_grain": source["original_grain"],
            "file_name": archive.name,
            "size_bytes": archive.stat().st_size,
            "sha256": checksum,
            "download_date": downloaded,
        }

    config.SOURCE_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    config.SOURCE_MANIFEST.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"manifest written to {config.SOURCE_MANIFEST.relative_to(config.ROOT)}")
    return status


if __name__ == "__main__":
    sys.exit(main())
