---
name: stats
description: 위키의 규모, 형태, 링크 밀도를 보여준다
---

xllmwiki 지식베이스의 규모와 형태를 보고한다.

```bash
# 페이지 파일 목록 — 타입 디렉터리 전체, 빈 디렉터리에도 조용하다
PAGES=$(find wiki -mindepth 2 -maxdepth 2 -name '*.md' -not -path '*/graph/*')
echo "$PAGES" | wc -l                    # 페이지 수
cat $PAGES | wc -l                       # 전체 줄 수
grep -ho '\[\[[^]]*\]\]' $PAGES | wc -l  # 링크 수
grep -h '^type:' $PAGES | sort | uniq -c | sort -rn
awk '/^tags:/{f=1;next} /^[a-z_]+:/{f=0} f&&/^  - /{sub(/^  - /,"");print}' \
  $PAGES | sort | uniq -c | sort -rn   # 태그 분포
ls raw/*.md 2>/dev/null | wc -l                                # 소스 수
grep -l '^type: source' $PAGES | wc -l   # source 페이지 수
wc -l $PAGES | sort -rn | head -10       # 가장 큰 페이지
tail -5 wiki/log.md 2>/dev/null                                # 최근 흡수 기록
```

페이지 수, 페이지 크기의 중앙값과 최댓값, 페이지당 링크 수, 타입 분포, 태그 분포,
소스 수, 최근 흡수 몇 건을 보고한다.

소스 수와 `type: source` 페이지 수가 어긋나면 지적한다 — 흡수가 소스 페이지를
남기지 않았다는 뜻이다.

그다음 `xllmwiki` 스킬의 "규모 확장" 절에 따라 현재 위키가 어느 임계점에 있는지
말한다: 약 50페이지 이하는 평면 인덱스, 그 이상은 샤딩된 인덱스, 수백 페이지 이상은
서브디렉터리. 재구조화가 필요한지 판단하고 — 필요하지 않다면 작업을 제안하는 대신
필요 없다고 말한다.
