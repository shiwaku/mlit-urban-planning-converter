"""都道府県ごとの GeoJSON zip をダウンロードし、展開する。

差分更新: zip のファイル名は提供元の content_id（内容が更新されるたびに変わる）。
同じ content_id の zip が手元にあり展開済みなら、その県は取得も展開もスキップする。
CI では raw/zip をキャッシュしておけば、変更のあった県だけダウンロードされる。
"""
from __future__ import annotations

import hashlib
import json
import shutil
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
    """zip を extract_dir に展開。展開した .geojson の数を返す。

    再展開時に旧版の残骸（廃止された市区町村ファイル等）が混ざらないよう、
    zip 内のトップレベルディレクトリを先に削除してから展開する。
    """
    extract_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zip_path) as zf:
        tops = {_fix_name(i).split("/", 1)[0] for i in zf.infolist() if not i.is_dir()}
        for top in tops:
            target = extract_dir / top
            if top and target.is_dir():
                shutil.rmtree(target)
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


def _marker_path(extract_dir: Path, content_id: str) -> Path:
    """展開済みマーカー（content_id 単位）。"""
    return extract_dir / ".extracted" / f"{content_id}.json"


def _write_marker(extract_dir: Path, content_id: str, geojson_files: int) -> None:
    m = _marker_path(extract_dir, content_id)
    m.parent.mkdir(parents=True, exist_ok=True)
    m.write_text(json.dumps({"geojson_files": geojson_files}), encoding="utf-8")


def _read_marker(extract_dir: Path, content_id: str) -> Optional[dict]:
    m = _marker_path(extract_dir, content_id)
    if not m.exists():
        return None
    try:
        return json.loads(m.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _entry_from_cached(source: dict, zip_path: Path, geojson_files: int) -> dict:
    """既存 zip から manifest エントリを作る（ダウンロードスキップ時）。"""
    return {
        "pref": source["pref"],
        "url": source["url"],
        "content_id": source["content_id"],
        "note": source.get("note"),
        "modified": source.get("modified"),
        "bytes": zip_path.stat().st_size,
        "sha256": _sha256(zip_path),
        "last_modified": None,
        "zip_path": str(zip_path),
        "cached": True,
        "geojson_files": geojson_files,
    }


def cleanup_stale_zips(sources: list[dict], zip_dir: Optional[Path] = None) -> int:
    """現行 sources に無い content_id の zip（旧版）を削除。消した数を返す。"""
    zip_dir = zip_dir or config.ZIP_DIR
    keep = {s["content_id"] for s in sources}
    removed = 0
    for z in zip_dir.glob("*.zip"):
        if z.stem not in keep:
            z.unlink()
            removed += 1
    return removed


def download_all(
    sources: list[dict],
    *,
    prefs: Optional[Iterable[str]] = None,
    zip_dir: Optional[Path] = None,
    extract_dir: Optional[Path] = None,
    sleep: float = 1.0,
    force: bool = False,
) -> list[dict]:
    """全県（または prefs 指定分）を取得・展開し、manifest エントリのリストを返す。

    差分更新: 同じ content_id の zip が既にあれば取得をスキップ（force で無効化）。
    zip はあるが未展開（CI で raw/zip だけキャッシュ復元された場合）は展開のみ行う。
    """
    zip_dir = zip_dir or config.ZIP_DIR
    extract_dir = extract_dir or config.EXTRACT_DIR
    wanted = set(prefs) if prefs else None
    entries: list[dict] = []
    targets = [s for s in sources if (wanted is None or s["pref"] in wanted)]
    n_skip = n_extract_only = n_download = 0
    for i, src in enumerate(targets, 1):
        zip_path = zip_dir / f"{src['content_id']}.zip"
        marker = None if force else _read_marker(extract_dir, src["content_id"])
        if not force and zip_path.exists() and zip_path.stat().st_size > 0:
            if marker is not None:
                # 変更なし: 取得も展開もスキップ
                entries.append(_entry_from_cached(src, zip_path, marker.get("geojson_files", 0)))
                n_skip += 1
                print(f"[{i}/{len(targets)}] {src['pref']}: 変更なし（スキップ）", flush=True)
                continue
            # zip はキャッシュ済みだが未展開 → 展開のみ
            n = extract_one(zip_path, extract_dir)
            _write_marker(extract_dir, src["content_id"], n)
            entries.append(_entry_from_cached(src, zip_path, n))
            n_extract_only += 1
            print(f"[{i}/{len(targets)}] {src['pref']}: キャッシュから展開（geojson {n} 件）", flush=True)
            continue
        print(f"[{i}/{len(targets)}] {src['pref']} を取得中 …", flush=True)
        entry = download_one(src, zip_dir)
        n = extract_one(Path(entry["zip_path"]), extract_dir)
        _write_marker(extract_dir, src["content_id"], n)
        entry["geojson_files"] = n
        entries.append(entry)
        n_download += 1
        print(f"    {entry['bytes']:,} bytes / geojson {n} 件 / sha256 {entry['sha256'][:12]}")
        if sleep and i < len(targets):
            time.sleep(sleep)
    print(f"download: 取得 {n_download} / キャッシュ展開 {n_extract_only} / スキップ {n_skip}")
    # 全県実行時のみ、現行版に無い旧 zip を掃除（キャッシュ肥大防止）
    if wanted is None:
        removed = cleanup_stale_zips(sources, zip_dir)
        if removed:
            print(f"cleanup: 旧版 zip を {removed} 件削除")
    return entries
