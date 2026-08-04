import type {
  ExpressionSpecification,
  FillLayerSpecification,
  LineLayerSpecification,
  SymbolLayerSpecification,
} from 'maplibre-gl'
// 配色・属性和名はリポジトリ直下の data/styles.json が唯一の出所。
// QGIS 用 QML（styles/*.qml）も同じファイルから生成されるので、色を変えるときはここではなく JSON を直す。
import stylesJson from '../../data/styles.json'

export type Geom = 'fill' | 'line'

export interface ThemeDef {
  /** テーマコード。PMTiles ファイル名・source-layer 名と一致する。 */
  key: string
  /** 表示名（日本語） */
  name: string
  geom: Geom
  /** 初期表示 ON/OFF */
  on: boolean
  /** 不透明度（未指定は既定値）。UI のスライダーで変更される。 */
  opacity?: number
  /** レイヤーの説明（パネルの i ボタンで表示） */
  desc: string
}

/** テーマ既定の不透明度。全テーマ一律（スライダーで個別に変更可能）。 */
export function defaultOpacity(_def: ThemeDef): number {
  return stylesJson.defaultOpacity
}
export function opacityOf(def: ThemeDef): number {
  return def.opacity ?? defaultOpacity(def)
}

/**
 * 描画対象テーマ（全26種）。パネルの並び順（先頭＝一番上）。
 * desc は各根拠法令の定義規定（e-Gov 法令検索 https://laws.e-gov.go.jp/ 掲載の条文）を基にした要約。
 * README の「収録テーマ（レイヤー）の説明」と同内容（変更時は両方を更新すること）。
 * 広域な区域（都市計画区域）を上に、用途地域を中位、細かい地区・線（都市計画道路）を下に置く。
 * 地図の描画順は main.ts の addDataLayers がこの配列順に addLayer するため、
 * **配列末尾ほど地図で最前面**（都市計画区域が最背面、都市計画道路が最前面）になる。
 */
