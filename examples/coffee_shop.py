"""
커피 구독 서비스 시장 반응 시뮬레이션 — 재현 예시

사용법:
    python examples/coffee_shop.py

이 스크립트는 페르소나 로드·필터·카드 생성까지의 데이터 준비 단계를 보여준다.
실제 시뮬레이션(Agent 응답 수집)은 Claude Code 세션에서 /market-simulation 스킬로 실행한다.

재현 조건:
    - 데이터: NVIDIA Nemotron-Personas-Korea (HuggingFace, CC BY 4.0)
    - 필터: 서울, 30~39세, 직장인(사무·기술·기획 등)
    - N: 20명 / 배치: 5명 × 4 에이전트
    - 질문: "월 9,900원에 커피 한 잔씩 매일 받는 구독 서비스를 신청하시겠어요?"
"""

import sys
from pathlib import Path

# installed 패키지가 없으면 로컬 소스에서 import
try:
    from market_simulation.personas import load_pool, filter_pool, persona_to_card, occupation_kw
    from market_simulation.analyze import write_report
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from market_simulation.personas import load_pool, filter_pool, persona_to_card, occupation_kw
    from market_simulation.analyze import write_report

# ── 파라미터 ─────────────────────────────────────────────────────────────────
COUNTRY = 'korea'
SAMPLE_N = 50_000        # HF 스트리밍 풀 크기 (편향 주의: 데이터셋 앞 ~150k 행)
SEED = 42

TARGET_PROVINCE = '서울'
TARGET_AGE = (30, 39)
TARGET_OCCUPATION = occupation_kw('직장인')

SIM_N = 20               # 시뮬 인원 (최대 30)
QUESTION = "월 9,900원에 커피 한 잔씩 매일 받는 구독 서비스를 신청하시겠어요? 왜 그렇게 생각하시나요?"
# ─────────────────────────────────────────────────────────────────────────────


def main():
    # 1. 풀 로드
    df = load_pool(COUNTRY, sample_n=SAMPLE_N, seed=SEED)
    print(f'풀 로드: {len(df):,}명')

    # 2. 필터
    pool = filter_pool(
        df,
        province=TARGET_PROVINCE,
        age_range=TARGET_AGE,
        occupation_keywords=TARGET_OCCUPATION,
    )
    print(f'필터 후: {len(pool):,}명 ({TARGET_PROVINCE} · {TARGET_AGE[0]}~{TARGET_AGE[1]}세 · 직장인)')

    if len(pool) < SIM_N:
        print(f'[경고] 풀({len(pool)}명)이 SIM_N({SIM_N})보다 작습니다. 조건을 완화하거나 SAMPLE_N을 늘리세요.')
        SIM_N_actual = len(pool)
    else:
        SIM_N_actual = SIM_N

    # 3. 샘플 추출 & 카드 생성
    sample = pool.sample(SIM_N_actual, random_state=SEED)
    cards = [persona_to_card(sample.iloc[i], i) for i in range(len(sample))]

    # 4. 출력 — Claude Code 시뮬에 붙여넣을 페르소나 카드
    print()
    print('=' * 60)
    print(f'질문: {QUESTION}')
    print('=' * 60)
    for card in cards:
        print(card)
        print()

    print('─' * 60)
    print(f'총 {SIM_N_actual}명 페르소나 준비 완료.')
    print()
    print('다음 단계: Claude Code 세션에서 /market-simulation 실행 후')
    print('위 페르소나 카드와 질문을 입력하면 시뮬레이션이 시작됩니다.')


if __name__ == '__main__':
    main()
