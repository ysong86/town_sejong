# -*- coding: utf-8 -*-
"""data/analysis.json → dashboard.html (파일 하나, 바깥 의존은 글꼴·배경지도 타일·조회수 배지뿐).

화면 규칙(작업 브리프)
  - 모든 지표는 시설 개수가 아니라 거리·시간. 기준선은 언제나 '동 지역 평균'.
  - 색은 대문 토큰(종이색 #F3F2EE, 남색 강조 #152484 / 다크 #8EA0F2). 격차는 한 가지 계열,
    동 평균보다 멀수록 진하게.
  - 지표마다 출처·기준일을 바로 아래 작은 글씨로. 추정치에는 '(연구진 추정)'.
  - 모바일은 카드 → 지도 세로 배치.
"""
from __future__ import annotations

import html
import json
import os

import sejong_map
from collectors.common import BASE_DIR

OUT_PATH = os.path.join(BASE_DIR, "dashboard.html")
TITLE = "세종 읍면 생활인프라 격차 상황판"
QUESTION = "읍면에서도 일상이 가까운가"

TABS = [
    ("acc", "① 생활SOC 접근성", "집에서 일상 시설까지 몇 분인가", True),
    ("care", "② 의료·돌봄 공백", "아프면 제때 닿는가", False),
    ("bus", "③ 대중교통 사각지대", "버스로 갈 수 있는가", True),
    ("edu", "④ 교육·아동", "아이를 키울 수 있는가", False),
    ("base", "⑤ 기초 생활기반", "물·가스·하수는 들어오는가", False),
    ("pledge", "⑥ 공약 이행 트래커", "약속은 어디까지 왔나", True),
]
LATER = {
    "care": ["응급실 30분 밖 인구", "고령자 1천 명당 의료기관·경로당·방문요양"],
    "edu": ["학교별 학생 수 추이·소규모 학교", "통학 거리", "돌봄시설"],
    "base": ["상수도·도시가스 보급률", "하수처리구역 편입률"],
}


def esc(v) -> str:
    return html.escape("" if v is None else str(v))


FONT = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:'
        'wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">')

