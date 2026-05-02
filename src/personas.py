"""
Nemotron-Personas 로드 / 필터 / 카드 빌더.

HuggingFace datasets 라이브러리로 스트리밍 로드 — 로컬 설치 불필요.
지원 국가: korea, japan

사용 예:
    from src.personas import load_pool, filter_pool, persona_to_card, occupation_kw
    df = load_pool('korea', sample_n=50000)
    pool = filter_pool(df, province='서울', age_range=(25, 39),
                       occupation_keywords=occupation_kw('IT'))
    sample = pool.sample(20, random_state=42)
    cards = [persona_to_card(sample.iloc[i]) for i in range(len(sample))]
"""

from __future__ import annotations
import pandas as pd

DATASET_IDS = {
    'korea': 'nvidia/Nemotron-Personas-Korea',
    'japan': 'nvidia/Nemotron-Personas-Japan',
}

OCCUPATION_KEYWORDS: dict[str, list[str]] = {
    '직장인':    ['사무', '관리', '전문', '기술', '연구', '개발', '기획', '영업', '회계', '마케팅', '디자인', '교사', '분석', '컨설턴트'],
    '자영업자':  ['자영', '대표', '사장', '경영주', '음식점', '상점', '소매'],
    '주부':      ['전업주부', '가사'],
    '학생':      ['학생'],
    '무직':      ['무직', '구직'],
    'IT':        ['개발', '프로그래머', '시스템', '데이터', '웹', '소프트웨어', '엔지니어'],
    '디자이너':  ['디자인', '디자이너'],
    '의료':      ['의사', '간호', '의료', '보건', '약사', '치료사'],
    '교육':      ['교사', '강사', '교수', '보육', '학원'],
    '제조·생산': ['생산', '제조', '조립', '용접', '기계', '설비', '검사'],
    '서비스':    ['서비스', '판매', '영업', '상담'],
    '운수':      ['운전', '운송', '택배', '물류', '배달'],
    '농림수산':  ['농업', '어업', '임업', '축산'],
    '예술·문화': ['작가', '음악', '연주', '배우', '감독', '미술', '출판', '편집'],
    '금융':      ['금융', '은행', '보험', '증권', '회계'],
}


def occupation_kw(intent: str) -> list[str]:
    """의도 단어 → 부분일치 키워드 리스트. 매칭 없으면 빈 리스트."""
    return OCCUPATION_KEYWORDS.get(intent, [])


def load_pool(country: str = 'korea', sample_n: int = 50000, seed: int = 42) -> pd.DataFrame:
    """HuggingFace에서 균등 랜덤 샘플 로드.

    첫 실행: 전체 데이터셋 다운로드 후 캐시 (수 분 소요, ~수 GB).
    이후 실행: 캐시에서 즉시 로드.

    streaming=True의 buffer shuffle은 sliding-window라 편향이 남으므로
    비스트리밍 + .shuffle()로 인덱스 수준 균등 샘플링을 사용한다.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError('pip install datasets 를 먼저 실행하세요.')

    ds_id = DATASET_IDS.get(country)
    if not ds_id:
        raise ValueError(f'country는 {list(DATASET_IDS)} 중 하나여야 합니다.')

    ds = load_dataset(ds_id, split='train')  # 캐시 후 재사용
    ds = ds.shuffle(seed=seed)
    return ds.select(range(min(sample_n, len(ds)))).to_pandas()


def filter_pool(
    df: pd.DataFrame,
    province: str | list[str] | None = None,
    district: str | list[str] | None = None,
    age_range: tuple[int, int] | None = None,
    sex: str | None = None,
    occupation_keywords: list[str] | None = None,
) -> pd.DataFrame:
    """조건 AND로 누적 필터. 결과가 요청 N의 3배 미만이면 호출자가 조건 완화."""
    m = pd.Series(True, index=df.index)
    if province is not None:
        m &= df['province'].isin([province] if isinstance(province, str) else province)
    if district is not None:
        m &= df['district'].isin([district] if isinstance(district, str) else district)
    if age_range is not None:
        m &= df['age'].between(*age_range)
    if sex is not None:
        m &= df['sex'] == sex
    if occupation_keywords:
        pat = '|'.join(occupation_keywords)
        m &= df['occupation'].str.contains(pat, na=False)
    return df[m]


def persona_to_card(p, idx: int = 0) -> str:
    """페르소나 1행 → Agent 프롬프트용 구조화 텍스트.

    출력 번호(idx+1)는 에이전트 응답 파싱 시 '## 응답 N' 과 1:1 대응한다.
    """
    return (
        f"## 인물 {idx+1}\n"
        f"- 기본: {p['sex']}, {p['age']}세, {p['province']} {p['district']}, {p['occupation']}, {p['education_level']}\n"
        f"- 배경: {p['persona']}\n"
        f"- 직업: {p['professional_persona']}\n"
        f"- 취미: {p['hobbies_and_interests']}"
    )


def print_card(p) -> None:
    print(f"━━━ {p['sex']} · {p['age']}세 · {p['province']} {p['district']} ━━━")
    print(f"  직업  : {p['occupation']}")
    print(f"  학력  : {p['education_level']}")
    print(f"  가구  : {p['family_type']} · {p['housing_type']}")
    print(f"\n  [요약]\n  {p['persona']}")
    print(f"\n  [취미]\n  {p['hobbies_and_interests']}")
    print()
