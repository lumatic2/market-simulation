---
name: market-simulation
description: >
  NVIDIA Nemotron 페르소나(HuggingFace 공개 데이터, 로컬 LLM·API 키 불필요)로
  시장 반응을 시뮬레이션한다. 한국·미국·일본·인도·프랑스·브라질·싱가포르 지원.
  Claude Code Agent 툴로 배치 격리 실행.
  "시장 반응", "사용자 조사", "포커스 그룹", "페르소나 시뮬", "타깃 반응",
  "구매 의향", "가격 테스트", "한국 소비자", "미국 시장" 등 언급 시 이 스킬을 사용하라.
  Also activate for English prompts mentioning: "market research", "persona simulation",
  "simulate reactions", "focus group", "purchase intent", "price test", "user survey",
  "target audience", "consumer research", "market test".
---

# /market-simulation — AI 시장 반응 시뮬레이터

**전제**: Claude Code만 있으면 동작. 로컬 LLM, 별도 API 키 불필요.  
**데이터**: NVIDIA Nemotron-Personas (HuggingFace, CC BY 4.0) — 7개국 총 800만+ 페르소나  
**권장 모델**: Claude Sonnet 이상 (리포트 인사이트 해석 품질에 영향)

---

## ⚠️ 면책 고지 — 시뮬 시작 전 반드시 사용자에게 고지

스킬 실행 첫 메시지에 다음 문구를 **항상** 포함한다:

> **이 시뮬레이션은 AI가 AI 페르소나를 연기하는 구조입니다.**  
> 결과는 실제 소비자 조사·인터뷰·설문을 대체할 수 없으며, 통계적 대표성이 없습니다.  
> 아이디어 초기 검증·가설 수립 용도로만 사용하세요.  
> 특히 찬성 비율은 LLM positive bias로 실제보다 높게 나오는 경향이 있습니다.  
> 페르소나 데이터는 **완전 합성**입니다. 실존 인물과의 유사성은 전적으로 우연입니다.  
> 금융·헬스케어 등 엔터프라이즈 직군은 데이터셋에 포함되지 않아 해당 필터 시 풀이 희박할 수 있습니다.

---

## 지원 국가 (country 파라미터)

| country | 데이터셋 | 언어 | level-1 지역 | level-2 지역 |
|---|---|---|---|---|
| `korea` | Nemotron-Personas-Korea | 한국어 | province (시도) | district (시군구) |
| `usa` | Nemotron-Personas-USA | 영어 | state (약어: 'CA', 'NY', 'TX'…) | city |
| `japan` | Nemotron-Personas-Japan | 일본어 | prefecture | area |
| `india` | Nemotron-Personas-India | 영어/힌디 | state | district |
| `france` | Nemotron-Personas-France | 프랑스어 | departement | commune |
| `brazil` | Nemotron-Personas-Brazil | 포르투갈어 | state | municipality |
| `singapore` | Nemotron-Personas-Singapore | 영어 | planning_area | — |

`filter_pool(province=...)` 의 province 파라미터는 각 국가의 level-1 컬럼에 자동 매핑된다.

> **USA 주의**: occupation 값이 snake_case 코드(`software_developer`, `not_in_workforce` 등)로 저장됨.  
> `not_in_workforce` 비율이 ~46%로 높으므로 직업 필터를 적용하지 않으면 풀이 희석됨.  
> 영어 occupation 필터는 `occupation_kw('tech')`, `occupation_kw('management')` 등 사용.

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
| **최대** | **30명** | 3 에이전트 × 10명. 초과 시 거부 |
| 배치 크기 | 10명/에이전트 | 컨텍스트 격리 + 응답 품질 균형 |

요청이 30명을 초과하면: "30명이 최대 한도입니다. N=30으로 진행할까요?" 확인 후 진행.

---

## 시작 전 의존성 + 버전 확인

```python
import importlib.util, importlib.metadata, subprocess, sys, re

# 1. 누락 패키지 설치
pip_map = {'datasets': 'datasets', 'pandas': 'pandas', 'pyarrow': 'pyarrow', 'market_simulation': 'market-simulation'}
missing = [pip_map[m] for m in pip_map if not importlib.util.find_spec(m)]
if missing:
    print(f'패키지 설치 중: {missing}', flush=True)
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q'] + missing)
    print('설치 완료 — 계속 진행합니다.', flush=True)

# 2. 버전 체크 (최신 여부 확인, 5초 타임아웃)
try:
    installed = importlib.metadata.version('market-simulation')
    r = subprocess.run(
        [sys.executable, '-m', 'pip', 'index', 'versions', 'market-simulation'],
        capture_output=True, text=True, timeout=5
    )
    m = re.search(r'LATEST:\s+(\S+)', r.stdout)
    latest = m.group(1) if m else None
    if latest and latest != installed:
        print(f'⚠ 스킬 업데이트 있음: {installed} → {latest}')
        print('  지금 업데이트하려면:')
        print('  pip install --upgrade market-simulation && market-simulation install-skill')
        print('  (설치 후 Claude Code 세션 재시작 필요)')
    else:
        print(f'OK (market-simulation {installed})', flush=True)
except Exception:
    print(f'OK', flush=True)
```

