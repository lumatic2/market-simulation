> 마지막 업데이트: 2026-05-03

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

## v0.2 — 검증 + 배포 개선

- [x] 실제 시뮬 1회 end-to-end 실행 — 서울 30대 직장인 20명, 커피 구독 (20/20 완료, 파싱 실패 0)
- [x] 응답 형식 파싱 안정성 확인 — `## 응답 N` 4배치 모두 정확 매칭, 포맷 불일치 0건
- [x] `market-simulation install-skill` CLI 추가 — pip+curl 이중 설치 → pip 단일 플로우로 개선. PyPI v0.2.0 배포
- [x] SKILL.md 의존성 자동설치 — 누락 패키지를 `sys.executable`로 직접 설치 (환경 불일치 해결)
- [x] personas.py 수집 후 재셔플 — filter 단계 편향 완화, 도큐스트링 한계 명시
- [x] README 한국어 상단 + 영어 하단 이중 언어 재작성, 단계 번호 버그 수정
- [x] 새 사용자 시뮬 3회 반복 → UX 문제 7개 발견·수정 (mkdir, Windows curl, 세션 재시작 안내 등)
- [x] Japan 페르소나 연동 테스트 — prefecture/area/marital_status 컬럼 확인, 도쿄 필터·카드 생성 정상
- [x] SKILL.md 이중 관리 해결 — setup.py build_py 훅으로 루트 → 패키지 자동 복사, market_simulation/SKILL.md gitignore 처리

## 이어서 할 일

새 세션에서 `~/projects/market-simulation/` 기준으로:
1. SKILL.md 이중 관리 해결 — `Makefile` 또는 `setup.py` pre-build hook으로 루트 SKILL.md → market_simulation/SKILL.md 자동 동기화
2. Japan 페르소나 실제 시뮬 — `load_pool('japan', sample_n=50000)` → 도쿄 30대 회사원 대상 시뮬 1회
3. 지인 3~5명 소프트론치 — 설치 → 시뮬 → 결과 피드백 수집

## v0.3 — 공개 준비

- [x] SKILL.md 단일 소스 관리 (setup.py build_py 훅)
- [x] Japan 시뮬 검증
- [x] 예제 스크립트 (`examples/coffee_shop.py`)
- [ ] 소프트론치 피드백 반영
