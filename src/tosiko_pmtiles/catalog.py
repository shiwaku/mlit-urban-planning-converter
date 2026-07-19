"""manifest / versions.json / CATALOG.md の生成と、変更検知。"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Optional

from . import config


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def tag_for(version: str) -> str:
    return f"data-{version}"


def build_manifest(
    scrape_result: dict,
    download_entries: list[dict],
    convert_results: list[dict],
    *,
    split: str,
    generated_at: Optional[str] = None,
) -> dict:
    version = scrape_result["version"]
    return {
        "version": version,
        "tag": tag_for(version),
        "generated_at": generated_at or _now_iso(),
        "source_page": scrape_result.get("source_page"),
        "info_page": scrape_result.get("info_page"),
        "fingerprint": scrape_result.get("fingerprint"),
        "split": split,
        "prefectures": download_entries or scrape_result.get("prefectures", []),
        "pmtiles": convert_results,
    }


def write_manifest(manifest: dict) -> tuple[Path, Path]:
    """versions/manifest-<version>.json（コミット用）と dist/manifest.json（Release用）を書く。"""
    config.VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    config.DIST_DIR.mkdir(parents=True, exist_ok=True)
    versioned = config.VERSIONS_DIR / f"manifest-{manifest['version']}.json"
    dist_copy = config.DIST_DIR / "manifest.json"
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    versioned.write_text(text, encoding="utf-8")
    dist_copy.write_text(text, encoding="utf-8")
    return versioned, dist_copy


def latest_committed_manifest() -> Optional[dict]:
    """versions/ 内の最新 manifest（変更検知・差分判定用）。無ければ None。"""
    files = sorted(config.VERSIONS_DIR.glob("manifest-*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def latest_committed_fingerprint() -> Optional[str]:
    """versions/ 内の最新 manifest の fingerprint（変更検知用）。無ければ None。"""
    data = latest_committed_manifest()
    return data.get("fingerprint") if data else None


def _versions_index_path() -> Path:
    return config.ROOT / "versions.json"


def update_versions_index(manifest: dict, *, release_url: Optional[str] = None) -> Path:
    """versions.json（新しい版が先頭）を更新。同一 version は置き換える。"""
    path = _versions_index_path()
    index = {"versions": []}
    if path.exists():
        try:
            index = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            index = {"versions": []}
    entry = {
        "version": manifest["version"],
        "tag": manifest["tag"],
        "generated_at": manifest["generated_at"],
        "split": manifest["split"],
        "release_url": release_url,
        "prefecture_count": len(manifest.get("prefectures", [])),
        "pmtiles": [{"name": p["pmtiles"], "bytes": p.get("bytes")} for p in manifest.get("pmtiles", [])],
    }
    others = [v for v in index.get("versions", []) if v.get("version") != manifest["version"]]
    index["versions"] = [entry] + others
    index["versions"].sort(key=lambda v: v.get("version", ""), reverse=True)
    index["latest"] = index["versions"][0]["version"] if index["versions"] else None
    path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _fmt_mb(nbytes: Optional[int]) -> str:
    if not nbytes:
        return "-"
    return f"{nbytes / 1048576:.1f} MB"


def write_catalog_md(manifest: dict) -> Path:
    path = config.ROOT / "CATALOG.md"
    lines = [
        "# データカタログ",
        "",
        f"- 最新版: **{manifest['version']}**（タグ `{manifest['tag']}`）",
        f"- 生成日時: {manifest['generated_at']}",
        f"- 出典: 国土交通省 都市局「都市計画決定GISデータ」 {manifest.get('source_page','')}",
        f"- 分割方式: `{manifest['split']}`",
        "",
        "## PMTiles",
        "",
        "| ファイル | 名称 | サイズ | ソース数 |",
        "| --- | --- | --- | --- |",
    ]
    for p in manifest.get("pmtiles", []):
        name = p.get("name") or p.get("prefecture") or p.get("theme") or ""
        src = p.get("source_files") or (len(p.get("themes", [])) if p.get("themes") else "")
        lines.append(f"| `{p['pmtiles']}` | {name} | {_fmt_mb(p.get('bytes'))} | {src} |")
    lines += [
        "",
        "## 収録都道府県",
        "",
        f"{len(manifest.get('prefectures', []))} 都道府県",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
