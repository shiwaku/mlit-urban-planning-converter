// キャッシュしない Service Worker。常に最新をネットワークから取得する。
// 以前の「キャッシュ優先」SW が古い画面を固定してしまう問題を解消するため、
// 有効化時に既存キャッシュをすべて削除し、fetch には介入しない（＝素通し＝常に最新）。
self.addEventListener('install', () => {
  self.skipWaiting()
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    (async () => {
      for (const k of await caches.keys()) await caches.delete(k)
      await self.clients.claim()
    })(),
  )
})

// fetch ハンドラを持たない＝リクエストに一切介入しない＝ブラウザが常にネットワークから取得する。