export const THEMES: ThemeDef[] = [
  { key: 'tokei', name: '都市計画区域', geom: 'fill', on: false,
    desc: '一体の都市として総合的に整備し、開発し、及び保全する必要がある区域（都市計画法第5条）。' },
  { key: 'jyuntoshi', name: '準都市計画区域', geom: 'fill', on: false,
    desc: '都市計画区域外の区域のうち、相当数の建築物等の建築・敷地造成が現に行われ又は見込まれ、そのまま放置すれば将来における一体の都市としての整備、開発及び保全に支障が生じるおそれがあると認められる区域（都市計画法第5条の2）。' },
  { key: 'senbiki', name: '区域区分', geom: 'fill', on: false,
    desc: '無秩序な市街化を防止し、計画的な市街化を図るため定める市街化区域と市街化調整区域との区分。市街化区域はすでに市街地を形成している区域及びおおむね10年以内に優先的かつ計画的に市街化を図るべき区域、市街化調整区域は市街化を抑制すべき区域（都市計画法第7条）。' },
  { key: 'ritteki', name: '立地適正化計画区域', geom: 'fill', on: false,
    desc: '住宅及び都市機能増進施設の立地の適正化を図るために市町村が作成する計画の区域。居住を誘導する居住誘導区域、医療・福祉・商業等の施設を誘導する都市機能誘導区域を定める（都市再生特別措置法第81条）。' },
  { key: 'youto', name: '用途地域', geom: 'fill', on: true,
    desc: '住居、商業、工業など市街地の土地利用の大枠を定める地域。第一種低層住居専用地域から工業専用地域まで13種類があり、種類ごとに建築物の用途・容積率・建蔽率等が制限される（都市計画法第8条・第9条）。' },
  { key: 'tkbt', name: '特別用途地区', geom: 'fill', on: false,
    desc: '用途地域内の一定の地区における当該地区の特性にふさわしい土地利用の増進、環境の保護等の特別の目的の実現を図るため、用途地域の指定を補完して定める地区（都市計画法第9条）。' },
  { key: 'tokuteiyouto', name: '特定用途制限地域', geom: 'fill', on: false,
    desc: '用途地域が定められていない土地の区域（市街化調整区域を除く）内において、その良好な環境の形成又は保持のため、当該地域の特性に応じて制限すべき特定の建築物等の用途の概要を定める地域（都市計画法第9条）。' },
  { key: 'tokuteiyuudou', name: '特定用途誘導地区', geom: 'fill', on: false,
    desc: '立地適正化計画に記載された都市機能誘導区域のうち、誘導施設を有する建築物の建築を誘導する必要があると認められる区域に定める地区（都市再生特別措置法第109条）。' },
  { key: 'koudoti', name: '高度地区', geom: 'fill', on: false,
    desc: '用途地域内において市街地の環境を維持し、又は土地利用の増進を図るため、建築物の高さの最高限度又は最低限度を定める地区（都市計画法第9条）。' },
  { key: 'koudori', name: '高度利用地区', geom: 'fill', on: false,
    desc: '用途地域内の市街地における土地の合理的かつ健全な高度利用と都市機能の更新とを図るため、建築物の容積率の最高限度及び最低限度、建蔽率の最高限度、建築面積の最低限度並びに壁面の位置の制限を定める地区（都市計画法第9条）。' },
  { key: 'tokureiyouseki', name: '特例容積率適用地区', geom: 'fill', on: false,
    desc: '適正な配置及び規模の公共施設を備えた土地の区域において、未利用となっている建築物の容積の活用を促進して土地の高度利用を図るため定める地区（都市計画法第9条）。' },
  { key: 'kousoujyukyo', name: '高層住居誘導地区', geom: 'fill', on: false,
    desc: '住居と住居以外の用途とを適正に配分し、利便性の高い高層住宅の建設を誘導するため定める地区（都市計画法第9条）。' },
  { key: 'kyojyuchosei', name: '居住調整地域', geom: 'fill', on: false,
    desc: '立地適正化計画の区域のうち、居住誘導区域外の区域で住宅地化を抑制すべき区域に定める地域（都市再生特別措置法第89条）。' },
  { key: 'bouka', name: '防火地域・準防火地域', geom: 'fill', on: false,
    desc: '市街地における火災の危険を防除するため定める地域（都市計画法第9条）。地域内では建築物の構造が制限される（建築基準法第61条）。' },
  { key: 'tokuteibou', name: '特定防災街区整備地区', geom: 'fill', on: false,
    desc: '密集市街地における特定防災機能の確保並びに土地の合理的かつ健全な利用を図るため定める地区（都市計画法第9条、密集市街地整備法第31条）。' },
  { key: 'fuuchichiku', name: '風致地区', geom: 'fill', on: false,
    desc: '都市の風致を維持するため定める地区（都市計画法第9条）。地区内では建築、宅地の造成、木竹の伐採等が条例で規制される（同法第58条）。' },
  { key: 'ryokukachiiki', name: '緑化地域', geom: 'fill', on: false,
    desc: '良好な都市環境の形成に必要な緑地が不足し、建築物の敷地内において緑化を推進する必要がある区域に定める地域（都市緑地法第34条）。' },
  { key: 'tokuryoku', name: '特別緑地保全地区', geom: 'fill', on: false,
    desc: '都市における良好な自然的環境となる緑地（無秩序な市街地化の防止に必要な遮断地帯等、伝統的・文化的意義を有するもの、風致景観が優れ又は動植物の生息地等として保全が必要なもの）を保全するため定める地区（都市緑地法第12条）。' },
  { key: 'rekifuu', name: '歴史的風土保存地区', geom: 'fill', on: false,
    desc: '古都における歴史的風土を保存するため、歴史的風土保存区域内の枢要な部分について都市計画に定める地区（古都保存法第6条）。' },
  { key: 'toshisaisei', name: '都市再生特別地区', geom: 'fill', on: false,
    desc: '都市再生緊急整備地域のうち、都市の再生に貢献し、土地の合理的かつ健全な高度利用を図る特別の用途、容積、高さ、配列等の建築物の建築を誘導する必要があると認められる区域に定める地区（都市再生特別措置法第36条）。' },
  { key: 'chikukei', name: '地区計画', geom: 'fill', on: false,
    desc: '建築物の建築形態、公共施設の配置等からみて、一体としてそれぞれの区域の特性にふさわしい態様を備えた良好な環境の各街区を整備し、開発し、及び保全するための計画（都市計画法第12条の5）。' },
  { key: 'tochiku', name: '土地区画整理事業', geom: 'fill', on: false,
    desc: '都市計画区域内の土地について、公共施設の整備改善及び宅地の利用の増進を図るため行われる、土地の区画形質の変更及び公共施設の新設又は変更に関する事業（土地区画整理法第2条）。' },
  { key: 'kouen', name: '公園', geom: 'fill', on: false,
    desc: '都市計画に都市施設として定められた公園（都市計画法第11条）。市民の休息・レクリエーションの場や、災害時の避難地等となるオープンスペース。' },
  { key: 'soubou', name: '航空機騒音障害防止地区', geom: 'fill', on: false,
    desc: '特定空港の周辺において、航空機の騒音により生ずる障害を防止し、あわせて適正かつ合理的な土地利用を図るため定める地区（特定空港周辺航空機騒音対策特別措置法第4条）。' },
  { key: 'fukkousaiseikyoten', name: '一団地の復興再生拠点市街地形成施設', geom: 'fill', on: false,
    desc: '大規模な災害を受けた地域における復興の拠点となる市街地を形成する一団地の住宅施設、特定業務施設又は公益的施設及び公共施設（大規模災害からの復興に関する法律）。' },
  { key: 'douro', name: '都市計画道路', geom: 'line', on: false,
    desc: '都市計画に都市施設として定められた道路（都市計画法第11条）。計画決定・事業中・整備済みの路線を含み、区域内では建築の制限がある（同法第53条・第54条）。' },
]

