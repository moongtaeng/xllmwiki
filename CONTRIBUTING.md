# 기여하기

## 개발 환경

Python 3.8 이상만 있으면 된다. 의존성은 없다 — 스크립트는 표준 라이브러리만 쓴다.

```
git clone https://github.com/moongtaeng/xllmwiki
cd xllmwiki
/plugin marketplace add .
/plugin install xllmwiki@xllmwiki
```

저장소를 고친 뒤에는 `.claude-plugin/plugin.json`의 `version`을 올리고
`/plugin update xllmwiki@xllmwiki`를 실행해야 반영된다. 같은 버전이면 캐시가 그대로다.

## 저장소 구조

```
.claude-plugin/     매니페스트 (plugin.json, marketplace.json)
skills/xllmwiki/
  SKILL.md          자동 트리거 + 워크플로 라우팅
  references/       작업별 절차 — 한 번에 하나만 로드된다
  scripts/          컴파일·질의·초기화 (표준 라이브러리만)
agents/             컨텍스트 격리용 서브에이전트 2종
commands/           슬래시 명령
```

`skills/`, `agents/`, `commands/`는 자동 발견되므로 파일을 추가하면 바로 잡힌다.

## 변경할 때

**스크립트를 고쳤다면 실제로 실행해서 확인한다.** 이 플러그인에는 테스트 프레임워크가
없다 — 대신 임시 디렉터리에 위키를 만들어 전체 흐름을 돌린다.

```bash
cd $(mktemp -d)
python3 <repo>/skills/xllmwiki/scripts/wiki_init.py
# 페이지를 하나 만들고
python3 <repo>/skills/xllmwiki/scripts/wiki_graph.py
python3 <repo>/skills/xllmwiki/scripts/wiki_query.py map
```

멀티 도메인(`--domain`), 200페이지 이상(샤딩), 비ASCII slug는 회귀가 잘 나는
지점이므로 그쪽을 건드렸다면 함께 확인한다.

**문서에 적은 셸 명령도 실행해 본다.** 레퍼런스와 커맨드에 있는 `grep`·`find` 한 줄들은
실제로 돌아가야 한다. 빈 타입 디렉터리에서 오류가 나지 않는지가 특히 잘 깨진다.

## 지키는 것

- **표준 라이브러리만.** 새 의존성을 추가하지 않는다. YAML 파서가 필요하면 지금 있는
  블록 형식 리더를 쓴다.
- **마크다운이 정본.** `wiki/graph/`는 언제든 지우고 다시 만들 수 있는 파생물이다.
  그래프가 없어도 위키가 온전히 동작해야 한다.
- **조용한 자동 수리 금지.** lint와 delete는 문제를 보고하고 승인을 받는다. 지식베이스를
  말없이 고치면 사용자가 잃은 것을 모른다.
- **한 세션에 레퍼런스 하나.** `SKILL.md`가 작업별로 하나만 로드하도록 라우팅한다.
  레퍼런스를 추가하면 그 표에도 넣는다.

## 문서 언어

본문은 한국어, frontmatter의 `description`은 한국어 서술 + 영어 키워드 병기.
`description`은 스킬·에이전트 트리거 판정에 쓰이므로 영어 요청("ingest this paper")
에서도 걸려야 한다.

## 커밋과 PR

- 커밋 메시지는 무엇을 왜 바꿨는지 한 줄로. 형식은 강제하지 않는다.
- 동작이 바뀌면 `CHANGELOG.md`의 `[Unreleased]`에 한 줄 추가한다.
- 버그 리포트에는 재현 절차를 넣는다 — 어떤 레이아웃(단일/멀티)에서, 어느 명령으로,
  무엇을 기대했고 무엇이 나왔는지.

## 라이선스

기여한 코드는 MIT로 배포된다.
