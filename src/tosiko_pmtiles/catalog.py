"""manifest / versions.json / CATALOG.md の生成と、変更検知。"""
from __future__ import annotations

import datetime as dt
import json
import os
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
    parquet_results: Optional[list[dict]] = None,
    bundle_results: Optional[list[dict]] = None,
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
        "crs": f"EPSG:{config.SOURCE_EPSG}",
        "prefectures": download_entries or scrape_result.get("prefectures", []),
        "pmtiles": convert_results,
        "parquet": parquet_results or [],
        "bundles": bundle_results or [],
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
        "parquet": [
            {"name": p["parquet"], "bytes": p.get("bytes"), "features": p.get("features")}
            for p in manifest.get("parquet", [])
        ],
        "bundles": [
            {"name": b["file"], "bytes": b.get("bytes"), "entries": b.get("entries")}
            for b in manifest.get("bundles", [])
        ],
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


def build_release_notes(manifest: dict, *, repo: Optional[str] = None) -> str:
    """Release 本文を manifest から組み立てる。

    手書きの固定文にしていると、配信物を足したり外したりしたときに本文だけ古いまま
    残る（実際 GeoParquet 追加後もしばらく「PMTiles 化した版」と書かれていた）。
    公開のたびに manifest から作り直して `gh release edit --notes-file` で当てる。
    """
    repo = repo or os.environ.get("GITHUB_REPOSITORY") or "shiwaku/mlit-urban-planning-converter"
    base = f"https://github.com/{repo}/releases/latest/download"
    pmtiles = manifest.get("pmtiles", [])
    parquet = manifest.get("parquet", [])
    bundles = manifest.get("bundles", [])
    pm_bytes = sum(p.get("bytes") or 0 for p in pmtiles)
    features = sum(p.get("features") or 0 for p in parquet)
    themes = len(parquet) or len(pmtiles)
    lines = [
        f"国土交通省 都市局『都市計画決定GISデータ』全国版を PMTiles / GeoParquet 化した版 "
        f"{manifest['version']}。",
        "",
        f"{len(manifest.get('prefectures', []))}都道府県 / {themes}テーマ / "
        f"{features:,} 地物 / 座標系 {manifest.get('crs', f'EPSG:{config.SOURCE_EPSG}')}",
        "",
        "## 添付ファイル",
        "",
        "| ファイル | 内容 | サイズ |",
        "| --- | --- | --- |",
    ]
    for b in bundles:
        lines.append(
            f"| `{b['file']}` | **QGIS 用一式**。GeoParquet {b.get('themes', 0)}テーマ + QML + "
            f"`.qlr` / `.qgz`（解凍して `toshikeikaku.qgz` を開くだけ） | {_fmt_mb(b.get('bytes'))} |"
        )
    if pmtiles:
        lines.append(
            f"| `<テーマ>.pmtiles` | MapLibre GL JS 等の地図描画用のベクトルタイル"
            f"（{len(pmtiles)}本） | "
            f"合計 {_fmt_mb(pm_bytes)} |"
        )
    lines += [
        "| `manifest.json` | 収録内容の台帳（都道府県ごとの取得元 URL・sha256・件数） | - |",
        "",
    ]
    if bundles:
        lines += [
            "## QGIS で見る",
            "",
            f"[`{bundles[0]['file']}`]({base}/{bundles[0]['file']}) を解凍し、"
            f"`toshikeikaku.qgz` を開くと {bundles[0].get('themes', themes)}レイヤ + "
            "背景地図（地理院タイル 淡色地図）が"
            "重ね順どおりに表示されます。GeoParquet と QML もこの zip に入っています"
            "（QGIS 3.28 以降が必要）。",
            "",
        ]
    if pmtiles:
        lines += [
            "## Web 地図で使う",
            "",
            "PMTiles は**落とさずに URL をそのまま指定**できます（HTTP Range で必要なタイルだけ取得）。",
            "",
            "```",
            f"{base}/{pmtiles[0]['pmtiles']}",
            "```",
            "",
        ]
    lines += [
        f"出典: 国土交通省 都市局 {manifest.get('source_page', '')}",
        "",
        "本データは提供元が公開する**参考情報**です（概ねの位置を示すもので、建築確認等の"
        "公式手続に用いることは想定されていません）。詳細は README と出典元をご確認ください。",
    ]
    return "\n".join(lines) + "\n"


def write_release_notes(manifest: dict, *, repo: Optional[str] = None) -> Path:
    path = config.DIST_DIR / "release-notes.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_release_notes(manifest, repo=repo), encoding="utf-8")
    return path


def write_catalog_md(manifest: dict) -> Path:
    path = config.ROOT / "CATALOG.md"
    parquet = manifest.get("parquet", [])
    lines = [
        "# データカタログ",
        "",
        f"- 最新版: **{manifest['version']}**（タグ `{manifest['tag']}`）",
        f"- 生成日時: {manifest['generated_at']}",
        f"- 出典: 国土交通省 都市局「都市計画決定GISデータ」 {manifest.get('source_page','')}",
        f"- 分割方式: `{manifest['split']}`",
        f"- 座標参照系: {manifest.get('crs', f'EPSG:{config.SOURCE_EPSG}')}",
        "",
    ]

    bundles = manifest.get("bundles", [])
    if bundles:
        lines += [
            "## 一括ダウンロード（QGIS 用一式）",
            "",
            "GeoParquet 全テーマ + QML + `.qlr` / `.qgz` を1本にまとめた zip です。",
            "解凍してできたフォルダの `toshikeikaku.qgz` を開くと、"
            f"{bundles[0].get('themes', len(parquet))}レイヤが重ね順どおりに表示されます。",
            "",
            "| ファイル | 内容 | サイズ |",
            "| --- | --- | --- |",
        ]
        for b in bundles:
            lines.append(
                f"| `{b['file']}` | GeoParquet {b.get('themes', 0)}テーマ + QML + `.qlr` / `.qgz` "
                f"（{b.get('entries', 0)} ファイル） | {_fmt_mb(b.get('bytes'))} |"
            )
        lines.append("")

    lines += [
        "## PMTiles（地図描画用）",
        "",
        "| ファイル | 名称 | サイズ | ソース数 |",
        "| --- | --- | --- | --- |",
    ]
    for p in manifest.get("pmtiles", []):
        name = p.get("name") or p.get("prefecture") or p.get("theme") or ""
        src = p.get("source_files") or (len(p.get("themes", [])) if p.get("themes") else "")
        lines.append(f"| `{p['pmtiles']}` | {name} | {_fmt_mb(p.get('bytes'))} | {src} |")

    if parquet:
        lines += [
            "",
            "## GeoParquet（QGIS・解析用。属性と座標は元データのまま）",
            "",
            "Release には個別添付せず、**上の zip に同梱**しています（同名の QML も隣に入って"
            "いるので、QGIS に読み込むだけで配色が当たります）。",
            "",
            "| ファイル | 名称 | サイズ | 地物数 |",
            "| --- | --- | --- | --- |",
        ]
        for p in parquet:
            lines.append(
                f"| `{p['parquet']}` | {p.get('name','')} | {_fmt_mb(p.get('bytes'))} | {p.get('features', 0):,} |"
            )

    lines += [
        "",
        "## 収録都道府県",
        "",
        f"{len(manifest.get('prefectures', []))} 都道府県",
        "",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
