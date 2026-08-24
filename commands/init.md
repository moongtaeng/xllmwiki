---
name: init
description: 위키를 생성한다 — 단일, 또는 도메인별로 나뉜 멀티 도메인
---

xllmwiki 위키를 생성한다: $ARGUMENTS

`xllmwiki` 스킬을 호출하고 `references/init.md`를 따른다.

```bash
python3 "<skill>/scripts/wiki_init.py"                 # 단일
python3 "<skill>/scripts/wiki_init.py" --domain <이름>  # 멀티 도메인
```

`<skill>`은 이 스킬 디렉터리의 절대 경로다.

위에 도메인 이름이 주어졌으면 멀티 도메인으로, 없으면 단일로 만든다. 이미 위키가
있으면 스크립트가 현재 구성을 보고하고 아무것도 바꾸지 않는다.

생성 후 `purpose.md`를 함께 작성한다 — 목표, 다루는 범위, 답하려는 핵심 질문을
사용자에게 묻는다. 이 파일이 이후 모든 흡수·질의의 판정 기준이 되므로, 템플릿으로
때우지 말고 실제 답을 받는다.
