# -*- coding: utf-8 -*-
"""수집 자료 → data/analysis.json (상황판이 읽는 단 하나의 파일).

거리·시간을 재는 방법
  수요 = 주거용 건물(단독·공동주택). 행정동 인구를 세대수(없으면 주거 연면적) 비례로 나눠 얹었다.
         건물·인구 배분·도로망은 화재안전 상황판(sejong_fire/data/analysis.json)을 그대로 쓴다.
  차량 = 전국표준노드링크 도로망 + ITS 실측 낮 시간대 속도. 건물→가까운 도로까지는 20km/h,
         직선의 1.3배(화재 상황판과 같은 가정). 시설도 같은 방식으로 도로에 붙인다.
  직선 = 건물에서 가장 가까운 시설까지 직선거리(km). 걷기·자전거 감각용.
  기준선 = 동 지역(행복도시 15개 행정동) 인구가중 평균. 읍면 값 ÷ 동 평균 = 배수.

  python analyze.py
"""
from __future__ import annotations

import csv
import heapq
import json
import math
import os
import sys
from collections import defaultdict

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from collectors.common import CollectError, load_config  # noqa: E402

DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
FIRE = os.path.join(os.path.dirname(HERE), "sejong_fire", "data", "analysis.json")
UNITS = os.path.join(HERE, "assets", "sejong_units.json")

KX, KY = 89500.0, 111000.0             # 북위 36.5° 에서 경도·위도 1도의 미터
CELL = 250                             # 지도 격자 한 변(m) — 화재 상황판과 같은 격자
ACCESS_KMH, DETOUR = 20.0, 1.3         # 건물·시설 ↔ 가까운 도로 구간 가정(화재 상황판과 같다)
SLOT = 6                               # edges 열: [a, b, 제한속도, 심야, 출근, 퇴근, 낮] → 낮(평시)
STOP_M = 400                           # 버스정류장 도보권

# 시설 종류 — 순서가 화면 순서다. src 는 화면 출처 표기.
KINDS = [
    ("clinic", "병·의원"),
    ("pharm", "약국"),
    ("daycare", "어린이집"),
    ("library", "도서관"),
    ("sports", "공공체육시설"),
    ("mart", "대형마트"),
]
CLINIC_TYPES = {"의원", "병원", "종합병원", "보건소", "보건지소", "보건진료소"}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def raw(name):
    p = os.path.join(RAW, name + ".json")
    return load(p) if os.path.exists(p) else None


# ── 시 경계 ──────────────────────────────────────────────────
def inside(x, y, ring):
    c = False
    for i in range(len(ring) - 1):
        (x1, y1), (x2, y2) = ring[i][:2], ring[i + 1][:2]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / ((y2 - y1) or 1e-12):
            c = not c
    return c


class Units:
    def __init__(self):
        u = load(UNITS)
        self.units = u["units"]
        self.names = [x["name"] for x in self.units]
        self.outline = u["outline"]

    def of(self, x, y):
        for i, un in enumerate(self.units):
            if any(inside(x, y, r) for r in un["rings"]):
                return i
        return -1

    def in_city(self, x, y):
        return any(inside(x, y, r) for r in self.outline)


