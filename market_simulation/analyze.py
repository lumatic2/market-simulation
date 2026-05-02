"""
시뮬 결과 CSV → 통계 리포트 .report.md 자동 생성.

CSV 컬럼: id, age, sex, occupation, province, district, answer
  (다국어 데이터셋에서는 province/district 컬럼 이름이 다를 수 있음 — 자동 탐지)

독립 실행:
    python -m market_simulation.analyze output/2026-05-02_coffee.csv "커피 구독" "월 9,900원에 구독하시겠어요?"
"""
from __future__ import annotations

import datetime
import re
from collections import Counter

import pandas as pd

# ── 상수 ─────────────────────────────────────────────────────────────────────

SHORT_THRESHOLD = 20

# 규칙 기반 감성 분류 키워드 (한국어 + 영어)
_POS_KW = [
    # 한국어
    '신청', '구독', '괜찮', '합리적', '저렴', '가성비', '긍정', '해볼', '고려',
    '좋아', '만족', '추천', '기대', '이득', '편리', '간편', '좋겠', '살게', '써볼',
    # 영어
    'yes', 'would', 'definitely', 'great', 'affordable', 'worth', 'subscribe',
    'interested', 'convenient', 'value',
]
_NEG_KW = [
    # 한국어
    '안 하', '안하', '하지 않', '필요 없', '필요없', '낭비', '비싸', '거절',
    '패스', '모르겠', '망설', '불필요', '부담', '꺼려', '싫', '안 쓸', '안쓸',
    # 영어
    'no ', "wouldn't", "won't", 'not interested', 'expensive', 'waste',
    'unnecessary', "don't need", 'pass',
]

# 한국어 불용어 (2글자 이상 추출 후 제거)
_KO_STOPWORDS = {
    '이다', '있다', '하다', '것이', '있는', '하는', '에서', '에게', '으로', '로서',
    '에도', '에만', '지만', '그리고', '하지만', '그런데', '그래서', '때문', '때문에',
    '경우', '정도', '사실', '것도', '것은', '것을', '것이', '이런', '이렇게',
    '생각', '느낌', '사람', '경우', '부분', '때문', '이유', '방법',
}


# ── 감성 분류 ─────────────────────────────────────────────────────────────────

def label_sentiment(text: str) -> str:
    """긍정 / 부정 / 중립 3-way 규칙 기반 분류."""
    t = text.lower()
    pos = sum(1 for kw in _POS_KW if kw in t)
    neg = sum(1 for kw in _NEG_KW if kw in t)
    if pos > neg:
        return '긍정'
    if neg > pos:
        return '부정'
    return '중립'


def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """df에 'sentiment' 컬럼을 추가해 반환 (원본 불변)."""
    out = df.copy()
    out['sentiment'] = out['answer'].fillna('').apply(label_sentiment)
    return out


# ── 키워드 추출 ───────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """2~6글자 한글 토큰 추출 + 불용어 제거."""
    tokens = re.findall(r'[가-힣]{2,6}', text)
    return [t for t in tokens if t not in _KO_STOPWORDS]


def top_keywords(texts: list[str], n: int = 15) -> list[tuple[str, int]]:
    """텍스트 리스트에서 빈도 상위 N 키워드 반환."""
    counter: Counter = Counter()
    for t in texts:
        counter.update(_tokenize(t))
    return counter.most_common(n)


def keyword_table_md(texts: list[str], n: int = 15) -> str:
    """top_keywords → 마크다운 테이블."""
    kws = top_keywords(texts, n)
    if not kws:
        return '_키워드 없음._'
    lines = ['| 키워드 | 빈도 |', '|---|---|']
    lines += [f'| {w} | {c} |' for w, c in kws]
    return '\n'.join(lines)


# ── 인구통계 × 감성 교차표 ─────────────────────────────────────────────────────

def _age_group(age: float) -> str:
    a = int(age)
    if a < 20: return '10대'
    if a < 30: return '20대'
    if a < 40: return '30대'
    if a < 50: return '40대'
    if a < 60: return '50대'
    return '60대+'


