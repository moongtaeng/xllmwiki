# xllmwiki

세션을 넘어 축적되는 LLM 큐레이션 마크다운 지식베이스.

소스를 원자적이고 인용이 붙은 페이지로 흡수한다. 나중에 인용과 함께 질의한다. 낡은
내용을 점검한다. 순수 마크다운이다 — 임베딩도, 벡터 DB도, 데몬도 없다. `grep`으로
찾히고 사람이 읽을 수 있다.

## 설치

```
/plugin marketplace add moongtaeng/xllmwiki
/plugin install xllmwiki@xllmwiki
```

`xllmwiki@xllmwiki`는 `플러그인이름@마켓플레이스이름`이다. 둘 다 `xllmwiki`라서
중복돼 보이지만 정상이다.

### 로컬 경로에서

저장소를 클론했거나 직접 고칠 때:

```
/plugin marketplace add <저장소 경로>
/plugin install xllmwiki@xllmwiki
```

저장소 루트가 곧 플러그인 루트다 — `.claude-plugin/`에 매니페스트가 있고 `skills/`,
`agents/`, `commands/`가 그 옆에 있다. `marketplace.json`의 `source`는 `"./"`.

### 수정 후 반영

설치하면 `~/.claude/plugins/cache/`로 **복사**되므로, 저장소를 고쳐도 설치된 쪽은
그대로다. 반영하려면:

```
/plugin update xllmwiki@xllmwiki
```

`plugin.json`의 `version`을 올려야 업데이트가 잡힌다 — 같은 버전이면
"already at the latest version"으로 끝난다.

### 제거

```
/plugin uninstall xllmwiki@xllmwiki
/plugin marketplace remove xllmwiki
```

마켓플레이스까지 지워야 완전히 정리된다.

## 시작하기

처음이라면 [5분 퀵스타트](docs/quickstart.md) — 논문 하나를 넣고 질문해 보는 과정.

## 명령

| 명령 | 동작 |
|------|------|
| `/xllmwiki:init [도메인]` | 위키 생성. 도메인 이름을 주면 멀티 도메인. |
| `/xllmwiki:ingest <소스>` | 소스 → 위키 페이지. URL, 파일, PDF, 붙여넣은 텍스트. |
| `/xllmwiki:query <질문>` | 위키에서 답변, 주장 단위 인용. |
| `/xllmwiki:lint` | 15가지 점검 — 인덱스·미아 문서·무근거 주장·중복·낡은 그래프 등. |
| `/xllmwiki:stats` | 규모, 형태, 링크 밀도, 확장 임계점. |
| `/xllmwiki:delete <대상>` | 소스·페이지 삭제 + 딸린 페이지·링크 정리. |
| `/xllmwiki:graph` | 질의용 그래프 인덱스 컴파일 (200페이지↑ 자동 샤딩). |
| `/xllmwiki:ask <질문>` | 그래프에 직접 질의 — 본문 안 읽고 답만. |

`xllmwiki` 스킬은 슬래시 명령 없이도 자동으로 트리거된다 — "위키에 추가해줘", "내
노트에 X에 대해 뭐라고 있어" 같은 요청에 반응한다.

## 생성되는 레이아웃

```
.xllmwiki             # 마커 — 스크립트가 어느 하위 디렉터리에서도 위키를 찾는다
purpose.md            # 이 위키가 무엇을 위한 것인가 (init이 만들지 않는다 — 직접 쓴다)
wiki/
  index.md            # 지도: 모든 페이지를 한 줄씩
  log.md              # append-only 흡수 기록
  SCHEMA.md           # 이 위키의 지역 규약 (태그 목록, 고유 규칙)
  concept/<slug>.md   # 페이지는 타입별 디렉터리에 — 한 페이지에 한 개념
  entity/  source/  synthesis/
  graph/              # (선택) 컴파일된 질의 인덱스. 파생물이라 .gitignore 대상
raw/<slug>.md         # 원본 텍스트 그대로, 절대 편집하지 않음
```

타입별 디렉터리로 나누는 이유는 사람이다 — 옵시디언 vault로 열었을 때 한 폴더에
수백 개가 늘어지면 탐색이 불가능하다. `type:` frontmatter가 정본이고 디렉터리는
거울이며, 어긋나면 컴파일이 `type mismatch`로 보고한다.

주제가 여럿이면 도메인별로 나눌 수 있다. 도메인마다 독립된 `wiki`+`raw`를 가지므로
하나를 통째로 옮기거나 지울 수 있다.

```
.xllmwiki             # {"root": "_WIKI"}
_WIKI/
  index.md            # 도메인 목록 (페이지 목록이 아니다)
  SCHEMA.md           # 모든 도메인 공통 규약
  infra/
    purpose.md        # 목적은 도메인마다 하나 (직접 쓴다)
    wiki/  raw/
  poker/
    ...
```

미리 멀티로 만들지 말 것 — 주제가 실제로 갈라질 때 `/xllmwiki:init <도메인>`으로
추가한다. 도메인 간 링크는 허용되고, 컴파일이 `cross-domain links`로 보고한다.

경로 설정은 `.xllmwiki`에만 있다. `SCHEMA.md`에는 규약만 적어 두 곳이 어긋날 여지를
없앤다.

