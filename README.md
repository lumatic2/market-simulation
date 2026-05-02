# market-simulation

**Claude Code로 한국 소비자 반응을 시뮬레이션하는 도구 — 별도 API 키·로컬 LLM 불필요.**

NVIDIA Nemotron-Personas-Korea (HuggingFace 공개 데이터, 100만 한국 페르소나)를 사용해 타깃 세그먼트가 당신의 제품·가격·서비스 컨셉에 어떻게 반응하는지 시뮬합니다.

---

## 빠른 시작

### 요구사항

- [Claude Code](https://claude.ai/code) (기존 구독 사용 — 추가 비용 없음)
- Python 3.10+

### 설치

```bash
pip install market-simulation
market-simulation install-skill
```

설치 후 **Claude Code 세션을 새로 시작**하면 스킬이 로드됩니다.

### 사용

Claude Code에서 자연어로 요청:

```
서울 30대 직장인들이 월 9,900원 커피 구독 서비스에 어떻게 반응할지 시뮬해줘
```

Claude가 타깃 조건과 질문을 확인한 뒤 시뮬레이션을 실행합니다.

> 결과 파일(CSV + 리포트)은 현재 디렉토리의 `output/` 폴더에 저장됩니다.

---

## 작동 방식

```
HuggingFace 데이터셋          Claude Code 스킬
(100만 한국 페르소나)  ──▶   타깃 세그먼트 필터
                      ──▶   5명씩 배치 분할
                      ──▶   병렬 서브에이전트 실행 (배치별 독립 컨텍스트)
                      ──▶   응답 수집 → CSV + 리포트
```

각 서브에이전트는 5명의 페르소나 카드를 받아 1인칭으로 독립 응답합니다. 배치 간 교차오염 없음.

---

## 시뮬레이션 한도

| | 값 | 이유 |
|---|---|---|
| 기본 | 20명 | 탐색 시뮬 기본값, 테마 포화에 충분 |
| 최대 | **30명** | 6에이전트 × 5명. 초과 시 수익 감소 |
| 배치 크기 | 5명/에이전트 | 컨텍스트 격리 + 응답 품질 균형 |

> 시뮬 결과는 LLM이 생성한 가설이며 실제 시장 데이터가 아닙니다. 절대값보다 **상대 비교**(세그먼트 A vs B, 가격 X vs Y)에 활용하세요.

---

## 출력 예시

```
output/
├── 2026-05-02_coffee-subscription.csv       # 원본 응답
└── 2026-05-02_coffee-subscription.report.md # 자동 생성 통계 리포트
```

**CSV 컬럼:** `id, age, sex, occupation, province, district, answer`

**리포트 포함 내용:** 응답률, 인구통계 분포, 전체 응답 인용, 패턴 클러스터 요약 프롬프트

---

## 데이터셋

| 항목 | 내용 |
|---|---|
| 출처 | [nvidia/Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) |
| 규모 | ~100만 페르소나 |
| 라이선스 | CC BY 4.0 (상업적 사용 가능) |
| 근거 | 한국 인구통계 센서스 기반 생성 |
| 다른 국가 | [Japan](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Japan), [USA](https://huggingface.co/datasets/nvidia/Nemotron-Personas-USA), [France](https://huggingface.co/datasets/nvidia/Nemotron-Personas-France) 등 |

---

## 주의사항

- 시뮬 결과는 **LLM 생성 가설**이며 실제 설문 데이터가 아닙니다.
- 응답률·찬반 비율은 LLM positive bias로 과대 추정됩니다 — 같은 시뮬 내 상대 비교만 신뢰하세요.
- 페르소나 데이터는 CC BY 4.0 공개 데이터입니다. 출처: NVIDIA.

---

## 프로젝트 구조

```
market-simulation/
├── SKILL.md               ← Claude Code 스킬 정의
├── market_simulation/
│   ├── personas.py        ← HuggingFace 로더, 필터, 카드 빌더
│   └── analyze.py         ← CSV → 통계 리포트 생성
└── output/                ← 시뮬 결과 (gitignored)
```

---

## 라이선스

코드: MIT  
페르소나 데이터: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (NVIDIA)

---

---

# market-simulation (English)

**AI-powered market research simulation for Korean consumers — no local LLM or API key required.**

Simulate how real Korean personas respond to your product, price point, or service concept using [NVIDIA Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) (1M demographically grounded personas, CC BY 4.0) and Claude Code's built-in agent system.

---

## Quick start

**Requirements:** [Claude Code](https://claude.ai/code) (any plan) · Python 3.10+

```bash
pip install market-simulation
market-simulation install-skill
```

Restart your Claude Code session, then trigger from any session:

```
서울 30대 직장인들이 월 9,900원 커피 구독 서비스에 어떻게 반응할지 시뮬해줘
```

Results (CSV + report) are saved to `output/` in your current working directory.

---

## How it works

Each sub-agent receives a batch of 5 persona profiles and responds **in character** as each person — independently, with no cross-contamination between batches.

## Simulation limits

| | Value | Why |
|---|---|---|
| Default | 20 personas | Sufficient for theme saturation |
| Hard cap | **30 personas** | 6 agents × 5 personas |
| Batch size | 5 per agent | Context isolation + response quality |

## Programmatic use

```python
from market_simulation import load_pool, filter_pool, occupation_kw

df = load_pool('korea', sample_n=50000)
pool = filter_pool(df, province='서울', age_range=(25, 39),
                   occupation_keywords=occupation_kw('IT'))
sample = pool.sample(20, random_state=42)
```

## Dataset

[nvidia/Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) · ~1M personas · CC BY 4.0  
Also available: Japan, USA, France, and more.

## License

Code: MIT · Persona data: CC BY 4.0 (NVIDIA)