def _crosstab_md(df: pd.DataFrame, by: str, label: str) -> str:
    """by 컬럼 × sentiment 교차표 → 마크다운."""
    if by not in df.columns or 'sentiment' not in df.columns:
        return ''
    ct = pd.crosstab(df[by], df['sentiment'])
    ct['합계'] = ct.sum(axis=1)
    for col in ['긍정', '부정', '중립']:
        if col in ct.columns:
            ct[f'{col}율'] = (ct[col] / ct['합계']).map(lambda x: f'{x:.0%}')
    ct = ct.sort_values('합계', ascending=False).head(8)

    cols = [c for c in ['긍정', '부정', '중립', '긍정율', '부정율', '합계'] if c in ct.columns]
    lines = [f'**{label} × 감성**', '']
    header = '| ' + label + ' | ' + ' | '.join(cols) + ' |'
    sep = '|---|' + '---|' * len(cols)
    lines += [header, sep]
    for idx, row in ct[cols].iterrows():
        lines.append('| ' + str(idx) + ' | ' + ' | '.join(str(v) for v in row) + ' |')
    return '\n'.join(lines)


def crosstab_section(df: pd.DataFrame) -> str:
    """나이대·직업·지역 × 감성 교차표 섹션 전체."""
    df2 = df.copy()
    df2['나이대'] = df2['age'].apply(_age_group)

    # 지역 컬럼 자동 탐지
    geo_col = next((c for c in ['province', 'state', 'prefecture', 'departement', 'planning_area']
                    if c in df2.columns), None)
    occ_col = 'occupation' if 'occupation' in df2.columns else None

    parts = []
    parts.append(_crosstab_md(df2, '나이대', '나이대'))
    if occ_col:
        # 직업은 상위 6개만
        top_occ = df2[occ_col].value_counts().head(6).index
        parts.append(_crosstab_md(df2[df2[occ_col].isin(top_occ)], occ_col, '직업'))
    if geo_col:
        top_geo = df2[geo_col].value_counts().head(6).index
        parts.append(_crosstab_md(df2[df2[geo_col].isin(top_geo)], geo_col, '지역'))

    return '\n\n'.join(p for p in parts if p)


# ── 세그먼트 프로파일 ──────────────────────────────────────────────────────────

def segment_profile(df: pd.DataFrame) -> str:
    """긍정군 vs 부정군의 인구통계 평균 비교."""
    if 'sentiment' not in df.columns:
        return ''
    pos = df[df['sentiment'] == '긍정']
    neg = df[df['sentiment'] == '부정']
    if len(pos) == 0 or len(neg) == 0:
        return '_데이터 부족 — 세그먼트 비교 불가._'

    lines = ['| 항목 | 긍정군 | 부정군 |', '|---|---|---|']
    lines.append(f"| N | {len(pos)} | {len(neg)} |")
    lines.append(
        f"| 평균 나이 | {pos['age'].mean():.1f}세 | {neg['age'].mean():.1f}세 |"
    )
    if 'sex' in df.columns:
        for grp, label in [(pos, '긍정군'), (neg, '부정군')]:
            _ = label  # noqa
        pos_sex = pos['sex'].value_counts().head(1)
        neg_sex = neg['sex'].value_counts().head(1)
        lines.append(
            f"| 최다 성별 | {pos_sex.index[0]}({pos_sex.iloc[0]}) | {neg_sex.index[0]}({neg_sex.iloc[0]}) |"
        )
    if 'occupation' in df.columns:
        pos_occ = pos['occupation'].value_counts().head(1)
        neg_occ = neg['occupation'].value_counts().head(1)
        lines.append(
            f"| 최다 직업 | {str(pos_occ.index[0])[:12]} | {str(neg_occ.index[0])[:12]} |"
        )
    return '\n'.join(lines)


# ── 리포트 템플릿 ─────────────────────────────────────────────────────────────