`sys.executable`로 Claude Code Bash 툴이 사용하는 Python에 직접 설치하므로 환경 불일치 문제가 없다.  
버전 체크는 PyPI에 네트워크 요청 1회 (~1초). 오프라인 환경에서는 조용히 스킵된다.

---

## A. 시뮬레이션 ("○○에 대해 ○○ 사람들 반응 봐줘")

### 0단계 — 모드 자동 감지

질문 텍스트를 보고 시뮬 모드를 결정한다. 판단 불가 시 사용자에게 1회만 확인.

| 신호 | 모드 |
|---|---|
| ~겠어요? / ~할 의향 / 구독·구매·신청·사용하겠 | **A** — 수용 테스트 |
| 어떤 / 무엇 / 왜 / 어떻게 / 어느 것 / 가장 중요 | **B** — 발견 조사 |
| A 신호 + B 신호 동시 등장 | **C** — 수용 + 이유 |

모드별 차이점: 에이전트 출력 태그 형식, CSV 컬럼, 리포트 구조.

### 1단계 — 조건 확인 (1회 되묻기)

스킬이 처음 실행될 때 아래 형식으로 **사용 가능한 조건을 먼저 안내**한 후, 확인이 필요한 항목만 물어본다.

안내 메시지 예시 (국가·상황에 맞게 조정):
```
시뮬레이션을 시작합니다. 아래 조건을 조합할 수 있습니다:

• 국가: korea / usa / japan / india / france / brazil / singapore
• 지역: 시도 단위 (예: 서울, 부산 / CA, NY, TX)
• 나이대: 예) 20대, 30~45세
• 성별: 전체 균등(기본) / 여성만 / 남성만 / 직접 지정 (예: 여성 70%)
• 직업: 예) IT직군, 자영업자, 학생 / tech, finance, healthcare
• 인원: 기본 20명, 최대 30명

조건을 생략하면 해당 항목은 기본값(성별 균등, 나머지 무작위)으로 선택됩니다.
---
현재 요청 기준으로 아래와 같이 이해했습니다. 맞으면 바로 시작할게요:
[파악한 조건 정리]
```

미파악 항목이 있을 때만 추가로 질문. 사용자가 이미 충분한 정보를 줬다면 안내 후 바로 2단계 진행.

### 2단계 — 페르소나 카드 생성 (Python)

