import type {
  ExpressionSpecification,
  FillLayerSpecification,
  LineLayerSpecification,
} from 'maplibre-gl'

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
}

/** テーマ既定の不透明度。全テーマ一律 50%（スライダーで個別に変更可能）。 */
export function defaultOpacity(_def: ThemeDef): number {
  return 0.5
}
export function opacityOf(def: ThemeDef): number {
  return def.opacity ?? defaultOpacity(def)
}

/**
 * 描画対象テーマ（全26種）。パネルの並び順（先頭＝一番上）。
 * 広域な区域（都市計画区域）を上に、用途地域を中位、細かい地区・線（都市計画道路）を下に置く。
 * 地図の描画順は main.ts の addDataLayers がこの配列順に addLayer するため、
 * **配列末尾ほど地図で最前面**（都市計画区域が最背面、都市計画道路が最前面）になる。
 */
export const THEMES: ThemeDef[] = [
  { key: 'tokei', name: '都市計画区域', geom: 'fill', on: false },
  { key: 'jyuntoshi', name: '準都市計画区域', geom: 'fill', on: false },
  { key: 'senbiki', name: '区域区分', geom: 'fill', on: false },
  { key: 'ritteki', name: '立地適正化計画区域', geom: 'fill', on: false },
  { key: 'youto', name: '用途地域', geom: 'fill', on: true },
  { key: 'tkbt', name: '特別用途地区', geom: 'fill', on: false },
  { key: 'tokuteiyouto', name: '特定用途制限地域', geom: 'fill', on: false },
  { key: 'tokuteiyuudou', name: '特定用途誘導地区', geom: 'fill', on: false },
  { key: 'koudoti', name: '高度地区', geom: 'fill', on: false },
  { key: 'koudori', name: '高度利用地区', geom: 'fill', on: false },
  { key: 'tokureiyouseki', name: '特例容積率適用地区', geom: 'fill', on: false },
  { key: 'kousoujyukyo', name: '高層住居誘導地区', geom: 'fill', on: false },
  { key: 'kyojyuchosei', name: '居住調整地域', geom: 'fill', on: false },
  { key: 'bouka', name: '防火地域・準防火地域', geom: 'fill', on: false },
  { key: 'tokuteibou', name: '特定防災街区整備地区', geom: 'fill', on: false },
  { key: 'fuuchichiku', name: '風致地区', geom: 'fill', on: false },
  { key: 'ryokukachiiki', name: '緑化地域', geom: 'fill', on: false },
  { key: 'tokuryoku', name: '特別緑地保全地区', geom: 'fill', on: false },
  { key: 'rekifuu', name: '歴史的風土保存地区', geom: 'fill', on: false },
  { key: 'toshisaisei', name: '都市再生特別地区', geom: 'fill', on: false },
  { key: 'chikukei', name: '地区計画', geom: 'fill', on: false },
  { key: 'tochiku', name: '土地区画整理事業', geom: 'fill', on: false },
  { key: 'kouen', name: '公園', geom: 'fill', on: false },
  { key: 'soubou', name: '航空機騒音障害防止地区', geom: 'fill', on: false },
  { key: 'fukkousaiseikyoten', name: '一団地の復興再生拠点市街地形成施設', geom: 'fill', on: false },
  { key: 'douro', name: '都市計画道路', geom: 'line', on: false },
]