CSS = r"""
:root{--paper:#F3F2EE;--panel:#FBFAF7;--ink:#111110;--ink2:#4A4A47;--ink3:#8B8A85;--rule:#11111022;--rule2:#1111110F;
  --accent:#152484;--accent-rgb:21,36,132;--warn:#8A5A12;--bar:rgba(243,242,238,.94);--tipbg:#111110;--tipink:#F3F2EE}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--paper:#0F0F0E;--panel:#161615;--ink:#EDECE8;--ink2:#B2B1AC;
  --ink3:#76756F;--rule:#EDECE826;--rule2:#EDECE812;--accent:#8EA0F2;--accent-rgb:142,160,242;--warn:#E9B865;--bar:rgba(15,15,14,.94);
  --tipbg:#EDECE8;--tipink:#0F0F0E;color-scheme:dark}}
:root[data-theme="dark"]{--paper:#0F0F0E;--panel:#161615;--ink:#EDECE8;--ink2:#B2B1AC;--ink3:#76756F;--rule:#EDECE826;--rule2:#EDECE812;
  --accent:#8EA0F2;--accent-rgb:142,160,242;--warn:#E9B865;--bar:rgba(15,15,14,.94);--tipbg:#EDECE8;--tipink:#0F0F0E;color-scheme:dark}
*{box-sizing:border-box}
html,body{margin:0}
body{background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans KR","Malgun Gothic",system-ui,sans-serif;line-height:1.55;
  word-break:keep-all;-webkit-font-smoothing:antialiased}
a{color:inherit}
button{font:inherit;color:inherit;cursor:pointer}
.mono,.num{font-family:"IBM Plex Mono",ui-monospace,monospace;letter-spacing:.01em;font-variant-numeric:tabular-nums}
.wrap{max-width:1320px;margin:0 auto;padding:0 32px 48px}
.mast{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 0;border-bottom:1px solid var(--ink)}
.mast .brand{font-size:12.5px;letter-spacing:.04em}
.mast .brand b{font-weight:700}
.mast .brand span{color:var(--ink3);margin-left:10px;letter-spacing:.14em;font-size:11px}
.theme-toggle{display:flex;gap:2px;border:1px solid var(--rule);padding:2px}
.theme-toggle button{border:0;background:none;padding:3px 9px;font-size:12px;color:var(--ink3)}
.theme-toggle button.on{background:var(--ink);color:var(--paper)}
.hero{padding:34px 0 26px;border-bottom:1px solid var(--rule)}
.hero .kick{font-size:12px;color:var(--ink3);letter-spacing:.14em;margin-bottom:10px}
.hero h1{margin:0 0 16px;font-size:clamp(30px,4.4vw,60px);line-height:1.05;letter-spacing:-.04em;font-weight:700}
.hero h1 em{font-style:normal;color:var(--accent)}
.hero .lede{max-width:860px;margin:0;font-size:15px;color:var(--ink2)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:0;margin-top:26px;border-top:1px solid var(--ink)}
.kpi{padding:14px 18px 12px 0;border-right:1px solid var(--rule)}
.kpi+.kpi{padding-left:18px}
.kpi:last-child{border-right:0}
.kpi .l{font-size:12.5px;color:var(--ink2)}
.kpi .v{font-size:32px;font-weight:500;letter-spacing:-.02em;font-family:"IBM Plex Mono",monospace;margin:4px 0 2px}
.kpi .v small{font-size:14px;color:var(--ink3);margin-left:4px;font-family:"IBM Plex Sans KR",sans-serif}
.kpi .c{font-size:12.5px;color:var(--ink2)}
.kpi .c b{color:var(--accent);font-weight:600}
.src{font-size:11.5px;color:var(--ink3);margin-top:6px;line-height:1.45}
.est{color:var(--warn);font-size:11.5px;white-space:nowrap}
h2{font-size:13px;letter-spacing:.14em;color:var(--ink3);font-weight:500;margin:34px 0 12px;padding-bottom:8px;border-bottom:1px solid var(--ink)}
h2 b{color:var(--ink);letter-spacing:0;font-size:17px;margin-right:10px}
/* 읍면 프로필 카드 */
.cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0;border-left:1px solid var(--rule);border-top:1px solid var(--rule)}
.card{border-right:1px solid var(--rule);border-bottom:1px solid var(--rule);padding:12px 14px 12px;background:none;text-align:left;
  display:flex;flex-direction:column;gap:6px;min-width:0}
.card:hover,.card.on{background:var(--panel)}
.card.on{box-shadow:inset 0 0 0 2px var(--accent)}
.card .t{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.card .t b{font-size:18px;letter-spacing:-.02em}
.card .t span{font-size:11.5px;color:var(--ink3)}
.card .p{font-size:12.5px;color:var(--ink2)}
.card .p .num{color:var(--ink)}
.card ol{margin:2px 0 0;padding:0;list-style:none;display:flex;flex-direction:column;gap:3px}
.card li{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:6px;font-size:12.5px;align-items:baseline}
.card li .x{font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--accent);font-weight:500}
.card li .m{color:var(--ink3);font-size:11.5px}
/* 탭 */
.tabs{display:flex;gap:0;flex-wrap:wrap;border-bottom:1px solid var(--ink);margin-top:34px;position:sticky;top:0;z-index:20;background:var(--bar);
  backdrop-filter:blur(6px)}
.tab{border:0;background:none;padding:12px 16px 10px;font-size:14px;font-weight:600;color:var(--ink2);border-bottom:3px solid transparent;margin-bottom:-1px}
.tab small{display:block;font-size:11px;font-weight:400;color:var(--ink3)}
.tab.on{color:var(--ink);border-bottom-color:var(--accent)}
.tab.later{color:var(--ink3)}
.tab.later::after{content:"2단계";font-size:10px;margin-left:6px;padding:1px 5px;border:1px solid var(--rule);color:var(--ink3);font-weight:500;vertical-align:2px}
.grid{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:28px;margin-top:22px;align-items:start}
.pane{display:none}
.pane.on{display:block}
.mapcol{position:sticky;top:64px}
.ctl{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-bottom:12px}
.ctl .lab{font-size:11.5px;color:var(--ink3);letter-spacing:.1em;margin-right:4px}
.chip{border:1px solid var(--rule);background:none;padding:5px 11px;font-size:13px;border-radius:0}
.chip.on{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.chip[disabled]{color:var(--ink3);border-style:dashed;cursor:not-allowed}
.chip[disabled]::after{content:" · 대기";font-size:11px}
.q{font-size:22px;font-weight:600;letter-spacing:-.02em;margin:0 0 4px}
.q+p{margin:0 0 14px;color:var(--ink2);font-size:14px}
/* 격차 막대 */
.bars{position:relative;margin:6px 0 4px}
.br{display:grid;grid-template-columns:72px minmax(0,1fr) 96px;gap:10px;align-items:center;height:28px;cursor:pointer}
.br .n{font-size:13px}
.br .trk{position:relative;height:100%}
.br .fill{position:absolute;left:0;top:7px;height:14px;background:var(--accent);border-radius:0 4px 4px 0}
.br .v{font-family:"IBM Plex Mono",monospace;font-size:12.5px;text-align:right}
.br .v small{color:var(--ink3);margin-left:4px}
.br:hover .n,.br.on .n{color:var(--accent);font-weight:600}
.br.on .fill{box-shadow:0 0 0 2px var(--paper),0 0 0 3.5px var(--accent)}
.br.dong .fill{background:var(--ink3)}
.refline{position:absolute;top:-6px;bottom:-4px;width:0;border-left:1.5px dashed var(--ink);pointer-events:none}
.refline span{position:absolute;top:-16px;left:4px;font-size:11px;color:var(--ink2);white-space:nowrap}
/* 지도 */
.mapbox{position:relative;border:1px solid var(--rule);background:var(--panel)}
.map{display:block;width:100%;height:auto;max-height:calc(100vh - 170px);touch-action:none;user-select:none}
@media (max-width:1000px){.map{max-height:none}}
.map .ad{fill:transparent;stroke:var(--ink3);stroke-width:calc(.6px * var(--zw,1));vector-effect:non-scaling-stroke;cursor:pointer}
.map .ad.dong{stroke-dasharray:2 2;stroke:var(--ink3)}
.map .ad:hover{fill:rgba(var(--accent-rgb),.06)}
.map .ad.on{stroke:var(--accent);stroke-width:2.2px;stroke-dasharray:none}
.map .cityline{fill:none;stroke:var(--ink);stroke-width:1.2px;vector-effect:non-scaling-stroke}
.map .cells rect{stroke:none;shape-rendering:crispEdges}
.map .drt{display:none;pointer-events:none}
.map.mode-bus .drt{display:inline}
.map .hl{stroke:var(--accent);stroke-width:1.1;opacity:.55}
.map .nm{font-size:12px;font-weight:600;fill:var(--ink);paint-order:stroke;stroke:var(--panel);stroke-width:3px;pointer-events:none}
.map .pts circle{fill:var(--paper);stroke:var(--ink);stroke-width:1.2px;vector-effect:non-scaling-stroke}
.map .pts circle.stop{fill:var(--ink);stroke:none}
.map .sb-label{font-size:11px;fill:var(--ink2)}
.map .sb-bar,.map .sb-tick{fill:var(--ink2)}
.map .basemap-credit{font-size:10px;fill:var(--ink3)}
.map.has-base .ad{fill:transparent}
.map.has-base .cells{opacity:.85}
.zoombtns{position:absolute;right:10px;top:10px;display:flex;flex-direction:column;gap:2px;z-index:3}
.zoombtns button{width:30px;height:28px;border:1px solid var(--rule);background:var(--paper);font-size:15px;padding:0}
.maptools{display:flex;flex-wrap:wrap;gap:6px;align-items:center;padding:8px 10px;border-top:1px solid var(--rule);font-size:12px}
.legend{display:flex;align-items:center;gap:0;flex-wrap:wrap;font-size:11.5px;color:var(--ink2)}
.legend .sw{display:inline-flex;flex-direction:column;align-items:center;gap:2px;min-width:44px}
.legend .sw i{display:block;width:100%;height:10px;background:var(--accent)}
.legend .t{margin-right:10px;color:var(--ink3)}
.tip{position:absolute;pointer-events:none;background:var(--tipbg);color:var(--tipink);font-size:12px;line-height:1.45;padding:7px 9px;
  max-width:240px;z-index:5;display:none}
.tip b{font-weight:600}
/* 표 */
.tblwrap{overflow-x:auto;margin-top:8px}
table{border-collapse:collapse;width:100%;font-size:12.5px}
th,td{padding:6px 8px;border-bottom:1px solid var(--rule2);text-align:right;white-space:nowrap}
th{font-weight:500;color:var(--ink3);font-size:11.5px;border-bottom:1px solid var(--ink)}
td:first-child,th:first-child{text-align:left}
td.l,th.l{text-align:left;white-space:normal}
tr.dongavg td{border-top:1px solid var(--ink);font-weight:600}
tr.on td{background:rgba(var(--accent-rgb),.08)}
tbody tr{cursor:pointer}
.x{color:var(--accent);font-weight:600}
details{margin-top:14px;border-top:1px solid var(--rule)}
summary{cursor:pointer;padding:10px 0;font-size:13px;color:var(--ink2)}
.pending{border:1px dashed var(--ink3);padding:12px 14px;font-size:13px;color:var(--ink2);margin:14px 0}
.pending b{color:var(--ink)}
.drtlist{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0;border-top:1px solid var(--rule);margin-top:8px}
.drtlist div{padding:8px 10px 8px 0;border-bottom:1px solid var(--rule2);font-size:12.5px}
.drtlist b{display:inline-block;min-width:58px}
.stage{display:inline-block;font-size:11.5px;padding:1px 7px;border:1px solid var(--rule)}
.stage.s0{color:var(--ink3);border-style:dashed}
.stage.s1,.stage.s2{border-color:var(--accent);color:var(--accent)}
.stage.s3,.stage.s4{background:var(--accent);color:var(--paper);border-color:var(--accent)}
.steps{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:0;border-top:1px solid var(--ink);margin:10px 0 16px}
.steps div{padding:10px 10px 8px 0;border-right:1px solid var(--rule)}
.steps div+div{padding-left:10px}
.steps div:last-child{border-right:0}
.steps b{display:block;font-size:26px;font-weight:500;font-family:"IBM Plex Mono",monospace}
.steps span{font-size:12px;color:var(--ink2)}
.method{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 32px;font-size:13px;color:var(--ink2)}
.method p{margin:0 0 10px}
.foot{margin-top:40px;border-top:1px solid var(--ink);padding-top:14px;font-size:12.5px;color:var(--ink2);display:flex;justify-content:space-between;
  gap:20px;flex-wrap:wrap}
.foot .aside{font-style:italic;color:var(--ink3);margin:0 0 8px;max-width:640px}
.foot p{margin:0 0 4px}
.hits img{height:20px;display:block}
@media (max-width:1000px){
  .wrap{padding:0 16px 40px}
  .cards{grid-template-columns:repeat(2,minmax(0,1fr))}
  .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
  .kpi:nth-child(2){border-right:0}
  .kpi:nth-child(3){padding-left:0}
  .kpi:nth-child(n+3){border-top:1px solid var(--rule)}
  .grid{grid-template-columns:minmax(0,1fr)}
  .mapcol{position:static;order:2}
  .method{grid-template-columns:minmax(0,1fr)}
  .tab{padding:10px 10px 8px;font-size:13px}
  .tab small{display:none}
}
@media (max-width:520px){.cards{grid-template-columns:minmax(0,1fr)}.hero h1{white-space:normal}}
"""

