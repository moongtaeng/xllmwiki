---
name: ingest
description: 소스(URL, 파일, PDF, 붙여넣은 텍스트)를 위키로 흡수한다
---

xllmwiki 지식베이스로 흡수: $ARGUMENTS

`xllmwiki` 스킬을 호출하고 `references/ingest.md`를 따른다. 위키가 아직 없으면
`references/init.md`로 먼저 만든다. 멀티 도메인이면 어느 도메인에 넣을지 정한다.

위에 소스가 주어지지 않았으면 무엇을 흡수할지 물어본다.
