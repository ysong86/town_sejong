# -*- coding: utf-8 -*-
"""읍면 생활인프라 상황판 소개 영상(약 30초, MP4) — 비밀번호 문에서 '미리보기'로 공개한다.

  python tools/make_video.py
    입력: http://127.0.0.1:8775/dashboard.html (launch.json sejong-town 서버, 평문은 로컬에만)
    출력: site/preview.mp4 (data/video_tmp 는 작업용)

공개 영상이라 숫자(지표·막대 값·카드 배수·표)는 흐리게 처리한다(화면 구성·지도 색은 보이게).
녹화 방식은 화재안전 상황판 tools/make_video.py 와 같다(설치된 Chrome, 가짜 포인터·클릭 물결·자막, hits.sh 차단).
"""
from __future__ import annotations

import glob
import os
import subprocess
import time

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = "http://127.0.0.1:8775/dashboard.html"
TMP = os.path.join(HERE, "data", "video_tmp")
SITE = os.path.join(HERE, "site", "preview.mp4")
W, H = 1440, 810

BLUR = r"""
(() => {
  const css = document.createElement('style');
  css.textContent = `
  .kpi .v,.kpi .c,.card .p,.card li .x,.card li .m,.br .v,td,.steps b,.tip,.refline span{filter:blur(5px)!important}`;
  document.head.appendChild(css);
})();
"""

OVERLAY = r"""
(() => {
  const css = document.createElement('style');
  css.textContent = `
  #vcur{position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;
        transform:translate(-3px,-2px);filter:drop-shadow(0 2px 3px rgba(0,0,0,.35))}
  .vring{position:fixed;width:46px;height:46px;margin:-23px 0 0 -23px;border-radius:50%;border:3px solid #152484;
         z-index:2147483646;pointer-events:none;animation:vr .6s ease-out forwards}
  @keyframes vr{from{transform:scale(.3);opacity:.9}to{transform:scale(1.4);opacity:0}}
  #vcap{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:2147483645;pointer-events:none;
        background:rgba(17,17,16,.9);color:#fff;font:700 21px/1.3 "IBM Plex Sans KR","Malgun Gothic",sans-serif;
        padding:10px 22px;letter-spacing:-.01em;opacity:0;transition:opacity .35s;white-space:nowrap}
  #vcap small{font-weight:400;font-size:15px;opacity:.85;margin-left:10px}
  html{scroll-behavior:auto!important}`;
  document.head.appendChild(css);
  const c = document.createElement('div'); c.id = 'vcur';
  c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M4 2l15 9.5-6.6 1.6 3.9 7.4-3.1 1.6-3.9-7.5L4 19.5z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  const cap = document.createElement('div'); cap.id = 'vcap'; document.body.appendChild(cap);
  document.addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  document.addEventListener('mousedown', e => {
    const r = document.createElement('div'); r.className = 'vring';
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    document.body.appendChild(r); setTimeout(() => r.remove(), 700);
  }, true);
  window.__cap = (t, s) => { cap.innerHTML = t + (s ? '<small>' + s + '</small>' : ''); cap.style.opacity = t ? 1 : 0; };
  window.__scroll = (y, ms) => new Promise(res => {
    const y0 = scrollY, t0 = performance.now(), ease = t => t < .5 ? 2*t*t : 1 - Math.pow(-2*t + 2, 2) / 2;
    (function step(now){ const k = Math.min(1, (now - t0) / ms); scrollTo(0, y0 + (y - y0) * ease(k));
      k < 1 ? requestAnimationFrame(step) : res(); })(t0);
  });
  window.__top = sel => { const el = document.querySelector(sel); return el ? el.getBoundingClientRect().top + scrollY : 0; };
})();
"""