THEME_BOOT = ("<script>(function(){try{var t=localStorage.getItem('town-theme');"
              "if(t)document.documentElement.setAttribute('data-theme',t);}catch(e){}})();</script>")

APP_JS = r"""
(function(){
var D = window.__TOWN, $ = function(s,r){return (r||document).querySelector(s)}, $$ = function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
var KIND = {}; D.kinds.forEach(function(k){ KIND[k.id]=k; });
var RURAL = D.units.filter(function(u){return u.kind!=='dong';});
var UNIT = {}; D.units.forEach(function(u){ UNIT[u.name]=u; });
var state = {tab:'acc', kind:D.acc_cols[0], meas:'min', unit:null};
function f1(v){ return v==null?'—':(Math.round(v*10)/10).toFixed(1); }
function f2(v){ return v==null?'—':(Math.round(v*100)/100).toFixed(2); }
function fmtN(v){ return v==null?'—':Math.round(v).toLocaleString('ko-KR'); }
function measTxt(v){ return state.meas==='min' ? f1(v)+'분' : f2(v)+'km'; }

// ── 테마
(function(){ var root=document.documentElement;
  function paint(){ var t=root.getAttribute('data-theme')||'auto'; $$('.theme-toggle button').forEach(function(b){ b.classList.toggle('on', b.dataset.t===t); }); }
  $$('.theme-toggle button').forEach(function(b){ b.addEventListener('click', function(){
    if(b.dataset.t==='auto'){ root.removeAttribute('data-theme'); try{localStorage.removeItem('town-theme');}catch(e){} }
    else { root.setAttribute('data-theme', b.dataset.t); try{localStorage.setItem('town-theme', b.dataset.t);}catch(e){} }
    paint(); }); });
  paint(); })();

// ── 지도 기초
var svg = $('.map'), g = $('.zoom', svg), cellsG = $('.cells', svg), ptsG = $('.pts', svg);
var LON0=+svg.dataset.lon0, LAT1=+svg.dataset.lat1, KX=+svg.dataset.kx, PS=+svg.dataset.scale, OX=+svg.dataset.offx, OY=+svg.dataset.offy;
function px(lon){ return OX + (lon-LON0)*KX*PS; }
function py(lat){ return OY + (LAT1-lat)*PS; }
var dLon = D.cell / D.kx, dLat = D.cell / D.ky;
var NS='http://www.w3.org/2000/svg';
var cellEls = D.grid.map(function(c, i){
  var lon = D.origin[0] + c[0]*dLon, lat = D.origin[1] + c[1]*dLat;
  var r = document.createElementNS(NS,'rect');
  var x0=px(lon), x1=px(lon+dLon), y0=py(lat+dLat), y1=py(lat);
  r.setAttribute('x', x0.toFixed(2)); r.setAttribute('y', y0.toFixed(2));
  r.setAttribute('width', (x1-x0+0.15).toFixed(2)); r.setAttribute('height', (y1-y0+0.15).toFixed(2));
  r.dataset.i = i; cellsG.appendChild(r); return r; });
var NK = D.acc_cols.length;
function cellVal(c, kind, meas){ var j = D.acc_cols.indexOf(kind); if(j<0) return null; return meas==='min' ? c[4+j] : c[4+NK+j]; }

// 동 평균 대비 배수 → 진하기(한 가지 색, 멀수록 진하게)
var XB = [1, 1.5, 2, 3, 5], XO = [0.07, 0.2, 0.34, 0.5, 0.68, 0.86];
var XL = ['동 평균 이하','~1.5배','~2배','~3배','~5배','5배 넘게'];
var SB = [0.0001, 0.25, 0.5, 0.75], SO = [0.0, 0.2, 0.42, 0.64, 0.86];
var SL = ['모두 400m 안','25% 미만','25~50%','50~75%','75% 이상'];
function bin(v, br){ var i=0; while(i<br.length && v>br[i]) i++; return i; }
function legend(lab, ops, title){
  $('#legend').innerHTML = '<span class="t">'+title+'</span>' + lab.map(function(l,i){
    return '<span class="sw"><i style="opacity:'+(ops[i]||0.03)+'"></i>'+l+'</span>'; }).join(''); }

function paintCells(){
  var mode = state.tab;
  svg.classList.toggle('mode-bus', mode==='bus');
  if(mode==='acc'){
    var base = D.base[state.kind] && D.base[state.kind][state.meas];
    cellEls.forEach(function(r,i){ var v=cellVal(D.grid[i], state.kind, state.meas);
      if(v==null||!base){ r.style.display='none'; return; } r.style.display='';
      r.setAttribute('fill','rgb('+getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb')+')');
      r.setAttribute('fill-opacity', XO[bin(v/base, XB)]); });
    legend(XL, XO, KIND[state.kind].label+' · 동 평균('+measTxt(base)+') 대비');
  } else if(mode==='bus'){
    cellEls.forEach(function(r,i){ var c=D.grid[i]; var s=c[2]?c[4+2*NK]/c[2]:0; r.style.display='';
      r.setAttribute('fill','rgb('+getComputedStyle(document.documentElement).getPropertyValue('--accent-rgb')+')');
      r.setAttribute('fill-opacity', SO[bin(s, SB)]||0.03); });
    legend(SL, SO, '정류장 400m 밖 인구 비율 · 빗금=두루타 운행 읍면');
  } else {
    cellEls.forEach(function(r){ r.style.display='none'; });
    legend([], [], '읍면을 누르면 그 읍면 사업만 표에 남습니다');
  }
  paintPoints();
}
function paintPoints(){
  ptsG.innerHTML='';
  var list = state.tab==='acc' ? (D.fac[state.kind]||[]) : state.tab==='bus' ? D.stops : [];
  var cls = state.tab==='bus' ? 'stop' : 'fac';
  var rr = (state.tab==='bus'?1.6:3.2)/zk;
  list.forEach(function(p){ var c=document.createElementNS(NS,'circle'); c.setAttribute('cx',px(p[0]).toFixed(1)); c.setAttribute('cy',py(p[1]).toFixed(1));
    c.setAttribute('r', rr.toFixed(2)); c.setAttribute('class', cls); c.dataset.n = p[2]||''; ptsG.appendChild(c); });
}
// 테마가 바뀌면 칸 색(--accent-rgb)을 다시 읽는다
new MutationObserver(function(){ paintCells(); }).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

// ── 확대·이동·배경지도 (교통안전 상황판 ZOOM_JS 를 줄인 것)
var vb=svg.getAttribute('viewBox').split(/\s+/).map(Number), W=vb[2], H=vb[3], zk=1, tx=0, ty=0, drag=null, moved=0;
var sb=$('.scalebar',svg), MPU=sb?+sb.dataset.mpu:0;
function updScale(){ if(!sb) return; var per=MPU/zk, best=1; for(var e=0;e<7;e++) for(var i=0;i<3;i++){ var m=[1,2,5][i]*Math.pow(10,e); if(m/per<=120) best=m; }
  var w=best/per, x0=+sb.dataset.x; $('.sb-bar',sb).setAttribute('width',w.toFixed(1)); $('.sb-tick2',sb).setAttribute('x',(x0+w-1.4).toFixed(1));
  $('.sb-label',sb).textContent = best>=1000 ? (best/1000)+' km' : best+' m'; }
function apply(){ zk=Math.min(16,Math.max(1,zk)); tx=Math.min(0,Math.max(W*(1-zk),tx)); ty=Math.min(0,Math.max(H*(1-zk),ty));
  g.setAttribute('transform','translate('+tx.toFixed(2)+','+ty.toFixed(2)+') scale('+zk.toFixed(4)+')');
  var inv=(1/zk).toFixed(4); $$('.cs',svg).forEach(function(e){ e.setAttribute('transform','translate('+e.dataset.x+','+e.dataset.y+') scale('+inv+')'); });
  var rr=(state.tab==='bus'?1.6:3.2)/zk; $$('circle',ptsG).forEach(function(c){ c.setAttribute('r', rr.toFixed(2)); });
  updScale(); schedBase(); }
function toSvg(e){ var m=svg.getScreenCTM(); if(!m) return null; m=m.inverse(); return {x:e.clientX*m.a+e.clientY*m.c+m.e, y:e.clientX*m.b+e.clientY*m.d+m.f}; }
function zoomAt(x,y,f){ var nk=Math.min(16,Math.max(1,zk*f)); if(nk===zk) return; tx=x-(x-tx)*(nk/zk); ty=y-(y-ty)*(nk/zk); zk=nk; apply(); }
svg.addEventListener('wheel', function(e){ e.preventDefault(); var p=toSvg(e); if(p) zoomAt(p.x,p.y,Math.exp(-e.deltaY*0.0016)); }, {passive:false});
svg.addEventListener('pointerdown', function(e){ if(e.button!==0) return; drag={x:e.clientX,y:e.clientY,tx:tx,ty:ty,cap:false}; moved=0; });
svg.addEventListener('pointermove', function(e){ if(!drag) return; var rect=svg.getBoundingClientRect(), per=W/(rect.width||1);
  var dx=e.clientX-drag.x, dy=e.clientY-drag.y; moved=Math.max(moved,Math.abs(dx)+Math.abs(dy)); if(moved<=4) return;
  if(!drag.cap){ drag.cap=true; try{svg.setPointerCapture(e.pointerId);}catch(_){} } tx=drag.tx+dx*per; ty=drag.ty+dy*per; apply(); });
function endDrag(e){ if(drag&&drag.cap){ try{svg.releasePointerCapture(e.pointerId);}catch(_){} } drag=null; }
svg.addEventListener('pointerup', endDrag); svg.addEventListener('pointercancel', endDrag);
svg.addEventListener('click', function(e){ if(moved>6){ e.stopPropagation(); moved=0; } }, true);
$$('.zoombtns button').forEach(function(b){ b.addEventListener('click', function(){ var m=b.dataset.zoom;
  if(m==='reset'){ zk=1; tx=0; ty=0; apply(); return; } zoomAt(W/2,H/2,m==='in'?1.5:1/1.5); }); });

var BASE = window.__TOWNBASE || {}, baseG=$('.basemap',svg), tiles=new Map(), baseOn=false, baseTimer=null;
function lonAt(x){ return LON0+(x-OX)/(KX*PS); } function latAt(y){ return LAT1-(y-OY)/PS; }
function lon2t(l,z){ return (l+180)/360*Math.pow(2,z); }
function lat2t(l,z){ var r=l*Math.PI/180; return (1-Math.log(Math.tan(r)+1/Math.cos(r))/Math.PI)/2*Math.pow(2,z); }
function t2lon(x,z){ return x/Math.pow(2,z)*360-180; }
function t2lat(y,z){ var n=Math.PI-2*Math.PI*y/Math.pow(2,z); return 180/Math.PI*Math.atan(0.5*(Math.exp(n)-Math.exp(-n))); }
function isDark(){ var t=document.documentElement.getAttribute('data-theme'); return t==='dark' || (!t && matchMedia('(prefers-color-scheme: dark)').matches); }
function clearTiles(){ tiles.forEach(function(el){ el.remove(); }); tiles.clear(); }
function drawBase(){ if(!baseOn||!BASE.url) return; var rect=svg.getBoundingClientRect(), ratio=Math.max(1,(rect.width||W)/W);
  var z=Math.round(Math.log(360*KX*PS*zk*ratio/256)/Math.LN2); z=Math.max(9,Math.min(BASE.max_zoom||18,z));
  var lo0=lonAt((0-tx)/zk), lo1=lonAt((W-tx)/zk), la1=latAt((0-ty)/zk), la0=latAt((H-ty)/zk), x0,x1,y0,y1;
  for(;;){ x0=Math.floor(lon2t(lo0,z)); x1=Math.floor(lon2t(lo1,z)); y0=Math.floor(lat2t(la1,z)); y1=Math.floor(lat2t(la0,z)); if((x1-x0+1)*(y1-y0+1)<=240||z<=9) break; z--; }
  var want={}, tpl=(isDark()&&BASE.dark_url)?BASE.dark_url:BASE.url;
  for(var ix=x0;ix<=x1;ix++) for(var iy=y0;iy<=y1;iy++){ var key=z+'/'+ix+'/'+iy+(tpl===BASE.url?'':'d'); want[key]=1; if(tiles.has(key)) continue;
    var ax=px(t2lon(ix,z)), ay=py(t2lat(iy,z)), bx=px(t2lon(ix+1,z)), by=py(t2lat(iy+1,z));
    var img=document.createElementNS(NS,'image'); img.setAttribute('x',ax.toFixed(2)); img.setAttribute('y',ay.toFixed(2));
    img.setAttribute('width',(bx-ax+0.6).toFixed(2)); img.setAttribute('height',(by-ay+0.6).toFixed(2)); img.setAttribute('preserveAspectRatio','none');
    img.setAttribute('href', String(tpl).replace('{z}',z).replace('{x}',ix).replace('{y}',iy));
    img.addEventListener('error', function(){ $('.basemap-credit',svg).textContent='배경지도를 불러오지 못했습니다 — 인증키·도메인 등록 확인'; });
    baseG.appendChild(img); tiles.set(key,img); }
  tiles.forEach(function(el,key){ if(!want[key]){ el.remove(); tiles.delete(key); } }); }
function schedBase(){ if(!baseOn) return; clearTimeout(baseTimer); baseTimer=setTimeout(drawBase,130); }
var bchip=$('#basechip');
if(bchip){ if(!BASE.url) bchip.remove(); else bchip.addEventListener('click', function(){ baseOn=!baseOn; bchip.classList.toggle('on',baseOn);
  svg.classList.toggle('has-base',baseOn); $('.basemap-credit',svg).textContent = baseOn ? ('배경지도 '+(BASE.attribution||'')) : '';
  if(baseOn) drawBase(); else clearTiles(); }); }
new MutationObserver(function(){ if(baseOn){ clearTiles(); drawBase(); } }).observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});

// ── 지도 툴팁
var tip=$('#tip'), box=$('.mapbox');
function showTip(e, htmlText){ var r=box.getBoundingClientRect(); tip.innerHTML=htmlText; tip.style.display='block';
  var x=e.clientX-r.left+14, y=e.clientY-r.top+14; if(x+250>r.width) x=e.clientX-r.left-250; tip.style.left=x+'px'; tip.style.top=y+'px'; }
function hideTip(){ tip.style.display='none'; }
svg.addEventListener('pointermove', function(e){ if(drag&&drag.cap) return; var t=e.target;
  if(t.parentNode===cellsG){ var c=D.grid[+t.dataset.i], un=D.units[c[3]].name;
    if(state.tab==='acc'){ var v=cellVal(c,state.kind,state.meas), b=D.base[state.kind][state.meas];
      showTip(e,'<b>'+un+'</b> · 250m 격자<br>주민 약 '+fmtN(c[2])+'명<br>'+KIND[state.kind].label+'까지 '+measTxt(v)+' <span class="x">(동 평균의 '+f1(v/b)+'배)</span>'); }
    else if(state.tab==='bus'){ var o=c[4+2*NK]; showTip(e,'<b>'+un+'</b> · 250m 격자<br>주민 약 '+fmtN(c[2])+'명 중 정류장 400m 밖 '+fmtN(o)+'명'); }
    return; }
  if(t.tagName==='circle' && t.parentNode===ptsG){ showTip(e,'<b>'+(t.dataset.n||'')+'</b>'); return; }
  if(t.classList && t.classList.contains('ad')){ var u=UNIT[t.dataset.dong]; if(!u){hideTip();return;}
    showTip(e,'<b>'+u.name+'</b><br>인구 '+fmtN(u.pop)+'명'); return; }
  hideTip(); });
svg.addEventListener('pointerleave', hideTip);
$$('.ad',svg).forEach(function(a){ a.addEventListener('click', function(){ select(state.unit===a.dataset.dong?null:a.dataset.dong); }); });

// ── 읍면 고르기(카드·막대·표·지도 연동)
function select(name){ state.unit=name;
  $$('.ad',svg).forEach(function(a){ var on=a.dataset.dong===name; a.classList.toggle('on',on); if(on) a.parentNode.appendChild(a); });
  $$('[data-unit]').forEach(function(el){ el.classList.toggle('on', el.dataset.unit===name); });
  if(state.tab==='pledge') renderPledges(); }
$$('.card').forEach(function(c){ c.addEventListener('click', function(){
  select(state.unit===c.dataset.unit?null:c.dataset.unit);
  if(state.tab==='pledge') return; if(innerWidth<1000) box.scrollIntoView({behavior:'smooth',block:'center'}); }); });

// ── ① 접근성
function renderAcc(){
  var base=D.base[state.kind]; if(!base) return;
  var b=base[state.meas], rows=RURAL.map(function(u){ return {u:u, v:u.acc[state.kind]&&u.acc[state.kind][state.meas], x:u.acc[state.kind]&&u.acc[state.kind].x}; })
    .filter(function(r){return r.v!=null;}).sort(function(a,b){return b.v-a.v;});
  var mx=Math.max.apply(null, rows.map(function(r){return r.v;}).concat([b]))*1.05;
  $('#accbars').innerHTML = rows.map(function(r){ var x = r.v/b;
      return '<div class="br" data-unit="'+r.u.name+'"><span class="n">'+r.u.name+'</span><span class="trk"><span class="fill" style="width:'+(r.v/mx*100).toFixed(1)+'%"></span></span>'+
        '<span class="v">'+measTxt(r.v)+'<small>'+f1(x)+'배</small></span></div>'; }).join('') +
    '<div class="refline" style="left:calc(82px + (100% - 188px) * '+(b/mx).toFixed(4)+')"><span>동 평균 '+measTxt(b)+'</span></div>';
  $$('#accbars .br').forEach(function(el){ el.addEventListener('click', function(){ select(state.unit===el.dataset.unit?null:el.dataset.unit); }); });
  $('#acchead').textContent = KIND[state.kind].label+'까지 '+(state.meas==='min'?'차량 이동시간':'직선거리')+' — 인구가중 평균';
  $('#accsrc').textContent = '시설: '+KIND[state.kind].src+' (시설 '+KIND[state.kind].n+'곳)';
  // 표: 25개 읍면동 × 시설
  var ks=D.acc_cols;
  var head='<tr><th>읍면동</th><th>인구</th>'+ks.map(function(k){return '<th>'+KIND[k].label+'</th>';}).join('')+'</tr>';
  function cells(u){ return ks.map(function(k){ var a=u.acc[k]; if(!a) return '<td>—</td>'; var v=a[state.meas];
      return '<td>'+(state.meas==='min'?f1(v):f2(v))+(a.x>=1.5?' <span class="x">'+f1(a.x)+'×</span>':'')+'</td>'; }).join(''); }
  var body = D.units.filter(function(u){return u.pop;}).map(function(u){ return '<tr data-unit="'+u.name+'"><td>'+u.name+'</td><td class="num">'+fmtN(u.pop)+'</td>'+cells(u)+'</tr>'; }).join('');
  var avg = '<tr class="dongavg"><td>동 지역 평균</td><td></td>'+ks.map(function(k){ return '<td>'+(state.meas==='min'?f1(D.base[k].min):f2(D.base[k].km))+'</td>'; }).join('')+'</tr>';
  $('#acctable').innerHTML='<table><thead>'+head+'</thead><tbody>'+body+avg+'</tbody></table>';
  $$('#acctable tbody tr[data-unit]').forEach(function(tr){ tr.addEventListener('click', function(){ select(state.unit===tr.dataset.unit?null:tr.dataset.unit); }); });
  select(state.unit);
}
$$('#kindchips .chip').forEach(function(c){ c.addEventListener('click', function(){ if(c.disabled) return; state.kind=c.dataset.k;
  $$('#kindchips .chip').forEach(function(x){ x.classList.toggle('on', x===c); }); renderAcc(); paintCells(); }); });
$$('#measchips .chip').forEach(function(c){ c.addEventListener('click', function(){ state.meas=c.dataset.m;
  $$('#measchips .chip').forEach(function(x){ x.classList.toggle('on', x===c); }); renderAcc(); paintCells(); }); });

// ── ③ 대중교통
function renderBus(){
  var b=D.bus_base.share, rows=RURAL.filter(function(u){return u.bus;}).sort(function(a,c){return c.bus.share-a.bus.share;});
  var mx=Math.max.apply(null, rows.map(function(r){return r.bus.share;}).concat([b]))*1.08;
  $('#busbars').innerHTML = rows.map(function(u){ return '<div class="br" data-unit="'+u.name+'"><span class="n">'+u.name+'</span><span class="trk"><span class="fill" style="width:'+(u.bus.share/mx*100).toFixed(1)+'%"></span></span>'+
      '<span class="v">'+f1(u.bus.share)+'%<small>'+fmtN(u.bus.out)+'명</small></span></div>'; }).join('') +
    '<div class="refline" style="left:calc(82px + (100% - 188px) * '+(b/mx).toFixed(4)+')"><span>동 평균 '+f1(b)+'%</span></div>';
  $$('#busbars .br').forEach(function(el){ el.addEventListener('click', function(){ select(state.unit===el.dataset.unit?null:el.dataset.unit); }); });
  select(state.unit);
}
var onlyRural=true;
function renderRoutes(){
  var rows=D.bus_ops.filter(function(r){ return !onlyRural || r.rural; });
  $('#routes').innerHTML='<table><thead><tr><th>노선</th><th class="l">구분</th><th class="l">기점 → 경유 → 종점</th><th>배차간격</th><th>운행횟수</th></tr></thead><tbody>'+
    rows.map(function(r){ return '<tr><td class="num">'+r.no+'</td><td class="l">'+r.type+'</td><td class="l">'+r.from+' → '+r.via+' → '+r.to+'</td><td>'+(r.gap||'—')+'</td><td>'+(r.runs||'—')+'</td></tr>'; }).join('')+'</tbody></table>';
  $('#routecount').textContent = rows.length+'개 노선';
}
var rr=$('#ruralonly'); if(rr) rr.addEventListener('change', function(){ onlyRural=rr.checked; renderRoutes(); });

// ── ⑥ 공약
var STAGES=['미확인','계획','설계','착공','완료'];
function renderPledges(){
  var all=D.pledges, list=all.filter(function(p){ return !state.unit || p['읍면']===state.unit || (p['읍면']==='읍면 전체' && state.unit && UNIT[state.unit] && UNIT[state.unit].kind!=='dong'); });
  $('#steps').innerHTML = STAGES.map(function(s){ return '<div><b>'+all.filter(function(p){return p['단계']===s;}).length+'</b><span>'+s+'</span></div>'; }).join('');
  $('#pledgehead').textContent = state.unit ? (state.unit+' 관련 사업 '+list.length+'건 (읍면 전체 사업 포함)') : ('전체 '+all.length+'건');
  $('#pledges').innerHTML='<table><thead><tr><th class="l">읍면</th><th class="l">분야</th><th class="l">사업</th><th class="l">단계</th><th>예산(백만원)</th><th>집행</th><th class="l">출처·기준일</th></tr></thead><tbody>'+
    list.map(function(p){ var si=Math.max(0,STAGES.indexOf(p['단계']));
      return '<tr><td class="l">'+p['읍면']+'</td><td class="l">'+p['분야']+'</td><td class="l"><b>'+p['사업명']+'</b>'+(p['내용']?'<br><span class="src">'+p['내용']+'</span>':'')+'</td>'+
        '<td class="l"><span class="stage s'+si+'">'+p['단계']+'</span></td><td>'+(p['예산_백만원']||'—')+'</td><td>'+(p['집행_백만원']||'—')+'</td>'+
        '<td class="l src">'+p['출처'].replace(/(https?:\/\/\S+)/,'<a href="$1" target="_blank" rel="noopener">원문</a>')+' · '+p['기준일']+(p['비고']?'<br>'+p['비고']:'')+'</td></tr>'; }).join('')+'</tbody></table>';
  // 지도: 읍면별 사업 수로 면 칠하기
  var cnt={}; all.forEach(function(p){ cnt[p['읍면']]=(cnt[p['읍면']]||0)+1; });
  $$('.ad',svg).forEach(function(a){ a.style.fill = state.tab==='pledge' && cnt[a.dataset.dong] ? 'rgba(var(--accent-rgb),'+Math.min(0.75,0.18*cnt[a.dataset.dong])+')' : ''; });
}

// ── 탭
function setTab(id){ state.tab=id; $$('.tab').forEach(function(t){ t.classList.toggle('on', t.dataset.tab===id); });
  $$('.pane').forEach(function(p){ p.classList.toggle('on', p.id==='pane-'+id); });
  var live = ['acc','bus','pledge'].indexOf(id)>=0; $('.mapcol').style.display = live ? '' : 'none';
  if(id==='acc') renderAcc(); if(id==='bus') renderBus(); renderPledges(); paintCells(); apply();
  try{ history.replaceState(null,'','#'+id); }catch(e){} }
$$('.tab').forEach(function(t){ t.addEventListener('click', function(){ setTab(t.dataset.tab); }); });
renderRoutes();
var start=(location.hash||'').replace('#',''); setTab($('#pane-'+start)?start:'acc');
})();
"""


