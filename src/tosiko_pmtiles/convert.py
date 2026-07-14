"""展開済み GeoJSON を tippecanoe で PMTiles に変換する。

既定は「テーマ別・全国統合」（split=theme）: テーマごとに 1 つの PMTiles を生成し、
レイヤーには全都道府県・全市区町村の当該テーマ地物を統合する。
split=prefecture では都道府県ごとに 1 つの PMTiles（テーマ = レイヤー）を生成する。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Optional

from . import config

_THEME_RE = re.compile(r"_([a-z0-9]+)\.geojson$", re.IGNORECASE)


def require_tippecanoe() -> str:
    exe = shutil.which("tippecanoe")
    if not exe:
        raise RuntimeError("tippecanoe が見つかりません。インストールしてください。")
    return exe


def discover_by_theme(extract_dir: Path) -> dict[str, list[Path]]:
    """extract_dir 配下の .geojson をテーマコード別にグルーピング。"""
    groups: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(extract_dir.rglob("*.geojson")):
        m = _THEME_RE.search(path.name)
        if m:
            groups[m.group(1).lower()].append(path)
    return dict(groups)


def discover_by_prefecture(extract_dir: Path) -> dict[str, dict[str, list[Path]]]:
    """都道府県（zip 直下フォルダ名）-> テーマ -> ファイル群。"""
    prefs: dict[str, dict[str, list[Path]]] = defaultdict(lambda: defaultdict(list))
    for path in sorted(extract_dir.rglob("*.geojson")):
        m = _THEME_RE.search(path.name)
        if not m:
            continue
        rel = path.relative_to(extract_dir)
        pref_dir = rel.parts[0] if rel.parts else "unknown"
        prefs[pref_dir][m.group(1).lower()].append(path)
    return {k: dict(v) for k, v in prefs.items()}


def _tippecanoe_base(minzoom: int, maxzoom: int, extra: Optional[list[str]]) -> list[str]:
    args = [
        require_tippecanoe(),
        "-Z", str(minzoom),
        "-z", str(maxzoom),
        "--coalesce-densest-as-needed",
        "--drop-densest-as-needed",
        "--extend-zooms-if-still-dropping",
        "--no-tile-size-limit",
        "--force",
    ]
    if extra:
        args += extra
    return args


def _merge_to_geojsonseq(files: list[Path], out: Path) -> int:
    """複数 FeatureCollection を newline-delimited GeoJSON にまとめる。地物数を返す。"""
    n = 0
    with out.open("w", encoding="utf-8") as dst:
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"    !! 読み込みスキップ {f}: {exc}")
                continue
            feats = data.get("features", []) if isinstance(data, dict) else []
            for feat in feats:
                dst.write(json.dumps(feat, ensure_ascii=False, separators=(",", ":")))
                dst.write("\n")
                n += 1
    return n


def convert_by_theme(
    extract_dir: Path,
    dist_dir: Path,
    *,
    minzoom: int = 4,
    maxzoom: int = 14,
    extra: Optional[list[str]] = None,
) -> list[dict]:
    dist_dir.mkdir(parents=True, exist_ok=True)
    groups = discover_by_theme(extract_dir)
    results: list[dict] = []
    order = sorted(groups.items(), key=lambda kv: config.theme_order(kv[0]))
    for theme, files in order:
        out = dist_dir / f"{theme}.pmtiles"
        cmd = _tippecanoe_base(minzoom, maxzoom, extra) + ["-l", theme, "-o", str(out)] + [str(f) for f in files]
        print(f"[theme] {theme} ({config.theme_name(theme)}): {len(files)} files -> {out.name}", flush=True)
        subprocess.run(cmd, check=True)
        results.append(
            {
                "kind": "theme",
                "theme": theme,
                "name": config.theme_name(theme),
                "pmtiles": out.name,
                "bytes": out.stat().st_size,
                "source_files": len(files),
            }
        )
    return results


def convert_by_prefecture(
    extract_dir: Path,
    dist_dir: Path,
    *,
    minzoom: int = 4,
    maxzoom: int = 14,
    extra: Optional[list[str]] = None,
) -> list[dict]:
    dist_dir.mkdir(parents=True, exist_ok=True)
    prefs = discover_by_prefecture(extract_dir)
    results: list[dict] = []
    for pref_dir, theme_files in sorted(prefs.items()):
        out = dist_dir / f"{pref_dir}.pmtiles"
        with tempfile.TemporaryDirectory() as tmp:
            layer_args: list[str] = []
            total = 0
            for theme, files in sorted(theme_files.items(), key=lambda kv: config.theme_order(kv[0])):
                seq = Path(tmp) / f"{theme}.geojsonl"
                total += _merge_to_geojsonseq(files, seq)
                layer_args += ["-L", f"{theme}:{seq}"]
            cmd = _tippecanoe_base(minzoom, maxzoom, extra) + ["-o", str(out)] + layer_args
            print(f"[pref] {pref_dir}: {len(theme_files)} themes / {total} features -> {out.name}", flush=True)
            subprocess.run(cmd, check=True)
        results.append(
            {
                "kind": "prefecture",
                "prefecture": pref_dir,
                "pmtiles": out.name,
                "bytes": out.stat().st_size,
                "themes": sorted(theme_files.keys(), key=config.theme_order),
            }
        )
    return results


def convert(
    split: str = "theme",
    *,
    extract_dir: Optional[Path] = None,
    dist_dir: Optional[Path] = None,
    minzoom: int = 4,
    maxzoom: int = 14,
    extra: Optional[list[str]] = None,
) -> list[dict]:
    extract_dir = extract_dir or config.EXTRACT_DIR
    dist_dir = dist_dir or config.DIST_DIR
    if split == "theme":
        return convert_by_theme(extract_dir, dist_dir, minzoom=minzoom, maxzoom=maxzoom, extra=extra)
    if split == "prefecture":
        return convert_by_prefecture(extract_dir, dist_dir, minzoom=minzoom, maxzoom=maxzoom, extra=extra)
    raise ValueError(f"未知の split: {split}")