# ── 시설 ─────────────────────────────────────────────────────
def facilities(status):
    """종류 → [(경도, 위도, 이름)]. 자료가 없는 종류는 빈 목록 + note."""
    out, notes = {k: [] for k, _ in KINDS}, {}

    h = raw("hira")
    for it in (h or {}).get("items", []):
        if it.get("clCdNm") in CLINIC_TYPES and it.get("XPos"):
            out["clinic"].append((float(it["XPos"]), float(it["YPos"]), it.get("yadmNm") or it.get("clCdNm")))
    notes["clinic"] = "심평원 병원정보 — 의원·병원·종합병원·보건소·보건지소·보건진료소(치과·한방·요양병원 제외)"

    ph = raw("pharm")
    if ph and ph.get("items"):
        for it in ph["items"]:
            if it.get("XPos"):
                out["pharm"].append((float(it["XPos"]), float(it["YPos"]), it.get("yadmNm", "약국")))
        notes["pharm"] = "심평원 약국정보"
    else:
        sb = raw("sbiz")
        for it in (sb or {}).get("items", []):
            if it.get("indsSclsNm") == "약국" and it.get("lon"):
                out["pharm"].append((float(it["lon"]), float(it["lat"]), it.get("bizesNm", "약국")))
        notes["pharm"] = ("소상공인 상가정보의 '약국' 업종(%s 기준) — 심평원 약국정보 활용신청 전 임시"
                          % ((sb or {}).get("stdrYm") or ""))

    dc = raw("daycare")
    if dc and dc.get("items"):
        for it in dc["items"]:
            if it.get("lon") and it.get("lat"):
                out["daycare"].append((float(it["lon"]), float(it["lat"]), it.get("name", "어린이집")))
        notes["daycare"] = dc.get("source") or "어린이집 정보"

    lib = load(os.path.join(HERE, "assets", "sejong_libraries.json"))
    for r in lib.get("records", []):
        if r.get("위도"):
            out["library"].append((float(r["경도"]), float(r["위도"]), r["도서관명"]))
    notes["library"] = ("전국도서관표준데이터(2025-08-31) — 공공 15·작은도서관 9곳. 읍면 도서관은 대부분 작은도서관으로 "
                        "등록돼 있어 함께 넣었다. 아파트 단지 작은도서관은 거의 등록돼 있지 않다")

    k = raw("kspo")
    for it in (k or {}).get("items", []):
        if it.get("faci_gb_nm") == "공공" and it.get("faci_stat_nm") != "폐업" and it.get("faci_lat"):
            out["sports"].append((float(it["faci_lot"]), float(it["faci_lat"]), it.get("faci_nm") or it.get("ftype_nm")))
    notes["sports"] = "국민체육진흥공단 전국체육시설 — 공공 시설 중 운영 중인 것"

    mt = raw("mart")
    if mt and mt.get("items"):
        for it in mt["items"]:
            out["mart"].append((float(it["lon"]), float(it["lat"]), it.get("name", "대형마트")))
        notes["mart"] = mt.get("source") or "대규모점포"
    return out, notes


# ── 도로망·건물(화재 상황판) ─────────────────────────────────
def network():
    if not os.path.exists(FIRE):
        raise CollectError("화재 상황판 분석 결과가 없습니다: %s" % FIRE)
    a = load(FIRE)
    n = len(a["nodes"])
    adj = [[] for _ in range(n)]
    for e in a["edges"]:
        adj[e[1]].append((e[0], e[SLOT]))   # 시설 → 집 방향이 아니라 집 → 시설 시간이 필요하므로 뒤집어 건다
    return a, adj


def dijkstra_multi(adj, sources):
    """여러 출발점 → 모든 노드 최단시간(초). sources: [(노드, 출발 시각 보정초)]."""
    dist = [math.inf] * len(adj)
    h = []
    for s, t0 in sources:
        if t0 < dist[s]:
            dist[s] = t0
            h.append((t0, s))
    heapq.heapify(h)
    while h:
        d, u = heapq.heappop(h)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                heapq.heappush(h, (nd, v))
    return dist


class Snap:
    """가까운 도로 노드. 건물이 실제로 붙어 있는 노드(=주 도로망)만 후보로 쓴다."""

    def __init__(self, nodes, ok):
        self.nodes = nodes
        self.c = defaultdict(list)
        for i in ok:
            x, y = nodes[i]
            self.c[(int(x * KX / 300), int(y * KY / 300))].append(i)

    def near(self, x, y):
        cx, cy = int(x * KX / 300), int(y * KY / 300)
        for r in range(0, 40):
            best, bd = None, math.inf
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    for i in self.c.get((cx + dx, cy + dy), ()):
                        nx, ny = self.nodes[i]
                        d = math.hypot((nx - x) * KX, (ny - y) * KY)
                        if d < bd:
                            best, bd = i, d
            if best is not None and bd <= (r + 1) * 300:
                return best, bd
        return None, math.inf