def _fmt(v, d=1):
    return "—" if v is None else ("%.*f" % (d, v))


def render_cards(D) -> str:
    kind = {k["id"]: k["label"] for k in D["kinds"]}
    out = []
    for u in D["units"]:
        if u["kind"] == "dong":
            continue
        items = []
        for k in u.get("worst", []):
            a = u["acc"][k]
            items.append('<li><span>%s <span class="m">%s분 · %skm</span></span><span class="x">%s배</span></li>'
                         % (esc(kind[k]), _fmt(a["min"]), _fmt(a["km"]), _fmt(a["x"])))
        out.append('<button type="button" class="card" data-unit="%s"><span class="t"><b>%s</b><span>%s</span></span>'
                   '<span class="p">인구 <span class="num">%s</span>명 · 70세 이상 <span class="num">%s%%</span></span>'
                   '<ol>%s</ol></button>'
                   % (esc(u["name"]), esc(u["name"]), "읍" if u["kind"] == "eup" else "면",
                      "{:,}".format(u["pop"] or 0), _fmt(u["s70"]), "".join(items)))
    return '<div class="cards">%s</div>' % "".join(out)


def render_kpis(D) -> str:
    R, B = D["rural"], D["base"]
    k1 = R["acc"].get("clinic"), B.get("clinic")
    k2 = R["acc"].get("pharm"), B.get("pharm")
    bus, bb = R.get("bus") or {}, D.get("bus_base") or {}
    st = [p["단계"] for p in D["pledges"]]
    checked = sum(1 for s in st if s != "미확인")
    return ('<div class="kpis">'
            '<div class="kpi"><div class="l">읍면 인구(1읍 9면)</div><div class="v">%s<small>명</small></div>'
            '<div class="c">세종 전체의 <b>%s%%</b></div><div class="src">행정안전부 주민등록 인구 %s</div></div>'
            '<div class="kpi"><div class="l">병·의원까지 차량 <span class="est">(연구진 추정)</span></div><div class="v">%s<small>분</small></div>'
            '<div class="c">동 평균 %s분의 <b>%s배</b></div><div class="src">인구가중 평균 · 낮 시간대 ITS 속도</div></div>'
            '<div class="kpi"><div class="l">약국까지 직선거리</div><div class="v">%s<small>km</small></div>'
            '<div class="c">동 평균 %skm의 <b>%s배</b></div><div class="src">상가정보 약국 업종(임시)</div></div>'
            '<div class="kpi"><div class="l">버스정류장 400m 밖 주민</div><div class="v">%s<small>%%</small></div>'
            '<div class="c">약 %s명 · 동 평균 <b>%s%%</b></div><div class="src">TAGO 정류소 · 직선 400m</div></div>'
            '</div>'
            % ("{:,}".format(R["pop"]), _fmt(R["pop"] / sum((u["pop"] or 0) for u in D["units"]) * 100),
               _ym(D.get("pop_ym")),
               _fmt(k1[0]["min"]), _fmt(k1[1]["min"]), _fmt(k1[0]["min"] / k1[1]["min"]),
               _fmt(k2[0]["km"], 2), _fmt(k2[1]["km"], 2), _fmt(k2[0]["km"] / k2[1]["km"]),
               _fmt(bus.get("share")), "{:,}".format(bus.get("out") or 0), _fmt(bb.get("share"))))


