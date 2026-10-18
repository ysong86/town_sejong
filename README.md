# 세종 읍면 생활인프라 격차 상황판

세종 1읍 9면 주민이 일상 시설까지 얼마나 멀리 가야 하는지를 동 지역 평균과 나란히 놓는 상황판.
대문 https://ysong86.github.io/ 의 02번, 주소 /town_sejong/ (저장소 ysong86/town_sejong, 공개 예정).

## 만드는 순서

```
C:\Python313\python.exe run.py --probe        # 포털 자료원 승인 여부(200 됨 / 403 활용신청 필요)
C:\Python313\python.exe run.py --collect      # 수집 → analyze.py → dashboard.html  (분기마다)
C:\Python313\python.exe run.py --analyze      # assets/pledges.csv 만 고쳤을 때
C:\Python313\python.exe run.py --dashboard --out site   # 화면만 다시 + 배포본 site/index.html
```

배포는 다른 상황판과 같다: gh-pages 에 site/index.html + .nojekyll 한 커밋(강제 푸시).

## 탭 (1단계 MVP = ①③⑥)

| 탭 | 지표 | 자료 |
|---|---|---|
| ① 생활SOC 접근성 | 병·의원·약국·도서관·공공체육시설까지 차량 분(연구진 추정)·직선 km, 동 평균 대비 배수 | 심평원 병원, 상가정보 약국(임시), 도서관 표준데이터, 체육시설 |
| ③ 대중교통 사각지대 | 정류장 400m 밖 인구, 두루타(DRT) 운행 읍면, 노선별 배차간격·운행횟수 | TAGO 정류소, 세종_버스운행 현황 CSV(assets), config drt |
| ⑥ 공약 이행 트래커 | 사업별 단계·예산·집행 | assets/pledges.csv (수작업) |

②④⑤는 2단계 — 탭만 자리를 잡아 두었다.

## 알아둘 것

- **이웃 상황판에 기댄다.** 건물·인구 배분·도로망(ITS 낮 속도)은 `../sejong_fire/data/analysis.json` 을 읽는다.
  화재 상황판을 다시 돌리면 여기도 `--analyze` 를 다시. 포털 수집이 막히면 `../sejong_livingzone/data/raw` 캐시로 물러선다.
- 키: config.json(gitignore) `portal.key` = 생활권 상황판 포털 키, `site.basemap.key` = 브이월드(교통 상황판과 같은 키).
- **활용신청 필요(2026-10-18, 셋 다 403)**: 심평원 약국정보, TAGO 버스노선정보(첫차·막차·배차), 응급의료기관.
  승인되면 `--collect` 만 다시 — 약국은 저절로 심평원 자료로 바뀐다.
- 자료 대기: 어린이집(표준데이터가 LINK형 → 어린이집정보공개포털 키), 대형마트(행안부 생활_대규모점포 API 1741000, 좌표 EPSG:5174).
  data/raw/daycare.json · mart.json 을 `{"items":[{"name","lon","lat"}], "source": "..."}` 로 넣으면 ①에 붙는다.
- 도서관 표준데이터는 24곳뿐(아파트 작은도서관 거의 없음), 일부 행은 주소가 뒤바뀌어 있다(조치원읍도서관↔전의도래샘).
- 읍면 DRT 는 이응버스가 아니라 **두루타**(장군·금남·조치원·연서·소정·전의). 이응버스는 동 지역.
- 공약 원문 미확보. pledges.csv 는 중도일보 공약 돋보기(2026-06-28) 기준, 단계는 전부 '미확인'.
  보도에서는 이 공약이 5대 공약의 셋째(브리프의 '공약 6번'과 다름).
- 로컬 확인: 루트 .claude/launch.json `sejong-town`(8775), 대문 안에서 보기 `sejong-portal-local`(8771).
