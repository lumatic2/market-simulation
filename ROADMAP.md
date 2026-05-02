# ROADMAP — market-simulation

## v0.1 — 기반 구조 (현재)

- [x] `src/personas.py` — HF 스트리밍 로더 (로컬 parquet 의존성 제거)
- [x] `src/analyze.py` — 결과 CSV → 통계 리포트 (Agent 방식 맞게 정제)
- [x] `SKILL.md` — 배치 5명 × 최대 6 에이전트, 30명 하드캡
- [x] `pyproject.toml`, `CLAUDE.md`
- [x] `.gitignore` 추가
- [x] GitHub 레포 생성 및 초기 커밋
- [x] README.md (영문, 공개용)

## v0.2 — 검증

- [ ] 실제 시뮬 1회 실행 후 파싱 로직 검증
- [ ] 응답 형식 파싱 엣지케이스 처리 (에이전트 형식 불일치)
- [ ] Japan 페르소나 연동 테스트

## v0.3 — 공개 준비

- [ ] 예제 노트북 또는 예제 스크립트 (`examples/coffee_shop.py`)
- [ ] HuggingFace Space 또는 GitHub Actions CI 고려