def _ym(ym):
    return "%s년 %s월" % (ym[:4], int(ym[4:])) if ym and len(str(ym)) == 6 else (ym or "")


def render_acc(D) -> str:
    chips = []
    first = True
    for k in D["kinds"]:
        if k["ready"]:
            chips.append('<button type="button" class="chip%s" data-k="%s">%s</button>'
                         % (" on" if first else "", k["id"], esc(k["label"])))
            first = False
        else:
            chips.append('<button type="button" class="chip" data-k="%s" disabled title="자료 대기">%s</button>'
                         % (k["id"], esc(k["label"])))
    waiting = [k for k in D["kinds"] if not k["ready"]]
    wait_html = ""
    if waiting:
        wait_html = ('<div class="pending"><b>자료 대기 — %s</b><br>%s</div>'
                     % ("·".join(esc(k["label"]) for k in waiting),
                        "어린이집: 공공데이터포털 전국어린이집표준데이터는 LINK형(어린이집정보공개포털 인증키 필요). "
                        "대형마트: 행정안전부 「생활_대규모점포 조회서비스」(1741000/large_scale_retail_stores) 활용신청 필요, "
                        "좌표가 EPSG:5174 라 변환해 넣는다."))
    m = D["method"]
    return (
        '<p class="q">집에서 일상 시설까지 몇 분인가</p>'
        '<p>읍면 주민이 사는 건물에서 가장 가까운 시설까지의 차량 이동시간과 직선거리를 동 지역 평균과 나란히 놓았습니다. '
        '막대 길이가 길수록 멀고, 점선이 동 지역 평균입니다.</p>'
        '<div class="ctl" id="kindchips"><span class="lab">시설</span>%s</div>'
        '<div class="ctl" id="measchips"><span class="lab">단위</span>'
        '<button type="button" class="chip on" data-m="min">차량 분</button>'
        '<button type="button" class="chip" data-m="km">직선 km</button></div>'
        '<h2 style="margin-top:18px"><b id="acchead"></b>1읍 9면</h2>'
        '<div class="bars" id="accbars"></div>'
        '<div class="src" id="accsrc"></div>'
        '<div class="src">차량 시간: 전국표준노드링크 + ITS 낮 시간대 실측 속도(%s), 건물·시설↔도로 %dkm/h·직선×%.1f '
        '<span class="est">(연구진 추정)</span> · 인구: 행정동 인구를 주거 건물 세대수 비례로 배분(%s) · 주거 건물 %s동</div>'
        '%s'
        '<details><summary>표로 보기 — 25개 읍면동 × 시설 (1.5배 이상은 배수 표시)</summary><div class="tblwrap" id="acctable"></div></details>'
        % ("".join(chips), " ~ ".join(m.get("its") or []) or "—", m["access_kmh"], m["detour"],
           _ym(D.get("pop_ym")), "{:,}".format(m["n_res"]), wait_html))