_REPORT_TEMPLATE = """\
# {title}

- **일시**: {today}
- **샘플 N**: {n} (지역 최빈={geo_top} / 직업 상위3={occ_top})
- **엔진**: Claude Code Agents (배치 5명 × {n_batches}개 병렬)
- **응답률**: {ok}/{n} ({rate:.0%}) · 평균 {mean_len:.0f}자 · 중앙값 {med_len:.0f}자
- **LLM 시뮬 기반 가설 — 실제 시장 데이터 아님**

## 질문

> {question}

---

## 인구통계 분포

{demo_table}

---

## 감성 분포

{sentiment_dist}

### 세그먼트 프로파일 (긍정 vs 부정)

{segment_profile}

---

## 인구통계 × 감성 교차표

{crosstab}

---

## 키워드 분석

### 전체 응답 상위 키워드

{kw_all}

### 긍정 응답 키워드

{kw_pos}

### 부정 응답 키워드

{kw_neg}

---

## 전체 응답 (N={ok})

{quotes}

---

## 짧·빈 응답 ({n_short}건)

{short_table}

---

## 자기진단

{diag}
"""

_MD_ESCAPE = str.maketrans({'|': '/', '\n': ' ', '\r': ' '})


def _md_safe(s: str, max_len: int = 0) -> str:
    cleaned = str(s).translate(_MD_ESCAPE)
    return cleaned[:max_len] if max_len else cleaned


# ── 메인 함수 ─────────────────────────────────────────────────────────────────

