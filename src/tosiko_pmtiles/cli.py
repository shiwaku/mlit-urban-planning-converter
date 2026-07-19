"""コマンドラインエントリ: scrape / download / convert / catalog / all / check-update。"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Optional

from . import catalog, config, convert as convert_mod, download as download_mod, scrape as scrape_mod


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sources_path() -> Path:
    return config.DIST_DIR / "sources.json"


def _download_path() -> Path:
    return config.DIST_DIR / "download.json"


def _convert_path() -> Path:
    return config.DIST_DIR / "convert.json"


def cmd_scrape(args) -> int:
    result = scrape_mod.scrape()
    _write_json(_sources_path(), result)
    n = len(result["prefectures"])
    print(f"scrape: {n} 都道府県 / version={result['version']} / fp={result['fingerprint'][:12]}")
    print(f"  -> {_sources_path()}")
    return 0 if n == 47 else 1


def _load_sources() -> dict:
    if _sources_path().exists():
        return json.loads(_sources_path().read_text(encoding="utf-8"))
    return scrape_mod.scrape()


def cmd_download(args) -> int:
    config.ensure_dirs()
    sources = _load_sources()
    entries = download_mod.download_all(
        sources["prefectures"],
        prefs=args.pref or None,
        sleep=args.sleep,
        force=getattr(args, "force", False),
    )
    _write_json(_download_path(), {"generated_at": _now_iso(), "entries": entries})
    print(f"download: {len(entries)} 県分 完了 -> {_download_path()}")
    return 0


def cmd_convert(args) -> int:
    config.ensure_dirs()
    results = convert_mod.convert(
        split=args.split,
        minzoom=args.minzoom,
        maxzoom=args.maxzoom,
        extra=args.extra.split() if args.extra else None,
    )
    _write_json(_convert_path(), {"generated_at": _now_iso(), "split": args.split, "results": results})
    total = sum(r.get("bytes", 0) for r in results)
    print(f"convert: {len(results)} PMTiles / 合計 {total/1048576:.1f} MB -> {config.DIST_DIR}")
    return 0


def _build_and_write_catalog(split: str, release_url: Optional[str]) -> dict:
    sources = _load_sources()
    dl = json.loads(_download_path().read_text(encoding="utf-8")) if _download_path().exists() else {}
    cv = json.loads(_convert_path().read_text(encoding="utf-8")) if _convert_path().exists() else {}
    manifest = catalog.build_manifest(
        sources,
        dl.get("entries", []),
        cv.get("results", []),
        split=cv.get("split", split),
    )
    v_path, d_path = catalog.write_manifest(manifest)
    idx = catalog.update_versions_index(manifest, release_url=release_url)
    md = catalog.write_catalog_md(manifest)
    print(f"catalog: version={manifest['version']} tag={manifest['tag']}")
    for p in (v_path, d_path, idx, md):
        print(f"  -> {p}")
    return manifest


def cmd_catalog(args) -> int:
    _build_and_write_catalog(args.split, args.release_url)
    return 0


def cmd_all(args) -> int:
    config.ensure_dirs()
    rc = cmd_scrape(args)
    if rc:
        return rc
    cmd_download(args)
    cmd_convert(args)
    _build_and_write_catalog(args.split, args.release_url)
    return 0


def cmd_check_update(args) -> int:
    """scrape して、コミット済み最新 manifest と fingerprint を比較。

    県単位（content_id）の差分も算出する。JSON を stdout に出力。
    --github-output 指定時は key=value も追記する。
    """
    result = scrape_mod.scrape()
    prev_manifest = catalog.latest_committed_manifest()
    prev = prev_manifest.get("fingerprint") if prev_manifest else None
    changed = result["fingerprint"] != prev
    # 県単位の差分（前回 manifest の content_id と比較）
    prev_ids = {
        p["pref"]: p.get("content_id")
        for p in (prev_manifest.get("prefectures", []) if prev_manifest else [])
    }
    changed_prefs = [
        s["pref"] for s in result["prefectures"] if prev_ids.get(s["pref"]) != s["content_id"]
    ]
    out = {
        "version": result["version"],
        "tag": catalog.tag_for(result["version"]),
        "fingerprint": result["fingerprint"],
        "previous_fingerprint": prev,
        "changed": changed,
        "changed_prefs": changed_prefs,
    }
    # sources.json も保存しておく（後続 download の再スクレイプ回避）
    _write_json(_sources_path(), result)
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if changed:
        print(f"# 変更あり: {len(changed_prefs)} 県 ({'、'.join(changed_prefs[:10])}{' …' if len(changed_prefs) > 10 else ''})", file=sys.stderr)
    if args.github_output:
        with open(args.github_output, "a", encoding="utf-8") as fh:
            fh.write(f"version={out['version']}\n")
            fh.write(f"tag={out['tag']}\n")
            fh.write(f"changed={'true' if changed else 'false'}\n")
            fh.write(f"fingerprint={out['fingerprint']}\n")
            fh.write(f"changed_pref_count={len(changed_prefs)}\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tosiko_pmtiles", description="都市計画決定GISデータ → PMTiles パイプライン")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("scrape", help="ダウンロードページを解析し sources.json を出力")
    sp.set_defaults(func=cmd_scrape)

    dp = sub.add_parser("download", help="GeoJSON zip を取得・展開（既取得の県はスキップ）")
    dp.add_argument("--pref", action="append", help="対象都道府県名（複数指定可）。省略で全県")
    dp.add_argument("--sleep", type=float, default=1.0, help="県ごとの待機秒")
    dp.add_argument("--force", action="store_true", help="変更が無くても再ダウンロードする")
    dp.set_defaults(func=cmd_download)

    cp = sub.add_parser("convert", help="GeoJSON を PMTiles に変換")
    cp.add_argument("--split", choices=["theme", "prefecture"], default="theme")
    cp.add_argument("--minzoom", type=int, default=4)
    cp.add_argument("--maxzoom", type=int, default=14)
    cp.add_argument("--extra", default="", help="tippecanoe への追加引数（スペース区切り）")
    cp.set_defaults(func=cmd_convert)

    kp = sub.add_parser("catalog", help="manifest / versions.json / CATALOG.md を生成")
    kp.add_argument("--split", choices=["theme", "prefecture"], default="theme")
    kp.add_argument("--release-url", default=None)
    kp.set_defaults(func=cmd_catalog)

    ap = sub.add_parser("all", help="scrape→download→convert→catalog を一括実行")
    ap.add_argument("--pref", action="append")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--force", action="store_true", help="変更が無くても再ダウンロードする")
    ap.add_argument("--split", choices=["theme", "prefecture"], default="theme")
    ap.add_argument("--minzoom", type=int, default=4)
    ap.add_argument("--maxzoom", type=int, default=14)
    ap.add_argument("--extra", default="")
    ap.add_argument("--release-url", default=None)
    ap.set_defaults(func=cmd_all)

    up = sub.add_parser("check-update", help="更新有無を判定（CI用）")
    up.add_argument("--github-output", default=None, help="GITHUB_OUTPUT ファイルパス")
    up.set_defaults(func=cmd_check_update)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