def render_bus(D) -> str:
    drt = D.get("drt") or {}
    zones = drt.get("zones") or []
    detail = drt.get("detail") or {}
    rural = [u["name"] for u in D["units"] if u["kind"] != "dong"]
    drt_rows = "".join('<div><b>%s</b> %s</div>' % (esc(n), esc(detail.get(n, "운행")) if n in zones else
                                                     '<span class="src">두루타 없음</span>')
                       for n in rural)
    return (
        '<p class="q">버스로 갈 수 있는가</p>'
        '<p>집에서 버스정류장까지 직선 400m(걸어서 5~6분)를 넘는 주민의 비율입니다. 정류장이 가까워도 하루 몇 번 오는지가 '
        '더 큰 문제라서 노선별 배차간격을 아래에 같이 둡니다.</p>'
        '<h2 style="margin-top:18px"><b>정류장 400m 밖 주민 비율</b>1읍 9면</h2>'
        '<div class="bars" id="busbars"></div>'
        '<div class="src">정류장: 국토교통부 TAGO 버스정류소정보(세종 도시코드 12, 시 경계 밖 청주 정류장 제외) %s곳 · '
        '인구: 주거 건물 배분 <span class="est">(연구진 추정)</span></div>'
        '<h2><b>읍면 수요응답형 버스 — %s</b>%s</h2>'
        '<div class="drtlist">%s</div>'
        '<div class="src">%s · %s · 06~22시, 구역 사이 이동 불가. 지도의 빗금이 운행 읍면(구역 도형은 공개돼 있지 않아 읍면 단위).</div>'
        '<h2><b>노선별 배차간격·운행횟수</b><span id="routecount"></span></h2>'
        '<label class="src"><input type="checkbox" id="ruralonly" checked> 읍면을 지나는 노선만(기점·경유·종점에 읍면 지명)</label>'
        '<div class="tblwrap" id="routes"></div>'
        '<div class="src">세종특별자치시 「세종_버스운행 현황」(공공데이터포털 3077230, 2026-09) — 원문 표기 그대로. '
        '읍면 판정은 지명 일치라 빠지거나 더해진 노선이 있을 수 있음.</div>'
        '<div class="pending"><b>첫차·막차·실시간 배차는 대기</b><br>국토교통부 TAGO 버스노선정보(1613000/BusRouteInfoInqireService) '
        '활용신청 필요(현재 403 = 주소는 맞음). 승인되면 노선별 첫차·막차·평일/주말 배차를 붙인다.</div>'
        % ("{:,}".format(len(D["stops"])), esc(drt.get("name") or "DRT"), "운행 %d곳" % len(zones),
           drt_rows, esc(drt.get("source") or ""), esc(drt.get("as_of") or "")))


