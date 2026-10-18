# -*- coding: utf-8 -*-
"""세종 읍면 생활인프라 격차 상황판 — 실행기.

  python run.py --collect      포털 API 수집(안 되면 이웃 상황판 캐시) → 분석 → 상황판
  python run.py --analyze      받아 둔 자료로 분석 → 상황판
  python run.py --dashboard    data/analysis.json 으로 HTML 만 다시
  python run.py --probe        포털 자료원마다 승인 여부(200/403/400)만 확인
  --out site                   site/index.html 로도 저장(배포본)

시설 위치는 분기마다 --collect, 공약 트래커(assets/pledges.csv)는 고칠 때마다 --analyze.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import analyze
import build_dashboard
from collectors import portal
from collectors.common import CollectError, load_config, load_json, now_kst, save_json, stamp

ORDER = ["mois_age", "hira", "pharm", "tago", "route", "ermct", "kspo", "sbiz"]
STATE_TEXT = {"ok": "됨", "refused": "활용신청 필요", "error": "실패", "nokey": "키 없음"}


def _key(cfg):
    return ((cfg.get("portal") or {}).get("key") or "").strip()


def collect(cfg) -> list:
    key = _key(cfg)
    status = []
    for name in ORDER:
        print("  - %-9s" % name, end="", flush=True)
        _, st = portal.fetch(name, key)
        base = st["state"].split("+")[0]
        print(" %s%s%s" % (STATE_TEXT.get(base, base),
                           (" · " + st["how"]) if st.get("how") else "",
                           (" · %d건" % st["n"]) if st.get("n") is not None else ""))
        st["at"] = stamp(now_kst())
        status.append(st)
    _, lib = portal.libraries()
    status.append(lib)
    save_json("sources.json", status)
    return status


def probe(cfg) -> int:
    key = _key(cfg)
    if not key:
        print("config.json 의 portal.key 가 비어 있습니다.")
        return 1
    import urllib.parse
    for name in ORDER:
        tpl = portal.SOURCES[name][0]
        url = tpl.format(k=urllib.parse.quote(key, safe=""), page=1, ym=portal._ym(2))
        code, body = portal._get(url)
        meaning = {200: "됨", 403: "주소 맞음 · 활용신청 필요", 401: "키 오류",
                   400: "주소·파라미터 틀림", 404: "주소 없음"}.get(code, "확인 필요")
        print("%-9s %s  %s  — %s" % (name, code, meaning, portal.SOURCES[name][2]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="세종 읍면 생활인프라 격차 상황판")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--dashboard", action="store_true")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--out", default=None, help="배포용 디렉터리. <디렉터리>/index.html 로도 저장")
    args = ap.parse_args(argv)
    if not any([args.collect, args.analyze, args.dashboard, args.probe]):
        args.dashboard = True

    cfg = load_config()
    if args.probe:
        return probe(cfg)
    if args.collect:
        print("수집 시작 %s" % stamp(now_kst()))
        collect(cfg)
    if args.collect or args.analyze:
        analyze.main()
    data = load_json("analysis.json")
    if not data:
        print("data/analysis.json 이 없습니다. --collect 또는 --analyze 를 먼저 실행하세요.")
        return 1
    data["sources"] = load_json("sources.json", [])
    data["site"] = cfg.get("site") or {}
    path = build_dashboard.write(data)
    if args.out:
        os.makedirs(args.out, exist_ok=True)
        build_dashboard.write(data, os.path.join(args.out, "index.html"))
        print("배포본 → %s" % os.path.join(args.out, "index.html"))
    print("상황판 → %s" % path)
    if args.open:
        webbrowser.open("file:///" + path.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CollectError as exc:
        print("\n%s" % exc)
        sys.exit(1)
