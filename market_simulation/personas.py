"""
Nemotron-Personas 로드 / 필터 / 카드 빌더.

HuggingFace datasets 라이브러리로 스트리밍 로드 — 로컬 설치 불필요.
지원 국가: korea, japan

컬럼 스키마 차이:
  Korea: province, district, family_type, housing_type
  Japan: prefecture, area, region, marital_status (province/district 없음)
filter_pool(province=...) 는 두 스키마 모두 처리.

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
    """HuggingFace 스트리밍으로 sample_n 행 로드.

    편향 주의: buffer_size=100_000 셔플은 데이터셋 앞쪽 ~150k 행 안에서만
    무작위 추출한다. 1M 전체 균등 샘플이 아님. Nemotron 데이터가 인구통계
    비례 생성이므로 탐색 시뮬에서는 허용 가능하지만, 드문 직업·지역은
    과소대표될 수 있다. 수집 후 재셔플로 필터 단계 편향은 완화한다.
    전체 다운로드 대비 시작 시간이 수십 배 빠르다.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError('pip install datasets 를 먼저 실행하세요.')

    ds_id = DATASET_IDS.get(country)
    if not ds_id:
        raise ValueError(f'country는 {list(DATASET_IDS)} 중 하나여야 합니다.')

    print(f'[{country}] HuggingFace 스트리밍 로드 중... (첫 실행은 캐시 없으면 수십 초 소요)', flush=True)
    ds = load_dataset(ds_id, split='train', streaming=True)
    ds = ds.shuffle(seed=seed, buffer_size=100_000)
    rows = []
    for i, row in enumerate(ds):
        if i >= sample_n:
            break
        rows.append(row)
        if (i + 1) % 10000 == 0:
            print(f'  {i + 1:,} / {sample_n:,} 행 수집...', flush=True)
    print(f'  완료: {len(rows):,}행 로드됨', flush=True)
    return pd.DataFrame(rows).sample(frac=1, random_state=seed).reset_index(drop=True)


def filter_pool(
    df: pd.DataFrame,
    province: str | list[str] | None = None,
    district: str | list[str] | None = None,
    age_range: tuple[int, int] | None = None,
    sex: str | None = None,
    occupation_keywords: list[str] | None = None,
) -> pd.DataFrame:
    """조건 AND로 누적 필터. 결과가 요청 N의 3배 미만이면 호출자가 조건 완화.

    Korea/Japan 스키마 자동 감지:
      province 파라미터 → 'province' 컬럼(Korea) 또는 'prefecture' 컬럼(Japan)
      district 파라미터 → 'district' 컬럼(Korea) 또는 'area' 컬럼(Japan)
    """
    m = pd.Series(True, index=df.index)
    if province is not None:
        col = 'province' if 'province' in df.columns else 'prefecture'
        m &= df[col].isin([province] if isinstance(province, str) else province)
    if district is not None:
        col = 'district' if 'district' in df.columns else 'area'
        m &= df[col].isin([district] if isinstance(district, str) else district)
    if age_range is not None:
        m &= df['age'].between(*age_range)
    if sex is not None:
        m &= df['sex'] == sex
    if occupation_keywords:
        pat = '|'.join(occupation_keywords)
        m &= df['occupation'].str.contains(pat, na=False)
    return df[m]


def _location(p) -> str:
    """Korea/Japan 스키마 모두에서 지역 문자열 반환."""
    if 'province' in p.index:
        return f"{p['province']} {p['district']}"
    return f"{p.get('prefecture', '')} {p.get('area', '')}".strip()


def persona_to_card(p, idx: int = 0) -> str:
    """페르소나 1행 → Agent 프롬프트용 구조화 텍스트.

    출력 번호(idx+1)는 에이전트 응답 파싱 시 '## 응답 N' 과 1:1 대응한다.
    Korea/Japan 스키마 모두 지원.
    """
    return (
        f"## 인물 {idx+1}\n"
        f"- 기본: {p['sex']}, {p['age']}세, {_location(p)}, {p['occupation']}, {p['education_level']}\n"
        f"- 배경: {p['persona']}\n"
        f"- 직업: {p['professional_persona']}\n"
        f"- 취미: {p['hobbies_and_interests']}"
    )


def print_card(p) -> None:
    loc = _location(p)
    print(f"━━━ {p['sex']} · {p['age']}세 · {loc} ━━━")
    print(f"  직업  : {p['occupation']}")
    print(f"  학력  : {p['education_level']}")
    if 'family_type' in p.index:
        print(f"  가구  : {p['family_type']} · {p.get('housing_type', '')}")
    elif 'marital_status' in p.index:
        print(f"  혼인  : {p['marital_status']}")
    print(f"\n  [요약]\n  {p['persona']}")
    print(f"\n  [취미]\n  {p['hobbies_and_interests']}")
    print()