// ---- 配色（https://toshikeikaku-info.jp/ を参考） ----
// 用途地域は YoutoCode（1..13）で色分け。田園住居地域(8) は参考サイト未収録のため補完。
const YOUTO: Record<number, string> = {
  1: 'rgba(0,255,153,1)', // 第一種低層住居専用地域
  2: 'rgba(0,85,46,1)', // 第二種低層住居専用地域
  3: 'rgba(146,208,80,1)', // 第一種中高層住居専用地域
  4: 'rgba(204,255,153,1)', // 第二種中高層住居専用地域
  5: 'rgba(255,255,102,1)', // 第一種住居地域
  6: 'rgba(255,204,153,1)', // 第二種住居地域
  7: 'rgba(255,204,102,1)', // 準住居地域
  8: 'rgba(215,235,110,1)', // 田園住居地域（補完）
  9: 'rgba(255,102,204,1)', // 近隣商業地域
  10: 'rgba(255,0,102,1)', // 商業地域
  11: 'rgba(153,0,255,1)', // 準工業地域
  12: 'rgba(204,255,255,1)', // 工業地域
  13: 'rgba(51,204,255,1)', // 工業専用地域
}
const YOUTO_NAME: Record<number, string> = {
  1: '第一種低層住居専用地域', 2: '第二種低層住居専用地域',
  3: '第一種中高層住居専用地域', 4: '第二種中高層住居専用地域',
  5: '第一種住居地域', 6: '第二種住居地域', 7: '準住居地域', 8: '田園住居地域',
  9: '近隣商業地域', 10: '商業地域', 11: '準工業地域', 12: '工業地域', 13: '工業専用地域',
}

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

const BLACK = 'rgba(0,0,0,1)'

// 色は https://toshikeikaku-info.jp/ の定義に準拠（rgba のアルファもサイトの値を踏襲）。
// サイト未収録のテーマはアルファ 1 とし、共通の fill-opacity 0.7 で透過させる。
const STYLES: Record<string, ThemeStyle> = {
  youto: { kind: 'youto' },
  senbiki: {
    kind: 'cats',
    prop: 'AreaType',
    cats: {
      市街化区域: { label: '市街化区域', fill: 'rgba(255,250,190,1)', outline: 'rgba(255,160,230,1)' },
      市街化調整区域: { label: '市街化調整区域', fill: 'rgba(220,220,220,1)', outline: 'rgba(255,160,230,1)' },
    },
    fallback: { label: 'その他', fill: 'rgba(210,210,210,1)', outline: 'rgba(160,160,160,1)' },
  },
  bouka: {
    kind: 'cats',
    prop: 'AreaType',
    cats: {
      防火地域: { label: '防火地域', fill: 'rgba(255,0,100,0.6)', outline: 'rgba(255,0,102,1)' },
      準防火地域: { label: '準防火地域', fill: 'rgba(255,150,200,0.4)', outline: 'rgba(255,0,102,1)' },
    },
    fallback: { label: 'その他', fill: 'rgba(255,120,170,0.4)', outline: 'rgba(255,0,102,1)' },
  },
  ritteki: {
    kind: 'cats',
    prop: 'AreaType',
    cats: {
      立地適正化計画区域: { label: '立地適正化計画区域', fill: 'rgba(215,250,165,1)', outline: 'rgba(160,195,95,1)' },
      居住誘導区域: { label: '居住誘導区域', fill: 'rgba(0,150,0,0.5)', outline: 'rgba(0,0,255,1)' },
      都市機能誘導区域: { label: '都市機能誘導区域', fill: 'rgba(0,150,0,0.5)', outline: 'rgba(255,0,0,1)' },
    },
    fallback: { label: 'その他', fill: 'rgba(215,250,165,1)', outline: 'rgba(160,195,95,1)' },
  },
  tokei: { kind: 'single', fill: 'rgba(200,200,200,1)', outline: 'rgba(100,100,100,1)' },
  jyuntoshi: { kind: 'single', fill: 'rgba(200,50,20,0.5)', outline: 'rgba(200,50,20,1)' },
  koudoti: { kind: 'single', fill: 'rgba(230,200,170,1)', outline: 'rgba(120,90,40,1)' },
  koudori: { kind: 'single', fill: 'rgba(200,200,200,0.7)', outline: BLACK },
  tokureiyouseki: { kind: 'single', fill: 'rgba(180,150,220,1)', outline: 'rgba(120,90,180,1)' },
  kousoujyukyo: { kind: 'single', fill: 'rgba(120,180,255,1)', outline: 'rgba(40,100,200,1)' },
  kyojyuchosei: { kind: 'single', fill: 'rgba(0,150,0,0.5)', outline: 'rgba(0,100,0,1)' },
  tkbt: { kind: 'single', fill: 'rgba(255,200,255,0.5)', outline: 'rgba(255,102,204,1)' },
  tokuteiyouto: { kind: 'single', fill: 'rgba(200,200,50,0.5)', outline: 'rgba(200,200,50,1)' },
  tokuteiyuudou: { kind: 'single', fill: 'rgba(255,180,120,1)', outline: 'rgba(200,120,60,1)' },
  tokuteibou: { kind: 'single', fill: 'rgba(255,120,120,1)', outline: 'rgba(200,60,60,1)' },
  fuuchichiku: { kind: 'single', fill: 'rgba(50,200,20,0.5)', outline: 'rgba(50,150,20,1)' },
  ryokukachiiki: { kind: 'single', fill: 'rgba(120,220,120,1)', outline: 'rgba(30,150,30,1)' },
  tokuryoku: { kind: 'single', fill: 'rgba(34,139,34,0.5)', outline: 'rgba(0,100,0,1)' },
  rekifuu: { kind: 'single', fill: 'rgba(150,120,80,1)', outline: 'rgba(110,80,40,1)' },
  toshisaisei: { kind: 'single', fill: 'rgba(255,100,180,1)', outline: 'rgba(200,40,120,1)' },
  chikukei: { kind: 'single', fill: 'rgba(255,170,0,1)', outline: 'rgba(200,120,0,1)' },
  tochiku: { kind: 'single', fill: 'rgba(255,140,90,1)', outline: 'rgba(200,90,40,1)' },
  kouen: { kind: 'single', fill: 'rgba(255,255,80,1)', outline: 'rgba(30,180,30,1)' },
  soubou: { kind: 'single', fill: 'rgba(120,120,200,1)', outline: 'rgba(60,60,150,1)' },
  fukkousaiseikyoten: { kind: 'single', fill: 'rgba(200,150,100,1)', outline: 'rgba(150,100,60,1)' },
  douro: { kind: 'single', fill: 'rgba(0,0,255,1)', outline: 'rgba(0,0,255,1)' },
}

