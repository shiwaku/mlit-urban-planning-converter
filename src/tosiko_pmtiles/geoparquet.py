"""展開済み GeoJSON をテーマ別の GeoParquet（全国統合）に変換する。

PMTiles と同じ「テーマごとに1ファイル・全国統合」の単位で `dist/<theme>.parquet` を作る。
PMTiles が地図描画用（ズームに応じて間引き・座標を量子化）なのに対し、こちらは元の
GeoJSON の属性・座標をそのまま保持した解析用の配布物。

出力仕様:
  - GeoParquet 1.1.0 / geometry は WKB（ISO）カラム、CRS は EPSG:6668 の PROJJSON
  - 空間絞り込み用に `bbox` struct カラム（covering）を付ける。DuckDB spatial 等が
    row group 統計でプルーニングできる
  - 圧縮は zstd、行グループは既定 50,000 行

属性の型は「テーマ内の全ファイルを見て決める」。提供元データはテーマごとに項目が
統一されている（コード類が整数、他は文字列、未設定は null）が、県によって値が全て
null の項目があるため、1ファイルだけ見て決めると型が揺れる。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from . import config
from .convert import discover_by_theme

GEOPARQUET_VERSION = "1.1.0"
GEOMETRY_COLUMN = "geometry"
BBOX_COLUMN = "bbox"
DEFAULT_ROW_GROUP_SIZE = 50_000
DEFAULT_COMPRESSION = "zstd"
DEFAULT_COMPRESSION_LEVEL = 9
# 行グループ1つあたりのジオメトリ量の目安（非圧縮 WKB のバイト数）。
# 都市計画区域のように「地物数は少ないが1地物が巨大」なテーマだと 50,000 行では
# ファイル全体が1行グループになり、bbox で絞っても読み飛ばせない。行数だけでなく
# 平均バイト数からも行数を決めて、範囲検索が効くようにする。地物ごとの大きさは
# 均一ではないので、実際の行グループはこの値の前後に散る（厳密な上限ではない）。
TARGET_ROW_GROUP_BYTES = 64 * 1024 * 1024
MIN_ROW_GROUP_SIZE = 2_000


def _require_deps():
    """pyarrow / shapely / pyproj をまとめて import（未導入なら分かりやすく落とす）。"""
    try:
        import numpy as np
        import pyarrow as pa
        import pyarrow.parquet as pq
        import shapely
        from shapely.geometry import shape as shapely_shape
    except ImportError as exc:  # noqa: BLE001
        raise RuntimeError(
            "GeoParquet 生成には pyarrow / shapely / pyproj が必要です。"
            "`pip install -r requirements.txt` を実行してください。"
        ) from exc
    return np, pa, pq, shapely, shapely_shape


def _crs_projjson() -> dict:
    from pyproj import CRS

    return CRS.from_epsg(config.SOURCE_EPSG).to_json_dict()


def _arrow_type(pa, kinds: set[str]):
    """テーマ内で観測した python 型の集合 -> Arrow 型。

    全国の全地物が null の項目（提供元で未記入の告示番号など）も、null 型ではなく
    文字列にする。null 型のカラムは GDAL / QGIS が扱えないことがあるため。
    """
    kinds = kinds - {"NoneType"}
    if not kinds:
        return pa.string()
    if kinds == {"bool"}:
        return pa.bool_()
    if kinds == {"int"}:
        return pa.int64()
    if kinds <= {"int", "float"}:
        return pa.float64()
    return pa.string()  # 文字列、または型が混在する項目は文字列に寄せる


def _is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))


def _to_python(value, target_is_string: bool):
    if value is None:
        return None
    if target_is_string and not isinstance(value, str):
        return json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)
    return value


class _ThemeAccumulator:
    """1テーマ分の地物を溜める。ジオメトリはファイル単位で WKB に落として GEOS を解放する。"""

    def __init__(self, np, shapely, shapely_shape):
        self._np = np
        self._shapely = shapely
        self._shape = shapely_shape
        self.wkb_chunks: list = []
        self.bounds_chunks: list = []
        self.props: dict[str, list] = {}
        self.prop_types: dict[str, set[str]] = {}
        self.geometry_types: set[str] = set()
        self.n = 0
        self.skipped = 0
        self._intern: dict = {}

    def _keep(self, value):
        """同じ値のオブジェクトを共有して、属性リストのメモリを抑える。"""
        if value is None or isinstance(value, (int, float, bool)):
            return value
        try:
            return self._intern.setdefault(value, value)
        except TypeError:  # unhashable（list / dict）はそのまま
            return value

    def add_file(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"    !! 読み込みスキップ {path}: {exc}")
            return
        features = data.get("features", []) if isinstance(data, dict) else []
        if not features:
            return

        geoms = []
        rows = []
        for feat in features:
            geom = feat.get("geometry")
            if not geom:
                self.skipped += 1
                continue
            try:
                geoms.append(self._shape(geom))
            except Exception as exc:  # noqa: BLE001
                print(f"    !! ジオメトリスキップ {path}: {exc}")
                self.skipped += 1
                continue
            self.geometry_types.add(geom.get("type"))
            rows.append(feat.get("properties") or {})
        if not geoms:
            return

        arr = self._np.empty(len(geoms), dtype=object)
        arr[:] = geoms
        self.wkb_chunks.append(self._shapely.to_wkb(arr, flavor="iso"))
        self.bounds_chunks.append(self._shapely.bounds(arr))

        base = self.n
        for offset, props in enumerate(rows):
            for key, value in props.items():
                column = self.props.get(key)
                if column is None:
                    # 途中から現れた項目は、それ以前の地物を null で埋めて長さを揃える
                    column = [None] * (base + offset)
                    self.props[key] = column
                    self.prop_types[key] = set()
                column.append(self._keep(value))
                self.prop_types[key].add(type(value).__name__)
            self.n += 1
            for key, column in self.props.items():
                if len(column) < self.n:
                    column.append(None)


def _build_table(pa, acc: _ThemeAccumulator, np):
    fields = []
    arrays = []
    for key in acc.props:
        arrow_type = _arrow_type(pa, acc.prop_types[key])
        as_string = pa.types.is_string(arrow_type)
        values = acc.props[key]
        if as_string:
            values = [_to_python(v, True) for v in values]
        arrays.append(pa.array(values, type=arrow_type))
        fields.append(pa.field(key, arrow_type))

    bounds = np.concatenate(acc.bounds_chunks) if acc.bounds_chunks else np.zeros((0, 4))
    bbox_fields = ["xmin", "ymin", "xmax", "ymax"]
    bbox_type = pa.struct([pa.field(n, pa.float64()) for n in bbox_fields])
    bbox = pa.StructArray.from_arrays(
        [pa.array(bounds[:, i], type=pa.float64()) for i in range(4)],
        names=bbox_fields,
    )
    arrays.append(bbox)
    fields.append(pa.field(BBOX_COLUMN, bbox_type))

    # ジオメトリは連結せず ChunkedArray のままにする。全国分の WKB は
    # binary 配列1本の上限（2GB）に近づくため、連結もコピーも避ける。
    wkb = pa.chunked_array([pa.array(chunk, type=pa.binary()) for chunk in acc.wkb_chunks], type=pa.binary())
    arrays.append(wkb)
    fields.append(pa.field(GEOMETRY_COLUMN, pa.binary()))

    table = pa.Table.from_arrays(arrays, schema=pa.schema(fields))
    layer_bbox = None
    if len(bounds) and np.isfinite(bounds).any():
        # 空ジオメトリの bbox は NaN になる。NaN は JSON に出せないので nan 無視で畳む。
        layer_bbox = [
            float(np.nanmin(bounds[:, 0])),
            float(np.nanmin(bounds[:, 1])),
            float(np.nanmax(bounds[:, 2])),
            float(np.nanmax(bounds[:, 3])),
        ]
        if not all(map(_is_finite, layer_bbox)):
            layer_bbox = None
    return table, layer_bbox


def _geo_metadata(geometry_types: Iterable[str], layer_bbox: Optional[list[float]]) -> dict:
    column: dict = {
        "encoding": "WKB",
        "geometry_types": sorted(t for t in geometry_types if t),
        "crs": _crs_projjson(),
        "edges": "planar",
        "covering": {
            "bbox": {
                "xmin": [BBOX_COLUMN, "xmin"],
                "ymin": [BBOX_COLUMN, "ymin"],
                "xmax": [BBOX_COLUMN, "xmax"],
                "ymax": [BBOX_COLUMN, "ymax"],
            }
        },
    }
    if layer_bbox:
        column["bbox"] = layer_bbox
    return {
        "version": GEOPARQUET_VERSION,
        "primary_column": GEOMETRY_COLUMN,
        "columns": {GEOMETRY_COLUMN: column},
    }


def _row_group_size(geometry_bytes: int, rows: int, requested: int) -> int:
    """行数の上限と、平均ジオメトリ量から見た行数（TARGET_ROW_GROUP_BYTES 相当）の小さい方。"""
    if rows <= 0 or geometry_bytes <= 0:
        return requested
    by_bytes = max(MIN_ROW_GROUP_SIZE, int(TARGET_ROW_GROUP_BYTES / (geometry_bytes / rows)))
    return max(1, min(requested, by_bytes))


def convert_theme(
    theme: str,
    files: list[Path],
    out: Path,
    *,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    compression: str = DEFAULT_COMPRESSION,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> Optional[dict]:
    np, pa, pq, shapely, shapely_shape = _require_deps()
    acc = _ThemeAccumulator(np, shapely, shapely_shape)
    for path in files:
        acc.add_file(path)
    if acc.n == 0:
        print(f"    !! {theme}: 地物が無いためスキップ")
        return None

    table, layer_bbox = _build_table(pa, acc, np)
    table = table.replace_schema_metadata(
        {"geo": json.dumps(_geo_metadata(acc.geometry_types, layer_bbox), ensure_ascii=False)}
    )
    rows_per_group = _row_group_size(table[GEOMETRY_COLUMN].nbytes, acc.n, row_group_size)
    out.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        table,
        out,
        compression=compression,
        compression_level=compression_level,
        row_group_size=rows_per_group,
        write_statistics=True,
    )
    if acc.skipped:
        print(f"    !! {theme}: ジオメトリ無し {acc.skipped} 件を除外")
    return {
        "kind": "theme",
        "theme": theme,
        "name": config.theme_name(theme),
        "parquet": out.name,
        "bytes": out.stat().st_size,
        "features": acc.n,
        "source_files": len(files),
        "geometry_types": sorted(t for t in acc.geometry_types if t),
        "bbox": layer_bbox,
    }


def convert(
    *,
    extract_dir: Optional[Path] = None,
    dist_dir: Optional[Path] = None,
    themes: Optional[list[str]] = None,
    row_group_size: int = DEFAULT_ROW_GROUP_SIZE,
    compression: str = DEFAULT_COMPRESSION,
    compression_level: int = DEFAULT_COMPRESSION_LEVEL,
) -> list[dict]:
    """テーマ別 GeoParquet を生成し、manifest 用の結果リストを返す。"""
    extract_dir = extract_dir or config.EXTRACT_DIR
    dist_dir = dist_dir or config.DIST_DIR
    dist_dir.mkdir(parents=True, exist_ok=True)
    groups = discover_by_theme(extract_dir)
    if themes:
        wanted = {t.lower() for t in themes}
        groups = {k: v for k, v in groups.items() if k in wanted}
    results: list[dict] = []
    for theme, files in sorted(groups.items(), key=lambda kv: config.theme_order(kv[0])):
        out = dist_dir / f"{theme}.parquet"
        print(f"[parquet] {theme} ({config.theme_name(theme)}): {len(files)} files -> {out.name}", flush=True)
        entry = convert_theme(
            theme,
            files,
            out,
            row_group_size=row_group_size,
            compression=compression,
            compression_level=compression_level,
        )
        if entry:
            print(f"    {entry['features']:,} features / {entry['bytes']/1048576:.1f} MB", flush=True)
            results.append(entry)
    return results
