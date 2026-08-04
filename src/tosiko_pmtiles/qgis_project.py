"""QGIS のレイヤ定義ファイル（.qlr）とプロジェクト（.qgz）を生成する。

QML は「レイヤ1枚のスタイル」しか持てないため、26テーマの**重ね順**までは配れない。
順序を持てるのはプロジェクト側の形式なので、次の2つを用意する。

  - `.qlr`  レイヤ群 + スタイル + 重ね順。QGIS に D&D すると26レイヤが一括で入る
  - `.qgz`  上記に加えて背景地図（地理院タイル）・プロジェクト CRS・初期表示範囲。
            開くだけで完成状態になる（中身は .qgs を1つ含む zip）

重ね順は `data/styles.json` の `drawOrder`（ビューアと共有、先頭が最背面）。QGIS の
レイヤツリーは**先頭が最前面**なので、書き出すときに反転する。

データソースはファイル名だけの相対パス（`./youto.parquet`）にしてある。したがって
**.qlr / .qgz は GeoParquet と同じフォルダに置く**必要がある（QML と同じ約束）。
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape, quoteattr

from . import config, qml

PROJECT_BASENAME = "toshikeikaku"
PROJECT_TITLE = "都市計画決定GISデータ（全国）"
# 背景地図。地理院タイル（淡色地図）。出典表示が必要なので layername に入れておく。
BASEMAP_NAME = "地理院タイル 淡色地図"
BASEMAP_URL = "https://cyberjapandata.gsi.go.jp/xyz/pale/{z}/{x}/{y}.png"
BASEMAP_ID = "gsi_pale_basemap"
# XYZ タイルの座標系と全球範囲（Web メルカトルのメートル）。
BASEMAP_EPSG = 3857
_WEB_MERCATOR_MAX = 20037508.342789244
BASEMAP_EXTENT = (-_WEB_MERCATOR_MAX, -_WEB_MERCATOR_MAX, _WEB_MERCATOR_MAX, _WEB_MERCATOR_MAX)
# 初期表示範囲（EPSG:6668 の経緯度）。日本全体が入る範囲。
DEFAULT_EXTENT = (122.0, 20.0, 154.0, 46.0)
# .qgz（zip）内のタイムスタンプ。再現性のため固定する（ZIP 形式が表せる最小の日時）。
ZIP_EPOCH = (1980, 1, 1, 0, 0, 0)

# GeoJSON のジオメトリ種別 -> QGIS の wkbType 表記。MultiPolygon と Polygon が
# 混在するテーマは Multi 側に寄せる（QGIS は単一の型を期待するため）。
_WKB_TYPE = {
    ("Polygon",): "Polygon",
    ("MultiPolygon",): "MultiPolygon",
    ("MultiPolygon", "Polygon"): "MultiPolygon",
    ("LineString",): "LineString",
    ("MultiLineString",): "MultiLineString",
    ("LineString", "MultiLineString"): "MultiLineString",
}


def _srs_xml(epsg: int = config.SOURCE_EPSG) -> str:
    """<spatialrefsys>。pyproj から proj4 / WKT を引く。

    背景地図（XYZ タイル）は EPSG:3857 なので、データ側の EPSG:6668 とは別に
    書き出す必要がある。ここを取り違えるとタイル座標が度として扱われ、
    レイヤが画面上のどこにも出てこない。
    """
    import warnings

    from pyproj import CRS

    crs = CRS.from_epsg(epsg)
    with warnings.catch_warnings():
        # 一般に proj4 化は情報が落ちうるという警告だが、扱うのは経緯度と
        # Web メルカトルなので落ちるものは無い。QGIS の旧バージョン互換のため併記する。
        warnings.simplefilter("ignore", UserWarning)
        proj4 = crs.to_proj4()
    acronym = "longlat" if crs.is_geographic else (
        dict(p.split("=", 1) for p in proj4.split() if "=" in p).get("+proj", "")
    )
    # 楕円体は EPSG コードで書く（GRS80 = EPSG:7019、WGS84 = EPSG:7030）。
    ident = (crs.ellipsoid.to_json_dict().get("id") or {}) if crs.ellipsoid else {}
    ellipsoid = (
        f"{ident['authority']}:{ident['code']}" if ident.get("authority") and ident.get("code") else ""
    )
    return (
        "      <spatialrefsys nativeFormat=\"Wkt\">\n"
        f"        <wkt>{escape(crs.to_wkt())}</wkt>\n"
        f"        <proj4>{escape(proj4)}</proj4>\n"
        f"        <srsid>{epsg}</srsid>\n"
        f"        <srid>{epsg}</srid>\n"
        f"        <authid>EPSG:{epsg}</authid>\n"
        f"        <description>{escape(crs.name)}</description>\n"
        f"        <projectionacronym>{escape(acronym)}</projectionacronym>\n"
        f"        <ellipsoidacronym>{ellipsoid}</ellipsoidacronym>\n"
        f"        <geographicflag>{'true' if crs.is_geographic else 'false'}</geographicflag>\n"
        "      </spatialrefsys>"
    )


def _wkb_type(geometry_types: list[str]) -> str:
    return _WKB_TYPE.get(tuple(sorted(geometry_types)), "Unknown")


def _extent_xml(bbox: Optional[list[float]], indent: str) -> str:
    box = bbox or list(DEFAULT_EXTENT)
    return (
        f"{indent}<extent>\n"
        f"{indent}  <xmin>{box[0]!r}</xmin>\n"
        f"{indent}  <ymin>{box[1]!r}</ymin>\n"
        f"{indent}  <xmax>{box[2]!r}</xmax>\n"
        f"{indent}  <ymax>{box[3]!r}</ymax>\n"
        f"{indent}</extent>"
    )


def _layer_id(theme: str) -> str:
    return f"{theme}_layer"


def _maplayer(theme: str, meta: dict, srs: str) -> str:
    """1テーマ分の <maplayer>。renderer と別名は QML 生成と同じものを使う。"""
    renderer, geom = qml.renderer_for(theme)
    # QML では <qgis> 直下、ここでは <maplayer> 直下に入るのでインデントだけ深くする
    renderer = "\n".join("  " + line for line in renderer.splitlines())
    aliases = "\n".join("  " + line for line in qml.aliases_xml().splitlines())
    name = config.theme_name(theme)
    wkb = _wkb_type(meta.get("geometry_types") or (["LineString"] if geom == "line" else ["Polygon"]))
    return (
        f'    <maplayer type="vector" geometry="{"Line" if geom == "line" else "Polygon"}" '
        f'wkbType="{wkb}" hasScaleBasedVisibilityFlag="0" minScale="1e+08" maxScale="0" '
        f'simplifyDrawingHints="1" simplifyDrawingTol="1" simplifyLocal="1" simplifyMaxScale="1" '
        f'simplifyAlgorithm="0" readOnly="0" labelsEnabled="0" '
        f'styleCategories="AllStyleCategories" autoRefreshMode="Disabled" autoRefreshTime="0">\n'
        f"{_extent_xml(meta.get('bbox'), '      ')}\n"
        f"      <id>{_layer_id(theme)}</id>\n"
        f"      <datasource>./{theme}.parquet</datasource>\n"
        f"      <layername>{escape(name)}</layername>\n"
        f"      <srs>\n{srs}\n      </srs>\n"
        f'      <provider encoding="UTF-8">ogr</provider>\n'
        f"{renderer}\n"
        f"      <layerOpacity>{config.load_styles()['defaultOpacity']}</layerOpacity>\n"
        f"{aliases}\n"
        f"      <blendMode>0</blendMode>\n"
        f"      <featureBlendMode>0</featureBlendMode>\n"
        f"    </maplayer>"
    )


def _basemap_maplayer() -> str:
    """地理院タイル（淡色地図）の XYZ ラスタレイヤ。

    QGIS 自身が書き出した .qgs（QGIS-Documentation の training_manual、pfaedle）の
    XYZ レイヤをそのまま写した構造にしてある。ラスタは手書きの最小構成では読み込みに
    失敗しうるので、実物に合わせるのが確実:

      - タイルは Web メルカトル。レイヤの CRS と extent は EPSG:3857 で書く
        （プロジェクトの EPSG:6668 を流用すると、メートル値が度として扱われて出てこない）
      - URI はパラメータをアルファベット順に並べ、`format` は**値を持たないフラグ**として
        書く（`format=` ではない）
      - **`url` は percent encode しない**。QGIS 3.34 の読み取り経路では
        `mBaseUrl = uri.param("url")` をそのまま使い、リテラルの `{x}` `{y}` `{z}` を
        文字列置換する（`qgswmsprovider.cpp` の createTileRequestsXYZ）。デコードを
        行う prepareUri() はこの経路を通らないので、`%7Bz%7D` と書くと置換されず
        壊れた URL を叩いて真っ白になる。`&` や `=` を含まない URL なので、
        波括弧のまま書いても URI のパース自体は壊れない
      - `crs` は xyz では provider 側が EPSG:3857 に固定するので効かないが、実物に
        合わせて書いておく（`EPSG3857` のようにコロンを落とした値は無効）
      - <pipe> には rasterrenderer だけでなく brightnesscontrast / huesaturation /
        rasterresampler まで入れる。<noData> と <map-layer-style-manager> も実物にある
    """
    ds = (
        f"crs=EPSG:{BASEMAP_EPSG}&amp;format&amp;type=xyz&amp;url={escape(BASEMAP_URL)}"
        "&amp;zmax=18&amp;zmin=0"
    )
    return (
        f'    <maplayer type="raster" hasScaleBasedVisibilityFlag="0" minScale="1e+08" maxScale="0" '
        f'styleCategories="AllStyleCategories" autoRefreshEnabled="0" autoRefreshTime="0" '
        f'refreshOnNotifyEnabled="0" refreshOnNotifyMessage="" legendPlaceholderImage="">\n'
        f"{_extent_xml(list(BASEMAP_EXTENT), '      ')}\n"
        f"      <wgs84extent>\n"
        f"        <xmin>-180</xmin>\n"
        f"        <ymin>-85.05112877980660357</ymin>\n"
        f"        <xmax>180</xmax>\n"
        f"        <ymax>85.05112877980658936</ymax>\n"
        f"      </wgs84extent>\n"
        f"      <id>{BASEMAP_ID}</id>\n"
        f"      <datasource>{ds}</datasource>\n"
        f"      <keywordList>\n        <value></value>\n      </keywordList>\n"
        f"      <layername>{escape(BASEMAP_NAME)}</layername>\n"
        f"      <srs>\n{_srs_xml(BASEMAP_EPSG)}\n      </srs>\n"
        f"      <customproperties>\n"
        f'        <property key="identify/format" value="Undefined"/>\n'
        f"      </customproperties>\n"
        f"      <provider>wms</provider>\n"
        f"      <noData>\n"
        f'        <noDataList bandNo="1" useSrcNoData="0"/>\n'
        f"      </noData>\n"
        f'      <map-layer-style-manager current="default">\n'
        f'        <map-layer-style name="default"/>\n'
        f"      </map-layer-style-manager>\n"
        f"      <pipe>\n"
        f'        <rasterrenderer opacity="1" alphaBand="-1" band="1" type="singlebandcolordata">\n'
        f"          <rasterTransparency/>\n"
        f"        </rasterrenderer>\n"
        f'        <brightnesscontrast brightness="0" contrast="0"/>\n'
        f'        <huesaturation colorizeGreen="128" colorizeOn="0" colorizeRed="255" '
        f'colorizeBlue="128" grayscaleMode="0" saturation="0" colorizeStrength="100"/>\n'
        f'        <rasterresampler maxOversampling="2"/>\n'
        f"      </pipe>\n"
        f"      <blendMode>0</blendMode>\n"
        f"    </maplayer>"
    )


def _tree_layer(layer_id: str, name: str, checked: bool, indent: str) -> str:
    state = "Qt::Checked" if checked else "Qt::Unchecked"
    return (
        f"{indent}<layer-tree-layer id={quoteattr(layer_id)} name={quoteattr(name)} "
        f'source="" providerKey="" checked="{state}" expanded="0">\n'
        f"{indent}  <customproperties/>\n"
        f"{indent}</layer-tree-layer>"
    )


def _visible_themes(themes: list[str]) -> set[str]:
    """初期チェックを入れるテーマ。`defaultVisible` が "all" なら全部 ON。"""
    conf = config.load_styles().get("defaultVisible", "all")
    return set(themes) if conf == "all" else set(conf)


def _ordered_themes(available: set[str]) -> list[str]:
    """drawOrder の順（背面→前面）。データが無いテーマは落とす。"""
    return [t for t in config.load_styles()["drawOrder"] if t in available]


def _load_parquet_meta() -> dict[str, dict]:
    """dist/parquet.json から bbox・ジオメトリ種別を拾う。無ければ空。"""
    path = config.DIST_DIR / "parquet.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["theme"]: r for r in data.get("results", [])}


def build_qlr(themes: list[str], meta: dict[str, dict]) -> str:
    srs = _srs_xml()
    visible = _visible_themes(themes)
    # レイヤツリーは先頭が最前面。drawOrder は先頭が最背面なので反転する。
    tree = "\n".join(
        _tree_layer(_layer_id(t), config.theme_name(t), t in visible, "    ")
        for t in reversed(themes)
    )
    layers = "\n".join(_maplayer(t, meta.get(t, {}), srs) for t in themes)
    return (
        "<!DOCTYPE qgis-layer-definition>\n"
        f"<!-- {PROJECT_TITLE}: GeoParquet 26テーマのレイヤ定義。\n"
        "     https://github.com/shiwaku/mlit-urban-planning-converter が生成。\n"
        "     *.parquet と同じフォルダに置いてから QGIS にドラッグ&ドロップすること。 -->\n"
        "<qlr>\n"
        "  <layer-tree-group>\n"
        f"{tree}\n"
        "  </layer-tree-group>\n"
        "  <maplayers>\n"
        f"{layers}\n"
        "  </maplayers>\n"
        "</qlr>\n"
    )


def build_qgs(themes: list[str], meta: dict[str, dict]) -> str:
    srs = _srs_xml()
    visible = _visible_themes(themes)
    tree = "\n".join(
        _tree_layer(_layer_id(t), config.theme_name(t), t in visible, "    ")
        for t in reversed(themes)
    )
    tree += "\n" + _tree_layer(BASEMAP_ID, BASEMAP_NAME, True, "    ")
    layers = "\n".join(_maplayer(t, meta.get(t, {}), srs) for t in themes)
    layers += "\n" + _basemap_maplayer()
    # 描画順（先頭が最前面）。レイヤツリーと同じ並びを明示しておく。
    order = "\n".join(
        f'    <layer id={quoteattr(_layer_id(t))}/>' for t in reversed(themes)
    ) + f'\n    <layer id={quoteattr(BASEMAP_ID)}/>'
    return (
        "<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>\n"
        f'<qgis version="{qml.QGIS_VERSION}" projectname={quoteattr(PROJECT_TITLE)}>\n'
        f"  <title>{escape(PROJECT_TITLE)}</title>\n"
        '  <homePath path=""/>\n'
        f"  <projectCrs>\n{srs}\n  </projectCrs>\n"
        "  <layer-tree-group>\n"
        f"{tree}\n"
        '    <custom-order enabled="0"/>\n'
        "  </layer-tree-group>\n"
        '  <mapcanvas name="theMapCanvas" annotationsVisible="1">\n'
        "    <units>degrees</units>\n"
        f"{_extent_xml(list(DEFAULT_EXTENT), '    ')}\n"
        f"    <destinationsrs>\n{srs}\n    </destinationsrs>\n"
        "  </mapcanvas>\n"
        "  <projectlayers>\n"
        f"{layers}\n"
        "  </projectlayers>\n"
        "  <layerorder>\n"
        f"{order}\n"
        "  </layerorder>\n"
        "  <properties>\n"
        "    <Paths>\n"
        "      <Absolute type=\"bool\">false</Absolute>\n"
        "    </Paths>\n"
        "  </properties>\n"
        "</qgis>\n"
    )


def write_all(
    *,
    out_dirs: Optional[list[Path]] = None,
    themes: Optional[list[str]] = None,
) -> list[dict]:
    """.qlr と .qgz を書き出す。既定では styles/ と dist/ の両方に置く。"""
    out_dirs = out_dirs or [config.STYLES_DIR, config.DIST_DIR]
    meta = _load_parquet_meta()
    available = set(themes) if themes else set(config.load_styles()["themes"])
    ordered = _ordered_themes(available)
    qlr = build_qlr(ordered, meta)
    qgs = build_qgs(ordered, meta)

    results: list[dict] = []
    for out_dir in out_dirs:
        out_dir.mkdir(parents=True, exist_ok=True)
        qlr_path = out_dir / f"{PROJECT_BASENAME}.qlr"
        qlr_path.write_text(qlr, encoding="utf-8")
        qgz_path = out_dir / f"{PROJECT_BASENAME}.qgz"
        # .qgz は .qgs を1つ含む zip。QGIS は同名の .qgs を探す。
        # タイムスタンプは固定する。実行時刻を入れると中身が同じでも zip のバイト列が
        # 毎回変わり、styles/ がコミット対象なので実行のたびに空の差分が出てしまう。
        info = zipfile.ZipInfo(f"{PROJECT_BASENAME}.qgs", date_time=ZIP_EPOCH)
        info.compress_type = zipfile.ZIP_DEFLATED
        with zipfile.ZipFile(qgz_path, "w") as zf:
            zf.writestr(info, qgs)
        results += [
            {"file": qlr_path.name, "dir": str(out_dir), "bytes": qlr_path.stat().st_size},
            {"file": qgz_path.name, "dir": str(out_dir), "bytes": qgz_path.stat().st_size},
        ]
    print(
        f"qgis-project: {len(ordered)} レイヤ -> "
        + " と ".join(str(d) for d in out_dirs)
        + f" の {PROJECT_BASENAME}.qlr / .qgz"
    )
    return results
