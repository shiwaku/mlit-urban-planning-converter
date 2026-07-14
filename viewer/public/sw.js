// アプリシェル（HTML/JS/CSS/アイコン）のみをキャッシュする軽量 Service Worker。
// PMTiles（巨大）や外部タイル（地理院）はキャッシュせず常にネットワークから取得する。
const CACHE = 'tosiko-viewer-v1'

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
  // 同一オリジンかつ PMTiles 以外のみ cache-first で扱う
  if (url.origin !== self.location.origin || url.pathname.endsWith('.pmtiles')) return
  e.respondWith(
    (async () => {
      const cache = await caches.open(CACHE)
      const hit = await cache.match(req)
      if (hit) return hit
      try {
        const res = await fetch(req)
        if (res.ok && res.type === 'basic') cache.put(req, res.clone())
        return res
      } catch (err) {
        const fallback = await cache.match('./index.html')
        if (fallback) return fallback
        throw err
      }
    })(),
  )
})
