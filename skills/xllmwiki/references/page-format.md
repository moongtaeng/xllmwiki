# 페이지 형식

## Frontmatter

```yaml
---
title: KV Cache
slug: kv-cache
type: concept
tags:
  - inference
  - transformers
sources:
  - raw/attention-is-all-you-need.md
updated: 2026-08-24
---
```

`tags`와 `sources`는 블록 목록으로 쓴다 (`- 항목`을 줄마다). 인라인
(`tags: [a, b]`)도 유효한 YAML이지만, 한 형식으로 통일해야 grep 집계가 성립한다.
항목이 하나여도 블록으로 쓴다.

`slug`는 파일명과 일치시킨다. `sources`에는 이 페이지가 근거로 삼은 모든 `raw/`
파일 또는 URL을 나열한다 — 나중에 오래된 내용을 탐지할 수 있게 하는 것이 바로 이
필드이자, 페이지 간 관련성을 찾는 주된 신호다. `updated`는 마지막 편집 날짜이며,
소스의 날짜가 아니다.

`type`은 `concept` · `entity` · `source` · `synthesis` 중 하나다. 무엇을 뜻하는지는
`xllmwiki` 스킬의 표에 있다. 이 필드가 검색을 좁히고, 소스 요약과 개념 설명이 섞이지
않게 한다.

태그는 인덱스에서 그룹을 나누는 용도이므로, 새로 만들기 전에 기존 태그를 재사용한다.
이미 쓰이는 태그 확인:

```bash
# 페이지 파일 목록 — 타입 디렉터리 전체, 빈 디렉터리에도 조용하다
PAGES=$(find wiki -mindepth 2 -maxdepth 2 -name '*.md' -not -path '*/graph/*')
awk '/^tags:/{f=1;next} /^[a-z_]+:/{f=0} f&&/^  - /{sub(/^  - /,"");print}' \
  $PAGES | sort | uniq -c | sort -rn
```

## 본문

```markdown
# KV Cache

Caching key and value projections from previous tokens so a decoder-only
transformer computes attention for one new token instead of the whole
sequence.[^vaswani]

## Why it matters

Turns per-token decode cost from O(n²) to O(n) at the price of memory that
grows linearly with context length.[^vaswani]

## Open questions

- Whether quantized KV caches degrade long-context recall (inferred — no source
  in the wiki addresses this yet)

## See also

- [[attention-mechanism]]
- [[inference-latency]]

[^vaswani]: raw/attention-is-all-you-need.md
```

첫 문단은 페이지 전체의 축소판이다. 그 한 줄만 읽은 낯선 사람이 계속 읽을지 판단할
수 있어야 한다. 서론이 아니라 정의로 쓴다 — "이 페이지는 …을 다룬다" 같은 문장은
쓰지 않는다.

첫 문단 이후의 섹션은 선택이다. 내용이 있을 때 제목을 추가하고, 템플릿을 채우기
위해 추가하지 않는다. `## Open questions`는 실제 내용이 있을 때 유지할 가치가 있다 —
미래의 세션에게 어디를 파야 하는지 알려주는 장치다.

링크는 `[[slug]]` 형식을 쓴다. 아직 없는 페이지를 가리켜도 된다. 끊긴 링크는 다음에
무엇을 쓸지에 대한 메모이며, lint가 그렇게 보고한다.

## relations (선택)

`[[링크]]`는 "관련 있음"만 말한다. "누가 무엇을 만들었나", "무엇이 무엇에 의존하나"
같은 질문에는 답하지 못한다. 그 답이 필요할 때만 `relations`를 쓴다.

```yaml
relations:
  - depends_on: kv-cache
    source: src-vllm-2023
    evidence: "PagedAttention은 KV 캐시를 블록 단위로 관리한다"
    status: current
```

필드 4개. `predicate: object` 한 줄, 그리고 `source`(소스 페이지 slug),
`evidence`(소스에서 그대로 따온 인용문), `status`.

`status`는 `current`(기본) · `historical`(과거엔 사실) · `disputed`(소스 간 이견) ·
`superseded`(더 나은 근거로 대체됨). 이것이 산문으로만 병기하던 모순을 기계적으로
구분되게 한다.

predicate는 자유롭게 쓴다 — 미리 정의된 목록도, 온톨로지 파일도 없다. 대신 lint가
`founded` / `founded_by`처럼 갈라진 표기를 잡아 통합을 제안한다.

**언제 쓰지 않는가.** 관계가 암시적일 때, 인용문 하나로 못 박을 수 없을 때, predicate가
결국 "언급함"일 때는 그냥 `[[링크]]`를 쓴다. 과소 주장은 벌점이 아니다 — lint는 근거
누락만 지적하고, 관계를 적지 않은 것은 문제 삼지 않는다.

## 소스 페이지

`type: source`는 구조가 다르다. 개념을 설명하는 것이 아니라 **하나의 소스가 무엇을
주장했는지**를 담는다. 흡수한 소스마다 하나씩 만든다.

```markdown
---
title: "Attention Is All You Need (Vaswani et al., 2017)"
slug: src-attention-is-all-you-need
type: source
tags:
  - transformers
sources:
  - raw/attention-is-all-you-need.md
updated: 2026-08-24
---

# Attention Is All You Need (Vaswani et al., 2017)

순환·합성곱 없이 어텐션만으로 구성한 시퀀스 변환 모델(Transformer)을 제안한 논문.

## 주장

- 어텐션만으로 기계번역 SOTA를 달성하며 학습이 훨씬 병렬화된다
- 위치 정보는 순환 구조 대신 positional encoding으로 주입한다

## 방법

WMT 2014 En-De / En-Fr, BLEU로 평가. 8 GPU로 12시간 학습.

## 한계

- 시퀀스 길이에 대해 어텐션이 O(n²) — 논문이 명시적으로 남긴 과제
- 평가가 기계번역에 한정됨

## 여기서 나온 페이지

- [[kv-cache]]
- [[attention-mechanism]]
```

`## 한계`가 중요하다. 소스가 무엇을 말하지 않았는지가 나중에 그 소스를 얼마나 신뢰할지
결정한다. 논문이 스스로 밝힌 한계와 당신이 관찰한 한계를 구분해 적는다.

`## 여기서 나온 페이지`는 이 소스에서 뽑아낸 `concept`·`entity` 페이지 목록이다. 삭제
시 무엇이 딸려 있는지 알려주는 역할도 한다.

위 예시는 영문 그대로 두었다. 인용 각주와 frontmatter 문법을 보여주는 것이 목적이며,
위키 자체는 원본 소스의 언어로 쓰면 된다.
