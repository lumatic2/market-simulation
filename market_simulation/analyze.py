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

    # HTML 리포트 + 터미널 요약
    html_path = write_html_report(csv_path, df, topic, question, auto_open=True)
    print_summary(df, topic, html_path)

    return md_path


# ── 터미널 요약 ───────────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame, topic: str, report_path: str) -> None:
    """핵심 지표를 터미널에 간결하게 출력."""
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    n = len(df)
    sent = df['sentiment'].value_counts() if 'sentiment' in df.columns else {}
    pos = sent.get('긍정', 0)
    neg = sent.get('부정', 0)
    neu = sent.get('중립', 0)

    bar_w = 20

    def bar(count: int) -> str:
        filled = round(count / n * bar_w) if n else 0
        return '#' * filled + '-' * (bar_w - filled)

    kws = top_keywords(df['answer'].dropna().tolist(), 3)
    kw_str = '  '.join(f"{w}({c})" for w, c in kws)

    pos_df = df[df['sentiment'] == '긍정'] if 'sentiment' in df.columns else pd.DataFrame()
    neg_df = df[df['sentiment'] == '부정'] if 'sentiment' in df.columns else pd.DataFrame()
    age_insight = ''
    if len(pos_df) and len(neg_df):
        age_insight = f"  긍정 평균나이 {pos_df['age'].mean():.1f}세  부정 {neg_df['age'].mean():.1f}세"

    title = (topic.replace('_', ' ') or '시뮬 결과')[:30]
    w = 52
    print('=' * w)
    print(f"  {title}")
    print('=' * w)
    print(f"  응답    {n:2d}명")
    print(f"  긍정    {pos:2d}명  ({pos/n:.0%})  {bar(pos)}")
    print(f"  중립    {neu:2d}명  ({neu/n:.0%})  {bar(neu)}")
    print(f"  부정    {neg:2d}명  ({neg/n:.0%})  {bar(neg)}")
    print('-' * w)
    if kw_str:
        print(f"  키워드  {kw_str}")
    if age_insight:
        print(f" {age_insight}")
    print('-' * w)
    print(f"  리포트  {report_path}")
    print('=' * w)


# ── HTML 리포트 ───────────────────────────────────────────────────────────────

