---
name: market-simulation
description: >
  Nemotron 한국 페르소나(HuggingFace 공개 데이터, 로컬 LLM·API 키 불필요)로
  시장 반응을 시뮬레이션한다. Claude Code Agent 툴로 배치 격리 실행.
  "시장 반응", "사용자 조사", "포커스 그룹", "페르소나 시뮬", "타깃 반응",
  "구매 의향", "가격 테스트", "한국 소비자" 등 언급 시 이 스킬을 사용하라.
---

# /market-simulation — AI 시장 반응 시뮬레이터

**전제**: Claude Code만 있으면 동작. 로컬 LLM, 별도 API 키 불필요.  
**데이터**: NVIDIA Nemotron-Personas-Korea (HuggingFace, CC BY 4.0, 100만 한국 페르소나)

---

## 시뮬레이션 한도 (하드캡)

| | 값 | 이유 |
|---|---|---|
| **기본** | **20명** | 탐색 시뮬 기본, 테마 포화 충분 |
| **최대** | **30명** | 6 에이전트 × 5명. 초과 시 거부 |
| 배치 크기 | 5명/에이전트 | 컨텍스트 격리 + 응답 품질 균형 |

> 요청이 30명을 초과하면: "30명이 최대 한도입니다. N=30으로 진행할까요?" 라고 묻고 사용자 확인 후 진행.

---

## 시작 전 의존성 확인

```python
# 첫 실행 또는 의심스러울 때만 실행
import importlib
missing = [m for m in ['datasets', 'pandas'] if not importlib.util.find_spec(m)]
if missing:
    print(f'pip install {" ".join(missing)}')
```

설치 안 됐으면 사용자에게 `pip install datasets pandas` 안내 후 중단.

---

## A. 시뮬레이션 ("○○에 대해 ○○ 사람들 반응 봐줘")

### 1단계 — 조건 확인 (1회 되묻기)

사용자에게 확인:
- **타깃 조건**: 지역(시도), 나이대, 성별, 직업 유형 (없으면 무작위)
- **질문**: 페르소나에게 던질 질문 1개
- **인원**: 기본 20명, 요청 시 최대 30명

### 2단계 — 페르소나 풀 추출

```python
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from src.personas import load_pool, filter_pool, occupation_kw, persona_to_card
import pandas as pd

df = load_pool('korea', sample_n=50000)

# 사용자 조건 반영 (예시 — 실제 조건으로 교체)
pool = filter_pool(
    df,
    province='서울',          # 없으면 None
    age_range=(25, 45),       # 없으면 None
    occupation_keywords=occupation_kw('직장인'),  # 없으면 None
)

N = 20  # 사용자 요청 인원 (최대 30)
if len(pool) < N * 3:
    print(f'필터 후 {len(pool)}명 — 조건 완화 필요')
else:
    sample = pool.sample(N, random_state=42)
    print(f'선택된 {N}명 준비 완료')
```

풀이 N의 3배 미만이면 사용자에게 조건 완화 제안 후 재필터.

### 3단계 — 배치 분할 및 에이전트 병렬 실행

배치당 5명, 최대 6배치. 모든 에이전트를 **background=True로 동시 발사**.

각 에이전트에게 전달하는 프롬프트 구조:

```
다음 {batch_size}명의 한국인 페르소나가 있습니다.
각 페르소나 입장에서, 그 인물의 어휘·말투·가치관으로 아래 질문에 1인칭 한국어로 답해주세요.

**중요**:
- 각 페르소나는 서로의 응답을 모릅니다. 완전히 독립적으로 답하세요.
- AI 또는 가상 인물이라는 사실은 절대 언급하지 마세요.
- 답변은 2~5문장. 자신의 일상·예산·우선순위에 비추어 솔직하게.
- 모르면 "잘 모르겠는데, 아마…"처럼 불확실성을 표시.

**질문**: {question}

---

{persona_cards}  ← persona_to_card(p, idx) 결과 5개 이어붙이기

---

**출력 형식** (정확히 따르세요. 다른 설명 없이 이 형식만):

=== {페르소나_1 | age}세 | {sex} | {occupation} | {province} {district} ===
{응답}

=== {페르소나_2 | ...} ===
{응답}

...
```

```python
# 배치 분할 코드
import math
BATCH_SIZE = 5
batches = [sample.iloc[i:i+BATCH_SIZE] for i in range(0, N, BATCH_SIZE)]

# 각 배치에 대해 Agent 툴 호출 (background=True, 모두 동시)
# → Agent가 반환한 텍스트를 수집하여 다음 단계에서 파싱
```

### 4단계 — 응답 파싱 및 CSV 저장

에이전트 응답에서 `=== ... ===` 블록을 파싱하여 CSV로 저장:

```
output/YYYY-MM-DD_{topic}.csv
```

CSV 컬럼: `id, age, sex, occupation, province, district, answer`

파싱 실패(빈 응답, 형식 불일치)는 answer를 빈 문자열로 기록.

### 5단계 — 리포트 생성 및 요약

```python
from src.analyze import write_report
import datetime

date_str = datetime.date.today().isoformat()
csv_path = f'output/{date_str}_{topic}.csv'
write_report(csv_path, topic=topic, question=question)
```

.report.md 생성 후:
- 응답률·핵심 군집 1단락으로 요약
- 핵심 인용 3~5개 선별
- 미충족 니즈·거부 사유 추출
- 산출물 경로 안내
- 후속 분석 제안 1줄

---

## B. 페르소나 카드 보기 ("○○ 페르소나 보여줘")

```python
from src.personas import load_pool, filter_pool, print_card
df = load_pool('korea', sample_n=10000)
pool = filter_pool(df, ...)  # 사용자 조건
for i in range(min(3, len(pool))):
    print_card(pool.sample(1).iloc[0])
```

---

## 공통 규칙

- **모든 결과는** `output/YYYY-MM-DD_{topic}.{csv,report.md}` 저장
- **필수 면책**: "LLM 시뮬 기반 가설 — 실제 시장 데이터 아님" 보고마다 명시
- **응답률·찬반 비율은 LLM positive bias로 항상 부풀려짐** — 같은 시뮬 안의 상대 비교(세그먼트 A vs B, 가격 X vs Y)에만 신뢰. 절대값 단독 해석 금지.
- **output/** 폴더가 없으면 생성 후 저장
