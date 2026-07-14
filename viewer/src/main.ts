import maplibregl from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import 'maplibre-gl/dist/maplibre-gl.css'

import { getBasemapStyle, type Basemap } from './basemap'
import { THEMES, type ThemeDef, hoverHtml, legendFor, opacityOf, paintFor, popupHtml } from './layers'
import { applyThemeAttr, initialTheme, type Theme } from './theme'
import './style.css'

const PMTILES_BASE = import.meta.env.VITE_PMTILES_BASE ?? '/pmtiles'
const DATA_ATTRIBUTION =
  '都市計画決定GISデータ（<a href="https://www.mlit.go.jp/toshi/tosiko/toshi_tosiko_tk_000182.html" target="_blank" rel="noopener">国土交通省 都市局</a>）'

let theme: Theme = initialTheme()
let base: Basemap = 'pale'
applyThemeAttr(theme)

const protocol = new Protocol()
maplibregl.addProtocol('pmtiles', protocol.tile)

const map = new maplibregl.Map({
  container: 'map',
  style: getBasemapStyle(base, theme),
  center: [139.74, 35.68],
  zoom: 10,
  attributionControl: false,
})
map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right')
map.addControl(
  new maplibregl.GeolocateControl({
    positionOptions: { enableHighAccuracy: true },
    trackUserLocation: true,
    showUserLocation: true,
  }),
  'top-right',
)
map.addControl(new maplibregl.ScaleControl(), 'bottom-left')
map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: DATA_ATTRIBUTION }))

const layerId = (key: string): string => `${key}-lyr`
const keyFromLayer = (id: string): string => id.replace(/-lyr$/, '')
const defOf = (key: string): ThemeDef | undefined => THEMES.find((t) => t.key === key)
const activeLayerIds = (): string[] =>
  THEMES.filter((t) => t.on).map((t) => layerId(t.key)).filter((id) => map.getLayer(id))

const themeIndex = (key: string): number => THEMES.findIndex((t) => t.key === key)

// canonical z順: THEMES 配列の後ろほど地図で最前面（都市計画区域が最背面, 都市計画道路が最前面）。
// def の直上に来るべき既存レイヤーを beforeId に指定して正規順で挿入する。
function beforeIdFor(def: ThemeDef): string | undefined {
  const i = themeIndex(def.key)
  for (let j = i + 1; j < THEMES.length; j++) {
    const id = layerId(THEMES[j].key)
    if (map.getLayer(id)) return id
  }
  return undefined
}

function ensureLayer(def: ThemeDef): void {
  if (map.getLayer(layerId(def.key))) return
  if (!map.getSource(def.key)) {
    map.addSource(def.key, { type: 'vector', url: `pmtiles://${PMTILES_BASE}/${def.key}.pmtiles` })
  }
  const p = paintFor(def)
  map.addLayer(
    {
      id: layerId(def.key),
      type: p.type,
      source: def.key,
      'source-layer': def.key,
      paint: p.paint,
    } as maplibregl.LayerSpecification,
    beforeIdFor(def),
  )
}

function removeLayer(def: ThemeDef): void {
  if (map.getLayer(layerId(def.key))) map.removeLayer(layerId(def.key))
  if (map.getSource(def.key)) map.removeSource(def.key)
}

// 有効なレイヤーのみを（正規 z順で）地図に載せる。無効なものはソースごと持たない＝軽量。
function addDataLayers(): void {
  for (const def of THEMES) {
    if (def.on) ensureLayer(def)
    else removeLayer(def)
  }
}

// ---- テーマ切替 ----
const themeBtn = document.getElementById('theme-btn') as HTMLButtonElement
const renderThemeBtn = (): void => {
  themeBtn.textContent = theme === 'dark' ? '☀️' : '🌙'
}
// 背景スタイルを差し替える。ラスタ（写真）↔ベクタ（淡色）の切替では diff 適用が
// 効かず背景が入れ替わらないため diff:false で完全に再構築する。
// setStyle 直後は isStyleLoaded() が旧スタイルで true を返して競合するため、
// 新スタイルの描画が落ち着く idle を待ってからデータ層を再追加する。
function reloadStyle(): void {
  map.setStyle(getBasemapStyle(base, theme), { diff: false })
  map.once('idle', () => addDataLayers())
}
themeBtn.addEventListener('click', () => {
  theme = theme === 'dark' ? 'light' : 'dark'
  applyThemeAttr(theme)
  renderThemeBtn()
  reloadStyle()
})

// ---- パネル開閉 ----
const panel = document.getElementById('panel') as HTMLElement
const collapseBtn = document.getElementById('collapse-btn') as HTMLButtonElement
const renderCollapseBtn = (): void => {
  collapseBtn.textContent = panel.classList.contains('collapsed') ? '▾' : '▴'
}
collapseBtn.addEventListener('click', () => {
  panel.classList.toggle('collapsed')
  renderCollapseBtn()
})

// ---- レイヤートグル（凡例を各レイヤー直下にインライン表示） ----
const layersDiv = document.getElementById('layers') as HTMLElement

function legendMarkup(def: ThemeDef): string {
  const items = legendFor(def)
  if (items.length <= 1) {
    const c = items[0]?.color ?? 'rgba(150,150,150,1)'
    return `<span class="lg-bar" style="background:${c}"></span>`
  }
  return items
    .map(
      (it) =>
        `<span class="lg-row"><span class="lg-sw" style="background:${it.color}"></span>${it.label}</span>`,
    )
    .join('')
}

