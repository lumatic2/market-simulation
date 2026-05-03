"""
Nemotron-Personas 로드 / 필터 / 카드 빌더.

HuggingFace datasets 라이브러리로 스트리밍 로드 — 로컬 설치 불필요.

지원 국가 (모두 CC BY 4.0):
    korea, usa, japan, india, france, brazil, singapore

지역 컬럼 스키마 (국가별):
    korea     : province(시도)   + district(시군구)
    usa       : state            + city
    japan     : prefecture(도부현) + area(동/서)
    india     : state            + district
    france    : departement      + commune
    brazil    : state            + municipality
    singapore : planning_area    (level2 없음)

filter_pool(province=...) 의 province 파라미터는 level-1 지역 컬럼에
자동 매핑되며, district 파라미터는 level-2 컬럼에 매핑됩니다.

사용 예:
    from market_simulation.personas import load_pool, filter_pool, persona_to_card
    df = load_pool('usa', sample_n=50000)
    pool = filter_pool(df, province='California', age_range=(25, 39))
    cards = [persona_to_card(pool.iloc[i], i) for i in range(20)]
"""

from __future__ import annotations
import pandas as pd

DATASET_IDS = {
    'korea':     'nvidia/Nemotron-Personas-Korea',
    'usa':       'nvidia/Nemotron-Personas-USA',
    'japan':     'nvidia/Nemotron-Personas-Japan',
    'india':     'nvidia/Nemotron-Personas-India',
    'france':    'nvidia/Nemotron-Personas-France',
    'brazil':    'nvidia/Nemotron-Personas-Brazil',
    'singapore': 'nvidia/Nemotron-Personas-Singapore',
}

# (level-1 컬럼, level-2 컬럼) 우선순위 순서로 탐색
_GEO_PRIORITY = [
    ('province',     'district'),      # Korea
    ('state',        'city'),          # USA, India, Brazil
    ('prefecture',   'area'),          # Japan
    ('departement',  'commune'),       # France
    ('planning_area', None),           # Singapore
]

OCCUPATION_KEYWORDS: dict[str, list[str]] = {
    # ── 한국 직업 분류 ──────────────────────────────────────────────
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
    # ── 영어권 직업 분류 (USA, Singapore 등) ────────────────────────
    'tech':      ['engineer', 'developer', 'programmer', 'software', 'data', 'system', 'IT', 'tech'],
    'finance':   ['finance', 'banking', 'accountant', 'analyst', 'investment', 'insurance'],
    'healthcare':['doctor', 'nurse', 'physician', 'therapist', 'pharmacist', 'medical', 'health'],
    'education': ['teacher', 'professor', 'instructor', 'tutor', 'educator', 'lecturer'],
    'retail':    ['retail', 'sales', 'cashier', 'store', 'shop'],
    'management':['manager', 'director', 'executive', 'CEO', 'COO', 'VP', 'supervisor'],
    'creative':  ['designer', 'artist', 'writer', 'photographer', 'creative'],
    'student':   ['student', 'undergraduate', 'graduate'],
}


def occupation_kw(intent: str) -> list[str]:
    """의도 단어 → 부분일치 키워드 리스트. 매칭 없으면 빈 리스트."""
    return OCCUPATION_KEYWORDS.get(intent, [])


def _geo_cols(df: pd.DataFrame) -> tuple[str | None, str | None]:
    """데이터프레임 컬럼에서 (level-1, level-2) 지역 컬럼 이름을 탐지."""
    for l1, l2 in _GEO_PRIORITY:
        if l1 in df.columns:
            return l1, (l2 if l2 and l2 in df.columns else None)
    return None, None


def _geo_from_row(p: pd.Series) -> tuple[str | None, str | None]:
    """Series 인덱스에서 (level-1, level-2) 지역 컬럼 이름을 탐지."""
    for l1, l2 in _GEO_PRIORITY:
        if l1 in p.index:
            return l1, (l2 if l2 and l2 in p.index else None)
    return None, None