def main():
    os.makedirs(TMP, exist_ok=True)
    for f in glob.glob(os.path.join(TMP, "*.webm")):
        os.remove(f)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=1, color_scheme="light",
                            record_video_dir=TMP, record_video_size={"width": W, "height": H})
        ctx.route("**/hits.sh/**", lambda r: r.abort())          # 녹화가 실제 조회수를 올리지 않게
        ctx.add_init_script("try{localStorage.clear()}catch(e){}")
        ctx.add_init_script(f"document.addEventListener('DOMContentLoaded', () => {{ {BLUR} }});")
        pg = ctx.new_page()
        t_open = time.time()
        pg.goto(SRC + "#acc", wait_until="networkidle")
        pg.wait_for_function("document.querySelectorAll('.cells rect').length > 100", timeout=60000)
        pg.evaluate(OVERLAY)
        pg.mouse.move(W * 0.55, H * 0.45)
        pg.wait_for_timeout(800)

        segs = []

        def now():
            return time.time() - t_open

        def hold(ms):
            t0 = now()
            pg.wait_for_timeout(ms)
            segs.append((t0, now()))

        def cap(t, s=""):
            pg.evaluate("([t,s]) => __cap(t,s)", [t, s])

        def scroll_to(sel, ms, off=70):
            y = pg.evaluate(f"__top('{sel}')") - off
            t0 = now()
            pg.evaluate(f"__scroll({max(0, y)}, {ms})")
            pg.wait_for_timeout(ms + 50)
            segs.append((t0, now()))

        def move(sel, steps=18, click=True, dx=0.5, dy=0.5):
            box = pg.locator(sel).first.bounding_box()
            x, y = box["x"] + box["width"] * dx, box["y"] + box["height"] * dy
            t0 = now()
            pg.mouse.move(x, y, steps=steps)
            if click:
                pg.mouse.down()
                pg.mouse.up()
                pg.wait_for_timeout(300)
            segs.append((t0, now()))

        cap("세종 읍면 생활인프라 격차 상황판", "읍면에서도 일상이 가까운가")
        hold(2400)
        cap("시설 개수가 아니라 시설까지 걸리는 시간·거리", "기준선은 언제나 동 지역 평균")
        move(".kpi:nth-child(2)", steps=16, click=False)
        hold(1800)

        cap("1읍 9면 프로필", "동 평균보다 가장 먼 시설 세 가지")
        scroll_to(".cards", 800, 90)
        move('.card[data-unit="전동면"]', steps=16, click=False)
        hold(1600)

        cap("① 생활SOC 접근성", "막대 = 차량 이동시간, 점선 = 동 평균")
        scroll_to(".tabs", 900, 0)
        hold(1400)
        cap("시설을 바꾸면 막대와 지도가 함께", "지도 색 = 동 평균의 몇 배인가")
        move('#kindchips [data-k="library"]', steps=16)
        hold(1600)
        move('#kindchips [data-k="pharm"]', steps=12)
        hold(1200)
        cap("읍면을 누르면 지도에 표시", "")
        move('#accbars .br', steps=14)
        hold(1200)
        move('.map .cells rect:nth-child(400)', steps=18, click=False)
        hold(1500)

        cap("③ 대중교통 사각지대", "정류장 400m 밖 주민 · 빗금 = 두루타 운행 읍면")
        move('[data-tab="bus"]', steps=16)
        hold(2600)

        cap("⑥ 공약 이행 트래커", "사업마다 계획→설계→착공→완료")
        move('[data-tab="pledge"]', steps=16)
        hold(2200)

        cap("출처·기준일과 추정 방법을 모두 밝혔습니다", "")
        pg.mouse.move(W * 0.92, H * 0.4, steps=8)
        scroll_to(".method", 1000, 120)
        hold(1800)
        cap("세종연구원 연구모임", "비밀번호 문의: 송양호(ysong@sri.re.kr)")
        hold(2000)

        video = pg.video.path()
        ctx.close()
        b.close()

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    merged = []
    for t0, t1 in sorted(segs):
        if merged and t0 - merged[-1][1] < 0.08:
            merged[-1] = (merged[-1][0], t1)
        else:
            merged.append((t0, t1))
    dur = sum(t1 - t0 for t0, t1 in merged)
    parts = "".join(f"[0:v]trim=start={t0:.3f}:end={t1:.3f},setpts=PTS-STARTPTS[v{i}];" for i, (t0, t1) in enumerate(merged))
    fc = parts + "".join(f"[v{i}]" for i in range(len(merged))) + f"concat=n={len(merged)}:v=1:a=0,fps=30,format=yuv420p[out]"
    os.makedirs(os.path.dirname(SITE), exist_ok=True)
    cmd = [ff, "-y", "-i", video, "-filter_complex", fc, "-map", "[out]", "-c:v", "libx264", "-preset", "slow", "-crf", "24",
           "-movflags", "+faststart", "-an", SITE]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"영상: {SITE}  ({dur:.1f}초, 구간 {len(merged)}개, {os.path.getsize(SITE) / 1e6:.1f}MB)")


if __name__ == "__main__":
    main()
