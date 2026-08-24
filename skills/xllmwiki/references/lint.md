# 점검 (Lint)

상태 점검. 문제를 보고하고 수정을 제안하되, 적용은 사용자가 요청할 때만 한다.
지식베이스를 조용히 자동 수리하는 것은 실제 노트를 잃는 방법이다.

## 검사 항목

아래를 모두 실행해 결과를 모은 뒤 보고한다.

**인덱스에 없는 페이지** — 보이지 않는 페이지.

```bash
# 페이지 파일 목록 — 타입 디렉터리 전체, 빈 디렉터리에도 조용하다
PAGES=$(find wiki -mindepth 2 -maxdepth 2 -name '*.md' -not -path '*/graph/*')

echo "$PAGES" | sed 's|.*/||; s|\.md$||' | sort > /tmp/xw-pages
grep -o '\[\[[^]]*\]\]' wiki/index.md | tr -d '[]' | sort -u > /tmp/xw-indexed
comm -23 /tmp/xw-pages /tmp/xw-indexed
```

**페이지가 없는 인덱스 항목** — 정리 없이 삭제·이름 변경된 것.

```bash
comm -13 /tmp/xw-pages /tmp/xw-indexed
```

**미아 문서** — `index.md`가 가리키지 않는 관리 문서. 옵시디언 그래프에서 고립되고,
있는 줄도 모르게 된다. 페이지와 달리 이건 항상 오류다.

```bash
for f in SCHEMA log; do
  grep -q "\[\[$f\]\]\|($f\.md)" wiki/index.md || echo "index.md에 $f.md 링크 없음"
done
# purpose.md는 위키 루트(단일) 또는 도메인 루트(멀티)에 있다
ls purpose.md ../purpose.md 2>/dev/null | head -1 || echo "purpose.md 없음"
grep -q 'purpose' wiki/index.md || echo "index.md에 purpose.md 링크 없음"
```

멀티 도메인이면 루트 `index.md`도 검사한다 — 공통 `SCHEMA.md` 링크와 **모든 도메인의
index.md 링크**가 있어야 한다. 도메인을 추가했는데 루트 인덱스에 없으면 그 도메인은
위키 전체에서 보이지 않는다.

```bash
# 컨테이너 루트에서
for d in */; do
  d=${d%/}
  [ -d "$d/wiki" ] || continue
  grep -q "$d" index.md || echo "루트 index.md에 도메인 $d 링크 없음"
done
```

**끊긴 `[[링크]]`** — 오류가 아니다. 다음에 쓸 것의 대기열이므로, 그렇게 보고하고
가리키는 페이지 수 순으로 정렬한다. 세 페이지가 참조하는 slug가 다음에 쓸 가치가 있는
페이지다.

**인용 없는 페이지** — `sources`도 각주도 없는 페이지는 아무것도 뒷받침하지 않는 주장을
한다. 배경지식이거나(괜찮다), 나중에 사실로 읽히게 될 무근거 주장이다.

**오래된 페이지** — 빠르게 변하는 주제인데 `updated`가 한참 전이거나, `sources`가
더 이상 존재하지 않는 `raw/` 파일을 가리키는 경우.

**과대 페이지** — 200줄을 넘거나 서로 무관한 최상위 제목이 여러 개인 페이지. 분할
후보이며, 미래의 세션이 건너뛰는 페이지다.

**유사 중복** — 같은 개념이 두 slug로 존재. 인덱스 전체에서 제목과 태그를 비교한다.
태그 집합이 같고 제목이 비슷한 두 페이지는 보통 흡수 2단계 검색을 건너뛴 결과다.
`sources[]`가 겹치는 페이지끼리 먼저 비교하면 후보가 빠르게 좁혀진다.

```bash
# 페이지 파일 목록 — 타입 디렉터리 전체, 빈 디렉터리에도 조용하다
PAGES=$(find wiki -mindepth 2 -maxdepth 2 -name '*.md' -not -path '*/graph/*')
# 같은 소스를 인용하는 페이지끼리 — 중복 후보
for f in raw/*.md; do
  echo "-- $f"; grep -l "$f" $PAGES
done
```

