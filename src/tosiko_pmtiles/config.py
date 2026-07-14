"""パス・URL・定数と、テーマ定義の読み込み。"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

# データ提供元（国土交通省 都市局）
SELECTION_URL = "https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html"
INFO_URL = "https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000087.html"
SITE_ORIGIN = "https://www.mlit.go.jp"

# ダウンロードページのテーブルで GeoJSON 形式が入っている列見出し
GEOJSON_COLUMN_HEADER = "GeoJSON形式"

USER_AGENT = (
    "toshi-tosiko-tk-pmtiles-pipeline/0.1 "
    "(+https://github.com/; GeoJSON downloader for MLIT urban-planning GIS data)"
)


def project_root() -> Path:
    """リポジトリルート。環境変数 TOSIKO_ROOT で上書き可、無ければパッケージから2つ上。"""
    env = os.environ.get("TOSIKO_ROOT")
    if env:
        return Path(env).resolve()
    # src/tosiko_pmtiles/config.py -> リポジトリルート
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
DATA_DIR = ROOT / "data"
RAW_DIR = ROOT / "raw"
ZIP_DIR = RAW_DIR / "zip"
EXTRACT_DIR = RAW_DIR / "extracted"
DIST_DIR = ROOT / "dist"
VERSIONS_DIR = ROOT / "versions"
THEMES_JSON = DATA_DIR / "themes.json"
# themes.json はコード同梱資産。TOSIKO_ROOT を作業用に上書きしても見つかるよう、
# パッケージ相対（リポジトリ同梱）をフォールバックにする。
_PACKAGE_THEMES = Path(__file__).resolve().parents[2] / "data" / "themes.json"


@lru_cache(maxsize=1)
def load_themes() -> dict[str, dict]:
    """テーマコード -> {name, order} の辞書を返す。"""
    path = THEMES_JSON if THEMES_JSON.exists() else _PACKAGE_THEMES
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    return {t["code"]: t for t in data["themes"]}


def theme_name(code: str) -> str:
    """テーマコードから日本語名。未知コードはコード自体を返す。"""
    return load_themes().get(code, {}).get("name", code)


def theme_order(code: str) -> int:
    """テーマの表示順。未知コードは末尾。"""
    return load_themes().get(code, {}).get("order", 9999)


def ensure_dirs() -> None:
    for d in (DATA_DIR, ZIP_DIR, EXTRACT_DIR, DIST_DIR, VERSIONS_DIR):
        d.mkdir(parents=True, exist_ok=True)