// ---- 配色（data/styles.json / https://toshikeikaku-info.jp/ を参考） ----

/** カテゴリ配色（fill + outline）。凡例にもそのまま使う。 */
interface Cat {
  label: string
  fill: string
  outline: string
}
type ThemeStyle =
  | { kind: 'single'; fill: string; outline: string }
  | { kind: 'youto' }
  | { kind: 'cats'; prop: string; cats: Record<string, Cat>; fallback: Cat }

const YOUTO: Record<number, string> = {}
const YOUTO_NAME: Record<number, string> = {}
const YOUTO_ABBR: Record<number, string> = {}
for (const c of stylesJson.youto.codes) {
  YOUTO[c.code] = c.color
  YOUTO_NAME[c.code] = c.name
  YOUTO_ABBR[c.code] = c.abbr
}
const YOUTO_CODES = stylesJson.youto.codes.map((c) => c.code)

const STYLES = stylesJson.themes as unknown as Record<string, ThemeStyle>
const FALLBACK_STYLE = stylesJson.fallbackStyle as ThemeStyle

function youtoMatch(): ExpressionSpecification {
  const cases: (number | string)[] = []
  for (const c of YOUTO_CODES) cases.push(c, YOUTO[c])
  const expr = ['match', ['to-number', ['get', 'YoutoCode'], 0], ...cases, stylesJson.youto.fallback]
  return expr as unknown as ExpressionSpecification
}

function catMatch(prop: string, cats: Record<string, Cat>, fallback: string, pick: 'fill' | 'outline'): ExpressionSpecification {
  const cases: string[] = []
  for (const [val, c] of Object.entries(cats)) cases.push(val, c[pick])
  const expr = ['match', ['get', prop], ...cases, fallback]
  return expr as unknown as ExpressionSpecification
}

type LayerPaint =
  | Pick<FillLayerSpecification, 'type' | 'paint'>
  | Pick<LineLayerSpecification, 'type' | 'paint'>

export function paintFor(def: ThemeDef): LayerPaint {
  const st = STYLES[def.key] ?? FALLBACK_STYLE

  if (def.geom === 'line') {
    const color = st.kind === 'single' ? st.outline : 'rgba(0,0,255,1)'
    return {
      type: 'line',
      paint: {
        'line-color': color,
        // 高密度な路線網が下のレイヤー（用途地域等）を覆い隠さないよう細めにする
        'line-width': ['interpolate', ['linear'], ['zoom'], 8, 0.4, 12, 1, 16, 2.4],
        'line-opacity': opacityOf(def),
      },
    }
  }

  let fill: string | ExpressionSpecification
  let outline: string | ExpressionSpecification
  if (st.kind === 'youto') {
    fill = youtoMatch()
    outline = stylesJson.youto.outline
  } else if (st.kind === 'cats') {
    fill = catMatch(st.prop, st.cats, st.fallback.fill, 'fill')
    outline = catMatch(st.prop, st.cats, st.fallback.outline, 'outline')
  } else {
    fill = st.fill
    outline = st.outline
  }
  return {
    type: 'fill',
    // 参考サイト（toshikeikaku-info.jp）と同様、塗りは fill-opacity 0.7 を基本とし、
    // 併せて各色の rgba アルファ（防火0.6 等）も効かせる。不透明度は UI で変更可能。
    paint: { 'fill-color': fill, 'fill-opacity': opacityOf(def), 'fill-outline-color': outline },
  }
}

