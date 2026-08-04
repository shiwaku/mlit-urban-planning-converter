# データカタログ

- 最新版: **20260707**（タグ `data-20260707`）
- 生成日時: 2026-08-04T09:05:18+00:00
- 出典: 国土交通省 都市局「都市計画決定GISデータ」 https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html
- 分割方式: `theme`
- 座標参照系: EPSG:6668

## PMTiles（地図描画用）

| ファイル | 名称 | サイズ | ソース数 |
| --- | --- | --- | --- |
| `youto.pmtiles` | 用途地域 | 4.3 MB | 52 |
| `tokei.pmtiles` | 都市計画区域 | 0.9 MB | 57 |
| `senbiki.pmtiles` | 区域区分 | 0.9 MB | 51 |
| `ritteki.pmtiles` | 立地適正化計画区域 | 0.3 MB | 7 |
| `koudoti.pmtiles` | 高度地区 | 2.7 MB | 50 |
| `koudori.pmtiles` | 高度利用地区 | 0.0 MB | 11 |
| `bouka.pmtiles` | 防火地域・準防火地域 | 1.5 MB | 51 |
| `tkbt.pmtiles` | 特別用途地区 | 0.2 MB | 19 |
| `fuuchichiku.pmtiles` | 風致地区 | 0.0 MB | 8 |
| `ryokukachiiki.pmtiles` | 緑化地域 | 0.0 MB | 1 |
| `tokuryoku.pmtiles` | 特別緑地保全地区 | 0.1 MB | 23 |
| `kousoujyukyo.pmtiles` | 高層住居誘導地区 | 0.0 MB | 1 |
| `tokureiyouseki.pmtiles` | 特例容積率適用地区 | 0.0 MB | 1 |
| `toshisaisei.pmtiles` | 都市再生特別地区 | 0.0 MB | 1 |
| `chikukei.pmtiles` | 地区計画 | 0.3 MB | 7 |
| `tochiku.pmtiles` | 土地区画整理事業 | 0.1 MB | 10 |
| `douro.pmtiles` | 都市計画道路 | 0.1 MB | 1 |
| `kouen.pmtiles` | 公園 | 0.1 MB | 4 |
| `tokuteibou.pmtiles` | tokuteibou | 0.0 MB | 4 |

## GeoParquet（解析用・属性と座標は元データのまま）

同名の QML（`styles/<テーマ>.qml`）を隣に置くと QGIS が配色を自動適用します。

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