`purpose.md`는 위키의 목표·범위·핵심 질문을 담고, 모든 작업이 이를 참조한다. 흡수에서
무엇을 생략할지, 질의에서 어떤 공백을 우선 보고할지가 여기서 결정된다. 도메인이 다르면
목적도 다르므로 도메인마다 하나씩 둔다.

`init`은 이 파일을 만들지 않는다 — 빈 템플릿을 남기면 채워지지 않은 채로 남아 판정
기준 역할을 못 하기 때문이다. `/xllmwiki:init`이 목표와 범위를 물어 함께 작성한다.

**`index.md`는 모든 관리 문서를 가리킨다.** 가리키지 않는 문서는 옵시디언 그래프에서
고립되고, 나중에 있는 줄도 모르게 된다. `init`이 아래 링크를 넣어두므로 지우지 말 것.

- 도메인 `index.md` → `[[SCHEMA]]`, `[[log]]`, `../purpose.md`
- 루트 `index.md` → `[[SCHEMA]]`, 그리고 **모든 도메인의 `index.md`**

도메인을 추가하면 `wiki_init.py`가 루트 인덱스를 다시 써서 링크를 넣는다. 손으로
디렉터리를 만들면 빠지고, 그 도메인은 위키 전체에서 보이지 않는다.

페이지에는 `type`이 있다 — `concept`(X란 무엇인가), `entity`(누가 무엇을 했나),
`source`(이 소스가 무엇을 주장했나), `synthesis`(여러 소스를 합치면). 소스마다
`source` 페이지 하나를 만들어 주장·방법·한계를 기록한다.

## 에이전트

- **wiki-scribe** — 긴 소스를 읽고 페이지를 작성한다. 소스 텍스트를 메인 컨텍스트
  밖에 둔다.
- **wiki-librarian** — 여러 페이지를 검색해 인용된 구절과 slug를 반환한다. 읽기 전용.

## 그래프 (선택)

마크다운 위에 올리는 컴파일 인덱스. 목적은 지식 표현이 아니라 **컨텍스트 절약**이다.

```bash
python3 "<skill>/scripts/wiki_graph.py"                  # 컴파일
python3 "<skill>/scripts/wiki_query.py" neighbors <slug> # 질의
```

`<skill>`은 설치된 스킬 디렉터리의 절대 경로다 —
`~/.claude/plugins/cache/xllmwiki/xllmwiki/<version>/skills/xllmwiki`. 인자 없이
실행하면 현재 디렉터리에서 위로 올라가며 `.xllmwiki` 마커를 찾으므로, 프로젝트 어느
하위 디렉터리에서든 동작한다. 멀티 도메인에서는 현재 위치의 도메인을 쓰고,
`--domain <이름>`으로 지정하거나 `--all`로 전체를 컴파일한다.

슬래시 명령(`/xllmwiki:graph`, `/xllmwiki:ask`)을 쓰면 경로를 직접 칠 필요가 없다.

40페이지 실측 (문자 수):

| | 크기 |
|---|---|
| 전체 페이지 본문 | 23,633 |
| `graph.json` 통째로 | 26,534 (본문보다 크다) |
| 라우팅 정보만 | 3,916 (83% 절감) |
| 이웃 질의 1건 | 893 (96% 절감) |

그래프를 통째로 로드하면 손해다 — 절약은 질의로 답만 받을 때 나온다. 250페이지에서는
질의 1건이 전체 본문의 0.55%였다.

질의 명령: `map`(전체 지도) · `find`(검색) · `neighbors`(연결) · `facts`(근거 있는
관계) · `path`(두 페이지 연결 경로) · `status`(논쟁 중인 관계) · `orphans`(고립·끊긴
링크) · `domains`(도메인 현황과 교차 링크).

- **표준 라이브러리만** — `uv`도, `pyyaml`도, 설치할 것도 없다
- **[JSON Graph Format v2](https://jsongraphformat.info/)** 준수 — 시각화 도구에
  그대로 넣을 수 있다
- **온톨로지 없음** — predicate는 자유, lint가 갈라진 표기만 잡는다
- **200페이지 넘으면 자동 샤딩** — 질의는 필요한 샤드만 읽는다
- **다국어** — 한국어·중국어·일본어·러시아어 slug·태그·predicate 모두 지원

`relations` 프론트매터는 선택이다. `[[링크]]`로 부족할 때, 즉 "누가 무엇을 만들었나"
같은 질문에 답해야 할 때만 쓴다. `status`(`current`/`historical`/`disputed`/
`superseded`)로 모순을 기계적으로 구분한다.

## 설계 원칙

- **한 페이지에 한 개념.** 긴 페이지는 건너뛰게 되고, 그러면 짐이 된다.
- **자명하지 않은 모든 주장은** `raw/` 파일이나 URL을 인용한다. 추론은 `(추론)`으로
  표시해 나중 세션이 추측을 사실로 승격하지 못하게 한다.
- **추가보다 갱신.** 모순되는 소스는 페이지를 편집해 양쪽 입장을 서술한다. 서로
  반대되는 주장을 하는 페이지 두 개는 위키가 없는 것보다 나쁘다.
- **위키 근거와 추론을 모든 답변에서 구분한다.**

## 기여

[CONTRIBUTING.md](CONTRIBUTING.md) — 개발 환경, 저장소 구조, 변경 시 확인할 것.
버전별 변경 내역은 [CHANGELOG.md](CHANGELOG.md)에 있다.

## 라이선스

MIT — [LICENSE](LICENSE) (한국어 번역 포함)