// ---- 用途地域スタンプ ----
// 都市計画総括図の用途地域スタンプ（円を横罫線2本で3分割した枠）を、枠スプライト＋テキスト式で再現する。
// 枠は組み合わせごとに焼いた画像ではなく1枚だけ持ち、中身は属性から描く。
// 全国では（用途地域13種 × 容積率19種 × 建蔽率7種）の組み合わせが数百通りに達するため、
// 組み合わせごとに画像を用意する方式は採らない。
//
// スプライト `用途地域スタンプ` の実測値: 150×150px、罫線は y=46 と y=103。
//   上段 y 0–46（中心 y=23）  → 容積率
//   中段 y 46–103（中心 y=74.5）→ 用途地域名（略称）
//   下段 y 103–150（中心 y=126.5）→ 建蔽率
// 段の中心間隔は (52 + 51.5) / 2 ≒ 51.75px。
export const STAMP_ICON = '用途地域スタンプ'
/** スタンプを出す最小ズーム。これ未満では枠が密集して読めない。 */
export const STAMP_MINZOOM = 13
const STAMP_SPRITE_PX = 150
const STAMP_BAND_PITCH_PX = 51.75
/**
 * 画面上のスタンプ直径(px)と文字サイズ。円形の枠なので、上下段は段の中央でも弦の幅しか使えない。
 * 中段4字（「工業専用」「1種低住」等）と上段4桁（容積率1300）が円弧に触れないよう、
 * 直径64px / 文字11px にして各段に5px以上の余白を残している。
 */
const STAMP_SCREEN_PX = 64
const STAMP_ICON_SIZE = STAMP_SCREEN_PX / STAMP_SPRITE_PX
const STAMP_TEXT_SIZE = 11
/**
 * 行送り（em）。3行テキストは中央行がアンカー、上下行が ±(行送り×文字サイズ) に置かれるため、
 * 枠実寸の段間隔と一致させると各行が各段の中央に来る。
 */
const STAMP_LINE_HEIGHT = (STAMP_BAND_PITCH_PX * STAMP_ICON_SIZE) / STAMP_TEXT_SIZE
/**
 * 3行テキストの微調整（em）。行送りだけでも各段の中心に概ね載るが、
 * 実測（枠を黒・文字を赤に分離してスクリーンショットを解析）で 0.5px ほど下寄りだったぶんを戻す。
 * これで各行の中心と各段の中心の差が ±0.4px 以内に収まる。
 */
const STAMP_TEXT_BASELINE_EM = -0.5 / STAMP_TEXT_SIZE

/** 中段に入れる略称（data/styles.json の youto.codes[].abbr）。 */
function youtoAbbrExpr(): ExpressionSpecification {
  const cases: (number | string)[] = []
  for (const c of YOUTO_CODES) cases.push(c, YOUTO_ABBR[c])
  const expr = ['match', ['to-number', ['get', 'YoutoCode'], 0], ...cases, '']
  return expr as unknown as ExpressionSpecification
}

/**
 * 容積率・建蔽率の表示文字列。元データは "200" と "200.0" が混在するため数値化して整数で描く。
 * 欠損（null / 空）は空文字にして、段のずれが出ないよう行だけ残す。
 */
function rateExpr(prop: string): ExpressionSpecification {
  const n = ['to-number', ['get', prop], 0]
  const expr = ['case', ['>', n, 0], ['to-string', ['round', n]], '']
  return expr as unknown as ExpressionSpecification
}