**`type` 누락** — 타입 없는 페이지는 검색에서 걸러지지 않고 소스 요약과 개념 설명이
섞인다.

```bash
grep -L '^type:' $PAGES
```

**소스 페이지가 없는 소스** — `raw/`에 있는데 그것을 다루는 `type: source` 페이지가
없다. "이 소스가 무엇을 주장했나"에 답할 곳이 없다는 뜻이다.

```bash
for f in raw/*.md; do
  hits=$(grep -l "$f" $PAGES)
  if [ -z "$hits" ] || ! echo "$hits" | xargs grep -l '^type: source' >/dev/null 2>&1; then
    echo "소스 페이지 없음: $f"
  fi
done
```

`grep -l` 결과를 변수로 받아 판정한다. `xargs -r`로 바로 파이프하면 인용이 아예 없는
소스에서 종료 코드 0이 나와 조용히 통과된다.

**frontmatter 형식 불일치** — `tags`·`sources`가 인라인(`[a, b]`)으로 쓰인 페이지.
집계 명령이 이 페이지를 조용히 빠뜨린다.

```bash
grep -n '^\(tags\|sources\):[[:space:]]*\[' $PAGES
```

**근거 없는 관계** — `relations`에 `source`나 `evidence`가 빠진 항목. 컴파일
스크립트가 이것을 problem으로 보고한다.

```bash
python3 "<skill>/scripts/wiki_graph.py"
```

**갈라진 predicate** — `founded`와 `founded_by`, `depends_on`과 `dependency` 처럼
같은 뜻이 다른 표기로 쓰인 경우. 온톨로지가 없는 대신 이 검사가 일관성을 지킨다.

```bash
python3 "<skill>/scripts/wiki_query.py" status --json | \
  python3 -c "import json,sys,collections; \
d=json.load(sys.stdin); \
print(collections.Counter(r['predicate'] for r in d['relations']))"
```

한 번만 쓰인 predicate가 여럿 있으면 통합 후보다. 다만 정말 한 번뿐인 관계일 수도
있으니 강제하지 않는다.

**낡은 그래프** — `wiki/graph/`가 페이지보다 오래됐다. 낡은 그래프는 없는 것보다
나쁘다.

```bash
ls -t wiki/graph/*.json $PAGES | head -1
```

가장 최근 파일이 페이지 쪽이면 재컴파일이 필요하다.

**목적에서 벗어난 페이지** — `purpose.md`의 범위와 무관한 주제. 삭제 대상이 아니라
`purpose.md`가 낡았다는 신호일 수 있다. 둘 중 무엇인지는 사용자만 판단할 수 있으므로
그대로 보고한다.

**답하지 못하는 핵심 질문** — `purpose.md`의 핵심 질문 중 위키가 아직 답할 수 없는
것. 결함이 아니라 흡수 백로그의 최우선 항목이다.

## 보고

심각도로 묶고, 사용자에게 실제로 비용이 되는 것을 먼저 말한다.

1. **검색이 깨진다** — 인덱스에 없는 페이지, 페이지가 없는 인덱스 항목, `type` 누락,
   미아 문서(SCHEMA·log·purpose·도메인 인덱스 링크 누락).
2. **신뢰가 깨진다** — 무근거 주장, 없는 파일을 가리키는 `sources`, 소스 페이지가 없는
   소스.
3. **시간이 갈수록 나빠진다** — 오래된 페이지, 과대 페이지, 유사 중복, 목적에서 벗어난
   페이지.
4. **백로그** — 답하지 못하는 핵심 질문(우선), 끊긴 링크(참조 수 순).

각 항목마다 파일명과 한 줄 수정안을 제시한다. 그다음 무엇을 적용할지 묻는다. 페이지
분할과 중복 병합은 의미를 바꾸므로, 일괄 승인이 아니라 사안별 명시적 승인이 필요하다.

건강한 위키는 4번만 보고된다. 1~2번이 비어 있지 않다면 흡수 워크플로가 어딘가에서
잘리고 있다는 뜻이므로, 그 점을 말할 가치가 있다.
