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

## 역할 분담 (중요)

| 단계 | 실행 주체 | 방법 |
|---|---|---|
| 데이터 로드·필터 | Python | Bash 툴로 실행 |
| 페르소나 시뮬 | **Claude (나)** | **Agent 툴 직접 사용** |
| CSV 저장 | Claude (나) | Write 툴 |
| 리포트 생성 | Python | Bash 툴로 실행 |

> Agent 툴은 Python에서 호출하지 않는다. Claude가 대화 흐름 안에서 직접 사용한다.

---

## 시뮬레이션 한도 (하드캡)

| | 값 | 이유 |
|---|---|---|
| **기본** | **20명** | 탐색 시뮬 기본, 테마 포화 충분 |
| **최대** | **30명** | 6 에이전트 × 5명. 초과 시 거부 |
| 배치 크기 | 5명/에이전트 | 컨텍스트 격리 + 응답 품질 균형 |

요청이 30명을 초과하면: "30명이 최대 한도입니다. N=30으로 진행할까요?" 확인 후 진행.

---

## 시작 전 의존성 확인

```python
import importlib, sys
missing = [m for m in ['datasets', 'pandas'] if not importlib.util.find_spec(m)]
print('OK' if not missing else f'pip install {" ".join(missing)}')
```

설치 안 됐으면 사용자에게 `pip install datasets pandas` 안내 후 중단.

---

## A. 시뮬레이션 ("○○에 대해 ○○ 사람들 반응 봐줘")

### 1단계 — 조건 확인 (1회 되묻기)

사용자에게 확인:
- **타깃 조건**: 지역(시도), 나이대, 성별, 직업 유형 (없으면 무작위)
- **질문**: 페르소나에게 던질 질문 1개
- **인원**: 기본 20명, 요청 시 최대 30명

### 2단계 — 페르소나 카드 생성 (Python)

```python
import sys, os
sys.stdout.reconfigure(encoding='utf-8')  # Windows 터미널 한글 깨짐 방지
sys.path.insert(0, os.path.abspath('.'))
from src.personas import load_pool, filter_pool, occupation_kw, persona_to_card

df = load_pool('korea', sample_n=50000)

pool = filter_pool(
    df,
    province='서울',                              # 없으면 제거
    age_range=(25, 45),                           # 없으면 제거
    occupation_keywords=occupation_kw('직장인'),  # 없으면 제거
)

N = 20          # 사용자 요청 인원
N = min(N, 30)  # 하드캡 강제 — 항상 유지
BATCH_SIZE = 5

if len(pool) < N * 3:
    print(f'WARNING: 필터 후 {len(pool)}명 — 조건 완화 권장')

sample = pool.sample(min(N, len(pool)), random_state=42).reset_index(drop=True)
n_batches = -(-len(sample) // BATCH_SIZE)
print(f'시뮬 설계: {len(sample)}명 / {n_batches}배치 × {BATCH_SIZE}명')

# 배치 분할 및 카드 출력 (Claude가 읽을 것)
for batch_idx in range(n_batches):
    batch = sample.iloc[batch_idx * BATCH_SIZE:(batch_idx + 1) * BATCH_SIZE]
    print(f'\n=== BATCH {batch_idx + 1} / {n_batches} ({len(batch)}명) ===')
    for local_idx, (_, p) in enumerate(batch.iterrows()):
        print(persona_to_card(p, local_idx))
        print()
```

풀이 N의 3배 미만이면 사용자에게 조건 완화 제안 후 재필터.

### 3단계 — 배치별 에이전트 시뮬 (Claude가 Agent 툴 직접 사용)

Python 출력으로 받은 배치별 카드를 보고, 각 배치마다 **Agent 툴**을 background=True로 호출한다.  
모든 배치의 에이전트를 **동시에** 발사하고 결과를 기다린다.

**각 에이전트에게 전달하는 프롬프트 (배치별로 카드만 교체):**

```
아래 {batch_size}명의 한국인 인물 프로필이 있습니다.
각 인물 입장에서, 그 인물의 어휘·말투·가치관으로 질문에 1인칭 한국어로 답해주세요.

규칙:
- 각 인물은 서로의 응답을 모릅니다. 완전히 독립적으로 답하세요.
- AI 또는 가상 인물이라는 사실은 절대 언급하지 마세요.
- 답변은 2~5문장. 자신의 일상·예산·우선순위에 비추어 솔직하게.
- 모르면 "잘 모르겠는데, 아마…"처럼 불확실성을 표시.
- **반드시 {batch_size}개 응답 블록을 출력하라. 한 명도 빠뜨리지 말 것.**

질문: {실제 질문 텍스트}

---

{persona_to_card 출력 batch_size개}

---

출력 형식 (정확히 이 형식만, 다른 설명 없이):

## 응답 1
[인물 1의 1인칭 응답]

## 응답 2
[인물 2의 1인칭 응답]

...
```

### 4단계 — 파싱 및 CSV 저장 (Claude가 Write 툴 사용)

각 에이전트 결과에서 `## 응답 N` 블록을 순서대로 읽어 해당 배치의 N번째 페르소나와 매칭한다.

**파싱 검증 (중요):** 각 배치 에이전트 결과에서 `## 응답` 블록 수를 센다.  
예상 수(`batch_size`)와 실제 수가 다르면 → **즉시 사용자에게 알리고** 해당 배치를 재실행하거나 누락 위치를 빈 값으로 명시.  
조용히 `""` 로 기록하고 넘어가지 말 것.

CSV 행 구조:
```
id, age, sex, occupation, province, district, answer
```

- `id`: 전체 시뮬 통산 번호 (0부터)
- 인구통계 컬럼: 2단계 sample DataFrame에서 직접 참조
- `answer`: `## 응답 N` 이후 다음 `## 응답` 전까지의 텍스트 (strip 후 저장)
- 파싱 실패: `answer = "[파싱 실패 - 배치 {batch_idx}, 인물 {local_idx}]"` 로 명시

저장 경로: `output/YYYY-MM-DD_{topic}.csv`  
`output/` 디렉토리 없으면 먼저 생성.

### 5단계 — 리포트 생성 및 요약 (Python)

```python
from src.analyze import write_report
import datetime

date_str = datetime.date.today().isoformat()
csv_path = f'output/{date_str}_{topic}.csv'
report_path = write_report(csv_path, topic=topic, question=question)
print(f'report: {report_path}')
```

리포트 생성 후 Claude가 직접:
- 응답률·핵심 군집 1단락 요약
- 핵심 인용 3~5개 선별
- 미충족 니즈·거부 사유 추출
- 산출물 경로 안내
- 후속 분석 제안 1줄

---

## B. 페르소나 카드 보기 ("○○ 페르소나 보여줘")

```python
import sys, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath('.'))
from src.personas import load_pool, filter_pool, print_card

df = load_pool('korea', sample_n=10000)
pool = filter_pool(df, province='서울')  # 사용자 조건으로 교체

cards = pool.sample(min(3, len(pool)), random_state=42)
for _, p in cards.iterrows():
    print_card(p)
```

---

## 공통 규칙

- **모든 결과**: `output/YYYY-MM-DD_{topic}.{csv,report.md}` 저장
- **필수 면책**: "LLM 시뮬 기반 가설 — 실제 시장 데이터 아님" 보고마다 명시
- **응답률·찬반 비율은 LLM positive bias로 항상 부풀려짐** — 같은 시뮬 안의 상대 비교(세그먼트 A vs B, 가격 X vs Y)에만 신뢰. 절대값 단독 해석 금지.