/** 用途地域スタンプのシンボルレイヤー定義。 */
export function youtoStampLayer(id: string, source: string, spriteId: string): SymbolLayerSpecification {
  return {
    id,
    type: 'symbol',
    source,
    'source-layer': 'youto',
    minzoom: STAMP_MINZOOM,
    layout: {
      'icon-image': `${spriteId}:${STAMP_ICON}`,
      'icon-size': STAMP_ICON_SIZE,
      'icon-padding': 4,
      // 上段=容積率 / 中段=用途地域名 / 下段=建蔽率。改行位置は枠の罫線に対応する。
      'text-field': ['concat', rateExpr('FAR'), '\n', youtoAbbrExpr(), '\n', rateExpr('BCR')],
      'text-font': ['NotoSansJP-Regular'],
      'text-size': STAMP_TEXT_SIZE,
      'text-line-height': STAMP_LINE_HEIGHT,
      'text-anchor': 'center',
      'text-justify': 'center',
      'text-offset': [0, STAMP_TEXT_BASELINE_EM],
      // 明示した改行だけで3段にしたいので自動折返しは実質無効化する
      'text-max-width': 20,
      'text-padding': 0,
    },
    paint: {
      'text-color': 'rgba(0,0,0,1)',
      // 枠内は透過で下の用途地域色が透けるため、白フチで文字を浮かせる
      'text-halo-color': 'rgba(255,255,255,0.9)',
      'text-halo-width': 1,
    },
  }
}

// ---- 凡例 ----
export interface LegendItem {
  color: string
  label: string
}

export function legendFor(def: ThemeDef): LegendItem[] {
  const st = STYLES[def.key]
  if (st?.kind === 'youto') {
    return Object.keys(YOUTO_NAME).map((k) => {
      const c = Number(k)
      return { color: YOUTO[c], label: YOUTO_NAME[c] }
    })
  }
  if (st?.kind === 'cats') {
    return Object.values(st.cats).map((c) => ({ color: c.fill, label: c.label }))
  }
  if (st?.kind === 'single') {
    return [{ color: st.fill, label: def.name }]
  }
  return [{ color: 'rgba(150,150,150,0.6)', label: def.name }]
}

/** レイヤートグルの色ドット用の代表色。 */
export function dotColor(def: ThemeDef): string {
  const items = legendFor(def)
  return items[0]?.color ?? 'rgba(150,150,150,0.8)'
}

// ---- ツールチップ / ポップアップ ----
const S = (p: Record<string, unknown>, k: string): string => {
  const v = p[k]
  return v === undefined || v === null || v === '' ? '' : String(v)
}

/** テーマごとの主表示ラベル（名称/種別）。 */
function primaryLabel(key: string, p: Record<string, unknown>): string {
  if (key === 'youto') {
    const code = Number(p['YoutoCode'])
    return S(p, 'YoutoName') || YOUTO_NAME[code] || '用途地域'
  }
  return (
    S(p, 'AreaType') ||
    S(p, 'DistType') ||
    S(p, 'YoutoName') ||
    S(p, 'DistName') ||
    S(p, 'ParkName') ||
    S(p, 'AreaName') ||
    S(p, 'FaciName') ||
    ''
  )
}

function esc(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c] as string)
}

// 属性名（ローマ字）→ 和名。出典: 都市計画決定GISデータ データ定義書。
const ATTR_LABELS: Record<string, string> = stylesJson.attributeLabels
function attrLabel(key: string): string {
  return ATTR_LABELS[key] ?? key
}
function fmtValue(key: string, v: unknown): string {
  const s = String(v)
  if ((key === 'FAR' || key === 'BCR') && /^\d/.test(s)) return `${s}%`
  return s
}

export function popupHtml(key: string, name: string, p: Record<string, unknown>): string {
  const title = primaryLabel(key, p) || name
  // クリック時は全属性を表示する（空値は除外）。
  const rows = Object.entries(p)
    .filter(([, v]) => v !== null && v !== undefined && v !== '')
    .map(([k, v]) => `<dt>${esc(attrLabel(k))}</dt><dd>${esc(fmtValue(k, v))}</dd>`)
    .join('')
  return (
    `<div class="pp-title">${esc(title)}</div>` +
    `<div class="pp-sub">${esc(name)}</div>` +
    (rows ? `<dl class="pp-dl pp-all">${rows}</dl>` : '')
  )
}
