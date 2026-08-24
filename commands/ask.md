---
name: ask
description: 컴파일된 그래프에 직접 질의한다 — 페이지 본문을 읽지 않고 답만 받는다
---

xllmwiki 그래프에 질의: $ARGUMENTS

`xllmwiki` 스킬을 호출하고 `references/graph.md`의 질의 표를 따른다. 질문의 성격에
맞는 명령을 고른다.

```bash
python3 "<skill>/scripts/wiki_query.py" map                  # 위키에 무엇이 있나
python3 "<skill>/scripts/wiki_query.py" find <용어>           # 어느 페이지인지
python3 "<skill>/scripts/wiki_query.py" neighbors <slug>     # 무엇이 연결됐나
python3 "<skill>/scripts/wiki_query.py" facts <slug>         # 근거 있는 관계
python3 "<skill>/scripts/wiki_query.py" path <a> <b>         # 두 페이지가 어떻게 이어지나
python3 "<skill>/scripts/wiki_query.py" status disputed      # 논쟁 중인 관계
python3 "<skill>/scripts/wiki_query.py" orphans              # 고립 페이지, 끊긴 링크
```

그래프가 없으면 컴파일을 제안한다. 질의 결과로 답이 부족하면 해당 페이지 본문을 읽어
보완하되, 어느 페이지에서 나온 근거인지 밝힌다.