function buildToggles(): void {
  for (const def of THEMES) {
    const item = document.createElement('div')
    item.className = 'layer-item'
    item.dataset.key = def.key

    const label = document.createElement('label')
    label.className = 'toggle'

    const input = document.createElement('input')
    input.type = 'checkbox'
    input.checked = def.on
    input.addEventListener('change', () => setLayerVisible(def, input.checked))

    const sw = document.createElement('span')
    sw.className = 'switch'
    const text = document.createElement('span')
    text.className = 't-label'
    text.textContent = def.name

    label.append(input, sw, text)

    // 不透明度スライダー（有効時のみ表示）
    const opac = document.createElement('div')
    opac.className = 'layer-opacity'
    opac.hidden = !def.on
    const range = document.createElement('input')
    range.type = 'range'
    range.min = '0'
    range.max = '1'
    range.step = '0.05'
    range.value = String(opacityOf(def))
    range.setAttribute('aria-label', `${def.name}の不透明度`)
    const val = document.createElement('span')
    val.className = 'op-val'
    val.textContent = `${Math.round(opacityOf(def) * 100)}%`
    range.addEventListener('input', () => {
      const v = Number(range.value)
      val.textContent = `${Math.round(v * 100)}%`
      setLayerOpacity(def, v)
    })
    opac.append(range, val)

    const legend = document.createElement('div')
    legend.className = 'layer-legend'
    legend.innerHTML = legendMarkup(def)
    legend.hidden = !def.on

    item.append(label, opac, legend)
    layersDiv.append(item)
  }
}

function setLayerVisible(def: ThemeDef, on: boolean): void {
  def.on = on
  if (on) ensureLayer(def)
  else removeLayer(def)
  const item = layersDiv.querySelector<HTMLElement>(`.layer-item[data-key="${def.key}"]`)
  item?.querySelector<HTMLElement>('.layer-legend')?.toggleAttribute('hidden', !on)
  item?.querySelector<HTMLElement>('.layer-opacity')?.toggleAttribute('hidden', !on)
}

function setLayerOpacity(def: ThemeDef, v: number): void {
  def.opacity = v
  const id = layerId(def.key)
  if (!map.getLayer(id)) return
  map.setPaintProperty(id, def.geom === 'line' ? 'line-opacity' : 'fill-opacity', v)
}

function setAll(on: boolean): void {
  for (const def of THEMES) {
    if (def.on === on) continue
    const input = layersDiv.querySelector<HTMLInputElement>(`.layer-item[data-key="${def.key}"] input`)
    if (input) input.checked = on
    setLayerVisible(def, on)
  }
}
;(document.getElementById('all-on') as HTMLButtonElement).addEventListener('click', () => setAll(true))
;(document.getElementById('all-off') as HTMLButtonElement).addEventListener('click', () => setAll(false))

// ---- 背景地図スイッチャー（右下） ----
class BasemapControl implements maplibregl.IControl {
  private el!: HTMLElement
  onAdd(): HTMLElement {
    this.el = document.createElement('div')
    this.el.className = 'maplibregl-ctrl basemap-switch'
    const defs: [Basemap, string][] = [
      ['pale', '地図'],
      ['photo', '写真'],
    ]
    for (const [b, label] of defs) {
      const btn = document.createElement('button')
      btn.type = 'button'
      btn.textContent = label
      btn.dataset.base = b
      btn.setAttribute('aria-selected', String(b === base))
      btn.addEventListener('click', () => setBase(b))
      this.el.append(btn)
    }
    return this.el
  }
  onRemove(): void {
    this.el.remove()
  }
  sync(): void {
    for (const btn of this.el.querySelectorAll<HTMLButtonElement>('button')) {
      btn.setAttribute('aria-selected', String(btn.dataset.base === base))
    }
  }
}
const basemapCtrl = new BasemapControl()
map.addControl(basemapCtrl, 'bottom-right')

function setBase(next: Basemap): void {
  if (next === base) return
  base = next
  basemapCtrl.sync()
  reloadStyle()
}

// ---- ホバーツールチップ ----
const tooltip = document.getElementById('tooltip') as HTMLElement
map.on('mousemove', (e) => {
  const ids = activeLayerIds()
  const feats = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids }) : []
  if (feats.length) {
    const f = feats[0]
    const key = keyFromLayer(f.layer.id)
    tooltip.innerHTML = hoverHtml(key, defOf(key)?.name ?? key, f.properties as Record<string, unknown>)
    tooltip.style.left = `${e.point.x}px`
    tooltip.style.top = `${e.point.y}px`
    tooltip.hidden = false
    map.getCanvas().style.cursor = 'pointer'
  } else {
    tooltip.hidden = true
    map.getCanvas().style.cursor = ''
  }
})
map.on('mouseout', () => {
  tooltip.hidden = true
})

// ---- クリックポップアップ ----
map.on('click', (e) => {
  const ids = activeLayerIds()
  const feats = ids.length ? map.queryRenderedFeatures(e.point, { layers: ids }) : []
  if (!feats.length) return
  const f = feats[0]
  const key = keyFromLayer(f.layer.id)
  new maplibregl.Popup({ closeButton: true, maxWidth: '300px' })
    .setLngLat(e.lngLat)
    .setHTML(popupHtml(key, defOf(key)?.name ?? key, f.properties as Record<string, unknown>))
    .addTo(map)
})

// ---- 初期化 ----
renderThemeBtn()
buildToggles()
// スマホでは初期状態でパネルを畳んで地図を広く見せる
if (window.matchMedia('(max-width: 640px)').matches) panel.classList.add('collapsed')
renderCollapseBtn()
map.on('load', addDataLayers)

// デバッグ/外部連携用にマップを公開
;(window as unknown as { __map: maplibregl.Map }).__map = map

// PWA: Service Worker 登録（本番のみ。dev では HMR を妨げないよう無効）
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('sw.js').catch(() => {})
  })
}
