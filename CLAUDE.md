# market-simulation

Claude Code Agents 기반 AI 시장 반응 시뮬레이터.
NVIDIA Nemotron-Personas-Korea (HuggingFace) → 페르소나 필터 → 배치 에이전트 격리 실행 → CSV + 리포트.

## 기술 스택

- Python 3.10+, pandas, HuggingFace datasets (스트리밍)
- Claude Code Agent 툴 (로컬 LLM·API 키 불필요)
- Markdown 기반 스킬 (`SKILL.md`)

## 프로젝트 구조

- `SKILL.md` — Claude Code 스킬 진입점 (배포 대상)
- `src/personas.py` — HF 스트리밍 로더 + 필터 + 카드 빌더
- `src/analyze.py` — 결과 CSV → 통계 리포트 .md
- `output/` — 시뮬 결과 저장 (gitignored)
- `pyproject.toml` — 의존성

## 시뮬 한도

- 기본 20명 / 최대 30명 (하드캡)
- 배치 5명 × 최대 6 에이전트 병렬

## 개발

```bash
pip install -e .
python src/personas.py   # smoke test
```

## 배포 (custom-skills 레포로 링크)

```bash
cp SKILL.md ~/projects/custom-skills/market-simulation.md
bash ~/projects/custom-skills/setup.sh
```
