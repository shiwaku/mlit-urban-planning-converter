"""ダウンロードページを解析し、47都道府県の GeoJSON zip URL を解決する。

DL リンクの content-ID は更新のたびに変わるため、ハードコードせず毎回スクレイプする。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import sys
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from . import config

# 「令和8年7月7日」「R8.7.7」「(R8.7.1修正)」等から日付を拾う
_REIWA_KANJI = re.compile(r"令和\s*(\d+)\s*年\s*(\d+)\s*月\s*(\d+)\s*日")
_REIWA_SHORT = re.compile(r"[RＲ]\s*(\d+)\s*[.．]\s*(\d+)\s*[.．]\s*(\d+)")


def _reiwa_to_iso(y: int, m: int, d: int) -> str:
    """令和y年m月d日 -> ISO 日付文字列 (令和元年 = 2019)。"""
    return dt.date(2018 + y, m, d).isoformat()


def parse_reiwa_dates(text: str) -> list[str]:
    """テキスト中の令和表記の日付を ISO 文字列のリストで返す。"""
    out: list[str] = []
    for y, m, d in _REIWA_KANJI.findall(text):
        out.append(_reiwa_to_iso(int(y), int(m), int(d)))
    for y, m, d in _REIWA_SHORT.findall(text):
        out.append(_reiwa_to_iso(int(y), int(m), int(d)))
    return out


def fetch(url: str, *, retries: int = 4, timeout: int = 60) -> str:
    """UA 付き・リトライ付きで HTML を取得する。"""
    headers = {"User-Agent": config.USER_AGENT}
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or resp.encoding
            return resp.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"取得に失敗: {url}: {last}")


def _geojson_column_index(header_cells: list[str]) -> Optional[int]:
    for i, txt in enumerate(header_cells):
        if config.GEOJSON_COLUMN_HEADER in txt.replace(" ", ""):
            return i
    return None


def parse_sources(html: str) -> list[dict]:
    """ダウンロードページ HTML から都道府県ごとの GeoJSON zip 情報を抽出。

    返り値: [{pref, url, content_id, note, modified}] を 47 件。
    """
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        # ヘッダ行（GeoJSON形式 を含む）を探し、列 index を確定
        col_idx = None
        header_row_i = None
        for i, tr in enumerate(rows):
            cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"])]
            idx = _geojson_column_index(cells)
            if idx is not None:
                col_idx, header_row_i = idx, i
                break
        if col_idx is None:
            continue

        sources: list[dict] = []
        for tr in rows[header_row_i + 1 :]:
            cells = tr.find_all(["th", "td"])
            if len(cells) <= col_idx:
                continue
            pref = cells[0].get_text(strip=True)
            if not pref or pref == "都道府県":
                continue
            cell = cells[col_idx]
            link = cell.find("a", href=re.compile(r"\.zip$"))
            if link is None:
                continue
            href = link["href"]
            url = href if href.startswith("http") else config.SITE_ORIGIN + href
            note = cell.get_text(" ", strip=True)
            dates = parse_reiwa_dates(note)
            sources.append(
                {
                    "pref": pref,
                    "url": url,
                    "content_id": url.rsplit("/", 1)[-1].removesuffix(".zip"),
                    "note": note,
                    "modified": max(dates) if dates else None,
                }
            )
        if sources:
            return sources
    raise RuntimeError("GeoJSON列を含むテーブルが見つかりませんでした（ページ構造変更の可能性）")


def detect_version(sources: list[dict], info_html: Optional[str] = None) -> str:
    """データ版の日付(YYYYMMDD)を決める。

    優先: 説明ページの「最終更新」日 > 各県 note の最大修正日 > 本日。
    """
    candidates: list[str] = []
    if info_html:
        text = BeautifulSoup(info_html, "html.parser").get_text(" ", strip=True)
        # 「最終更新 … 令和8年7月7日」付近を優先
        m = re.search(r"最終更新.{0,20}", text)
        if m:
            candidates += parse_reiwa_dates(m.group(0))
        if not candidates:
            candidates += parse_reiwa_dates(text)
    candidates += [s["modified"] for s in sources if s.get("modified")]
    if candidates:
        return max(candidates).replace("-", "")
    return dt.date.today().strftime("%Y%m%d")


def fingerprint(sources: list[dict]) -> str:
    """変更検知用フィンガープリント（県名+content_id の並び）。

    content-ID は更新のたびに変わるため、これが一致すれば内容不変とみなせる。
    """
    payload = "\n".join(f"{s['pref']}\t{s['content_id']}" for s in sorted(sources, key=lambda s: s["pref"]))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scrape() -> dict:
    """ページを取得して sources・version・fingerprint をまとめて返す。"""
    sel_html = fetch(config.SELECTION_URL)
    sources = parse_sources(sel_html)
    info_html = None
    try:
        info_html = fetch(config.INFO_URL)
    except Exception:  # noqa: BLE001
        pass
    return {
        "source_page": config.SELECTION_URL,
        "info_page": config.INFO_URL,
        "version": detect_version(sources, info_html),
        "fingerprint": fingerprint(sources),
        "prefectures": sources,
    }


def main(argv: Optional[list[str]] = None) -> int:
    result = scrape()
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    n = len(result["prefectures"])
    print(
        f"# 都道府県 {n} 件 / version={result['version']} / fp={result['fingerprint'][:12]}",
        file=sys.stderr,
    )
    return 0 if n == 47 else 1


if __name__ == "__main__":
    raise SystemExit(main())
