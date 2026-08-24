---
name: graph
description: 위키를 질의 가능한 그래프 인덱스로 컴파일한다 (200페이지 넘으면 자동 샤딩)
---

xllmwiki 그래프를 컴파일한다: $ARGUMENTS

`xllmwiki` 스킬을 호출하고 `references/graph.md`를 따른다.

```bash
python3 "<skill>/scripts/wiki_graph.py"                  # 현재 위치의 위키
python3 "<skill>/scripts/wiki_graph.py" --domain <이름>   # 특정 도메인
python3 "<skill>/scripts/wiki_graph.py" --all            # 모든 도메인
```

인자 없이 실행하면 상위로 올라가며 `.xllmwiki` 마커를 찾는다. 멀티 도메인인데 도메인
밖에서 실행하면 스크립트가 도메인 목록을 보여주고 멈추므로, 그때 위에서 지정된 이름이
있으면 `--domain`으로, 없으면 사용자에게 어느 도메인인지 묻는다.

페이지 수, 엣지 수, 샤딩 여부, 산출 파일 크기를 보고한다. 근거 없는 관계, 타입 불일치,
중복 slug, 끊긴 링크가 있으면 함께 알린다.

`wiki/graph/`는 전부 파생물이므로 `.gitignore` 대상이라는 점을 처음 컴파일할 때
알려준다 — `init`이 만든 `wiki/.gitignore`에 이미 들어 있다.
