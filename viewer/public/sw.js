// ネットワーク優先の軽量 Service Worker。
// オンライン時は常に最新を取得（＝デプロイ後すぐ反映される）。
// オフライン時のみキャッシュにフォールバックする。PMTiles（巨大）や外部タイルは対象外。
const CACHE = 'tosiko-viewer-v2'

self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    (async () => {
      for (const k of await caches.keys()) if (k !== CACHE) await caches.delete(k)
      await self.clients.claim()
    })(),
  )
})

self.addEventListener('fetch', (e) => {
  const req = e.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  // 同一オリジンかつ PMTiles 以外のみ扱う（外部タイル・PMTiles はそのまま素通し）
  if (url.origin !== self.location.origin || url.pathname.endsWith('.pmtiles')) return
  e.respondWith(
    (async () => {
      const cache = await caches.open(CACHE)
      try {
        const res = await fetch(req)
        if (res.ok && res.type === 'basic') cache.put(req, res.clone())
        return res
      } catch (err) {
        const hit = (await cache.match(req)) || (await cache.match('./index.html'))
        if (hit) return hit
        throw err
      }
    })(),
  )
})
