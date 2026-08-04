# 都市計画決定GISデータ PMTiles / GeoParquet パイプライン

国土交通省 都市局が公開する
**[都市計画決定GISデータ 全国データダウンロードページ](https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html)**
の全国 GeoJSON を自動でダウンロードし、テーマ別の **PMTiles**（地図描画用）と
**GeoParquet**（解析用）に変換して **GitHub Releases** で配信するためのツール群です。

- **DLツール** — ダウンロードページを毎回スクレイプし、47都道府県の GeoJSON zip を取得・展開
- **コンバーター** — GeoJSON → PMTiles（テーマ別 / 都道府県別を選択可）／ GeoParquet（テーマ別・全国統合）
- **QGIS スタイル** — テーマごとの配色を QML で同梱。GeoParquet の隣に置けば読み込むだけで色分け表示。
  26レイヤを正しい重ね順でまとめて開く `.qlr` / `.qgz` も配布
- **一括ダウンロード** — QGIS 用一式（GeoParquet 26テーマ + QML + `.qlr` / `.qgz`）を
  `toshikeikaku-qgis.zip` 1本で配布。解凍して `toshikeikaku.qgz` を開けば完成状態
- **バージョン管理** — 版ごとに GitHub Release を作成。**過去版はそのまま残る**
- **ワンクリック更新** — GitHub Actions の手動実行で 更新検知 → 変換 → 配信 を一括処理

> ⚠️ 本データは国土交通省が提供する**参考情報**です。概ねの位置を示すものであり、
> 建築確認等の公式手続に用いることは想定されていません。最新でない場合があります。
> 利用の際は必ず[提供元ページ](https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000087.html)の注記をご確認ください。

## データ構成

- 元データは 47都道府県 × 3形式（シェープファイル / CityGML / GeoJSON）。本パイプラインは **GeoJSON** を使用。
- zip 内は `都道府県/市区町村/<市区町村コード>_<テーマ>.geojson` 構造。
- テーマ（用途地域 `youto`、都市計画区域 `tokei`、区域区分 `senbiki` ほか全26種）と
  日本語名の対応は [`data/themes.json`](data/themes.json) を参照（出典: データ定義書）。
- 座標系は EPSG:6668（JGD2011 緯度経度、実用上 WGS84 と同等）。

生成物の一覧は [`CATALOG.md`](CATALOG.md)、版の履歴は
[`versions.json`](versions.json) にまとまります。

### 2つの出力形式

| | PMTiles | GeoParquet |
| --- | --- | --- |
| 用途 | Web 地図・QGIS での描画 | 集計・空間解析・他データとの結合 |
| 単位 | テーマ別 全国1ファイル（`youto.pmtiles`） | テーマ別 全国1ファイル（`youto.parquet`） |
| 座標・属性 | ズームに応じて間引き・量子化 | **元 GeoJSON のまま**（欠落なし） |
| 読み方 | MapLibre / QGIS / pmtiles CLI | DuckDB / GeoPandas / QGIS / Fiona 等 |

GeoParquet は **GeoParquet 1.1.0**（geometry = WKB、CRS = EPSG:6668 の PROJJSON）で書き出し、
空間絞り込み用に `bbox` struct カラム（covering）を付けています。圧縮は zstd、
行グループは最大 50,000 行、かつジオメトリがおおむね 64MB に収まる行数で区切るので、
DuckDB 等は範囲条件で不要な行グループを読み飛ばせます。

> ℹ️ ジオメトリは提供元 GeoJSON をそのまま WKB 化しています（簡略化・修復はしません）。
> このため、元データに含まれる自己交差等の**不正ジオメトリもそのまま残ります**
> （版 `20260707` で全 418,351 地物中 12 件）。解析前に `ST_MakeValid` 等の適用を検討してください。

## 収録テーマ（レイヤー）の説明

各テーマは都市計画法などの法令に基づき都市計画に定められる区域・地域地区・施設等です。
説明は各根拠法令の定義規定（条文）を基にした要約で、ビューアのレイヤー名横の **i ボタン**からも参照できます。

