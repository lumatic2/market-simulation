# market-simulation

**Claude Code로 AI 페르소나 시뮬레이션 — 별도 API 키·로컬 LLM 불필요.**

NVIDIA Nemotron-Personas (HuggingFace, CC BY 4.0) 7개국 800만+ 페르소나를  
Claude Code Agent로 배치 실행. 타깃 세그먼트의 반응을 10분 안에 수집합니다.

> ⚠️ **AI가 AI 페르소나를 연기하는 구조입니다.** 실제 소비자 조사·설문을 대체할 수 없으며,  
> 결과는 아이디어 초기 검증·가설 수립 용도로만 사용하세요.

---

## 빠른 시작

**요구사항:** [Claude Code](https://claude.ai/code) · Python 3.10+

```bash
pip install market-simulation
market-simulation install-skill
```

Claude Code 세션을 **새로 시작**하면 스킬이 로드됩니다.

---

## 사용 예시

Claude Code에서 자연어로 요청하면 됩니다.

### 시장 반응 시뮬

```
서울 30대 직장인들이 월 9,900원 커피 구독 서비스에 어떻게 반응할지 20명 시뮬해줘
```

```
도쿄 20대 여성 15명한테 이 앱 프리미엄 플랜 가격(월 $9.99)이 적절한지 물어봐줘
```

### 카피·메시지 A/B 테스트

```
아래 두 광고 카피 중 2030 서울 여성 20명이 어느 쪽에 더 끌리는지 비교해줘
A: "하루 한 잔, 나를 위한 루틴"
B: "매일 아침 커피값 아끼는 법"
```

### 콘텐츠 접근성 검증

```
이 서비스 약관을 고졸 학력의 40대 직장인 10명이 읽었을 때 이해하기 어려운 부분이 어디인지 시뮬해줘
[약관 텍스트 붙여넣기]
```

### AI/챗봇 편향 탐지

```
우리 고객센터 챗봇의 아래 응답이 50대 남성 사용자에게 자연스럽게 느껴지는지 10명한테 확인해줘
[챗봇 응답 텍스트]
```

### 정책·HR 시뮬

```
주 4.5일제 도입 계획을 발표했을 때 제조·IT·서비스 직군 각 10명이 어떻게 반응할지 비교해줘
```

### 브랜드 네이밍 테스트

```
아래 3개 브랜드명 중 30대 자영업자 20명이 가장 신뢰감 있다고 느끼는 건 어느 쪽인지 시뮬해줘
A: Brewly  B: DailyDrip  C: Cuppa
```

---

## 지원 국가

| country | 데이터셋 | 언어 | 페르소나 수 |
|---|---|---|---|
| `korea` | Nemotron-Personas-Korea | 한국어 | ~100만 |
| `usa` | Nemotron-Personas-USA | 영어 | ~100만 |
| `japan` | Nemotron-Personas-Japan | 일본어 | ~100만 |
| `india` | Nemotron-Personas-India | 영어/힌디 | ~300만 |
| `france` | Nemotron-Personas-France | 프랑스어 | ~100만 |
| `brazil` | Nemotron-Personas-Brazil | 포르투갈어 | ~100만 |
| `singapore` | Nemotron-Personas-Singapore | 영어 | ~15만 |

```
캘리포니아 25~40세 tech 직군 대상으로 USA 시뮬 돌려줘
```

---

## 작동 방식

```
HuggingFace 스트리밍          Claude Code 스킬
(800만+ 페르소나)   ──▶   타깃 세그먼트 필터
                   ──▶   5명씩 배치 분할
                   ──▶   병렬 서브에이전트 실행 (배치별 독립 컨텍스트)
                   ──▶   응답 수집 → CSV + 리포트
```

- 스트리밍 로드 — 전체 데이터셋 다운로드 없이 동작
- 배치별 독립 실행 — 페르소나 간 교차오염 없음
- 결과: `output/YYYY-MM-DD_{topic}.csv` + `.report.md`

---

## 시뮬레이션 한도

| | 값 |
|---|---|
| 기본 | 20명 |
| 최대 | **30명** (6에이전트 × 5명) |

---

## 프로그래매틱 사용

```python
from market_simulation import load_pool, filter_pool, occupation_kw

df = load_pool('korea', sample_n=50000)
pool = filter_pool(df, province='서울', age_range=(25, 39),
                   occupation_keywords=occupation_kw('IT'))
sample = pool.sample(20, random_state=42)
```

영어권 직업 필터: `occupation_kw('tech')`, `occupation_kw('finance')`, `occupation_kw('healthcare')` 등

---

## 주의사항

- 결과는 **LLM이 생성한 가설**이며 실제 설문·인터뷰 데이터가 아닙니다.
- 찬성 비율은 LLM positive bias로 과대 추정됩니다 — 같은 시뮬 내 **상대 비교**에만 활용하세요.
- 페르소나 데이터: CC BY 4.0 (NVIDIA). 출처 명시 필요.

---

## 라이선스

코드: MIT · 페르소나 데이터: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (NVIDIA)

---

---

# market-simulation (English)

**AI persona simulation via Claude Code — no local LLM or API key required.**

Run batched market research, copy testing, content audits, and more against  
NVIDIA Nemotron-Personas (7 countries, 8M+ personas, CC BY 4.0).

> ⚠️ **This is LLM-plays-LLM-personas.** Results are hypotheses for early-stage validation,  
> not a substitute for real consumer research. Absolute numbers are biased upward.

---

## Quick start

**Requirements:** [Claude Code](https://claude.ai/code) · Python 3.10+

```bash
pip install market-simulation
market-simulation install-skill
```

Restart your Claude Code session, then ask in natural language.

---

## What you can do

| Use case | Example prompt |
|---|---|
| Market reaction | "Simulate how 20 Seoul office workers in their 30s react to a ₩9,900/mo coffee subscription" |
| Copy A/B test | "Which of these 2 taglines resonates more with women in their 20s–30s in Tokyo?" |
| Content accessibility | "Would a high-school-educated 40-year-old find this terms-of-service confusing?" |
| Chatbot bias check | "Does our chatbot response feel natural to male users in their 50s?" |
| Policy / HR simulation | "Compare reactions to a 4.5-day workweek across manufacturing, IT, and service workers" |
| Brand naming test | "Which of these 3 brand names feels most trustworthy to self-employed people in their 30s?" |

---

## Supported countries

`korea` · `usa` · `japan` · `india` · `france` · `brazil` · `singapore`

---

## Programmatic use

```python
from market_simulation import load_pool, filter_pool, occupation_kw

df = load_pool('usa', sample_n=50000)
pool = filter_pool(df, province='CA', age_range=(25, 39),
                   occupation_keywords=occupation_kw('tech'))
sample = pool.sample(20, random_state=42)
```

---

## License

Code: MIT · Persona data: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (NVIDIA)