def load_pool(country: str = 'korea', sample_n: int = 50000, seed: int = 42) -> pd.DataFrame:
    """HuggingFace 스트리밍으로 sample_n 행 로드.

    편향 주의: buffer_size=100_000 셔플은 데이터셋 앞쪽 ~150k 행 안에서만
    무작위 추출한다. 전체 균등 샘플이 아님. 탐색 시뮬에서는 허용 가능하지만
    드문 직업·지역은 과소대표될 수 있다. 수집 후 재셔플로 완화.

    India: 3개 언어 split(EN/Hindi-Dev/Hindi-Lat) 중 EN(train) 기본 로드.
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


def stream_until_pool(
    country: str = 'korea',
    province: str | list[str] | None = None,
    district: str | list[str] | None = None,
    age_range: tuple[int, int] | None = None,
    sex: str | None = None,
    occupation_keywords: list[str] | None = None,
    target_pool: int = 100,
    max_rows: int = 300_000,
    seed: int = 42,
) -> pd.DataFrame:
    """스트리밍 중 행 단위로 필터를 적용해 target_pool 크기만큼 수집.

    province/age/sex는 스트리밍 도중 즉시 검사 → 불필요한 행 로드 최소화.
    occupation_keywords는 regex 필요로 수집 후 post-filter로 처리.
    조건이 좁을수록 max_rows까지 읽으며 최대한 모음.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        raise ImportError('pip install datasets 를 먼저 실행하세요.')

    ds_id = DATASET_IDS.get(country)
    if not ds_id:
        raise ValueError(f'country는 {list(DATASET_IDS)} 중 하나여야 합니다.')

    province_set = ({province} if isinstance(province, str) else set(province)) if province else None
    district_set = ({district} if isinstance(district, str) else set(district)) if district else None
    # occupation_keywords는 post-filter → 그만큼 더 모아야 함
    stream_target = target_pool * (4 if occupation_keywords else 1)

    print(f'[{country}] 스트리밍 필터 로드 중... (목표 풀: {target_pool}명)', flush=True)
    ds = load_dataset(ds_id, split='train', streaming=True)
    ds = ds.shuffle(seed=seed, buffer_size=100_000)

    collected, total_read, l1_col, l2_col = [], 0, None, None

    for row in ds:
        total_read += 1

        if l1_col is None:
            for c1, c2 in _GEO_PRIORITY:
                if c1 in row:
                    l1_col, l2_col = c1, (c2 if c2 and c2 in row else None)
                    break

        if province_set and l1_col and row.get(l1_col) not in province_set:
            continue
        if district_set and l2_col and row.get(l2_col) not in district_set:
            continue
        if age_range is not None:
            age = row.get('age', -1)
            if not (age_range[0] <= age <= age_range[1]):
                continue
        if sex is not None and row.get('sex') != sex:
            continue

        collected.append(row)
        if len(collected) >= stream_target or total_read >= max_rows:
            break

    print(f'  {total_read:,}행 읽음 → {len(collected)}명 수집', flush=True)
    df = pd.DataFrame(collected).sample(frac=1, random_state=seed).reset_index(drop=True)

    if occupation_keywords:
        df = filter_pool(df, occupation_keywords=occupation_keywords)
        print(f'  직업 필터 후: {len(df)}명', flush=True)

    return df


def filter_pool(
    df: pd.DataFrame,
    province: str | list[str] | None = None,
    district: str | list[str] | None = None,
    age_range: tuple[int, int] | None = None,
    sex: str | None = None,
    occupation_keywords: list[str] | None = None,
) -> pd.DataFrame:
    """조건 AND로 누적 필터.

    province 파라미터 → 국가별 level-1 지역 컬럼에 자동 매핑
    district 파라미터 → 국가별 level-2 지역 컬럼에 자동 매핑
    """
    l1_col, l2_col = _geo_cols(df)
    m = pd.Series(True, index=df.index)

    if province is not None and l1_col:
        m &= df[l1_col].isin([province] if isinstance(province, str) else province)
    if district is not None and l2_col:
        m &= df[l2_col].isin([district] if isinstance(district, str) else district)
    if age_range is not None:
        m &= df['age'].between(*age_range)
    if sex is not None:
        m &= df['sex'] == sex
    if occupation_keywords:
        pat = '|'.join(occupation_keywords)
        m &= df['occupation'].str.contains(pat, na=False, case=False)
    return df[m]


def _location(p: pd.Series) -> str:
    """Korea/USA/Japan/India/France/Brazil/Singapore 스키마 모두에서 지역 문자열 반환."""
    l1_col, l2_col = _geo_from_row(p)
    if l1_col is None:
        return ''
    loc = str(p[l1_col])
    if l2_col:
        loc = f"{loc} {p[l2_col]}"
    return loc.strip()


def persona_to_card(p: pd.Series, idx: int = 0) -> str:
    """페르소나 1행 → Agent 프롬프트용 구조화 텍스트.

    출력 번호(idx+1)는 에이전트 응답 파싱 시 '## 응답 N' 과 1:1 대응한다.
    모든 지원 국가 스키마 호환.
    """
    extras = []
    if 'family_type' in p.index and pd.notna(p.get('family_type')):
        extras.append(f"가구: {p['family_type']}")
    if 'marital_status' in p.index and pd.notna(p.get('marital_status')):
        extras.append(f"혼인: {p['marital_status']}")
    extra_line = f"\n- 기타: {' / '.join(extras)}" if extras else ''

    return (
        f"## 인물 {idx+1}\n"
        f"- 기본: {p['sex']}, {p['age']}세, {_location(p)}, {p['occupation']}, {p['education_level']}\n"
        f"- 배경: {p['persona']}\n"
        f"- 직업: {p['professional_persona']}\n"
        f"- 취미: {p['hobbies_and_interests']}"
        f"{extra_line}"
    )


def print_card(p: pd.Series) -> None:
    l1_col, l2_col = _geo_from_row(p)
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