def render_pledge(D) -> str:
    return (
        '<p class="q">약속은 어디까지 왔나</p>'
        '<p>읍면 생활인프라 관련 공약 사업을 하나씩 계획→설계→착공→완료 단계로 따라갑니다. '
        '예산 편성·집행은 본예산안과 시의회 회의록이 나오는 대로 채웁니다.</p>'
        '<div class="steps" id="steps"></div>'
        '<h2><b>사업 목록</b><span id="pledgehead"></span></h2>'
        '<div class="tblwrap" id="pledges"></div>'
        '<div class="pending"><b>공약집 원문을 아직 못 구했습니다.</b> 지금 목록은 언론 보도(중도일보 「조상호 세종시장 당선자 공약 돋보기」 '
        '3편 「읍·면 공간 대전환, 도농 상생 균형발전」, 2026-06-28)에서 옮긴 것이라 단계는 모두 \'미확인\'입니다. '
        '보도에는 이 공약이 5대 공약의 셋째로 나옵니다. 수작업 CSV(assets/pledges.csv)를 고치고 <code>run.py --analyze</code> 로 다시 만듭니다.</div>')


def render_later(tid) -> str:
    items = "".join("<li>%s</li>" % esc(x) for x in LATER.get(tid, []))
    q = next(t[2] for t in TABS if t[0] == tid)
    return ('<p class="q">%s</p><p>2단계에서 만듭니다. 들어갈 지표:</p><ul>%s</ul>' % (esc(q), items))