def nearest_km(bx, by, pts):
    """건물마다 가장 가까운 점까지 직선(km)."""
    if not pts:
        return None
    px = np.array([p[0] for p in pts]) * KX
    py = np.array([p[1] for p in pts]) * KY
    out = np.empty(len(bx))
    for s in range(0, len(bx), 4000):
        dx = bx[s:s + 4000, None] * KX - px[None, :]
        dy = by[s:s + 4000, None] * KY - py[None, :]
        out[s:s + 4000] = np.sqrt(dx * dx + dy * dy).min(axis=1) / 1000
    return out


# ── 인구 ─────────────────────────────────────────────────────
def population(names):
    m = raw("mois_age")
    if not m:
        return None, None
    pop, o65, o70, kid = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)
    for it in m["items"]:
        if it.get("tong") or it.get("ban"):
            continue
        nm = it["dongNm"]
        nm = "도담·어진동" if nm in ("도담동", "어진동") else nm
        g = lambda a: sum(int(it.get("%s%dAgeNmprCnt" % (s, a)) or 0) for s in ("male", "feml"))
        pop[nm] += int(it["totNmprCnt"])
        o70[nm] += sum(g(a) for a in (70, 80, 90, 100))
        kid[nm] += g(0)
    out = {}
    for nm in names:
        p = pop.get(nm, 0)
        out[nm] = {"pop": p, "old70": o70.get(nm, 0), "kid": kid.get(nm, 0),
                   "s70": round(o70[nm] / p * 100, 1) if p else None,
                   "skid": round(kid[nm] / p * 100, 1) if p else None}
    return out, m.get("ym")


# ── 버스 ─────────────────────────────────────────────────────
def bus_stops(units):
    t = raw("tago")
    pts = []
    for it in (t or {}).get("items", []):
        x, y = it.get("gpslong"), it.get("gpslati")
        if x and y and units.in_city(float(x), float(y)):       # TAGO 세종(12)에 청주 정류장이 섞여 온다
            pts.append((float(x), float(y), it.get("nodenm", "")))
    return pts


def drt_zones():
    """config.json 의 drt.zones(읍면 이름 목록). 운행 구역 도형이 공개돼 있지 않아 읍면 단위로 적는다."""
    try:
        cfg = load_config()
    except CollectError:
        return {}
    return (cfg.get("drt") or {})


RURAL_WORDS = ["조치원", "연기", "연동", "부강", "금남", "장군", "연서", "전의", "전동", "소정",
               "명학", "용담리", "해정리", "대곡리", "신안리", "번암리", "부강역", "봉안"]


