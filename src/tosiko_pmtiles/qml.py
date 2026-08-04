"""テーマごとの QGIS レイヤスタイル（QML）を生成する。

配色は `data/styles.json`（ビューアと共有）から作るので、Web ビューアと QGIS で
同じ見た目になる。QGIS はファイル系レイヤを読み込むとき、同じディレクトリにある
`<ファイル名>.qml` を自動で適用する。したがって `youto.parquet` と `youto.qml` を
並べて置けば、読み込んだ時点で用途地域が色分けされた状態になる。

出力するもの:
  - 単一シンボル（塗り / 線）またはカテゴリ分け（用途地域 = YoutoCode、
    区域区分・防火・立地適正化 = AreaType）のレンダラ
  - 属性のフィールド別名（Pref -> 都道府県 など）。属性テーブルが和名で読める
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import quoteattr

from . import config

# 生成対象の QGIS バージョン表記。QML の互換性判定には使われないが、
# QGIS が開いたときのバージョン表示に出る。
QGIS_VERSION = "3.34.0"
# 面の輪郭線幅（mm）。密なポリゴンでも塗りが潰れない細さ。
OUTLINE_WIDTH_MM = "0.2"
# 都市計画道路（線）の線幅（mm）。
LINE_WIDTH_MM = "0.4"

_RGBA_RE = re.compile(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([\d.]+)\s*)?\)")


def parse_rgba(value: str) -> str:
    """`rgba(r,g,b,a)` -> QGIS の色表記 `r,g,b,a`（a は 0-255）。"""
    m = _RGBA_RE.fullmatch(value.strip())
    if not m:
        raise ValueError(f"色の書式が不正です: {value!r}")
    r, g, b, a = m.group(1), m.group(2), m.group(3), m.group(4)
    alpha = 255 if a is None else round(float(a) * 255)
    return f"{r},{g},{b},{alpha}"


def _options(pairs: list[tuple[str, str]]) -> str:
    body = "\n".join(
        f'          <Option name="{k}" type="QString" value={quoteattr(v)}/>' for k, v in pairs
    )
    return f'        <Option type="Map">\n{body}\n        </Option>'


def fill_symbol(name: str, fill: str, outline: str) -> str:
    opts = _options(
        [
            ("color", parse_rgba(fill)),
            ("outline_color", parse_rgba(outline)),
            ("outline_style", "solid"),
            ("outline_width", OUTLINE_WIDTH_MM),
            ("outline_width_unit", "MM"),
            ("style", "solid"),
            ("joinstyle", "bevel"),
            ("offset", "0,0"),
            ("offset_unit", "MM"),
        ]
    )
    return (
        f'    <symbol name="{name}" type="fill" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">\n'
        f'      <layer class="SimpleFill" enabled="1" locked="0" pass="0">\n'
        f"{opts}\n"
        f"      </layer>\n"
        f"    </symbol>"
    )


def line_symbol(name: str, color: str) -> str:
    opts = _options(
        [
            ("line_color", parse_rgba(color)),
            ("line_style", "solid"),
            ("line_width", LINE_WIDTH_MM),
            ("line_width_unit", "MM"),
            ("capstyle", "square"),
            ("joinstyle", "bevel"),
            ("offset", "0"),
            ("offset_unit", "MM"),
            ("use_custom_dash", "0"),
        ]
    )
    return (
        f'    <symbol name="{name}" type="line" alpha="1" clip_to_extent="1" force_rhr="0" frame_rate="10" is_animated="0">\n'
        f'      <layer class="SimpleLine" enabled="1" locked="0" pass="0">\n'
        f"{opts}\n"
        f"      </layer>\n"
        f"    </symbol>"
    )


def _single_renderer(symbol: str) -> str:
    return (
        '  <renderer-v2 type="singleSymbol" forceraster="0" symbollevels="0" '
        'enableorderby="0" referencescale="-1">\n'
        "    <symbols>\n"
        f"{symbol}\n"
        "    </symbols>\n"
        "  </renderer-v2>"
    )


def _categorized_renderer(attr: str, categories: list[tuple[str, str]], symbols: list[str]) -> str:
    """categories は (値, ラベル) の並び。末尾に値が空のフォールバックを置く。"""
    cats = "\n".join(
        f'      <category value={quoteattr(value)} symbol="{i}" label={quoteattr(label)} render="true"/>'
        for i, (value, label) in enumerate(categories)
    )
    return (
        f'  <renderer-v2 type="categorizedSymbol" attr={quoteattr(attr)} forceraster="0" '
        'symbollevels="0" enableorderby="0" referencescale="-1">\n'
        "    <categories>\n"
        f"{cats}\n"
        "    </categories>\n"
        "    <symbols>\n"
        + "\n".join(symbols)
        + "\n    </symbols>\n"
        "  </renderer-v2>"
    )


def _renderer_for(theme: str) -> tuple[str, str]:
    """テーマ -> (renderer-v2 の XML, ジオメトリ種別)。"""
    styles = config.load_styles()
    style = styles["themes"].get(theme, styles["fallbackStyle"])
    geom = style.get("geom", "fill")

    if geom == "line":
        color = style.get("outline") or style.get("fill")
        return _single_renderer(line_symbol("0", color)), geom

    kind = style["kind"]
    if kind == "youto":
        youto = styles["youto"]
        outline = youto["outline"]
        categories = [(str(c["code"]), c["name"]) for c in youto["codes"]]
        symbols = [fill_symbol(str(i), c["color"], outline) for i, c in enumerate(youto["codes"])]
        categories.append(("", "その他・不明"))
        symbols.append(fill_symbol(str(len(symbols)), youto["fallback"], outline))
        return _categorized_renderer("YoutoCode", categories, symbols), geom

    if kind == "cats":
        categories = []
        symbols = []
        for value, cat in style["cats"].items():
            symbols.append(fill_symbol(str(len(symbols)), cat["fill"], cat["outline"]))
            categories.append((value, cat["label"]))
        fallback = style["fallback"]
        symbols.append(fill_symbol(str(len(symbols)), fallback["fill"], fallback["outline"]))
        categories.append(("", fallback["label"]))
        return _categorized_renderer(style["prop"], categories, symbols), geom

    return _single_renderer(fill_symbol("0", style["fill"], style["outline"])), geom


def _aliases() -> str:
    labels = config.load_styles()["attributeLabels"]
    rows = "\n".join(
        f'    <alias field={quoteattr(field)} index="{i}" name={quoteattr(label)}/>'
        for i, (field, label) in enumerate(labels.items())
    )
    return f"  <aliases>\n{rows}\n  </aliases>"


def build_qml(theme: str) -> str:
    renderer, geom = _renderer_for(theme)
    opacity = config.load_styles()["defaultOpacity"]
    # 0=点 / 1=線 / 2=面
    geometry_type = 1 if geom == "line" else 2
    name = config.theme_name(theme)
    return (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        f"<!-- {name}（{theme}）: 国土交通省 都市局『都市計画決定GISデータ』用のスタイル。\n"
        "     https://github.com/shiwaku/mlit-urban-planning-converter が data/styles.json から生成。\n"
        f"     配色は全国都市計画GISビューア（https://toshikeikaku-info.jp/）を参考にしている。 -->\n"
        f'<qgis version="{QGIS_VERSION}" styleCategories="Symbology|Fields">\n'
        f"{renderer}\n"
        f"  <layerOpacity>{opacity}</layerOpacity>\n"
        f"{_aliases()}\n"
        f"  <layerGeometryType>{geometry_type}</layerGeometryType>\n"
        "</qgis>\n"
    )


def write_all(
    *,
    out_dir: Optional[Path] = None,
    themes: Optional[list[str]] = None,
) -> list[dict]:
    """全テーマ分の QML を書き出し、manifest 用の結果リストを返す。"""
    out_dir = out_dir or config.STYLES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    codes = themes or sorted(config.load_styles()["themes"], key=config.theme_order)
    results: list[dict] = []
    for theme in codes:
        path = out_dir / f"{theme}.qml"
        path.write_text(build_qml(theme), encoding="utf-8")
        results.append(
            {
                "theme": theme,
                "name": config.theme_name(theme),
                "qml": path.name,
                "bytes": path.stat().st_size,
            }
        )
    print(f"qml: {len(results)} ファイル -> {out_dir}")
    return results
