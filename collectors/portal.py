# -*- coding: utf-8 -*-
"""공공데이터포털 수집 — 인구·시설·버스정류장.

각 자료원은 `SOURCES` 한 줄. 받을 수 없으면(403 = 주소는 맞고 활용신청만 안 됨)
같은 자료를 이미 받아 둔 이웃 상황판 캐시(생활권 sejong_livingzone/data/raw)로 물러선다.
어느 쪽을 썼는지는 `status` 에 남겨 화면 '자료원' 표에 그대로 보인다.

인증키는 생활권 상황판에서 승인받은 포털 키(88자)를 config.json 의 portal.key 에 넣는다.
그 키로 승인된 것: 행안부 성·연령별 인구, 심평원 병원, TAGO 정류소, 체육시설, 상가정보.
아직 승인 안 된 것(2026-10-18 확인, 셋 다 403): 심평원 약국, TAGO 버스노선, 응급의료기관.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from .common import BASE_DIR, safe_url

RAW = os.path.join(BASE_DIR, "data", "raw")
SIBLING_RAW = os.path.join(os.path.dirname(BASE_DIR), "sejong_livingzone", "data", "raw")
SIBLING_LIB = os.path.join(os.path.dirname(BASE_DIR), "sejong_livingzone", "assets",
                           "sejong_libraries.json")

SEJONG = "%EC%84%B8%EC%A2%85%ED%8A%B9%EB%B3%84%EC%9E%90%EC%B9%98%EC%8B%9C"
SOURCES = {
    # 이름: (요청 주소, 응답 모양, 설명)
    "mois_age": ("https://apis.data.go.kr/1741000/admmSexdAgePpltn/selectAdmmSexdAgePpltn"
                 "?serviceKey={k}&admmCd=3611000000&srchFrYm={ym}&srchToYm={ym}&lv=3&regSeCd=1"
                 "&type=JSON&numOfRows=100&pageNo={page}", "mois", "행정안전부 행정동별 성·연령별 주민등록 인구"),
    "hira": ("https://apis.data.go.kr/B551182/hospInfoServicev2/getHospBasisList"
             "?serviceKey={k}&sidoCd=410000&_type=json&numOfRows=1000&pageNo={page}",
             "resp", "건강보험심사평가원 병원정보서비스"),
    "pharm": ("https://apis.data.go.kr/B551182/pharmacyInfoService/getParmacyBasisList"
              "?serviceKey={k}&sidoCd=410000&_type=json&numOfRows=1000&pageNo={page}",
              "resp", "건강보험심사평가원 약국정보서비스"),
    "tago": ("https://apis.data.go.kr/1613000/BusSttnInfoInqireService/getSttnNoList"
             "?serviceKey={k}&cityCode=12&_type=json&numOfRows=1000&pageNo={page}",
             "resp", "국토교통부 TAGO 버스정류소정보"),
    "route": ("https://apis.data.go.kr/1613000/BusRouteInfoInqireService/getRouteNoList"
              "?serviceKey={k}&cityCode=12&_type=json&numOfRows=1000&pageNo={page}",
              "resp", "국토교통부 TAGO 버스노선정보"),
    "ermct": ("https://apis.data.go.kr/B552657/ErmctInfoInqireService/getEgytListInfoInqire"
              "?serviceKey={k}&Q0=" + SEJONG + "&_type=json&numOfRows=100&pageNo={page}",
              "resp", "국립중앙의료원 응급의료기관 정보"),
    "kspo": ("https://apis.data.go.kr/B551014/SRVC_API_SFMS_FACI/TODZ_API_SFMS_FACI"
             "?serviceKey={k}&resultType=json&numOfRows=500&pageNo={page}&cp_nm=" + SEJONG,
             "resp", "국민체육진흥공단 전국체육시설"),
    "sbiz": ("https://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
             "?serviceKey={k}&divId=signguCd&key=36110&type=json&numOfRows=1000&pageNo={page}",
             "sbiz", "소상공인시장진흥공단 상가(상권)정보"),
}


def _ym(back: int) -> str:
    now = datetime.now()
    y, m = now.year, now.month - back
    while m <= 0:
        y, m = y - 1, m + 12
    return "%d%02d" % (y, m)


def _get(url: str, timeout: int = 60):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "sejong-town-dashboard/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:                                  # 타임아웃·연결 끊김
        return None, str(e).encode()


class Refused(Exception):
    """403/401 — 주소는 맞고 활용신청(승인)만 안 된 상태."""


def _json(url, tries=4):
    """포털은 가끔 타임아웃이나 빈 본문을 준다. 몇 번 다시 시도한다."""
    last = None
    for i in range(tries):
        code, body = _get(url)
        if code == 200:
            try:
                return json.loads(body)
            except ValueError:
                last = "JSON 아님: " + body[:80].decode("utf-8", "replace")
        elif code in (401, 403):
            raise Refused("HTTP %s" % code)
        else:
            last = "HTTP %s" % code
        time.sleep(2 * (i + 1))
    raise RuntimeError("%s — %s" % (safe_url(url.split("?")[0]), last))


def _pick(shape, d):
    """응답 모양별로 (이번 쪽 항목, 전체 건수)."""
    if shape == "mois":
        r = d["Response"]
        if r["head"]["resultCode"] != "0":
            return [], 0
        it = r["items"]["item"] if r.get("items") else []
        it = [it] if isinstance(it, dict) else it
        return it, int(r["head"].get("totalCount") or len(it))
    if shape == "sbiz":
        b = d["body"]
        return b.get("items") or [], int(b.get("totalCount", 0))
    b = d["response"]["body"]
    it = (b["items"].get("item") or []) if isinstance(b.get("items"), dict) else []
    return ([it] if isinstance(it, dict) else it), int(b.get("totalCount", 0))


def _paged(name, key, **kw):
    tpl, shape, _ = SOURCES[name]
    items, page = [], 1
    while True:
        got, total = _pick(shape, _json(tpl.format(k=urllib.parse.quote(key, safe=""),
                                                   page=page, **kw)))
        items += got
        if not got or len(items) >= total:
            return items
        page += 1


def _save(name, obj):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def _cached(name):
    """내 캐시 → 이웃(생활권) 캐시 순."""
    for folder, how in ((RAW, "직전 수집분"), (SIBLING_RAW, "생활권 상황판 캐시")):
        path = os.path.join(folder, name + ".json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                obj = json.load(f)
            stamp = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            return obj, "%s(%s)" % (how, stamp)
    return None, ""


def fetch(name, key):
    """한 자료원. 돌려주는 값: (자료, 상태 dict)."""
    label = SOURCES[name][2]
    st = {"id": name, "label": label, "api": SOURCES[name][0].split("?")[0]}
    if key:
        try:
            if name == "mois_age":
                for back in range(1, 5):          # 이번 달 자료는 다음 달 초에 올라온다
                    ym = _ym(back)
                    items = _paged(name, key, ym=ym)
                    if items:
                        break
                obj = {"ym": ym, "items": items}
            elif name == "sbiz":
                tpl = SOURCES[name][0]
                first = _json(tpl.format(k=urllib.parse.quote(key, safe=""), page=1))
                obj = {"stdrYm": first["header"].get("stdrYm"), "items": _paged(name, key)}
            else:
                obj = {"items": _paged(name, key)}
            _save(name, obj)
            st.update(state="ok", how="API 수집", n=len(obj["items"]))
            return obj, st
        except Refused as e:
            st.update(state="refused", why="%s · 주소 맞음, 활용신청 필요" % e)
        except Exception as e:                    # 수집 하나가 죽어도 나머지는 산다
            st.update(state="error", why=str(e)[:160])
    else:
        st.update(state="nokey", why="portal.key 없음")
    obj, how = _cached(name)
    if obj is not None:
        st.update(how=how, n=len(obj.get("items") or []))
        st["state"] = st["state"] + "+cache"
        return obj, st
    return None, st


def libraries():
    """전국도서관표준데이터(생활권 상황판에 사용자가 준 파일) — API 가 없어 파일을 그대로 쓴다."""
    for path in (os.path.join(BASE_DIR, "assets", "sejong_libraries.json"), SIBLING_LIB):
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f), {"id": "library", "label": "전국도서관표준데이터",
                                      "state": "file", "how": os.path.basename(path)}
    return None, {"id": "library", "label": "전국도서관표준데이터", "state": "missing"}