```python
import sys, time
sys.stdout.reconfigure(encoding='utf-8')  # Windows 터미널 한글 깨짐 방지
from market_simulation.personas import stream_until_pool, occupation_kw, persona_to_card

N = 20          # 사용자 요청 인원
N = min(N, 30)  # 하드캡 강제 — 항상 유지
BATCH_SIZE = 10
seed = int(time.time()) % 100000   # 매 실행마다 다른 페르소나
country = 'korea'  # 1단계에서 결정

# 성별 모드 (1단계에서 결정):
#   '균등'                      → 성별 필터 없음, 남/여 균등 샘플 (기본값)
#   '여성만' | '남성만'         → 해당 성별만 스트리밍 필터
#   {'여성': 0.7, '남성': 0.3} → 비율 지정 샘플
sex_mode = '균등'

# 국가 → 에이전트 응답 언어 (에이전트 프롬프트에 주입)
LANG = {'korea': '한국어', 'usa': 'English', 'japan': '日本語',
        'india': 'English', 'france': 'Français', 'brazil': 'Português', 'singapore': 'English'}
response_lang = LANG.get(country, 'English')

sex_filter = '여성' if sex_mode == '여성만' else ('남성' if sex_mode == '남성만' else None)

# 좁은 조건(특정 지역+직업 등)은 max_rows=300,000행까지 스캔하므로 수 분 소요 가능
pool = stream_until_pool(
    country=country,
    province='서울',                              # 국가별 level-1 지역 (없으면 제거)
    age_range=(25, 45),                           # 없으면 제거
    occupation_keywords=occupation_kw('직장인'),  # 없으면 제거 (영어권: occupation_kw('tech') 등)
    sex=sex_filter,
    target_pool=N * 5,
    seed=seed,
)

if len(pool) == 0:
    print('ERROR: 조건에 맞는 페르소나가 없습니다. 필터 조건을 완화해주세요.')
    raise SystemExit(1)
if len(pool) < N * 3:
    print(f'WARNING: 필터 후 {len(pool)}명 — 조건 완화 권장')

import pandas as pd

def _stratified_sample(pool, N, sex_mode, seed):
    if sex_mode in ('여성만', '남성만'):
        return pool.sample(min(N, len(pool)), random_state=seed).reset_index(drop=True)
    if isinstance(sex_mode, dict):
        parts = [pool[pool['sex'] == s].sample(
                     min(round(N * r), len(pool[pool['sex'] == s])), random_state=seed)
                 for s, r in sex_mode.items() if len(pool[pool['sex'] == s]) > 0]
    else:  # '균등'
        sex_groups = [s for s in pool['sex'].unique() if len(pool[pool['sex'] == s]) > 0]
        quota = max(1, N // max(len(sex_groups), 1))
        parts = [pool[pool['sex'] == s].sample(min(quota, len(pool[pool['sex'] == s])), random_state=seed)
                 for s in sex_groups]
    if not parts:
        return pool.sample(min(N, len(pool)), random_state=seed).reset_index(drop=True)
    combined = pd.concat(parts)
    if len(combined) < N:
        remain = pool.drop(combined.index)
        if len(remain) > 0:
            combined = pd.concat([combined, remain.sample(min(N - len(combined), len(remain)), random_state=seed)])
    return combined.sample(frac=1, random_state=seed).reset_index(drop=True)

sample = _stratified_sample(pool, N, sex_mode, seed)
sex_dist = sample['sex'].value_counts().to_dict()
print(f'성별 구성: {sex_dist}')
print(f'응답 언어: {response_lang}')
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

> `{batch_size}` 플레이스홀더는 Python 출력의 `=== BATCH N / M (K명) ===` 에서 읽은 K값(해당 배치 실제 인원)으로 채운다. 마지막 배치는 BATCH_SIZE보다 적을 수 있다.

**에이전트 프롬프트 — 모드별로 출력 형식 블록만 교체한다. 나머지(인물 설명, 규칙)는 동일.**

공통 규칙 블록:
```
아래 {batch_size}명의 인물 프로필이 있습니다.
각 인물 입장에서, 그 인물의 어휘·말투·가치관으로 질문에 1인칭으로 답해주세요.

규칙:
- 각 인물은 서로의 응답을 모릅니다. 완전히 독립적으로 답하세요.
- AI 또는 가상 인물이라는 사실은 절대 언급하지 마세요.
- 답변은 {response_lang}로, 2~5문장. 자신의 일상·예산·우선순위에 비추어 솔직하게.
- 모르면 그 언어로 "잘 모르겠는데, 아마…"처럼 불확실성을 표시.
- **반드시 {batch_size}개 응답 블록을 출력하라. 한 명도 빠뜨리지 말 것.**

질문: {실제 질문 텍스트}

---

{persona_to_card 출력 batch_size개}

---
```

**A모드 출력 형식 블록** (수용 테스트):
```
출력 형식 (정확히 이 형식만, 다른 설명 없이):

## 응답 1 [긍정|중립|부정 중 하나]
[인물 1의 1인칭 응답]

## 응답 2 [긍정|중립|부정 중 하나]
[인물 2의 1인칭 응답]

...

태그 기준:
- 긍정: 주제에 대해 수용·환영·관심·기대를 주로 표현
- 중립: 찬반이 혼재하거나 자신과 무관한 반응, 유보적
- 부정: 거부·불만·해당 없음·부담을 주로 표현
```

**B모드 출력 형식 블록** (발견 조사):
```
출력 형식 (정확히 이 형식만, 다른 설명 없이):

## 응답 1 [테마: 태그1, 태그2]
[인물 1의 1인칭 응답]

## 응답 2 [테마: 태그1]
[인물 2의 1인칭 응답]

...

테마 태그 규칙:
- 1~3개, {response_lang}로 작성
- 2~6자(영어 1~3단어) 명사구. 응답의 핵심 관심사·이유·패턴을 반영
- 예: 가격부담, 편의성, 보안우려, 습관변화 / price concern, convenience, habit change
```

**C모드 출력 형식 블록** (수용 + 이유):
```
출력 형식 (정확히 이 형식만, 다른 설명 없이):

