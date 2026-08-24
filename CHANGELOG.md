# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르며,
[유의적 버전](https://semver.org/lang/ko/)을 사용한다.

## [Unreleased]

## [0.1.2] — 2026-08-25

첫 공개 배포. 이전 버전(0.1.0, 0.1.1)은 개발 중 로컬 설치 테스트용이라 공개된 적이
없으므로 별도 항목을 두지 않는다.

### 추가

- **위키 생성** — `/xllmwiki:init`. 단일 위키 또는 도메인별로 나뉜 멀티 도메인.
  `.xllmwiki` 마커를 두어 프로젝트 어느 하위 디렉터리에서도 스크립트가 위키를 찾는다.
- **흡수** — `/xllmwiki:ingest`. 소스를 `raw/`에 보존하고, 분석 후 페이지를 쓴다.
  소스마다 `type: source` 페이지 하나를 만들어 주장·방법·한계를 기록한다.
- **질의** — `/xllmwiki:query`. 주장 단위로 인용하고, 위키 근거와 추론을 구분한다.
- **점검** — `/xllmwiki:lint`. 15가지 검사: 인덱스 누락, 미아 문서, 무근거 주장,
  타입 불일치, 중복 slug, 낡은 그래프 등.
- **삭제** — `/xllmwiki:delete`. 소스나 페이지를 지울 때 딸린 페이지와 끊긴 링크를
  함께 정리한다. 계획을 먼저 보여주고 승인을 받는다.
- **그래프** — `/xllmwiki:graph`, `/xllmwiki:ask`. 마크다운 위에 올리는 선택적 컴파일
  인덱스. [JSON Graph Format v2](https://jsongraphformat.info/) 준수. 200페이지를
  넘으면 자동 샤딩하고, 질의는 필요한 샤드만 읽는다.
- **에이전트 2종** — `wiki-scribe`(긴 소스를 읽고 페이지 작성), `wiki-librarian`(여러
  페이지 검색, 읽기 전용). 둘 다 본문을 메인 컨텍스트 밖에 둔다.
- **`relations` 프론트매터** — 선택. 인용문과 `status`(`current`/`historical`/
  `disputed`/`superseded`)를 지닌 타입 관계로 모순을 기계적으로 구분한다.
- **다국어** — 한국어·중국어·일본어·러시아어 slug·태그·predicate 지원. 유니코드
  NFC 정규화, CJK 전각 폭 계산, Windows cp949 콘솔 대응.

### 설계 결정

- **페이지는 타입별 디렉터리에** (`concept`/`entity`/`source`/`synthesis`). 옵시디언
  vault로 열었을 때 한 폴더에 수백 개가 늘어지면 탐색이 불가능하기 때문이다.
  `type:` frontmatter가 정본이고 디렉터리는 거울이며, 어긋나면 컴파일이 보고한다.
- **표준 라이브러리만** — `uv`도, `pyyaml`도, 설치할 것도 없다. YAML 파서도 직접
  구현했다.
- **온톨로지 파일 없음** — predicate는 자유롭게 쓰고, lint가 갈라진 표기만 잡는다.
- **그래프를 통째로 로드하지 않는다** — 40페이지 실측에서 `graph.json` 전체(26,534자)가
  페이지 본문(23,633자)보다 컸다. 절약은 질의로 답만 받을 때 나온다. 250페이지에서
  질의 1건이 전체 본문의 0.55%였다.

[Unreleased]: https://github.com/moongtaeng/xllmwiki/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/moongtaeng/xllmwiki/releases/tag/v0.1.2