function youtoMatch(): ExpressionSpecification {
  const cases: (number | string)[] = []
  for (let c = 1; c <= 13; c++) cases.push(c, YOUTO[c])
  const expr = ['match', ['to-number', ['get', 'YoutoCode'], 0], ...cases, 'rgba(180,180,180,0.6)']
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
  const st = STYLES[def.key] ?? { kind: 'single', fill: 'rgba(150,150,150,0.5)', outline: BLACK }

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
    outline = 'rgba(0,0,0,0.55)'
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
const ATTR_LABELS: Record<string, string> = {
  Pref: '都道府県',
  Citycode: '市区町村コード',
  Cityname: '市区町村名',
  YoutoName: '用途地域名',
  YoutoCode: '用途地域コード',
  FAR: '容積率',
  BCR: '建蔽率',
  AreaType: '種類',
  AreaName: '名称',
  AreaCode: '種類コード',
  TokeiName: '都市計画区域名',
  TokeiType: '種類',
  TokeiCode: '種類コード',
  DistName: '名称',
  DistType: '種類',
  DistCode: '種類コード',
  ParkName: '公園名',
  ParkType: '種類',
  ParkCode: '種類コード',
  DouroType: '種類',
  DouroCode: '種類コード',
  FaciName: '施設名',
  FaciType: '種類',
  FaciCode: '種類コード',
  INDate: '当初決定日',
  FNDate: '最終告示日',
  INNumber: '当初告示番号',
  FNNumber: '最終告示番号',
  ValidType: '効力発生日の種類',
  Custodian: '決定者',
}
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
