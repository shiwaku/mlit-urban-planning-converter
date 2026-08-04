# データカタログ

- 最新版: **20260707**（タグ `data-20260707`）
- 生成日時: 2026-08-04T11:14:22+00:00
- 出典: 国土交通省 都市局「都市計画決定GISデータ」 https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html
- 分割方式: `theme`
- 座標参照系: EPSG:6668

## 一括ダウンロード（QGIS 用一式）

GeoParquet 全テーマ + QML + `.qlr` / `.qgz` を1本にまとめた zip です。
解凍してできたフォルダの `toshikeikaku.qgz` を開くと、26レイヤが重ね順どおりに表示されます。

| ファイル | 内容 | サイズ |
| --- | --- | --- |
| `toshikeikaku-qgis.zip` | GeoParquet 26テーマ + QML + `.qlr` / `.qgz` （55 ファイル） | 585.5 MB |

## PMTiles（地図描画用）

| ファイル | 名称 | サイズ | ソース数 |
| --- | --- | --- | --- |
| `youto.pmtiles` | 用途地域 | 61.3 MB | 1215 |
| `tokei.pmtiles` | 都市計画区域 | 37.1 MB | 1373 |
| `jyuntoshi.pmtiles` | 準都市計画区域 | 0.4 MB | 25 |
| `senbiki.pmtiles` | 区域区分 | 32.2 MB | 637 |
| `ritteki.pmtiles` | 立地適正化計画区域 | 31.4 MB | 582 |
| `koudoti.pmtiles` | 高度地区 | 10.4 MB | 214 |
| `koudori.pmtiles` | 高度利用地区 | 0.6 MB | 231 |
| `bouka.pmtiles` | 防火地域・準防火地域 | 7.1 MB | 581 |
| `tkbt.pmtiles` | 特別用途地区 | 3.8 MB | 337 |
| `tokuteiyouto.pmtiles` | 特定用途制限地域 | 3.2 MB | 77 |
| `tokuteiyuudou.pmtiles` | 特定用途誘導地区 | 0.0 MB | 6 |
| `fuuchichiku.pmtiles` | 風致地区 | 3.4 MB | 185 |
| `ryokukachiiki.pmtiles` | 緑化地域 | 0.4 MB | 4 |
| `tokuryoku.pmtiles` | 特別緑地保全地区 | 0.4 MB | 80 |
| `kousoujyukyo.pmtiles` | 高層住居誘導地区 | 0.0 MB | 1 |
| `kyojyuchosei.pmtiles` | 居住調整地域 | 0.0 MB | 1 |
| `tokureiyouseki.pmtiles` | 特例容積率適用地区 | 0.0 MB | 2 |
| `tokuteibou.pmtiles` | 特定防災街区整備地区 | 0.0 MB | 8 |
| `rekifuu.pmtiles` | 歴史的風土保存地区 | 0.3 MB | 7 |
| `toshisaisei.pmtiles` | 都市再生特別地区 | 0.1 MB | 14 |
| `chikukei.pmtiles` | 地区計画 | 8.3 MB | 601 |
| `tochiku.pmtiles` | 土地区画整理事業 | 6.4 MB | 485 |
| `douro.pmtiles` | 都市計画道路 | 32.1 MB | 785 |
| `kouen.pmtiles` | 公園 | 13.7 MB | 716 |
| `soubou.pmtiles` | 航空機騒音障害防止地区 | 0.1 MB | 5 |
| `fukkousaiseikyoten.pmtiles` | 一団地の復興再生拠点市街地形成施設 | 0.0 MB | 1 |

## GeoParquet（QGIS・解析用。属性と座標は元データのまま）

Release には個別添付せず、**上の zip に同梱**しています（同名の QML も隣に入っているので、QGIS に読み込むだけで配色が当たります）。

| ファイル | 名称 | サイズ | 地物数 |
| --- | --- | --- | --- |
| `youto.parquet` | 用途地域 | 127.1 MB | 102,159 |
| `tokei.parquet` | 都市計画区域 | 85.1 MB | 10,279 |
| `jyuntoshi.parquet` | 準都市計画区域 | 1.2 MB | 41 |
| `senbiki.parquet` | 区域区分 | 77.9 MB | 7,259 |
| `ritteki.parquet` | 立地適正化計画区域 | 79.1 MB | 9,675 |
| `koudoti.parquet` | 高度地区 | 25.2 MB | 18,460 |
| `koudori.parquet` | 高度利用地区 | 0.4 MB | 969 |
| `bouka.parquet` | 防火地域・準防火地域 | 16.1 MB | 9,931 |
| `tkbt.parquet` | 特別用途地区 | 10.7 MB | 10,254 |
| `tokuteiyouto.parquet` | 特定用途制限地域 | 8.7 MB | 1,639 |
| `tokuteiyuudou.parquet` | 特定用途誘導地区 | 0.0 MB | 29 |
| `fuuchichiku.parquet` | 風致地区 | 8.3 MB | 2,155 |
| `ryokukachiiki.parquet` | 緑化地域 | 1.2 MB | 217 |
| `tokuryoku.parquet` | 特別緑地保全地区 | 0.7 MB | 687 |
| `kousoujyukyo.parquet` | 高層住居誘導地区 | 0.0 MB | 1 |
| `kyojyuchosei.parquet` | 居住調整地域 | 0.1 MB | 4 |
| `tokureiyouseki.parquet` | 特例容積率適用地区 | 0.0 MB | 2 |
| `tokuteibou.parquet` | 特定防災街区整備地区 | 0.0 MB | 14 |
| `rekifuu.parquet` | 歴史的風土保存地区 | 0.7 MB | 77 |
| `toshisaisei.parquet` | 都市再生特別地区 | 0.0 MB | 95 |
| `chikukei.parquet` | 地区計画 | 15.7 MB | 10,886 |
| `tochiku.parquet` | 土地区画整理事業 | 12.6 MB | 6,522 |
| `douro.parquet` | 都市計画道路 | 93.8 MB | 185,782 |
| `kouen.parquet` | 公園 | 20.8 MB | 41,161 |
| `soubou.parquet` | 航空機騒音障害防止地区 | 0.0 MB | 51 |
| `fukkousaiseikyoten.parquet` | 一団地の復興再生拠点市街地形成施設 | 0.0 MB | 2 |

## 収録都道府県

47 都道府県