## 응답 1 [긍정 · 테마: 편의성, 가격합리]
[인물 1의 1인칭 응답]

## 응답 2 [부정 · 테마: 보안우려]
[인물 2의 1인칭 응답]

...

태그 규칙:
- 감성(긍정|중립|부정) 먼저, 공백·가운뎃점(·)·공백 후 테마: 로 구분
- 테마 태그는 B모드와 동일 규칙 (응답 언어 일치, 1~3개)
```

### 4단계 — 파싱 및 CSV 저장 (Claude가 Write 툴 사용)

각 에이전트 결과에서 `## 응답 N [태그]` 블록을 순서대로 읽어 해당 배치의 N번째 페르소나와 매칭한다.

**파싱 검증 (중요):** 각 배치 에이전트 결과에서 `## 응답` 블록 수를 센다.  
예상 수(`batch_size`)와 실제 수가 다르면 → **즉시 사용자에게 알리고** 해당 배치를 재실행하거나 누락 위치를 빈 값으로 명시.  
조용히 `""` 로 기록하고 넘어가지 말 것.

CSV 행 구조 — 모드별:

**A모드**: `id, age, sex, occupation, province, district, answer, sentiment`  
**B모드**: `id, age, sex, occupation, province, district, answer, themes`  
**C모드**: `id, age, sex, occupation, province, district, answer, sentiment, themes`

- `id`: 전체 시뮬 통산 번호 (0부터)
- 인구통계 컬럼: 2단계 sample DataFrame에서 직접 참조
- `answer`: `## 응답 N [태그]` 헤더 이후 다음 `## 응답` 전까지의 텍스트 (strip 후 저장)
- `sentiment`: A/C모드 — 헤더 `[긍정|중립|부정]` 또는 `[긍정 · 테마: ...]`에서 추출. 누락 시 `""` (analyze.py rule-based 보완)
- `themes`: B/C모드 — 헤더 `[테마: 태그1, 태그2]` 또는 `[감성 · 테마: 태그1, 태그2]`에서 태그 부분만 추출. 누락 시 `""`
- 파싱 실패: `answer = "[파싱 실패 - 배치 {batch_idx}, 인물 {local_idx}]"`, 나머지 컬럼 `""` 로 명시

저장 경로: `output/YYYY-MM-DD_{topic}.csv`  
`output/` 디렉토리 없으면 먼저 생성.

### 5단계 — 리포트 생성 및 요약 (Python)

```python
from market_simulation.analyze import write_report
import datetime

date_str = datetime.date.today().isoformat()
csv_path = f'output/{date_str}_{topic}.csv'
report_path = write_report(csv_path, topic=topic, question=question)
print(f'report: {report_path}')
```

리포트는 다음 섹션을 자동 생성한다:
- **감성 분포** — 긍정/부정/중립 비율 (에이전트 출력 태그 우선, 누락 시 rule-based 보완)
- **세그먼트 프로파일** — 긍정군 vs 부정군 평균 나이·직업 비교
- **인구통계 × 감성 교차표** — 나이대·직업·지역별 긍정율/부정율
- **키워드 분석** — 전체/긍정/부정 응답 상위 빈도 어휘
- **positive bias 경고** — 긍정률 70% 초과 시 자동 플래그

리포트 생성 후 Claude가 직접:
- 교차표에서 세그먼트 간 눈에 띄는 차이 1단락 해석
- 핵심 인용 3~5개 선별
- 거부 이유 키워드 패턴 요약
- 산출물 경로 안내
- 후속 분석 제안 1줄

---

## B. 페르소나 카드 보기 ("○○ 페르소나 보여줘")

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
from market_simulation.personas import stream_until_pool, print_card

pool = stream_until_pool(
    country='korea',
    province='서울',   # 사용자 조건으로 교체. 없으면 제거
    target_pool=20,
)

cards = pool.sample(min(3, len(pool)), random_state=42)
for _, p in cards.iterrows():
    print_card(p)
```

---

## 공통 규칙

- **모든 결과**: `output/YYYY-MM-DD_{topic}.{csv,report.md}` 저장
- **필수 면책**: "LLM 시뮬 기반 가설 — 실제 시장 데이터 아님" 보고마다 명시
- **응답률·찬반 비율은 LLM positive bias로 항상 부풀려짐** — 같은 시뮬 안의 상대 비교(세그먼트 A vs B, 가격 X vs Y)에만 신뢰. 절대값 단독 해석 금지.