> 出典: 各説明文は [e-Gov 法令検索](https://laws.e-gov.go.jp/) に掲載の各法令
> （都市計画法、都市再生特別措置法、都市緑地法、古都保存法、密集市街地整備法、
> 土地区画整理法、特定空港周辺航空機騒音対策特別措置法、大規模災害からの復興に関する法律）の
> 条文を基に要約したものです。正確な定義は必ず原文をご確認ください。

| コード | テーマ | 説明（根拠法令） |
| --- | --- | --- |
| `tokei` | 都市計画区域 | 一体の都市として総合的に整備し、開発し、及び保全する必要がある区域（都市計画法第5条）。 |
| `jyuntoshi` | 準都市計画区域 | 都市計画区域外の区域のうち、相当数の建築物等の建築・敷地造成が現に行われ又は見込まれ、そのまま放置すれば将来における一体の都市としての整備、開発及び保全に支障が生じるおそれがあると認められる区域（都市計画法第5条の2）。 |
| `senbiki` | 区域区分 | 無秩序な市街化を防止し、計画的な市街化を図るため定める市街化区域と市街化調整区域との区分。市街化区域はすでに市街地を形成している区域及びおおむね10年以内に優先的かつ計画的に市街化を図るべき区域、市街化調整区域は市街化を抑制すべき区域（都市計画法第7条）。 |
| `ritteki` | 立地適正化計画区域 | 住宅及び都市機能増進施設の立地の適正化を図るために市町村が作成する計画の区域。居住を誘導する居住誘導区域、医療・福祉・商業等の施設を誘導する都市機能誘導区域を定める（都市再生特別措置法第81条）。 |
| `youto` | 用途地域 | 住居、商業、工業など市街地の土地利用の大枠を定める地域。第一種低層住居専用地域から工業専用地域まで13種類があり、種類ごとに建築物の用途・容積率・建蔽率等が制限される（都市計画法第8条・第9条）。 |
| `tkbt` | 特別用途地区 | 用途地域内の一定の地区における当該地区の特性にふさわしい土地利用の増進、環境の保護等の特別の目的の実現を図るため、用途地域の指定を補完して定める地区（都市計画法第9条）。 |
| `tokuteiyouto` | 特定用途制限地域 | 用途地域が定められていない土地の区域（市街化調整区域を除く）内において、その良好な環境の形成又は保持のため、当該地域の特性に応じて制限すべき特定の建築物等の用途の概要を定める地域（都市計画法第9条）。 |
| `tokuteiyuudou` | 特定用途誘導地区 | 立地適正化計画に記載された都市機能誘導区域のうち、誘導施設を有する建築物の建築を誘導する必要があると認められる区域に定める地区（都市再生特別措置法第109条）。 |
| `koudoti` | 高度地区 | 用途地域内において市街地の環境を維持し、又は土地利用の増進を図るため、建築物の高さの最高限度又は最低限度を定める地区（都市計画法第9条）。 |
| `koudori` | 高度利用地区 | 用途地域内の市街地における土地の合理的かつ健全な高度利用と都市機能の更新とを図るため、建築物の容積率の最高限度及び最低限度、建蔽率の最高限度、建築面積の最低限度並びに壁面の位置の制限を定める地区（都市計画法第9条）。 |
| `tokureiyouseki` | 特例容積率適用地区 | 適正な配置及び規模の公共施設を備えた土地の区域において、未利用となっている建築物の容積の活用を促進して土地の高度利用を図るため定める地区（都市計画法第9条）。 |
| `kousoujyukyo` | 高層住居誘導地区 | 住居と住居以外の用途とを適正に配分し、利便性の高い高層住宅の建設を誘導するため定める地区（都市計画法第9条）。 |
| `kyojyuchosei` | 居住調整地域 | 立地適正化計画の区域のうち、居住誘導区域外の区域で住宅地化を抑制すべき区域に定める地域（都市再生特別措置法第89条）。 |
| `bouka` | 防火地域・準防火地域 | 市街地における火災の危険を防除するため定める地域（都市計画法第9条）。地域内では建築物の構造が制限される（建築基準法第61条）。 |
| `tokuteibou` | 特定防災街区整備地区 | 密集市街地における特定防災機能の確保並びに土地の合理的かつ健全な利用を図るため定める地区（都市計画法第9条、密集市街地整備法第31条）。 |
| `fuuchichiku` | 風致地区 | 都市の風致を維持するため定める地区（都市計画法第9条）。地区内では建築、宅地の造成、木竹の伐採等が条例で規制される（同法第58条）。 |
| `ryokukachiiki` | 緑化地域 | 良好な都市環境の形成に必要な緑地が不足し、建築物の敷地内において緑化を推進する必要がある区域に定める地域（都市緑地法第34条）。 |
| `tokuryoku` | 特別緑地保全地区 | 都市における良好な自然的環境となる緑地（無秩序な市街地化の防止に必要な遮断地帯等、伝統的・文化的意義を有するもの、風致景観が優れ又は動植物の生息地等として保全が必要なもの）を保全するため定める地区（都市緑地法第12条）。 |
| `rekifuu` | 歴史的風土保存地区 | 古都における歴史的風土を保存するため、歴史的風土保存区域内の枢要な部分について都市計画に定める地区（古都保存法第6条）。 |
| `toshisaisei` | 都市再生特別地区 | 都市再生緊急整備地域のうち、都市の再生に貢献し、土地の合理的かつ健全な高度利用を図る特別の用途、容積、高さ、配列等の建築物の建築を誘導する必要があると認められる区域に定める地区（都市再生特別措置法第36条）。 |
| `chikukei` | 地区計画 | 建築物の建築形態、公共施設の配置等からみて、一体としてそれぞれの区域の特性にふさわしい態様を備えた良好な環境の各街区を整備し、開発し、及び保全するための計画（都市計画法第12条の5）。 |
| `tochiku` | 土地区画整理事業 | 都市計画区域内の土地について、公共施設の整備改善及び宅地の利用の増進を図るため行われる、土地の区画形質の変更及び公共施設の新設又は変更に関する事業（土地区画整理法第2条）。 |
| `kouen` | 公園 | 都市計画に都市施設として定められた公園（都市計画法第11条）。市民の休息・レクリエーションの場や、災害時の避難地等となるオープンスペース。 |
| `soubou` | 航空機騒音障害防止地区 | 特定空港の周辺において、航空機の騒音により生ずる障害を防止し、あわせて適正かつ合理的な土地利用を図るため定める地区（特定空港周辺航空機騒音対策特別措置法第4条）。 |
| `fukkousaiseikyoten` | 一団地の復興再生拠点市街地形成施設 | 大規模な災害を受けた地域における復興の拠点となる市街地を形成する一団地の住宅施設、特定業務施設又は公益的施設及び公共施設（大規模災害からの復興に関する法律）。 |
| `douro` | 都市計画道路 | 都市計画に都市施設として定められた道路（都市計画法第11条）。計画決定・事業中・整備済みの路線を含み、区域内では建築の制限がある（同法第53条・第54条）。 |

## ローカルでの実行

前提: Python 3.10+ / [tippecanoe](https://github.com/felt/tippecanoe)（PMTiles 出力対応版）。
tippecanoe が必要なのは `convert` のみで、`scrape` / `download` / `parquet` / `qml` は
Python だけで動きます（GeoParquet は pyarrow / shapely / pyproj を使用。`make setup` で入ります）。

```bash
make setup                         # venv 作成 + 依存インストール
make all                           # 全県: scrape→download→convert→parquet→qml→catalog

# 一部の県・テーマだけ試す
make download PREF="東京都"
make convert SPLIT=theme           # dist/*.pmtiles を生成
make parquet THEME="youto"         # dist/youto.parquet を生成
make qml                           # styles/ と dist/ に QGIS 用ファイルを生成
make bundle                        # dist/toshikeikaku-qgis.zip（QGIS 一式）を作成
make catalog
```

### 元データ（GeoJSON）だけ取得する

PMTiles 変換は行わず、提供元の GeoJSON を全国分ローカルに置きたい場合は
`download` だけを実行します（tippecanoe は不要）。

```bash
make setup                         # 初回のみ
make scrape                        # ダウンロードページを解析し dist/sources.json を最新化
make download                      # PREF 省略 = 47都道府県すべて（県ごとに1秒待機）
```

- `PREF` を**省略すると全県**が対象。`PREF="東京都 京都府"` のように空白区切りで県を絞れる。
- `scrape` は必須ではない（`sources.json` が無ければ `download` が内部で自動スクレイプする）が、
  手元の `sources.json` が古いと旧版の zip を取りにいくため、**取得前に実行しておくのが安全**。
- 既に取得済みで提供元の `content-ID` が変わっていない県は**スキップ**される。
  変更が無くても取り直したい場合は `--force` を付ける（`make download` は `--force` を
  渡せないので CLI を直接呼ぶ）:
  `PYTHONPATH=src .venv/bin/python3 -m tosiko_pmtiles.cli download --force`

取得後の配置（`raw/` は `.gitignore` 対象）:

```
raw/zip/<content_id>.zip
raw/extracted/<都道府県コード>_<都道府県>/<市区町村コード>_<市区町村名>/<市区町村コード>_<テーマ>.geojson
例: raw/extracted/13_東京都/13101_千代田区/13101_youto.geojson
```

全国分の容量目安（版 `20260707` 実測）: zip 47本で約 **750 MB**、
展開後は GeoJSON **8,173 ファイル**・約 **2.4 GB**。
取得結果（県ごとの URL・サイズ・sha256・GeoJSON 件数）は `dist/download.json` に記録されます。

主なコマンド（`python -m tosiko_pmtiles.cli <sub>`）:

| サブコマンド | 内容 |
| --- | --- |
| `scrape` | ダウンロードページ解析 → `dist/sources.json` |
| `download [--pref 東京都 ...] [--force]` | GeoJSON zip 取得・展開（`raw/`）。**既取得で内容が変わっていない県はスキップ**（`--force` で全再取得） |
| `convert [--split theme\|prefecture]` | PMTiles 生成（`dist/*.pmtiles`） |
| `parquet [--theme youto ...]` | GeoParquet 生成（`dist/*.parquet`）。テーマ別・全国統合 |
| `qml [--theme youto ...]` | QGIS 用スタイル生成。`*.qml`（レイヤ単位）と `toshikeikaku.qlr` / `.qgz`（26レイヤ + 重ね順）を `styles/` と `dist/` の両方へ |
| `bundle [--theme youto ...]` | QGIS 一式（`*.parquet` + `*.qml` + `.qlr` / `.qgz`）を `dist/toshikeikaku-qgis.zip` にまとめる。`parquet` と `qml` の後に実行 |
| `catalog` | `versions/manifest-<版>.json` / `versions.json` / `CATALOG.md` 生成 |
| `all` | 上記を一括実行（`--no-parquet` で GeoParquet を省略） |
| `check-update` | 更新有無を判定（CI 用、`--github-output` 対応） |

### 変換の粒度

- `--split theme`（既定）: テーマごとに 1 つの PMTiles（例 `youto.pmtiles`）。
  レイヤーには全都道府県の当該テーマ地物を統合。Web地図で必要テーマだけ読み込める。
- `--split prefecture`: 都道府県ごとに 1 つの PMTiles。テーマ = レイヤーのマルチレイヤー構成。
- GeoParquet は**テーマ別・全国統合のみ**（`--split` の対象外）。県で絞りたい場合は
  ファイル内の `Pref` 列で絞り込みます（DuckDB なら `WHERE Pref = '東京都'`）。

## 自動更新（GitHub Actions）

[`.github/workflows/update.yml`](.github/workflows/update.yml) が

1. **手動（`workflow_dispatch`）で起動**（Actions タブから実行。定期実行は行いません）
2. `check-update` で提供元の更新を検知（県ごとの `content-ID` の変化で判定。変更のあった県数も出力）
3. 変更があれば ダウンロード → 変換（PMTiles / GeoParquet / QML）→ カタログ生成。
   **ダウンロードは差分方式**: 前回の zip を Actions cache（`raw/zip`）から復元し、
   content-ID が変わった県だけ提供元から再取得します（提供元サーバーへの負荷も最小化）
4. `data-<YYYYMMDD>` タグの **Release** を作成し、`*.pmtiles` / `*.parquet` /
   `*.qml` / `*.qlr` / `*.qgz` / `toshikeikaku-qgis.zip`（QGIS 一式）と `manifest.json` を添付
5. `versions/`・`versions.json`・`CATALOG.md`・`styles/` をコミット

を実行します。PMTiles / GeoParquet バイナリは git には置かず Release アセットとして
管理するため、**過去の版は過去の Release として保持**されます。

## 生成データ（PMTiles / GeoParquet）の入手 — GitHub Releases

生成された PMTiles・GeoParquet は **git リポジトリの中には入っていません**（`git clone` しても
`*.pmtiles` / `*.parquet` は含まれません）。**GitHub Releases** に版ごとに添付して配布しています。
QGIS 用ファイル（`styles/` の `*.qml` / `*.qlr` / `*.qgz`）だけは小さいのでリポジトリにも入っています。

### GitHub Releases とは

GitHub がリポジトリごとに提供している**ファイル配布機能**です。git のタグ
（ある時点のスナップショットの目印）に、タイトル・説明文・**添付ファイル（Assets）**を
付けて公開できます。ソースコードのように差分管理されるものではなく、
「この版の完成品一式」を棚に並べるイメージです。

本プロジェクトで使い分けは次のとおりです。

| 置き場 | 内容 | 理由 |
| --- | --- | --- |
| git リポジトリ | 変換コード・`versions.json`（版の台帳）・`CATALOG.md`・`styles/`（QGIS 用ファイル） | テキストで差分管理に向く |
| **GitHub Releases** | `*.pmtiles` 全26テーマ + `*.parquet` 全26テーマ + `*.qml` + `*.qlr` / `*.qgz` + **`toshikeikaku-qgis.zip`（QGIS 一式）** + `manifest.json` | 合計 GB 級のバイナリ。git に置くと履歴が肥大化し、100MB 超は GitHub が拒否。Releases は1ファイル2GBまで・帯域無料 |

### リポジトリからの辿り方

1. リポジトリのトップページ https://github.com/shiwaku/mlit-urban-planning-converter を開く
2. **右サイドバー**の「**Releases**」欄（`Latest` バッジ付き）をクリック
   - 見当たらない場合は URL 末尾に `/releases` を付ける →
     https://github.com/shiwaku/mlit-urban-planning-converter/releases
3. リリース（例: `都市計画決定GISデータ 20260707`）の「**Assets**」を展開
4. `youto.pmtiles` / `youto.parquet` などをクリックするとダウンロードされる

Assets は 80本を超えるため、**QGIS で全テーマ見たいだけなら
`toshikeikaku-qgis.zip` 1本だけ**落とせば済みます（後述）。
1ファイルずつ選ぶのは「特定テーマだけ欲しい」場合の使い方です。

### URL の使い方

```bash
# 常に最新版を指す固定 URL（releases/latest/download/<ファイル名>）
https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download/toshikeikaku-qgis.zip
https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download/youto.pmtiles
https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download/youto.parquet
https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download/youto.qml

# 特定の版に固定したい場合（releases/download/<タグ>/<ファイル名>）
https://github.com/shiwaku/mlit-urban-planning-converter/releases/download/data-20260707/youto.pmtiles
```

- データ更新のたびに `data-<YYYYMMDD>` という新しいリリースが追加され、
  `latest` は自動的に新版を指すようになります。**過去の版のリリースはそのまま残る**ため、
  タグ指定 URL は再現性のある固定参照として使えます
- 収録ファイルの一覧・サイズは [`CATALOG.md`](CATALOG.md)、
  版の履歴は [`versions.json`](versions.json) を参照してください
- QGIS ではこの URL をそのまま PMTiles ソースとして指定できます

### まとめて落としたいとき

**PMTiles は落とさずに使うのが基本**です（上の URL を Web地図や QGIS のソースに
そのまま指定でき、必要なタイルだけ HTTP Range で取得されます）。
セルフホストやオフライン利用で実体が必要な場合は、[GitHub CLI](https://cli.github.com/)
のパターン指定で一括取得できます。

```bash
gh release download data-20260707 -R shiwaku/mlit-urban-planning-converter -p '*.pmtiles'
gh release download data-20260707 -R shiwaku/mlit-urban-planning-converter -p '*.parquet' -p '*.qml'
```

- タグを省略すると最新リリースが対象になります
- ブラウザだけで済ませたい・QGIS で開きたい場合は次の zip が早いです

## QGIS での利用 — 一括 zip（推奨）

**[`toshikeikaku-qgis.zip`](https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download/toshikeikaku-qgis.zip)**（約 586 MB）を落として解凍し、
できた `toshikeikaku/` フォルダの **`toshikeikaku.qgz` を開くだけ**で、
26レイヤ + 背景地図（地理院タイル 淡色地図）が重ね順どおりに表示されます。

```
toshikeikaku/
├─ README.txt          使い方
├─ toshikeikaku.qgz    ← これを開く（背景地図・重ね順・初期表示範囲つき）
├─ toshikeikaku.qlr    既存プロジェクトに D&D すると26レイヤが一括で入る
├─ youto.parquet       データ本体 …… 全26テーマ
├─ youto.qml           スタイル（QGIS が自動適用）
└─ …
```

- 中身は下の「GeoParquet + QML」を**全部揃えた状態**です。`.qgz` / `.qlr` は
  `./<テーマ>.parquet` を相対パスで参照しているので、**フォルダごと**扱ってください
- 前提は同じく **QGIS 3.28 以降**（GDAL の Parquet ドライバ）
- 手元で作り直す場合は `make bundle`（`make parquet` と `make qml` の後）

## QGIS での利用 — GeoParquet + QML（テーマ単位）

特定テーマだけ使うときは、`<テーマ>.parquet` と `<テーマ>.qml` を
**同じフォルダに並べて置く**のがポイントです。
QGIS が自動適用するのは、データファイルと**同じディレクトリにある同名の `.qml`** だけです
（`youto.parquet` → 同じフォルダの `youto.qml`）。並べて置けば、parquet をドラッグ&ドロップ
した時点で用途地域が色分け表示され、属性テーブルも和名になります。

```bash
mkdir -p toshikeikaku && cd toshikeikaku
BASE=https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download
curl -L -O "$BASE/youto.parquet"
curl -L -O "$BASE/youto.qml"     # ← 同じフォルダに置く
# あとは youto.parquet を QGIS にドラッグ&ドロップするだけ
```

- 前提: **QGIS 3.28 以降**（GDAL の Parquet ドライバが必要）。
  「レイヤ > レイヤを追加 > ベクタレイヤの追加」からでも読み込めます
- QML には次が入っています
  - **配色**: 用途地域は `YoutoCode`（13区分）、区域区分・防火地域・立地適正化計画区域は
    `AreaType` によるカテゴリ分け。その他のテーマは単一シンボル。
    レイヤ不透明度は 0.5（下の地理院タイル等が透ける）
  - **フィールド別名**: `Pref` → 都道府県、`FAR` → 容積率 など（データ定義書に準拠）
- 配色は Web ビューアと同じ [`data/styles.json`](data/styles.json) から生成しているので、
  ビューアと QGIS で見た目が揃います。色を変えたい場合は QGIS 上で編集するか、
  `data/styles.json` を直して `make qml` で作り直してください
- リポジトリ内の [`styles/`](styles/) にも同じ QML が入っています（Release からの取得が面倒な場合はこちら）
- **ローカルで生成した場合**は `make qml` が `styles/`（コミット対象の正本）と
  `dist/`（生成した parquet の隣）の両方に書くので、`dist/youto.parquet` をそのまま
  QGIS に放り込めばスタイルが当たります

### 26テーマをまとめて・正しい重ね順で開く — QLR / QGZ

QML はレイヤ1枚のスタイルしか持てないため、**レイヤの重ね順は制御できません**。
順序まで含めて配布するために、次の2つも同梱しています。

| ファイル | 中身 | 使い方 |
| --- | --- | --- |
| `toshikeikaku.qlr` | 26レイヤ + スタイル + 重ね順 | QGIS に D&D。**いま開いているプロジェクトに追加**される |
| `toshikeikaku.qgz` | 上記 + 背景地図（地理院タイル 淡色地図）+ プロジェクト CRS + 初期表示範囲 | ダブルクリックで開く。**新しいプロジェクトとして完成状態** |

26テーマすべてを揃えるなら
[一括 zip](#qgis-での利用--一括-zip推奨) を落とすのが早いです。以下は
**一部のテーマだけ**手で揃える場合の例です。

```bash
mkdir -p toshikeikaku && cd toshikeikaku
BASE=https://github.com/shiwaku/mlit-urban-planning-converter/releases/latest/download
for t in youto tokei senbiki douro; do curl -L -O "$BASE/$t.parquet"; done
curl -L -O "$BASE/toshikeikaku.qgz"
# toshikeikaku.qgz をダブルクリック
```

- 重ね順は Web ビューアと同じ [`data/styles.json`](data/styles.json) の `drawOrder` から
  生成しています（都市計画区域が最背面 → 用途地域が中位 → 都市計画道路が最前面）
- **データソースは相対パス**（`./youto.parquet`）なので、`.qlr` / `.qgz` は
  parquet と同じフォルダに置いてください
- 初期表示は**用途地域のみ ON**（26枚すべて描くと重いため）。他はレイヤパネルで
  チェックを入れれば、正しい重ね順のまま表示されます
- 手元に無いテーマの parquet があってもレイヤが「見つかりません」になるだけで、
  他のレイヤは正常に開きます

### DuckDB / GeoPandas から使う

```sql
INSTALL spatial; LOAD spatial;   -- geometry が GEOMETRY('EPSG:6668') 型として読める

-- 属性で絞って集計する（空間拡張なしでも動く）
SELECT YoutoName, count(*) AS n FROM 'youto.parquet'
WHERE Pref = '東京都' GROUP BY YoutoName ORDER BY n DESC;

-- bbox カラム（covering）で範囲を絞る。不要な行グループを読み飛ばせる
SELECT Cityname, YoutoName FROM 'youto.parquet'
WHERE bbox.xmin < 139.78 AND bbox.xmax > 139.74
  AND bbox.ymin < 35.69 AND bbox.ymax > 35.67;

-- ある地点の用途地域を引く（東京駅 → 千代田区・商業地域・容積率900%・建蔽率80%）
SELECT Cityname, YoutoName, FAR, BCR FROM 'youto.parquet'
WHERE ST_Intersects(geometry, ST_Point(139.7671, 35.6812));
```

```python
# GeoPandas
import geopandas as gpd
gdf = gpd.read_parquet("youto.parquet")            # CRS は EPSG:6668 が入っている
tokyo = gpd.read_parquet("youto.parquet", filters=[("Pref", "==", "東京都")])
```

面積を求めるときは、平面直角座標系（東京なら `EPSG:6677`）に変換してから `ST_Area` を使います。
このとき **`always_xy := true` が必須**です。EPSG:6668 は EPSG 定義上の軸順が緯度→経度である一方、
GeoParquet の座標は仕様どおり経度→緯度で格納されているため、指定しないと結果が `inf` / `NaN` になります。

```sql
-- 東京都の商業地域の合計面積（7,404.3 ha）
SELECT round(sum(ST_Area(ST_Transform(geometry, 'EPSG:6668', 'EPSG:6677', always_xy := true)))/10000, 1) AS ha
FROM 'youto.parquet' WHERE Pref = '東京都' AND YoutoCode = 10;
```

## Web 地図での利用

> ⚠️ Release アセットは CORS ヘッダを返さないため、ブラウザから直接 fetch（Range 取得）はできません。
> Web 地図に組み込む場合は PMTiles を自分のホスト（同一オリジン）へ配置してください
> （本プロジェクトのビューアも、デプロイ時に Release から PMTiles をコピーして同一オリジンで配信しています）。

### ビューア（`viewer/`）— 全国都市計画GISビューワ

MapLibre GL JS + [pmtiles](https://github.com/protomaps/PMTiles) + 国土地理院 最適化ベクトルタイルの
モダンなビューア（Vite + TypeScript / ライト・ダークテーマ）を同梱しています。
用途地域などの配色は [全国都市計画GISビューア](https://toshikeikaku-info.jp/) を参考にしています。

#### 用途地域スタンプ

都市計画総括図と同じ円形3段のスタンプで、用途地域の指定内容を地図上に直接表示します
（用途地域レイヤーの「用途地域スタンプ表示」で切替、ズーム13以上）。

| 段 | 内容 | 属性 |
| --- | --- | --- |
| 上段 | 容積率(%) | `FAR` |
| 中段 | 用途地域名（略称） | `YoutoCode` |
| 下段 | 建蔽率(%) | `BCR` |

- 枠は [custom-smartmap-other-sprite](https://github.com/geolonia/custom-smartmap-other-sprite) の
  `用途地域スタンプ`（150×150、罫線 y=46 / y=103）を使用。MapLibre のスプライト複数指定で
  国土地理院スタイルのスプライトと併用しています（`smartmap:用途地域スタンプ`）。
- 中身は組み合わせごとに焼いた画像ではなく、属性からテキスト式で描いています。全国では
  （用途地域13種 × 容積率19種 × 建蔽率7種）の組み合わせが数百通りに達するためです。
- 中段の略称は最大4字（`1種低住` `1種中高` `準住居` `田園住居` `近隣商業` `準工` `工業専用` など）。
  正式名称はクリック時のポップアップで確認できます。

```bash
cd viewer
npm install
npm run dev      # http://localhost:8000（dev サーバーが ../dist/*.pmtiles を Range 配信）
```

**公開**: [`.github/workflows/pages.yml`](.github/workflows/pages.yml) が最新 Release の PMTiles を
ビューアに同梱して GitHub Pages へデプロイします（同一オリジン配信）。
公開先 → https://shiwaku.github.io/mlit-urban-planning-converter/

## ディレクトリ構成

```
src/tosiko_pmtiles/   スクレイプ・DL・変換・カタログのコード
  convert.py            GeoJSON → PMTiles（tippecanoe）
  geoparquet.py         GeoJSON → GeoParquet（pyarrow + shapely）
  qml.py                data/styles.json → QGIS スタイル（*.qml）
  qgis_project.py       data/styles.json → QGIS プロジェクト（*.qlr / *.qgz）
data/themes.json      テーマコード → 日本語名
data/styles.json      配色・属性和名（ビューアと QML の共通の出所）
styles/               生成された QGIS スタイル（*.qml / *.qlr / *.qgz、コミット対象の正本）
versions/             版ごとの manifest（監査証跡・コミット対象）
versions.json         版の履歴インデックス
viewer/               MapLibre + PMTiles ビューア（Vite + TypeScript）
raw/ dist/            中間・出力物（.gitignore、コミットしない）
                      dist/ には *.pmtiles / *.parquet と、その隣に置く QGIS 用ファイルの複製が入る
```

> 配色を変えるときは `data/styles.json` を直します。ビューア（`viewer/src/layers.ts`）は
> これを直接 import し、QGIS 用 QML は `make qml` で再生成されるので、両者がずれません。

## ライセンス / 出典

- コード: MIT（[LICENSE](LICENSE)）
- データ: 国土交通省 都市局「都市計画決定GISデータ」。利用時は出典を明記してください。
