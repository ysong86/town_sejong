# -*- coding: utf-8 -*-
"""세종 읍면동 지도 SVG — 물환경 상황판 sejong_map.py 의 투영·배경지도 규약을 그대로 따른다.

겹 구성 — 아래에서 위로
  0. 배경지도 자리(.basemap)   칩을 켜면 JS 가 타일을 채운다
  1. 접근성 격자(.cells)        JS 가 250m 격자를 칠한다(시설 종류를 바꿀 때마다)
  2. 읍면동 면(.ad)            assets/sejong_units.json — 생활권·화재 상황판과 같은 25개 행정동
  3. 두루타 구역(.drt)          빗금, 대중교통 탭에서만 보인다
  4. 시 외곽선
  5. 시설·정류장 점(.pts)       JS 가 채운다
  6. 읍면동 이름

투영 파라미터는 <svg data-lon0/lat1/kx/scale/offx/offy> 로 넘겨 JS 가 같은 식으로 좌표를 옮긴다.
"""
from __future__ import annotations

import json
import math
import os

from collectors.common import BASE_DIR

UNITS_FILE = os.path.join(BASE_DIR, "assets", "sejong_units.json")


class Projection:
    """등장방형 + 위도 보정. 시 하나 크기에서는 왜곡이 눈에 띄지 않는다."""

    def __init__(self, lon0, lat0, lon1, lat1, width, height, pad=16):
        self.lon0, self.lon1 = lon0, lon1
        self.lat0, self.lat1 = lat0, lat1
        self.k = math.cos(math.radians((lat0 + lat1) / 2))
        span_x = (lon1 - lon0) * self.k or 1e-6
        span_y = (lat1 - lat0) or 1e-6
        self.scale = min((width - pad * 2) / span_x, (height - pad * 2) / span_y)
        self.off_x = (width - span_x * self.scale) / 2
        self.off_y = (height - span_y * self.scale) / 2

    def __call__(self, lon, lat):
        return (self.off_x + (lon - self.lon0) * self.k * self.scale,
                self.off_y + (self.lat1 - lat) * self.scale)


def load_units():
    with open(UNITS_FILE, encoding="utf-8") as f:
        return json.load(f)


def _path(pj, ring):
    return "".join("%s%.1f,%.1f" % ("M" if i == 0 else "L", *pj(lon, lat))
                   for i, (lon, lat) in enumerate(ring)) + "Z"


def render(width=560, drt=(), cls="map") -> str:
    u = load_units()
    pts = [p for r in u["outline"] for p in r]
    lon0, lon1 = min(p[0] for p in pts), max(p[0] for p in pts)
    lat0, lat1 = min(p[1] for p in pts), max(p[1] for p in pts)
    k = math.cos(math.radians((lat0 + lat1) / 2))
    height = int(round(width * (lat1 - lat0) / ((lon1 - lon0) * k))) + 30
    pj = Projection(lon0, lat0, lon1, lat1, width, height - 30, pad=14)

    ads, labels, hatch = [], [], []
    for un in u["units"]:
        if not un.get("rings"):
            continue
        d = "".join(_path(pj, r) for r in un["rings"])
        ads.append('<path class="ad %s" data-dong="%s" d="%s" tabindex="0"/>' % (un["kind"], un["name"], d))
        if un["name"] in drt:
            hatch.append('<path d="%s"/>' % d)
        if un.get("label") and un["kind"] != "dong":
            x, y = pj(*un["label"])
            labels.append('<text class="cs nm" data-x="%.1f" data-y="%.1f" data-dong="%s" '
                          'transform="translate(%.1f,%.1f)" text-anchor="middle">%s</text>'
                          % (x, y, un["name"], x, y, un["name"]))
    outline = "".join('<path class="cityline" d="%s"/>' % _path(pj, r) for r in u["outline"])
    clip = '<clipPath id="cityclip-%s">%s</clipPath>' % (cls, "".join('<path d="%s"/>' % _path(pj, r) for r in u["outline"]))
    pat = ('<pattern id="hatch-%s" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="6" class="hl"/></pattern>' % cls)
    mpu = 111320.0 / pj.scale
    bx, by = width - 170, height - 26
    scalebar = ('<g class="scalebar" data-mpu="%.6f" data-x="%.1f" style="pointer-events:none">'
                '<text class="sb-label" x="%.1f" y="%.1f">—</text>'
                '<rect class="sb-bar" x="%.1f" y="%.1f" width="60" height="3"/>'
                '<rect class="sb-tick" x="%.1f" y="%.1f" width="1.4" height="8"/>'
                '<rect class="sb-tick sb-tick2" x="%.1f" y="%.1f" width="1.4" height="8"/></g>'
                % (mpu, bx, bx, by, bx, by + 6, bx, by + 3.5, bx + 58.6, by + 3.5))
    return ('<svg class="map" viewBox="0 0 %d %d" data-lon0="%.6f" data-lat1="%.6f" data-kx="%.8f" '
            'data-scale="%.4f" data-offx="%.3f" data-offy="%.3f" xmlns="http://www.w3.org/2000/svg">'
            '<defs>%s%s</defs><g class="zoom">'
            '<g class="basemap" aria-hidden="true"></g>'
            '<g class="cells" clip-path="url(#cityclip-%s)"></g>'
            '<g class="ads">%s</g>'
            '<g class="drt" fill="url(#hatch-%s)">%s</g>'
            '%s<g class="pts"></g><g class="names">%s</g></g>%s'
            '<text class="basemap-credit" x="12" y="%d"></text></svg>'
            % (width, height, pj.lon0, pj.lat1, pj.k, pj.scale, pj.off_x, pj.off_y,
               clip, pat, cls, "".join(ads), cls, "".join(hatch), outline, "".join(labels),
               scalebar, height - 10))