def write_report(csv_path: str, topic: str = '', question: str = '') -> str:
    """CSV 옆에 .report.md 통계 리포트를 생성하고 그 경로를 반환."""
    import os
    from pandas.errors import EmptyDataError

    os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)

    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except EmptyDataError:
        return _write_error(csv_path, topic, '빈 CSV — 시뮬레이션 결과가 없습니다.')

    if df.empty:
        return _write_error(csv_path, topic, '행 없음 — 시뮬레이션 결과가 없습니다.')

    required = {'age', 'sex', 'occupation', 'answer'}
    missing = required - set(df.columns)
    if missing:
        return _write_error(csv_path, topic, f'필수 컬럼 누락: {missing}')

    df['answer'] = df['answer'].fillna('')
    df = add_sentiment(df)

    # 기본 통계
    is_short = df['answer'].str.len() < SHORT_THRESHOLD
    ok_df    = df[~is_short]
    n, n_ok, n_short = len(df), len(ok_df), int(is_short.sum())
    n_batches = -(-n // 5)
    mean_len  = df['answer'].str.len().mean()
    med_len   = df['answer'].str.len().median()
    rate      = n_ok / n if n else 0

    # 지역 컬럼 자동 탐지
    geo_col = next((c for c in ['province', 'state', 'prefecture', 'departement', 'planning_area']
                    if c in df.columns), None)
    geo_top = df[geo_col].mode().iat[0] if geo_col and not df[geo_col].isna().all() else 'N/A'
    occ_top = ', '.join(df['occupation'].value_counts().head(3).index.tolist())

    # 인구통계 분포
    demo_lines = ['| 항목 | 분포 |', '|---|---|']
    demo_lines.append(f"| 나이 | min={df['age'].min()}, mean={df['age'].mean():.1f}, max={df['age'].max()} |")
    for col, label in [('sex', '성별'), ('occupation', '직업'), ('education_level', '학력'),
                       ('family_type', '가구'), ('marital_status', '혼인')]:
        if col in df.columns:
            vals = df[col].value_counts().head(5).to_dict()
            demo_lines.append(f"| {label} | " + ', '.join(f"{_md_safe(str(k))}({v})" for k, v in vals.items()) + ' |')
    if geo_col:
        vals = df[geo_col].value_counts().head(5).to_dict()
        demo_lines.append(f"| 지역 | " + ', '.join(f"{_md_safe(str(k))}({v})" for k, v in vals.items()) + ' |')

    # 감성 분포
    sent_counts = df['sentiment'].value_counts()
    sent_lines = ['| 감성 | N | 비율 |', '|---|---|---|']
    for s in ['긍정', '부정', '중립']:
        c = sent_counts.get(s, 0)
        sent_lines.append(f"| {s} | {c} | {c/n:.0%} |")
    sentiment_dist = '\n'.join(sent_lines)

    # 응답 인용
    quote_blocks = []
    loc_col2 = next((c for c in ['district', 'city', 'area', 'commune', 'municipality'] if c in df.columns), None)
    for _, r in ok_df.iterrows():
        loc2 = f"-{_md_safe(str(r[loc_col2]))}" if loc_col2 else ''
        geo_str = f"{_md_safe(str(r[geo_col]))}{loc2}" if geo_col else ''
        header = f"### [{r['age']}세 {_md_safe(str(r['sex']))} · {_md_safe(str(r['occupation']))} · {geo_str}] [{r['sentiment']}]"
        quote_blocks.append(f"{header}\n> {_md_safe(str(r['answer']))}\n")
    quotes = '\n'.join(quote_blocks) or '_정상 응답 없음._'

    # 짧은 응답 테이블
    if n_short > 0:
        short_lines = ['| 나이 | 직업 | 응답(앞 40자) |', '|---|---|---|']
        for _, r in df[is_short].iterrows():
            short_lines.append(f"| {r['age']} | {_md_safe(str(r['occupation']))} | {_md_safe(str(r['answer']), 40)} |")
        short_table = '\n'.join(short_lines)
    else:
        short_table = '_없음._'

    # 자기진단
    diag_lines = [f"- 응답률 {rate:.0%} ({n_ok}/{n})"]
    if rate < 0.7:
        diag_lines.append("- ⚠ 응답률 70% 미만 — 에이전트 응답 파싱 오류 가능. 원본을 확인하세요.")
    else:
        diag_lines.append("- 안정적. 현재 설정 그대로 다음 시뮬에 사용 가능.")
    pos_rate = sent_counts.get('긍정', 0) / n if n else 0
    if pos_rate > 0.7:
        diag_lines.append(f"- ⚠ 긍정 비율 {pos_rate:.0%} — LLM positive bias 가능성. 절대값보다 세그먼트 간 상대 비교 활용 권장.")

    # 키워드
    pos_texts = ok_df[ok_df['sentiment'] == '긍정']['answer'].tolist()
    neg_texts = ok_df[ok_df['sentiment'] == '부정']['answer'].tolist()

    body = _REPORT_TEMPLATE.format(
        title=topic.replace('_', ' ') or '시뮬 결과',
        today=datetime.date.today().isoformat(),
        n=n, n_batches=n_batches,
        geo_top=geo_top, occ_top=occ_top,
        ok=n_ok, rate=rate,
        mean_len=mean_len, med_len=med_len,
        n_short=n_short,
        question=question or '(질문 미입력)',
        demo_table='\n'.join(demo_lines),
        sentiment_dist=sentiment_dist,
        segment_profile=segment_profile(df),
        crosstab=crosstab_section(df),
        kw_all=keyword_table_md(ok_df['answer'].tolist()),
        kw_pos=keyword_table_md(pos_texts) if pos_texts else '_긍정 응답 없음._',
        kw_neg=keyword_table_md(neg_texts) if neg_texts else '_부정 응답 없음._',
        quotes=quotes,
        short_table=short_table,
        diag='\n'.join(diag_lines),
    )

    md_path = csv_path.replace('.csv', '.report.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(body)
    return md_path


def _write_error(csv_path: str, topic: str, msg: str) -> str:
    md_path = csv_path.replace('.csv', '.report.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f'# {topic or "시뮬 결과"}\n\n{msg}\n')
    return md_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('usage: python -m market_simulation.analyze <csv_path> [topic] [question]')
        sys.exit(1)
    out = write_report(
        sys.argv[1],
        topic=sys.argv[2] if len(sys.argv) > 2 else '',
        question=sys.argv[3] if len(sys.argv) > 3 else '',
    )
    print(f'wrote {out}')