def render_sources(D) -> str:
    rows = []
    for s in D.get("sources") or []:
        state = s.get("state", "")
        txt = {"ok": "API 수집", "refused": "활용신청 필요(403)", "error": "실패", "nokey": "키 없음",
               "file": "파일"}.get(state.split("+")[0], state)
        if "+cache" in state:
            txt += " → " + (s.get("how") or "")
        rows.append('<tr><td class="l">%s</td><td class="l">%s</td><td>%s</td><td class="l src">%s</td></tr>'
                    % (esc(s.get("label")), esc(txt), "{:,}".format(s["n"]) if s.get("n") is not None else "—",
                       esc(s.get("at") or s.get("how") or "")))
    return ('<div class="tblwrap"><table><thead><tr><th class="l">자료원</th><th class="l">상태</th><th>건수</th>'
            '<th class="l">수집 시각</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(rows))


def basemap(site) -> dict:
    b = (site or {}).get("basemap") or {}
    key = (b.get("key") or "").strip()
    if b.get("provider") == "vworld" and key and not key.startswith("여기에"):
        return {"url": "https://api.vworld.kr/req/wmts/1.0.0/%s/Base/{z}/{y}/{x}.png" % key,
                "dark_url": "https://api.vworld.kr/req/wmts/1.0.0/%s/midnight/{z}/{y}/{x}.png" % key,
                "attribution": "© VWorld 국토교통부", "max_zoom": 19}
    return {"url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "attribution": "© OpenStreetMap 기여자", "max_zoom": 18}


def render_foot(site) -> str:
    c = (site or {}).get("contact") or {}
    cnt = (site or {}).get("counter") or {}
    hits = ""
    if cnt.get("target"):
        hits = ('<span class="hits"><img alt="조회수" src="https://hits.sh/%s.svg?view=today-total&amp;style=flat-square'
                '&amp;label=%%EC%%A1%%B0%%ED%%9A%%8C%%EC%%88%%98&amp;color=1d5c7c&amp;labelColor=64748b" '
                'onerror="this.parentNode.style.display=\'none\'"></span>' % esc(cnt["target"]))
    return ('<footer class="foot"><div>'
            '<p class="aside">연구원의 공식 업무가 아닌, 참여 연구자들의 호기심과 재미에서 시작한 작업입니다. 결과물은 참고용으로 봐 주세요.</p>'
            '<p>제작: %s</p><p>%s</p><p>대표 문의: %s(%s)</p></div>%s</footer>'
            % (esc(c.get("org") or "세종연구원 연구모임"), esc(", ".join(c.get("members") or [])),
               esc(c.get("name") or "송양호"), esc(c.get("email") or "ysong@sri.re.kr"), hits))


def render(D) -> str:
    site = D.get("site") or {}
    payload = {k: D[k] for k in ("kinds", "acc_cols", "base", "units", "bus_base", "grid", "fac", "stops",
                                 "pledges", "bus_ops", "origin", "kx", "ky")}
    payload["cell"] = D["method"]["cell"]
    data_js = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tabs = "".join('<button type="button" class="tab%s" data-tab="%s">%s<small>%s</small></button>'
                   % ("" if live else " later", tid, esc(lab), esc(q)) for tid, lab, q, live in TABS)
    panes = ('<section class="pane" id="pane-acc">%s</section>' % render_acc(D)
             + '<section class="pane" id="pane-bus">%s</section>' % render_bus(D)
             + '<section class="pane" id="pane-pledge">%s</section>' % render_pledge(D)
             + "".join('<section class="pane" id="pane-%s">%s</section>' % (t, render_later(t)) for t in LATER))
    svg = sejong_map.render(560, drt=(D.get("drt") or {}).get("zones") or [])
    m = D["method"]
    return """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="세종 1읍 9면 주민이 병원·약국·도서관·버스까지 얼마나 걸리는지 동 지역과 나란히 놓고, 읍면 생활인프라 공약을 점검합니다.">
%(boot)s%(font)s<style>%(css)s</style></head>
<body>
<script src="https://ysong86.github.io/nav.js" data-site="town" defer></script>
<div class="wrap">
<header class="mast"><div class="brand"><b>%(title)s</b><span>TOWN · SEJONG</span></div>
<div class="theme-toggle" role="group" aria-label="화면 테마"><button type="button" data-t="auto">자동</button><button type="button" data-t="light">밝게</button><button type="button" data-t="dark">어둡게</button></div></header>
<section class="hero"><div class="kick">도농균형 · 생활SOC — 기준: 인구 %(ym)s · 분석 %(built)s</div>
<h1>%(q1)s <em>%(q2)s</em></h1>
<p class="lede">세종 1읍 9면 주민이 병·의원, 약국, 도서관, 체육시설, 버스정류장까지 얼마나 멀리 가야 하는지를 동 지역 평균과 나란히 놓았습니다.
시설이 몇 개인지가 아니라 시설까지 걸리는 시간과 거리로 봅니다.</p>
%(kpis)s</section>
<h2><b>읍면 프로필</b>인구·고령 비율과 동 평균보다 가장 먼 시설 세 가지 — 누르면 지도와 막대에 표시</h2>
%(cards)s
<div class="src">배수는 그 읍면의 차량 시간 ÷ 동 지역 평균 <span class="est">(연구진 추정)</span>. 70세 이상 비율은 주민등록 10세 단위 연령표라 65세 기준을 쓰지 못했습니다.</div>
<nav class="tabs" role="tablist">%(tabs)s</nav>
<div class="grid"><div class="panes">%(panes)s</div>
<div class="mapcol"><div class="mapbox"><div class="zoombtns"><button type="button" data-zoom="in" title="확대">+</button><button type="button" data-zoom="out" title="축소">&#8722;</button><button type="button" data-zoom="reset" title="원래대로" style="font-size:11px">↺</button></div>
%(svg)s<div class="tip" id="tip"></div>
<div class="maptools"><div class="legend" id="legend"></div><button type="button" class="chip" id="basechip" style="margin-left:auto">배경지도</button></div></div>
<div class="src">250m 격자마다 주민(주거 건물 배분) 가중 평균. 점은 시설·정류장. 실선 읍면, 점선 동. 휠·두 손가락으로 확대.</div></div></div>
<h2><b>자료와 방법</b>지표마다 출처·기준일</h2>
<div class="method"><div>
<p><b>거리·시간을 재는 법.</b> 수요는 주거용 건물(단독·공동주택) %(nres)s동입니다. 행정동 인구를 건물 세대수(없으면 주거 연면적) 비례로 나눠 얹었습니다.
건물·인구 배분·도로망은 화재안전 상황판과 같은 자료(브이월드 건물, 건축물대장, 전국표준노드링크)를 씁니다.</p>
<p><b>차량 시간 (연구진 추정).</b> 도로 링크마다 ITS 낮 시간대 실측 속도(실측 없는 링크는 같은 등급 실측/제한속도 비율), 건물·시설에서 가까운 도로까지는 %(acc)dkm/h·직선×%(det).1f로 더했습니다. 주차·대기 시간은 넣지 않았습니다.</p>
<p><b>직선거리.</b> 가장 가까운 시설까지 직선(km). 걷기·자전거 감각으로 읽습니다. 버스정류장 400m도 직선입니다.</p>
<p><b>기준선.</b> 동 지역(행복도시 행정동) 인구가중 평균. 읍면 값 ÷ 동 평균 = 배수. 지도 색도 이 배수입니다.</p>
</div><div>%(sources)s
<p class="src">도서관 표준데이터에는 아파트 단지 작은도서관이 거의 없어 동 지역 값이 실제보다 멀게 나올 수 있습니다(격차는 덜 보이는 쪽). 약국은 심평원 약국정보 활용신청 전이라 상가정보 업종을 임시로 씁니다.</p></div></div>
%(foot)s
</div>
<script>window.__TOWN=%(data)s;window.__TOWNBASE=%(base)s;</script>
<script>%(js)s</script>
</body></html>""" % {
        "title": esc(site.get("title") or TITLE), "boot": THEME_BOOT, "font": FONT, "css": CSS,
        "ym": _ym(D.get("pop_ym")), "built": esc(D.get("built")), "q1": "읍면에서도", "q2": "일상이 가까운가",
        "kpis": render_kpis(D), "cards": render_cards(D), "tabs": tabs, "panes": panes, "svg": svg,
        "nres": "{:,}".format(m["n_res"]), "acc": m["access_kmh"], "det": m["detour"],
        "sources": render_sources(D), "foot": render_foot(site), "data": data_js,
        "base": json.dumps(basemap(site)), "js": APP_JS}


def write(data: dict, path: str = OUT_PATH) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(data))
    return path
