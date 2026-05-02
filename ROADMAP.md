> 마지막 업데이트: 2026-05-02

# ROADMAP — market-simulation

## v0.1 — 기반 구조

- [x] `src/personas.py` — HF 스트리밍 로더 (로컬 parquet 의존성 제거)
- [x] `src/analyze.py` — 결과 CSV → 통계 리포트 (Agent 방식 맞게 정제)
- [x] `SKILL.md` — 배치 5명 × 최대 6 에이전트, 30명 하드캡
- [x] `pyproject.toml`, `CLAUDE.md`
- [x] `.gitignore` 추가
- [x] GitHub 레포 생성 및 초기 커밋 → https://github.com/lumatic2/market-simulation
- [x] README.md (영문, 공개용)
- [x] Codex adversarial review 반영 — 샘플링 편향·CSV crash·silent parse fail 수정
- [x] 실행 테스트 — 첫 로드 43s 문제(buffer_size=100k로 17s), Windows 인코딩 garbling 수정
- [x] `~/.claude/skills/market-simulation.md` 배포 완료

## v0.2 — 검증

- [ ] 실제 시뮬 1회 end-to-end 실행 (페르소나 로드 → Agent 배치 → CSV → report)
- [ ] 응답 형식 파싱 엣지케이스 처리 (에이전트 `## 응답 N` 형식 불일치)
- [ ] Japan 페르소나 연동 테스트

## 이어서 할 일

새 세션에서 `~/projects/market-simulation/` 기준으로:
1. "서울 30대 직장인 20명, 월 9,900원 커피 구독 반응 시뮬해줘" 로 end-to-end 실행
2. 에이전트 응답 `## 응답 N` 파싱 안정성 확인 → 형식 불일치 케이스 처리

## v0.3 — 공개 준비

- [ ] 예제 스크립트 (`examples/coffee_shop.py`)
- [ ] HuggingFace Space 또는 GitHub Actions CI 고려