def _he(s: str) -> str:
    """HTML 이스케이프."""
    return (str(s)
            .replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _jss(s) -> str:
    """JSON 문자열 이스케이프 (따옴표 없이)."""
    return str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').replace('\r', '')


def _auto_insights(df: pd.DataFrame) -> list[str]:
    """응답 데이터에서 자동으로 인사이트 문장을 생성한다."""
    insights = []
    if 'sentiment' not in df.columns or len(df) < 4:
        return insights

    pos_df = df[df['sentiment'] == '긍정']
    neg_df = df[df['sentiment'] == '부정']

    # 나이대별 긍정률 차이
    df2 = df.copy()
    df2['나이대'] = df2['age'].apply(_age_group)
    ag_rate = df2.groupby('나이대')['sentiment'].apply(lambda x: (x == '긍정').mean())
    if len(ag_rate) > 1:
        best, worst = ag_rate.idxmax(), ag_rate.idxmin()
        if ag_rate[best] - ag_rate[worst] > 0.15:
            insights.append(
                f"<b>{best}</b>에서 긍정률 {ag_rate[best]:.0%}로 가장 높고, "
                f"<b>{worst}</b>는 {ag_rate[worst]:.0%}로 가장 낮습니다."
            )

    # 긍정/부정 평균 나이 차이
    if len(pos_df) > 0 and len(neg_df) > 0:
        pa, na = pos_df['age'].mean(), neg_df['age'].mean()
        if abs(pa - na) >= 3:
            direction = "젊을수록" if pa < na else "나이 들수록"
            insights.append(
                f"{direction} 긍정 반응이 많습니다 "
                f"(긍정 평균 {pa:.1f}세 vs 부정 평균 {na:.1f}세)."
            )

    # 응답 길이 차이 — 부정이 길면 거부 이유가 많다는 신호
    if len(neg_df) > 0 and len(pos_df) > 0:
        pl = pos_df['answer'].str.len().mean()
        nl = neg_df['answer'].str.len().mean()
        if nl > pl * 1.25:
            insights.append(
                f"부정 응답이 긍정보다 평균 {nl/pl:.1f}배 길어 — "
                "거부 이유를 더 자세히 설명하는 경향이 있습니다."
            )
        elif pl > nl * 1.25:
            insights.append(
                f"긍정 응답이 부정보다 평균 {pl/nl:.1f}배 길어 — "
                "수용 이유·기대감을 더 적극적으로 표현합니다."
            )

    # positive bias 경고
    pos_rate = (df['sentiment'] == '긍정').mean()
    if pos_rate > 0.70:
        insights.append(
            f"⚠ 긍정 비율이 {pos_rate:.0%}로 높습니다. "
            "LLM positive bias 영향일 수 있으니 절대값보다 세그먼트 간 <b>상대 비교</b>를 활용하세요."
        )

    return insights


def write_html_report(
    csv_path: str,
    df: pd.DataFrame,
    topic: str = '',
    question: str = '',
    auto_open: bool = True,
) -> str:
    """시뮬 결과 DataFrame → self-contained HTML 리포트(다크모드) 생성 + 브라우저 자동 열기."""
    import json, os, webbrowser

    title = topic.replace('_', ' ') or '시뮬 결과'
    today = datetime.date.today().isoformat()
    n = len(df)

    geo_col  = next((c for c in ['province', 'state', 'prefecture', 'departement', 'planning_area']
                     if c in df.columns), None)
    loc2_col = next((c for c in ['district', 'city', 'area', 'commune', 'municipality']
                     if c in df.columns), None)

    # ── 차트 데이터 ──────────────────────────────────────────────────────────
    sent = df['sentiment'].value_counts() if 'sentiment' in df.columns else {}
    n_pos, n_neg, n_neu = int(sent.get('긍정', 0)), int(sent.get('부정', 0)), int(sent.get('중립', 0))
    pie_data = json.dumps([n_pos, n_neg, n_neu])

    # 나이대×감성 스택 바
    df2 = df.copy()
    df2['나이대'] = df2['age'].apply(_age_group)
    age_groups = [g for g in ['20대', '30대', '40대', '50대', '60대+', '10대'] if g in df2['나이대'].values]
    ag_pos = [int(((df2['나이대'] == g) & (df2['sentiment'] == '긍정')).sum()) for g in age_groups]
    ag_neg = [int(((df2['나이대'] == g) & (df2['sentiment'] == '부정')).sum()) for g in age_groups]
    ag_neu = [int(((df2['나이대'] == g) & (df2['sentiment'] == '중립')).sum()) for g in age_groups]
    age_labels = json.dumps(age_groups)

    # 응답 길이 by 감성 (박스플롯 대신 평균 바)
    len_labels, len_vals, len_colors = [], [], []
    for s, c in [('긍정', '#3fb950'), ('중립', '#6e7681'), ('부정', '#f85149')]:
        sub = df[df['sentiment'] == s]['answer'].str.len() if 'sentiment' in df.columns else pd.Series(dtype=float)
        if len(sub) > 0:
            len_labels.append(f"{s}({len(sub)}명)")
            len_vals.append(round(float(sub.mean()), 1))
            len_colors.append(c)

    # 키워드 (상위 10)
    def kw_data(texts):
        kws = top_keywords(texts, 10)
        return json.dumps([w for w, _ in kws]), json.dumps([c for _, c in kws])

    kw_labels_all, kw_vals_all = kw_data(df['answer'].dropna().tolist())
    pos_texts = df[df['sentiment'] == '긍정']['answer'].tolist() if 'sentiment' in df.columns else []
    neg_texts = df[df['sentiment'] == '부정']['answer'].tolist() if 'sentiment' in df.columns else []
    kw_labels_pos, kw_vals_pos = kw_data(pos_texts)
    kw_labels_neg, kw_vals_neg = kw_data(neg_texts)

    # 인사이트
    insights = _auto_insights(df)
    insight_html = ''.join(f'<li>{i}</li>' for i in insights) if insights else '<li>인사이트를 추출할 데이터가 부족합니다.</li>'

    # ── 응답 카드 ─────────────────────────────────────────────────────────────
    SENT_COLOR = {'긍정': '#3fb950', '부정': '#f85149', '중립': '#6e7681'}
    SENT_BORDER_BG = {'긍정': 'rgba(63,185,80,.12)', '부정': 'rgba(248,81,73,.12)', '중립': 'rgba(110,118,129,.1)'}

    cards_html = []
    for _, r in df.iterrows():
        sl  = r.get('sentiment', '중립')
        col = SENT_COLOR.get(sl, '#6e7681')
        bg  = SENT_BORDER_BG.get(sl, 'rgba(110,118,129,.1)')
        g1  = _he(str(r[geo_col])) if geo_col else ''
        g2  = f" {_he(str(r[loc2_col]))}" if loc2_col else ''
        ans = _he(str(r['answer'])) if r['answer'] else '<em style="color:#6e7681">응답 없음</em>'
        cards_html.append(f"""
      <div class="card" data-sentiment="{_he(sl)}" style="border-left:3px solid {col};background:{bg}">
        <div class="card-header">
          <span class="profile">{_he(str(r['age']))}세 {_he(str(r['sex']))} · {_he(str(r['occupation']))} · {g1}{g2}</span>
          <span class="badge" style="background:{col}">{_he(sl)}</span>
        </div>
        <p class="answer">{ans}</p>
      </div>""")
    cards_joined = '\n'.join(cards_html)

    # ── Chart.js 공통 다크 옵션 ───────────────────────────────────────────────
    dark_scales = """{
      x: { grid:{color:'rgba(255,255,255,0.06)'}, ticks:{color:'#8b949e'} },
      y: { grid:{color:'rgba(255,255,255,0.06)'}, ticks:{color:'#8b949e'} }
    }"""
    dark_legend = "{ labels:{ color:'#c9d1d9' }, position:'bottom' }"

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_he(title)} — market-simulation</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
:root {{
  --bg:      #0d1117;
  --surface: #161b22;
  --card:    #21262d;
  --border:  #30363d;
  --text:    #e6edf3;
  --muted:   #8b949e;
  --green:   #3fb950;
  --red:     #f85149;
  --blue:    #58a6ff;
  --yellow:  #d29922;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:-apple-system,'Malgun Gothic',sans-serif; background:var(--bg); color:var(--text); line-height:1.6; }}
a {{ color:var(--blue); }}
.wrap {{ max-width:980px; margin:0 auto; padding:28px 18px 48px; }}
h1 {{ font-size:1.55rem; font-weight:700; letter-spacing:-.01em; }}
h2 {{ font-size:1rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.06em;
      margin:32px 0 14px; border-bottom:1px solid var(--border); padding-bottom:6px; }}
.meta {{ color:var(--muted); font-size:.82rem; margin:5px 0 18px; }}
.disclaimer {{ background:rgba(248,81,73,.1); border:1px solid rgba(248,81,73,.3);
               padding:9px 14px; border-radius:6px; font-size:.8rem; color:#ffa198; margin-bottom:16px; }}
.question-box {{ background:rgba(210,153,34,.08); border-left:3px solid var(--yellow);
                 padding:11px 16px; border-radius:4px; font-style:italic; margin-bottom:24px; color:#e3b341; }}
/* 지표 */
.stats-row {{ display:flex; gap:10px; flex-wrap:wrap; margin-bottom:6px; }}
.stat-box {{ flex:1; min-width:110px; background:var(--surface); border:1px solid var(--border);
             border-radius:8px; padding:14px 16px; text-align:center; }}
.stat-num {{ font-size:1.9rem; font-weight:700; }}
.stat-lbl {{ font-size:.75rem; color:var(--muted); margin-top:3px; }}
/* 인사이트 */
.insight-box {{ background:var(--surface); border:1px solid var(--border); border-radius:8px;
                padding:14px 18px; margin-bottom:6px; }}
.insight-box ul {{ padding-left:18px; }}
.insight-box li {{ font-size:.88rem; margin-bottom:6px; color:#c9d1d9; }}
/* 차트 */
.charts-row {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:6px; }}
.charts-row3 {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:6px; }}
.chart-box {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:16px; }}
.chart-box canvas {{ max-height:230px; }}
.chart-title {{ font-size:.8rem; font-weight:600; color:var(--muted); margin-bottom:10px; }}
.chart-desc  {{ font-size:.73rem; color:#6e7681; margin-bottom:8px; }}
/* 키워드 */
.kw-box {{ background:var(--surface); border:1px solid var(--border); border-radius:8px; padding:14px; }}
.kw-box canvas {{ max-height:200px; }}
/* 필터 */
.filter-bar {{ display:flex; gap:8px; margin:18px 0 12px; flex-wrap:wrap; }}
.filter-btn {{ padding:5px 16px; border-radius:20px; border:1px solid var(--border);
               background:transparent; color:var(--muted); cursor:pointer; font-size:.82rem; transition:.15s; }}
.filter-btn:hover {{ border-color:var(--text); color:var(--text); }}
.filter-btn.active {{ background:var(--text); color:var(--bg); border-color:var(--text); }}
/* 카드 */
.card {{ border-radius:6px; padding:12px 16px; margin-bottom:10px; transition:.12s; }}
.card.hidden {{ display:none; }}
.card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:7px; gap:8px; }}
.profile {{ font-size:.78rem; color:var(--muted); flex:1; }}
.badge {{ font-size:.72rem; color:#000; padding:2px 9px; border-radius:12px; font-weight:700; white-space:nowrap; }}
.answer {{ font-size:.88rem; line-height:1.7; color:#c9d1d9; }}
footer {{ text-align:center; font-size:.72rem; color:#6e7681; margin-top:36px; }}
@media(max-width:640px) {{ .charts-row,.charts-row3 {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{_he(title)}</h1>
  <div class="meta">{today} · Claude Code Agents · LLM 시뮬 · {n}명</div>
  <div class="disclaimer">⚠ AI가 AI 페르소나를 연기하는 구조입니다. 실제 소비자 조사를 대체하지 않으며 통계적 대표성이 없습니다.</div>
  <div class="question-box">Q. {_he(question or '(질문 미입력)')}</div>

  <h2>핵심 지표</h2>
  <div class="stats-row">
    <div class="stat-box"><div class="stat-num">{n}</div><div class="stat-lbl">응답 수</div></div>
    <div class="stat-box"><div class="stat-num" style="color:var(--green)">{n_pos}</div><div class="stat-lbl">긍정 ({n_pos/n:.0%})</div></div>
    <div class="stat-box"><div class="stat-num" style="color:var(--red)">{n_neg}</div><div class="stat-lbl">부정 ({n_neg/n:.0%})</div></div>
    <div class="stat-box"><div class="stat-num" style="color:var(--muted)">{n_neu}</div><div class="stat-lbl">중립 ({n_neu/n:.0%})</div></div>
  </div>

  <h2>자동 인사이트</h2>
  <div class="insight-box"><ul>{insight_html}</ul></div>

  <h2>반응 분포</h2>
  <div class="charts-row">
    <div class="chart-box">
      <div class="chart-title">긍정 · 부정 · 중립 비율</div>
      <div class="chart-desc">규칙 기반 자동 분류 — 응답 텍스트에서 수용/거부 표현 감지</div>
      <canvas id="pieChart"></canvas>
    </div>
    <div class="chart-box">
      <div class="chart-title">나이대별 반응</div>
      <div class="chart-desc">어느 연령층이 더 긍정적/부정적인지 비교</div>
      <canvas id="ageChart"></canvas>
    </div>
  </div>

  <h2>응답 깊이</h2>
  <div class="chart-box" style="margin-bottom:6px">
    <div class="chart-title">감성별 평균 응답 길이 (글자 수)</div>
    <div class="chart-desc">응답이 길수록 해당 입장에 대한 생각이나 감정이 많다는 신호입니다</div>
    <canvas id="lenChart" style="max-height:160px"></canvas>
  </div>

  <h2>언급 키워드</h2>
  <div class="charts-row3">
    <div class="kw-box">
      <div class="chart-title">전체 응답</div>
      <div class="chart-desc">모든 응답에서 자주 등장한 핵심 단어</div>
      <canvas id="kwAll"></canvas>
    </div>
    <div class="kw-box">
      <div class="chart-title" style="color:var(--green)">긍정 응답만</div>
      <div class="chart-desc">수용·구매 이유 힌트 — 이 단어들이 호감 요소</div>
      <canvas id="kwPos"></canvas>
    </div>
    <div class="kw-box">
      <div class="chart-title" style="color:var(--red)">부정 응답만</div>
      <div class="chart-desc">거부·저항 이유 힌트 — 이 단어들이 장벽 요소</div>
      <canvas id="kwNeg"></canvas>
    </div>
  </div>

  <h2>개별 응답 ({n}건)</h2>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filter('all')">전체</button>
    <button class="filter-btn" onclick="filter('긍정')" style="color:var(--green)">긍정 {n_pos}명</button>
    <button class="filter-btn" onclick="filter('부정')" style="color:var(--red)">부정 {n_neg}명</button>
    <button class="filter-btn" onclick="filter('중립')" style="color:var(--muted)">중립 {n_neu}명</button>
  </div>
  <div id="cards">{cards_joined}</div>

  <footer>market-simulation v0.6 · LLM 시뮬 기반 가설 · 실제 시장 데이터 아님</footer>
</div>
<script>
Chart.defaults.color = '#8b949e';

const darkScales = {{
  x: {{ grid:{{color:'rgba(255,255,255,0.06)'}}, ticks:{{color:'#8b949e'}} }},
  y: {{ grid:{{color:'rgba(255,255,255,0.06)'}}, ticks:{{color:'#8b949e'}} }}
}};

// 도넛 — 반응 비율
new Chart(document.getElementById('pieChart'), {{
  type:'doughnut',
  data:{{ labels:['긍정','부정','중립'],
    datasets:[{{ data:{pie_data}, backgroundColor:['#3fb950','#f85149','#6e7681'], borderWidth:2, borderColor:'#161b22' }}] }},
  options:{{ plugins:{{ legend:{{ ...Chart.defaults.plugins?.legend, labels:{{color:'#c9d1d9'}}, position:'bottom' }} }}, responsive:true }}
}});

// 나이대 스택 바
new Chart(document.getElementById('ageChart'), {{
  type:'bar',
  data:{{
    labels:{age_labels},
    datasets:[
      {{label:'긍정', data:{json.dumps(ag_pos)}, backgroundColor:'#3fb950'}},
      {{label:'부정', data:{json.dumps(ag_neg)}, backgroundColor:'#f85149'}},
      {{label:'중립', data:{json.dumps(ag_neu)}, backgroundColor:'#6e7681'}}
    ]
  }},
  options:{{ scales:{{ x:{{...darkScales.x, stacked:true}}, y:{{...darkScales.y, stacked:true}} }},
             plugins:{{ legend:{{ labels:{{color:'#c9d1d9'}}, position:'bottom' }} }}, responsive:true }}
}});

// 응답 길이 바
new Chart(document.getElementById('lenChart'), {{
  type:'bar',
  data:{{ labels:{json.dumps(len_labels)},
    datasets:[{{ data:{json.dumps(len_vals)}, backgroundColor:{json.dumps(len_colors)}, borderRadius:4 }}] }},
  options:{{ indexAxis:'y', plugins:{{ legend:{{display:false}} }}, scales:darkScales, responsive:true }}
}});

// 키워드 공통 함수
function kwChart(id, labels, vals, color) {{
  new Chart(document.getElementById(id), {{
    type:'bar',
    data:{{ labels:labels, datasets:[{{data:vals, backgroundColor:color, borderRadius:3}}] }},
    options:{{ indexAxis:'y', plugins:{{legend:{{display:false}}}}, scales:darkScales, responsive:true,
               layout:{{padding:{{right:8}}}} }}
  }});
}}
kwChart('kwAll', {kw_labels_all}, {kw_vals_all}, '#58a6ff');
kwChart('kwPos', {kw_labels_pos}, {kw_vals_pos}, '#3fb950');
kwChart('kwNeg', {kw_labels_neg}, {kw_vals_neg}, '#f85149');

// 카드 필터
function filter(sent) {{
  document.querySelectorAll('.card').forEach(c =>
    c.classList.toggle('hidden', sent !== 'all' && c.dataset.sentiment !== sent));
  document.querySelectorAll('.filter-btn').forEach(b =>
    b.classList.toggle('active', b.textContent.startsWith(sent === 'all' ? '전체' : sent)));
}}
</script>
</body>
</html>"""

    html_path = csv_path.replace('.csv', '.report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    if auto_open:
        try:
            webbrowser.open(f'file:///{os.path.abspath(html_path).replace(chr(92), "/")}')
        except Exception:
            pass

    return html_path


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
