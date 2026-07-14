"""都道府県ごとの GeoJSON zip をダウンロードし、展開する。"""
from __future__ import annotations

import hashlib
import time
import zipfile
from pathlib import Path
from typing import Iterable, Optional

import requests

from . import config


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(source: dict, zip_dir: Path, *, retries: int = 4, timeout: int = 120) -> dict:
    """1 県分の zip を取得。manifest エントリ（サイズ・sha256・Last-Modified）を返す。"""
    zip_dir.mkdir(parents=True, exist_ok=True)
    out = zip_dir / f"{source['content_id']}.zip"
    headers = {"User-Agent": config.USER_AGENT}
    last_exc: Optional[Exception] = None
    last_modified = None
    for attempt in range(retries):
        try:
            with requests.get(source["url"], headers=headers, timeout=timeout, stream=True) as resp:
                resp.raise_for_status()
                last_modified = resp.headers.get("Last-Modified")
                with out.open("wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            time.sleep(2 * (attempt + 1))
    else:
        raise RuntimeError(f"DL失敗: {source['pref']} {source['url']}: {last_exc}")
    return {
        "pref": source["pref"],
        "url": source["url"],
        "content_id": source["content_id"],
        "note": source.get("note"),
        "modified": source.get("modified"),
        "bytes": out.stat().st_size,
        "sha256": _sha256(out),
        "last_modified": last_modified,
        "zip_path": str(out),
    }


def _fix_name(info: zipfile.ZipInfo) -> str:
    """UTF-8 フラグが立っていない zip の日本語ファイル名（cp932）を復元。"""
    if info.flag_bits & 0x800:
        return info.filename
    try:
        return info.filename.encode("cp437").decode("cp932")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return info.filename


def extract_one(zip_path: Path, extract_dir: Path) -> int:
    """zip を extract_dir に展開。展開した .geojson の数を返す。"""
    extract_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            name = _fix_name(info)
            target = extract_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                dst.write(src.read())
            if name.lower().endswith(".geojson"):
                count += 1
    return count


def download_all(
    sources: list[dict],
    *,
    prefs: Optional[Iterable[str]] = None,
    zip_dir: Optional[Path] = None,
    extract_dir: Optional[Path] = None,
    sleep: float = 1.0,
) -> list[dict]:
    """全県（または prefs 指定分）を取得・展開し、manifest エントリのリストを返す。"""
    zip_dir = zip_dir or config.ZIP_DIR
    extract_dir = extract_dir or config.EXTRACT_DIR
    wanted = set(prefs) if prefs else None
    entries: list[dict] = []
    targets = [s for s in sources if (wanted is None or s["pref"] in wanted)]
    for i, src in enumerate(targets, 1):
        print(f"[{i}/{len(targets)}] {src['pref']} を取得中 …", flush=True)
        entry = download_one(src, zip_dir)
        n = extract_one(Path(entry["zip_path"]), extract_dir)
        entry["geojson_files"] = n
        entries.append(entry)
        print(f"    {entry['bytes']:,} bytes / geojson {n} 件 / sha256 {entry['sha256'][:12]}")
        if sleep and i < len(targets):
            time.sleep(sleep)
    return entries
