> 마지막 업데이트: 2026-05-03 (v0.7.0 배포 완료)

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

## v0.3 — 공개 준비

- [x] SKILL.md 단일 소스 관리 (setup.py build_py 훅)
- [x] Japan 시뮬 검증
- [x] 예제 스크립트 (`examples/coffee_shop.py`)
- [ ] 소프트론치 피드백 반영 (보류 중)

## v0.4 — 다국가 확장

- [x] 7개국 페르소나 지원 (Korea, Japan, US, UK, Germany, France, Brazil)
- [x] LLM disclaimer + 윤리 가이드 추가
- [x] README 7-country + 6 use cases 이중언어 재작성
- [x] sentiment labeling + crosstab + keyword 분석 (`analyze.py`)

## v0.5 — 분석 고도화

- [x] analyze.py 감성 라벨링·교차분석·키워드 분석 안정화
- [x] PyPI v0.5.0 배포

## v0.6 — 리포트 개선

- [x] analyze.py HTML 리포트 생성 + 터미널 요약 출력
- [x] SKILL.md 자동 버전 체크 + 분석 섹션 문서화
- [x] PyPI v0.6.0 배포

## v0.7 — 리포트 UX

- [x] HTML 리포트 다크모드 (--bg:#0d1117, --surface:#161b22)
- [x] "감성 분포" → "반응 분포" 명칭 변경
- [x] "키워드 분석" → "언급 키워드" + 각 섹션에 chart-desc 설명 자막 추가
- [x] 자동 인사이트 섹션 (나이·길이·편향 경고)
- [x] 응답 깊이 섹션 추가 (감성별 평균 응답 길이)
- [x] 터미널 요약 UTF-8/CP949 인코딩 문제 수정
- [x] PyPI v0.7.0 배포

## 이어서 할 일

1. PyPI v0.7.0 배포 (`pyproject.toml` 버전 업 → build → upload)
2. 소프트론치 — 카톡 개발자 오픈채팅방 공유 (`pip install market-simulation`)
3. 피드백 수집 후 v0.8 기획