def bus_ops():
    """세종_버스운행 현황(공공데이터포털 3077230, 파일) — 노선별 배차간격·운행횟수. 원문 표기 그대로."""
    path = os.path.join(HERE, "assets", "sejong_bus_ops.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        stops = " ".join(r.get(k) or "" for k in ("기점지", "경유지", "종점지"))
        hit = [w for w in RURAL_WORDS if w in stops]
        out.append({"type": r.get("구분", ""), "no": r.get("노선번호", ""), "from": r.get("기점지", ""),
                    "via": r.get("경유지", ""), "to": r.get("종점지", ""), "gap": r.get("배차간격", ""),
                    "runs": r.get("운행횟수", ""), "rural": bool(hit)})
    return out


# ── 공약 ─────────────────────────────────────────────────────
STAGES = ["미확인", "계획", "설계", "착공", "완료"]


def pledges():
    path = os.path.join(HERE, "assets", "pledges.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if (r.get("사업명") or "").strip()]
    for r in rows:
        r["단계"] = (r.get("단계") or "미확인").strip()
        if r["단계"] not in STAGES:
            r["단계"] = "미확인"
    return rows


# ── 본체 ─────────────────────────────────────────────────────
def main():
    units = Units()
    names = units.names
    kind_of = {u["name"]: u["kind"] for u in units.units}
    dongs = [i for i, u in enumerate(units.units) if u["kind"] == "dong"]

    a, adj = network()
    nodes = a["nodes"]
    cols = a["bcols"]
    ix = {c: i for i, c in enumerate(cols)}
    # 주거 건물만 수요로
    B = [b for b in a["b"] if b[ix["u"]] in ("01", "02") and b[ix["pp"]] > 0]
    pop, pop_ym = population(names)
    if pop:   # 화재 상황판 배분 시점보다 새 인구가 있으면 행정동 합계를 새 값으로 맞춘다
        old = defaultdict(float)
        for b in B:
            old[b[ix["d"]]] += b[ix["pp"]]
        scale = {d: (pop[names[d]]["pop"] / v if v else 0) for d, v in old.items()}
    else:
        pop = {d["name"]: {"pop": d["pop"], "old70": d["old70"], "kid": None, "s70": d["share"], "skid": None}
               for d in a["dongs"]}
        pop_ym = a.get("pop_ym")
        scale = defaultdict(lambda: 1.0)
    w = np.array([b[ix["pp"]] * scale[b[ix["d"]]] for b in B])
    d_of = np.array([b[ix["d"]] for b in B])
    bx = np.array([b[ix["x"]] for b in B])
    by = np.array([b[ix["y"]] for b in B])
    bn = [b[ix["n"]] for b in B]
    bac = np.array([b[ix["ac"]] for b in B], dtype=float)

    ok_nodes = sorted(set(bn))
    snap = Snap(nodes, ok_nodes)
    acc_ms = ACCESS_KMH / 3.6

    fac, notes = facilities(None)
    kinds = []
    T, K = {}, {}
    for kid, label in KINDS:
        pts = [p for p in fac[kid] if units.in_city(p[0], p[1])]
        fac[kid] = pts
        kinds.append({"id": kid, "label": label, "n": len(pts), "src": notes.get(kid, ""),
                      "ready": bool(pts)})
        if not pts:
            continue
        src = []
        for x, y, _ in pts:
            k, d = snap.near(x, y)
            if k is not None:
                src.append((k, d * DETOUR / acc_ms))
        dist = dijkstra_multi(adj, src)
        t = np.array([dist[n] for n in bn]) + bac
        T[kid] = t / 60.0                               # 분
        K[kid] = nearest_km(bx, by, pts)

    stops = bus_stops(units)
    sk = nearest_km(bx, by, stops) if stops else None

    # 읍면동별 인구가중 평균
    def wavg(v, mask):
        ww = w[mask]
        return float((v[mask] * ww).sum() / ww.sum()) if ww.sum() else None

    dong_mask = np.isin(d_of, dongs)
    base = {}
    for kid in T:
        base[kid] = {"min": round(wavg(T[kid], dong_mask), 1), "km": round(wavg(K[kid], dong_mask), 2)}
    out_units = []
    for i, nm in enumerate(names):
        m = d_of == i
        pinfo = pop.get(nm) or {}
        row = {"name": nm, "kind": kind_of[nm], "pop": pinfo.get("pop"), "s70": pinfo.get("s70"),
               "skid": pinfo.get("skid"), "old70": pinfo.get("old70"), "acc": {}, "bus": None,
               "km2": units.units[i].get("km2")}
        if m.sum():
            for kid in T:
                mn, km = wavg(T[kid], m), wavg(K[kid], m)
                row["acc"][kid] = {"min": round(mn, 1), "km": round(km, 2),
                                   "x": round(mn / base[kid]["min"], 2) if base[kid]["min"] else None,
                                   "p15": round(float(w[m][T[kid][m] > 15].sum() / w[m].sum() * 100), 1)}
            if sk is not None:
                far = sk[m] > STOP_M / 1000
                row["bus"] = {"out": round(float(w[m][far].sum())), "share": round(float(w[m][far].sum() / w[m].sum() * 100), 1),
                              "km": round(wavg(sk, m), 2)}
        # 가장 먼 시설 셋(동 평균 대비 배수가 큰 순)
        ranked = sorted(((v["x"] or 0, k) for k, v in row["acc"].items()), reverse=True)
        row["worst"] = [k for _, k in ranked[:3]]
        out_units.append(row)

    bus_base = None
    if sk is not None:
        far = sk[dong_mask] > STOP_M / 1000
        bus_base = {"share": round(float(w[dong_mask][far].sum() / w[dong_mask].sum() * 100), 1),
                    "km": round(wavg(sk, dong_mask), 2)}
    # 읍면 전체(1읍 9면) 묶음 — 첫 화면 숫자용
    rural_mask = ~dong_mask
    rural = {"pop": int(sum((pop.get(n) or {}).get("pop") or 0 for n in names if kind_of[n] != "dong")),
             "acc": {kid: {"min": round(wavg(T[kid], rural_mask), 1), "km": round(wavg(K[kid], rural_mask), 2)} for kid in T}}
    if sk is not None:
        far = sk[rural_mask] > STOP_M / 1000
        rural["bus"] = {"out": round(float(w[rural_mask][far].sum())),
                        "share": round(float(w[rural_mask][far].sum() / w[rural_mask].sum() * 100), 1)}

    # 지도 격자(250m) — 인구가중 평균 시간·거리
    ox, oy = a["origin"]
    gx = ((bx - ox) * KX // CELL).astype(int)
    gy = ((by - oy) * KY // CELL).astype(int)
    cells = defaultdict(lambda: {"w": 0.0, "d": None})
    acc_cols = list(T)
    sums = defaultdict(lambda: np.zeros(len(acc_cols) * 2 + 1))
    cw = defaultdict(float)
    cd = {}
    for j in range(len(B)):
        key = (int(gx[j]), int(gy[j]))
        ww = w[j]
        if ww <= 0:
            continue
        cw[key] += ww
        cd.setdefault(key, defaultdict(float))[int(d_of[j])] += ww
        vec = [T[k][j] for k in acc_cols] + [K[k][j] for k in acc_cols] + [1.0 if (sk is not None and sk[j] > STOP_M / 1000) else 0.0]
        sums[key] += np.array(vec) * ww
    grid = []
    for key, ww in cw.items():
        v = sums[key] / ww
        d = max(cd[key].items(), key=lambda kv: kv[1])[0]
        grid.append([key[0], key[1], round(ww, 1), d]
                    + [round(float(x), 1) for x in v[:len(acc_cols)]]
                    + [round(float(x), 2) for x in v[len(acc_cols):2 * len(acc_cols)]]
                    + [round(float(v[-1]) * ww, 1)])

    res = {
        "built": __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pop_ym": pop_ym,
        "method": {"cell": CELL, "access_kmh": ACCESS_KMH, "detour": DETOUR, "stop_m": STOP_M,
                   "slot": "낮(평시)", "its": a["net"]["snapshots"].get("day", [])[:1] + a["net"]["snapshots"].get("day", [])[-1:],
                   "its_cov": a["net"]["coverage"].get("day"), "fire_built": a.get("built"),
                   "n_res": len(B)},
        "origin": [ox, oy], "kx": KX, "ky": KY,
        "kinds": kinds, "acc_cols": acc_cols, "base": base, "rural": rural,
        "units": out_units, "bus_base": bus_base, "drt": drt_zones(),
        "grid": grid,
        "fac": {k: [[round(x, 5), round(y, 5), nm] for x, y, nm in v] for k, v in fac.items()},
        "stops": [[round(x, 5), round(y, 5), nm] for x, y, nm in stops],
        "pledges": pledges(),
        "bus_ops": bus_ops(),
    }
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    print("분석 → data/analysis.json  (주거 건물 %d, 격자 %d, 정류장 %d)" % (len(B), len(grid), len(stops)))
    for kd in kinds:
        print("  %-8s %4d곳  %s" % (kd["label"], kd["n"], "" if kd["ready"] else "← 자료 대기"))
    return res


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
