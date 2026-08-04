"""QGIS 用一式（GeoParquet + QML + .qlr / .qgz）を1本の zip にまとめる。

Release に添付するファイルは 80 本を超えるため、「QGIS で全部見たい」人が
26 parquet + 26 qml + qgz + qlr を手で同じフォルダへ集める必要があった。
`.qgz` / `.qlr` / `.qml` はいずれも `./<テーマ>.parquet` という相対パス前提なので
（`qgis_project.py` 参照）、そもそも1フォルダに揃っていないと動かない。
そこで**解凍してできたフォルダの `toshikeikaku.qgz` を開けば完成状態**になる
zip を作り、Release に1本だけ足す。

  toshikeikaku-qgis.zip
    toshikeikaku/
      README.txt          使い方（Windows のメモ帳で読めるよう BOM + CRLF）
      toshikeikaku.qgz    これを開く
      toshikeikaku.qlr
      <テーマ>.parquet    × 26
      <テーマ>.qml        × 26

parquet と qgz は既に内部で圧縮済みなので無圧縮（store）で格納する。deflate を
掛けても数 % しか縮まないのに、586 MB を CI で舐める時間だけが増える。
タイムスタンプは `.qgz` と同じ理由で固定し、同じ入力から同じバイト列が出るようにする。
"""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Optional

from . import config
from .qgis_project import PROJECT_BASENAME, ZIP_EPOCH

# zip 内のトップレベルフォルダ名。解凍先を散らかさないために1段挟む。
BUNDLE_ROOT = PROJECT_BASENAME
BUNDLE_NAME = f"{PROJECT_BASENAME}-qgis.zip"
README_NAME = "README.txt"

_README = """\
都市計画決定GISデータ（全国） QGIS 用一式
=========================================

このフォルダは QGIS でそのまま開ける状態になっています。

■ 使い方
  1. このフォルダを丸ごと好きな場所に置く（中のファイルを個別に動かさないこと）
  2. toshikeikaku.qgz をダブルクリック、または QGIS の
     「プロジェクト > 開く」から選ぶ
  3. 26レイヤと背景地図（地理院タイル 淡色地図）が重ね順どおりに表示されます

  特定のテーマだけ見たいときは、<テーマ>.parquet を QGIS にドラッグ&ドロップ
  すれば、同じフォルダの同名 .qml が自動で当たって色分け表示されます。

■ 収録物
  toshikeikaku.qgz   QGIS プロジェクト（背景地図・重ね順・初期表示範囲つき）
  toshikeikaku.qlr   レイヤ定義。既存プロジェクトに D&D すると26レイヤが一括で入る
  <テーマ>.parquet   データ本体（GeoParquet。属性・座標は提供元のまま）
  <テーマ>.qml       スタイル。同じフォルダにあると QGIS が自動で適用する

■ 注意
  - QGIS 3.28 以降が必要です（GeoParquet の読み込みに GDAL の Parquet ドライバを使います）
  - .qgz / .qlr は ./<テーマ>.parquet を相対パスで参照しています。
    ファイルを別フォルダへ移すとレイヤが読めなくなります
  - 座標参照系は EPSG:6668（JGD2011 緯度経度）

■ 出典・生成元
  国土交通省 都市局「都市計画決定GISデータ」
  https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html
  変換: https://github.com/shiwaku/mlit-urban-planning-converter
"""


def build_readme(version: Optional[str] = None) -> bytes:
    """zip 同梱の README.txt。Windows の既定エディタで開くので BOM + CRLF。"""
    text = _README
    if version:
        text += f"  データ版: {version}\n"
    return text.replace("\n", "\r\n").encode("utf-8-sig")


def _members(themes: Optional[list[str]] = None) -> list[Path]:
    """zip に入れるファイル（dist/ 内）。存在しないものは呼び出し側で弾く。"""
    codes = themes or sorted(config.load_styles()["themes"], key=config.theme_order)
    paths = [
        config.DIST_DIR / f"{PROJECT_BASENAME}.qgz",
        config.DIST_DIR / f"{PROJECT_BASENAME}.qlr",
    ]
    for theme in codes:
        paths += [config.DIST_DIR / f"{theme}.parquet", config.DIST_DIR / f"{theme}.qml"]
    return paths


def build(
    *,
    themes: Optional[list[str]] = None,
    out_dir: Optional[Path] = None,
    version: Optional[str] = None,
) -> dict:
    """dist/toshikeikaku-qgis.zip を作り、内容の記録を返す。"""
    out_dir = out_dir or config.DIST_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    wanted = _members(themes)
    missing = [p.name for p in wanted if not p.exists()]
    present = [p for p in wanted if p.exists()]
    if not any(p.suffix == ".parquet" for p in present):
        raise FileNotFoundError(
            f"{config.DIST_DIR} に *.parquet がありません。先に parquet / qml を実行してください。"
        )

    zip_path = out_dir / BUNDLE_NAME
    with zipfile.ZipFile(zip_path, "w", allowZip64=True) as zf:
        info = zipfile.ZipInfo(f"{BUNDLE_ROOT}/{README_NAME}", date_time=ZIP_EPOCH)
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, build_readme(version))
        for path in present:
            info = zipfile.ZipInfo(f"{BUNDLE_ROOT}/{path.name}", date_time=ZIP_EPOCH)
            # テキスト（.qml / .qlr）だけ縮める。parquet / qgz は既に圧縮済み。
            info.compress_type = (
                zipfile.ZIP_DEFLATED if path.suffix in (".qml", ".qlr") else zipfile.ZIP_STORED
            )
            info.file_size = path.stat().st_size
            with path.open("rb") as src, zf.open(info, "w") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)

    result = {
        "file": BUNDLE_NAME,
        "root": BUNDLE_ROOT,
        "bytes": zip_path.stat().st_size,
        "entries": len(present) + 1,
        "themes": sum(1 for p in present if p.suffix == ".parquet"),
        "missing": missing,
    }
    print(
        f"bundle: {result['themes']} テーマ / {result['entries']} ファイル / "
        f"{result['bytes'] / 1048576:.1f} MB -> {zip_path}"
    )
    if missing:
        print(f"  !! dist/ に無く同梱できなかったファイル ({len(missing)}): {', '.join(missing)}")
    return result
