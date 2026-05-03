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


# ── 테마 분석 ─────────────────────────────────────────────────────────────────

def _parse_themes(themes_val) -> list[str]:
    """'편의성, 가격부담' → ['편의성', '가격부담']."""
    if themes_val is None:
        return []
    if isinstance(themes_val, float):
        import math
        if math.isnan(themes_val):
            return []
    s = str(themes_val).strip()
    if not s:
        return []
    return [t.strip() for t in s.split(',') if t.strip()]


def _theme_counts(df: pd.DataFrame, top_n: int = 15) -> list[tuple[str, int]]:
    """themes 컬럼에서 테마별 빈도 집계."""
    counter: Counter = Counter()
    if 'themes' not in df.columns:
        return []
    for ts in df['themes'].fillna(''):
        for t in _parse_themes(ts):
            counter[t] += 1
    return counter.most_common(top_n)


def _detect_mode(df: pd.DataFrame) -> str:
    """CSV 컬럼에서 시뮬 모드 자동 감지: 'A' | 'B' | 'C'."""
    has_sent   = ('sentiment' in df.columns
                  and df['sentiment'].notna().any()
                  and (df['sentiment'] != '').any())
    has_themes = ('themes' in df.columns
                  and df['themes'].notna().any()
                  and (df['themes'].astype(str).str.strip() != '').any())
    if has_sent and has_themes:
        return 'C'
    if has_themes:
        return 'B'
    return 'A'


# 한국어 불용어 (2글자 이상 추출 후 제거)
_KO_STOPWORDS = {
    '이다', '있다', '하다', '것이', '있는', '하는', '에서', '에게', '으로', '로서',
    '에도', '에만', '지만', '그리고', '하지만', '그런데', '그래서', '때문', '때문에',
    '경우', '정도', '사실', '것도', '것은', '것을', '것이', '이런', '이렇게',
    '생각', '느낌', '사람', '경우', '부분', '때문', '이유', '방법',
}

# 영어 불용어 (4글자 이상 추출 후 제거)
_EN_STOPWORDS = {
    'the', 'and', 'for', 'that', 'this', 'with', 'not', 'but', 'have',
    'from', 'they', 'would', 'what', 'about', 'which', 'when', 'there',
    'their', 'just', 'into', 'more', 'also', 'been', 'than', 'like',
    'will', 'some', 'could', 'even', 'very', 'really', 'think', 'actually',
    'know', 'sure', 'much', 'need', 'make', 'want', 'dont', 'doesnt',
    'before', 'after', 'does', 'were', 'your', 'mine', 'ours', 'them',
    'its', 'myself', 'something', 'anything', 'everything', 'nothing',
}


# ── 감성 정규화 ───────────────────────────────────────────────────────────────

def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    """sentiment 컬럼 정규화 (원본 불변).

    에이전트가 출력한 LLM 태그(긍정/중립/부정)를 기준으로 사용.
    유효하지 않은 값(태그 누락·파싱 실패)은 '중립'으로 채움.
    sentiment 컬럼이 없으면 df를 그대로 반환 (B모드).
    """
    out = df.copy()
    valid = {'긍정', '중립', '부정'}
    if 'sentiment' in out.columns:
        mask = ~out['sentiment'].isin(valid)
        if mask.any():
            out.loc[mask, 'sentiment'] = '중립'
    return out


# ── 키워드 추출 ───────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """한글 2~6글자 또는 영어 4글자 이상 토큰 추출 + 불용어 제거."""
    ko_tokens = [t for t in re.findall(r'[가-힣]{2,6}', text) if t not in _KO_STOPWORDS]
    if ko_tokens:
        return ko_tokens
    en_tokens = re.findall(r"[a-zA-Z]{4,}", text.lower())
    return [t for t in en_tokens if t not in _EN_STOPWORDS]


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
    mode = _detect_mode(df)
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

    # 감성/테마 분포
    if 'sentiment' in df.columns:
        sent_counts = df['sentiment'].value_counts()
        sent_lines = ['| 감성 | N | 비율 |', '|---|---|---|']
        for s in ['긍정', '부정', '중립']:
            c = sent_counts.get(s, 0)
            sent_lines.append(f"| {s} | {c} | {c/n:.0%} |")
        sentiment_dist = '\n'.join(sent_lines)
    else:
        sent_counts = Counter()
        tc = _theme_counts(df)
        if tc:
            tl = ['| 테마 | N |', '|---|---|']
            tl += [f'| {t} | {c} |' for t, c in tc[:10]]
            sentiment_dist = '\n'.join(tl)
        else:
            sentiment_dist = '_테마 데이터 없음._'

    # 응답 인용
    quote_blocks = []
    loc_col2 = next((c for c in ['district', 'city', 'area', 'commune', 'municipality'] if c in df.columns), None)
    for _, r in ok_df.iterrows():
        loc2 = f"-{_md_safe(str(r[loc_col2]))}" if loc_col2 else ''
        geo_str = f"{_md_safe(str(r[geo_col]))}{loc2}" if geo_col else ''
        sent_label = str(r.get('sentiment', '')) if 'sentiment' in ok_df.columns else ''
        sent_tag = f' [{sent_label}]' if sent_label else ''
        header = f"### [{r['age']}세 {_md_safe(str(r['sex']))} · {_md_safe(str(r['occupation']))} · {geo_str}]{sent_tag}"
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
    if pos_rate > 0.7 and 'sentiment' in df.columns:
        diag_lines.append(f"- ⚠ 긍정 비율 {pos_rate:.0%} — LLM positive bias 가능성. 절대값보다 세그먼트 간 상대 비교 활용 권장.")

    # 키워드
    if 'sentiment' in df.columns:
        pos_texts = ok_df[ok_df['sentiment'] == '긍정']['answer'].tolist()
        neg_texts = ok_df[ok_df['sentiment'] == '부정']['answer'].tolist()
    else:
        pos_texts = ok_df['answer'].tolist()
        neg_texts = []

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

    mode  = _detect_mode(df)
    n     = len(df)
    title = (topic.replace('_', ' ') or '시뮬 결과')[:30]
    w     = 52

    if mode == 'B':
        td       = _theme_counts(df, 3)
        theme_str = '  '.join(f"{t}({c})" for t, c in td)
        n_themes  = len(_theme_counts(df))
        print('=' * w)
        print(f"  {title}")
        print('=' * w)
        print(f"  응답    {n:2d}명  [발견 조사 모드]")
        print(f"  테마    {n_themes}개")
        if theme_str:
            print(f"  상위    {theme_str}")
        print('-' * w)
        print(f"  리포트  {report_path}")
        print('=' * w)
        return

    # A/C mode
    sent = df['sentiment'].value_counts() if 'sentiment' in df.columns else {}
    pos  = sent.get('긍정', 0)
    neg  = sent.get('부정', 0)
    neu  = sent.get('중립', 0)

    bar_w = 20

    def bar(count: int) -> str:
        filled = round(count / n * bar_w) if n else 0
        return '#' * filled + '-' * (bar_w - filled)

    kws    = top_keywords(df['answer'].dropna().tolist(), 3)
    kw_str = '  '.join(f"{kw}({c})" for kw, c in kws)

    pos_df = df[df['sentiment'] == '긍정'] if 'sentiment' in df.columns else pd.DataFrame()
    neg_df = df[df['sentiment'] == '부정'] if 'sentiment' in df.columns else pd.DataFrame()
    age_insight = ''
    if len(pos_df) and len(neg_df):
        age_insight = f"  긍정 평균나이 {pos_df['age'].mean():.1f}세  부정 {neg_df['age'].mean():.1f}세"

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


def _diff_keywords(pos_texts: list[str], neg_texts: list[str], top_n: int = 4) -> tuple[list[str], list[str]]:
    """긍정/부정 응답에서 차별 키워드 추출 (상대방 텍스트에 없는 단어 우선)."""
    pos_cnt = Counter()
    neg_cnt = Counter()
    for t in pos_texts:
        pos_cnt.update(_tokenize(t))
    for t in neg_texts:
        neg_cnt.update(_tokenize(t))

    pos_total = max(len(pos_texts), 1)
    neg_total = max(len(neg_texts), 1)

    # 긍정에서 상대적으로 많이 나오는 단어 (TF 비율 차이)
    pos_diff = sorted(
        {w for w in pos_cnt if pos_cnt[w] >= 2},
        key=lambda w: pos_cnt[w] / pos_total - neg_cnt.get(w, 0) / neg_total,
        reverse=True,
    )[:top_n]

    neg_diff = sorted(
        {w for w in neg_cnt if neg_cnt[w] >= 2},
        key=lambda w: neg_cnt[w] / neg_total - pos_cnt.get(w, 0) / pos_total,
        reverse=True,
    )[:top_n]

    return pos_diff, neg_diff


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
                f"{direction} 긍정 반응이 더 많습니다 "
                f"(긍정 평균 {pa:.1f}세 · 부정 평균 {na:.1f}세)."
            )

    # 성별 긍정률 차이
    if 'sex' in df.columns:
        sex_rate = df.groupby('sex')['sentiment'].apply(lambda x: (x == '긍정').mean())
        if len(sex_rate) >= 2:
            smax, smin = sex_rate.idxmax(), sex_rate.idxmin()
            if sex_rate[smax] - sex_rate[smin] > 0.15:
                insights.append(
                    f"<b>{smax}</b>의 긍정률 {sex_rate[smax]:.0%}로 "
                    f"{smin}({sex_rate[smin]:.0%})보다 높습니다."
                )

    # 직업군 최고·최저 긍정률
    if 'occupation' in df.columns:
        occ_cnt = df['occupation'].value_counts()
        valid_occ = occ_cnt[occ_cnt >= 2].index
        if len(valid_occ) >= 2:
            occ_rate = (df[df['occupation'].isin(valid_occ)]
                        .groupby('occupation')['sentiment']
                        .apply(lambda x: (x == '긍정').mean()))
            if len(occ_rate) >= 2:
                omax, omin = occ_rate.idxmax(), occ_rate.idxmin()
                if occ_rate[omax] - occ_rate[omin] > 0.20:
                    insights.append(
                        f"직업군 중 <b>{omax}</b>이 긍정률 {occ_rate[omax]:.0%}로 가장 높고, "
                        f"<b>{omin}</b>은 {occ_rate[omin]:.0%}로 가장 낮습니다."
                    )

    # 차별 키워드 — 긍정에만/부정에만 자주 나오는 단어 (양쪽 최소 3명 이상일 때만)
    pos_texts = pos_df['answer'].dropna().tolist()
    neg_texts = neg_df['answer'].dropna().tolist()
    if len(pos_texts) >= 3 and len(neg_texts) >= 3:
        pos_diff, neg_diff = _diff_keywords(pos_texts, neg_texts)
        if pos_diff:
            insights.append(
                f"긍정 응답에서 두드러진 단어: "
                + ', '.join(f'<b>{w}</b>' for w in pos_diff)
                + " — 긍정 이유를 암시합니다."
            )
        if neg_diff:
            insights.append(
                f"부정 응답에서 두드러진 단어: "
                + ', '.join(f'<b>{w}</b>' for w in neg_diff)
                + " — 부정 요인을 암시합니다."
            )

    # 조건부 긍정 비율 — "~다면", "~는데", "~지만" 등 명확한 조건·유보 표현
    _COND_PATTERNS = re.compile(r'다면|한다면|이라면|는데요|지만|긴 하|다고는|하지만|망설|아직|좀 더|고민')
    if len(pos_df) >= 3:
        cond_count = pos_df['answer'].fillna('').apply(
            lambda t: bool(_COND_PATTERNS.search(t))
        ).sum()
        cond_rate = cond_count / len(pos_df)
        if cond_rate >= 0.40:
            insights.append(
                f"긍정 응답 중 {cond_rate:.0%}가 조건부 수용 — "
                "'~다면', '~지만', '망설' 등 유보 표현을 포함합니다. 완전한 확신은 아닐 수 있습니다."
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


def _select_notable_quotes(df: pd.DataFrame, geo_col, loc2_col) -> list[dict]:
    """주목할 응답 최대 3개 자동 선별 (긍정 대표 · 저항 대표 · 복합 반응)."""
    _COND = re.compile(r'다면|한다면|이라면|는데요|지만|긴 하|다고는|하지만|망설|아직|좀 더|고민|걱정|모르겠')

    def _row_to_quote(row, label, color):
        g1 = str(row[geo_col]) if geo_col and geo_col in row.index else ''
        g2 = f' {str(row[loc2_col])}' if loc2_col and loc2_col in row.index else ''
        return {
            'label': label, 'color': color,
            'profile': f"{row['age']}세 {row['sex']} · {row['occupation']}" + (f' · {g1}{g2}' if g1 else ''),
            'answer': str(row['answer']) if row.get('answer') else '',
        }

    results, used = [], set()

    # 1. 긍정 대표 — 긍정 중 가장 긴 응답
    pos_df = df[df['sentiment'] == '긍정'] if 'sentiment' in df.columns else pd.DataFrame()
    if len(pos_df) > 0:
        idx = pos_df['answer'].str.len().idxmax()
        results.append(_row_to_quote(df.loc[idx], '긍정 대표 응답', '#3fb950'))
        used.add(idx)

    # 2. 저항 대표 — 부정 중 가장 긴 응답
    neg_df = df[(df['sentiment'] == '부정') & (~df.index.isin(used))] if 'sentiment' in df.columns else pd.DataFrame()
    if len(neg_df) > 0:
        idx = neg_df['answer'].str.len().idxmax()
        results.append(_row_to_quote(df.loc[idx], '부정 대표 응답', '#f85149'))
        used.add(idx)

    # 3. 복합 반응 — 조건부 표현이 가장 많은 응답 (중립/긍정 우선)
    remaining = df[~df.index.isin(used)].copy()
    if len(remaining) > 0:
        remaining['_cs'] = remaining['answer'].fillna('').apply(lambda t: len(_COND.findall(t)))
        idx = remaining['_cs'].idxmax()
        if remaining.loc[idx, '_cs'] > 0:
            results.append(_row_to_quote(df.loc[idx], '복합 반응', '#d29922'))

    return results


def _headline(df: pd.DataFrame, n_pos: int, n_neg: int, n_neu: int, n: int) -> str:
    """가장 중요한 발견 1줄 요약 문장 생성."""
    dom_label, dom_count = max([('긍정', n_pos), ('부정', n_neg), ('중립', n_neu)], key=lambda x: x[1])
    dom_pct = dom_count / n if n else 0

    # 직업군 차이
    if 'occupation' in df.columns and 'sentiment' in df.columns:
        occ_cnt = df['occupation'].value_counts()
        valid   = occ_cnt[occ_cnt >= 2].index
        if len(valid) >= 2:
            occ_rate = df[df['occupation'].isin(valid)].groupby('occupation')['sentiment'].apply(
                lambda x: (x == '긍정').mean()
            )
            if len(occ_rate) >= 2 and occ_rate.max() - occ_rate.min() >= 0.25:
                best, worst = occ_rate.idxmax(), occ_rate.idxmin()
                return (f"{dom_label} 우세 ({dom_pct:.0%}) — "
                        f"{best} 긍정률 {occ_rate[best]:.0%} vs {worst} {occ_rate[worst]:.0%}, 직군 간 격차 뚜렷")

    # 성별 차이
    if 'sex' in df.columns and 'sentiment' in df.columns:
        sex_rate = df.groupby('sex')['sentiment'].apply(lambda x: (x == '긍정').mean())
        if len(sex_rate) >= 2 and sex_rate.max() - sex_rate.min() >= 0.20:
            high = sex_rate.idxmax()
            return (f"{dom_label} 우세 ({dom_pct:.0%}) — "
                    f"{high}의 긍정률이 {sex_rate[high]:.0%}로 더 높음")

    # 기본 요약
    pos_pct = n_pos / n if n else 0
    if pos_pct >= 0.60:
        return f"전반적 긍정 반응 ({pos_pct:.0%}) — 과반이 긍정 반응"
    elif n_neg / n >= 0.40 if n else False:
        return f"부정 비율 높음 ({n_neg/n:.0%}) — 도입 장벽 점검 필요"
    else:
        return f"{dom_label} 우세 ({dom_pct:.0%}) — 응답 {n}명 중 절반 이상 중립"


def write_html_report(
    csv_path: str,
    df: pd.DataFrame,
    topic: str = '',
    question: str = '',
    auto_open: bool = True,
) -> str:
    """시뮬 결과 DataFrame → self-contained HTML 리포트(다크모드) 생성 + 브라우저 자동 열기."""
    import json, os, webbrowser

    title    = topic.replace('_', ' ') or '시뮬 결과'
    today    = datetime.date.today().isoformat()
    n        = len(df)
    geo_col  = next((c for c in ['province','state','prefecture','departement','planning_area'] if c in df.columns), None)
    loc2_col = next((c for c in ['district','city','area','commune','municipality'] if c in df.columns), None)
    mode     = _detect_mode(df)
    theme_data = _theme_counts(df) if mode in ('B', 'C') else []

    # ── 기본 통계 ────────────────────────────────────────────────────────────
    if 'sentiment' in df.columns:
        sent  = df['sentiment'].value_counts()
        n_pos = int(sent.get('긍정', 0))
        n_neg = int(sent.get('부정', 0))
        n_neu = int(sent.get('중립', 0))
    else:
        n_pos = n_neg = n_neu = 0
    pie_data = json.dumps([n_pos, n_neg, n_neu])

    # ── 핵심 발견 ─────────────────────────────────────────────────────────────
    if mode == 'B':
        top3         = ', '.join(t for t, _ in theme_data[:3]) if theme_data else '—'
        headline     = f"주요 테마 {len(theme_data)}개 발견 — 상위: {top3}"
        insight_html = ''.join(
            f'<li><b>{_he(t)}</b> — {c}건</li>' for t, c in theme_data[:8]
        ) or '<li>테마 데이터 없음.</li>'
    else:
        insights     = _auto_insights(df)
        insight_html = ''.join(f'<li>{i}</li>' for i in insights) if insights else '<li>인사이트를 추출할 데이터가 부족합니다.</li>'
        headline     = _headline(df, n_pos, n_neg, n_neu, n)

    # ── 세그먼트 차트 (A/C 모드만) ────────────────────────────────────────────
    seg_html_parts: list[str] = []
    seg_js_parts:   list[str] = []

    if mode != 'B':
        def _stacked_js(chart_id, labels, pos_c, neg_c, neu_c):
            return (
                f"new Chart(document.getElementById('{chart_id}'), {{"
                f"type:'bar',"
                f"data:{{labels:{json.dumps(labels)},datasets:["
                f"{{label:'긍정',data:{json.dumps(pos_c)},backgroundColor:'#3fb950'}},"
                f"{{label:'부정',data:{json.dumps(neg_c)},backgroundColor:'#f85149'}},"
                f"{{label:'중립',data:{json.dumps(neu_c)},backgroundColor:'#6e7681'}}"
                f"]}},"
                f"options:{{scales:{{x:{{...DS.x,stacked:true}},y:{{...DS.y,stacked:true}}}},"
                f"plugins:{{legend:{{labels:{{color:'#c9d1d9'}},position:'bottom'}}}},"
                f"responsive:true,maintainAspectRatio:true}}}});"
            )

        def _add_seg(col, chart_id, seg_title, desc, min_count=2, max_groups=8):
            if col not in df.columns or 'sentiment' not in df.columns:
                return
            vals  = df[col].value_counts()
            valid = vals[vals >= min_count].index.tolist()[:max_groups]
            if len(valid) < 2:
                return
            pc = [int(((df[col]==v)&(df['sentiment']=='긍정')).sum()) for v in valid]
            nc = [int(((df[col]==v)&(df['sentiment']=='부정')).sum()) for v in valid]
            uc = [int(((df[col]==v)&(df['sentiment']=='중립')).sum()) for v in valid]
            seg_html_parts.append(
                f'<div class="chart-box"><div class="chart-title">{_he(seg_title)}</div>'
                f'<div class="chart-desc">{_he(desc)}</div>'
                f'<canvas id="{chart_id}"></canvas></div>'
            )
            seg_js_parts.append(_stacked_js(chart_id, valid, pc, nc, uc))

        df2 = df.copy()
        df2['나이대'] = df2['age'].apply(_age_group)
        age_groups = [g for g in ['10대','20대','30대','40대','50대','60대+'] if g in df2['나이대'].values]
        if len(age_groups) >= 3:
            ag_pos = [int(((df2['나이대']==g)&(df2['sentiment']=='긍정')).sum()) for g in age_groups]
            ag_neg = [int(((df2['나이대']==g)&(df2['sentiment']=='부정')).sum()) for g in age_groups]
            ag_neu = [int(((df2['나이대']==g)&(df2['sentiment']=='중립')).sum()) for g in age_groups]
            seg_html_parts.append(
                '<div class="chart-box"><div class="chart-title">나이대별 반응</div>'
                '<div class="chart-desc">연령층별 긍정·부정 분포</div>'
                '<canvas id="ageChart"></canvas></div>'
            )
            seg_js_parts.append(_stacked_js('ageChart', age_groups, ag_pos, ag_neg, ag_neu))

        _add_seg('occupation', 'occChart', '직업군별 반응', '직군 간 긍정·부정 비교')
        if 'sex' in df.columns and (df['sex'].value_counts() >= 3).sum() >= 2:
            _add_seg('sex', 'sexChart', '성별 반응', '남/여 반응 분포 비교', min_count=3)

    # ── 반응/테마 분포 섹션 ──────────────────────────────────────────────────
    theme_chart_js = ''
    if mode == 'B':
        t_labels = json.dumps([t for t, _ in theme_data])
        t_counts = json.dumps([c for _, c in theme_data])
        dist_section = (
            '<div class="chart-box" style="max-width:680px">'
            '<div class="chart-title">테마 분포</div>'
            '<div class="chart-desc">응답에서 언급된 테마 빈도</div>'
            f'<canvas id="themeChart" style="max-height:{max(180, len(theme_data)*22)}px"></canvas></div>'
        )
        theme_chart_js = (
            f"new Chart(document.getElementById('themeChart'),{{"
            f"type:'bar',"
            f"data:{{labels:{t_labels},datasets:[{{data:{t_counts},"
            f"backgroundColor:'#58a6ff',borderRadius:4}}]}},"
            f"options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},"
            f"scales:{{x:{{...DS.x}},y:{{...DS.y}}}},"
            f"responsive:true,maintainAspectRatio:false}}}});"
        )
    else:
        if seg_html_parts:
            dist_section = (
                '<div class="dist-wrap">'
                '<div class="chart-box donut-box">'
                '<div class="chart-title">전체 반응 비율</div>'
                '<div class="chart-desc">긍정·부정·중립 비율</div>'
                '<canvas id="pieChart"></canvas></div>'
                f'<div class="seg-grid">{"".join(seg_html_parts)}</div>'
                '</div>'
            )
        else:
            dist_section = (
                '<div style="max-width:320px">'
                '<div class="chart-box">'
                '<div class="chart-title">전체 반응 비율</div>'
                '<div class="chart-desc">긍정·부정·중립 비율</div>'
                '<canvas id="pieChart"></canvas></div></div>'
            )
        # C모드: 감성 분포 뒤에 테마 차트 추가
        if mode == 'C' and theme_data:
            t_labels = json.dumps([t for t, _ in theme_data])
            t_counts = json.dumps([c for _, c in theme_data])
            dist_section += (
                f'<div class="chart-box" style="max-width:680px;margin-top:14px">'
                f'<div class="chart-title">테마 분포</div>'
                f'<div class="chart-desc">수용·거부 이유로 언급된 테마 빈도</div>'
                f'<canvas id="themeChart" style="max-height:{max(160, len(theme_data)*22)}px"></canvas></div>'
            )
            theme_chart_js = (
                f"new Chart(document.getElementById('themeChart'),{{"
                f"type:'bar',"
                f"data:{{labels:{t_labels},datasets:[{{data:{t_counts},"
                f"backgroundColor:'#58a6ff',borderRadius:4}}]}},"
                f"options:{{indexAxis:'y',plugins:{{legend:{{display:false}}}},"
                f"scales:{{x:{{...DS.x}},y:{{...DS.y}}}},"
                f"responsive:true,maintainAspectRatio:false}}}});"
            )

    # ── 주목할 응답 ────────────────────────────────────────────────────────────
    notable = _select_notable_quotes(df, geo_col, loc2_col)
    quotes_html = '\n'.join(
        f'<div class="quote-card" style="border-top:3px solid {q["color"]}">'
        f'<div class="quote-label" style="color:{q["color"]}">{_he(q["label"])}</div>'
        f'<blockquote class="quote-text">&#8220;{_he(q["answer"])}&#8221;</blockquote>'
        f'<div class="quote-profile">{_he(q["profile"])}</div>'
        f'</div>'
        for q in notable
    ) if notable else '<p style="color:var(--muted);font-size:.85rem">주목할 응답을 추출할 데이터가 부족합니다.</p>'

    # ── 개별 응답 카드 ─────────────────────────────────────────────────────────
    SENT_COLOR     = {'긍정': '#3fb950', '부정': '#f85149', '중립': '#6e7681'}
    SENT_BORDER_BG = {'긍정': 'rgba(63,185,80,.12)', '부정': 'rgba(248,81,73,.12)', '중립': 'rgba(110,118,129,.1)'}
    cards_html = []
    for _, r in df.iterrows():
        sl          = str(r.get('sentiment', '중립')) if 'sentiment' in df.columns else '중립'
        themes_list = _parse_themes(r.get('themes', '')) if 'themes' in df.columns else []
        themes_str  = ','.join(themes_list)

        if mode == 'B':
            col        = '#58a6ff'
            bg         = 'rgba(88,166,255,.1)'
            badge_text = ', '.join(themes_list) or '—'
        else:
            col        = SENT_COLOR.get(sl, '#6e7681')
            bg         = SENT_BORDER_BG.get(sl, 'rgba(110,118,129,.1)')
            badge_text = sl

        g1  = _he(str(r[geo_col])) if geo_col else ''
        g2  = f' {_he(str(r[loc2_col]))}' if loc2_col else ''
        ans = _he(str(r['answer'])) if r['answer'] else '<em style="color:#6e7681">응답 없음</em>'
        cards_html.append(
            f'<div class="card" data-sentiment="{_he(sl)}" data-themes="{_he(themes_str)}"'
            f' style="border-left:3px solid {col};background:{bg}">'
            f'<div class="card-header">'
            f'<span class="profile">{_he(str(r["age"]))}세 {_he(str(r["sex"]))} · {_he(str(r["occupation"]))} · {g1}{g2}</span>'
            f'<span class="badge" style="background:{col}">{_he(badge_text)}</span>'
            f'</div><p class="answer">{ans}</p></div>'
        )
    cards_joined = '\n'.join(cards_html)

    # ── 필터 바 & 핵심 지표 ───────────────────────────────────────────────────
    if mode == 'B':
        top_themes = [t for t, _ in theme_data[:8]]
        filter_parts = ['<button class="filter-btn active" onclick="filterCards(\'all\')">전체</button>']
        for t in top_themes:
            filter_parts.append(
                f'<button class="filter-btn" onclick="filterCards(\'{_he(t)}\')"'
                f' style="color:var(--blue)">{_he(t)}</button>'
            )
        filter_bar_html = '\n    '.join(filter_parts)

        top_t_label = theme_data[0][0] if theme_data else '—'
        top_t_count = theme_data[0][1] if theme_data else 0
        stats_html = (
            f'<div class="stat-box"><div class="stat-num">{n}</div><div class="stat-lbl">응답 수</div></div>'
            f'<div class="stat-box"><div class="stat-num" style="color:var(--blue)">{len(theme_data)}</div><div class="stat-lbl">발견 테마</div></div>'
            f'<div class="stat-box"><div class="stat-num" style="color:var(--blue);font-size:1.1rem">{_he(top_t_label)}</div>'
            f'<div class="stat-lbl">최다 테마 ({top_t_count}건)</div></div>'
        )
        dist_h2 = '테마 분포'
    else:
        filter_bar_html = (
            f'<button class="filter-btn active" onclick="filterCards(\'all\')">전체</button>\n'
            f'    <button class="filter-btn" onclick="filterCards(\'긍정\')" style="color:var(--green)">긍정 {n_pos}명</button>\n'
            f'    <button class="filter-btn" onclick="filterCards(\'부정\')" style="color:var(--red)">부정 {n_neg}명</button>\n'
            f'    <button class="filter-btn" onclick="filterCards(\'중립\')" style="color:var(--muted)">중립 {n_neu}명</button>'
        )
        stats_html = (
            f'<div class="stat-box"><div class="stat-num">{n}</div><div class="stat-lbl">응답 수</div></div>'
            f'<div class="stat-box"><div class="stat-num" style="color:var(--green)">{n_pos}</div><div class="stat-lbl">긍정 ({n_pos/n:.0%})</div></div>'
            f'<div class="stat-box"><div class="stat-num" style="color:var(--red)">{n_neg}</div><div class="stat-lbl">부정 ({n_neg/n:.0%})</div></div>'
            f'<div class="stat-box"><div class="stat-num" style="color:var(--muted)">{n_neu}</div><div class="stat-lbl">중립 ({n_neu/n:.0%})</div></div>'
        )
        dist_h2 = '반응 분포' if mode == 'A' else '반응 분포 &amp; 테마'

    pie_chart_js = '' if mode == 'B' else (
        f"new Chart(document.getElementById('pieChart'),{{"
        f"type:'doughnut',"
        f"data:{{labels:['긍정','부정','중립'],datasets:[{{data:{pie_data},"
        f"backgroundColor:['#3fb950','#f85149','#6e7681'],borderWidth:2,borderColor:'#161b22'}}]}},"
        f"options:{{plugins:{{legend:{{labels:{{color:'#c9d1d9'}},position:'bottom'}}}},"
        f"responsive:true}}}});"
    )

    # ── HTML ──────────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_he(title)} — market-simulation</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
:root{{--bg:#0d1117;--surface:#161b22;--card:#21262d;--border:#30363d;--text:#e6edf3;--muted:#8b949e;--green:#3fb950;--red:#f85149;--blue:#58a6ff;--yellow:#d29922;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:-apple-system,'Malgun Gothic',sans-serif;background:var(--bg);color:var(--text);line-height:1.6;}}
.wrap{{max-width:1080px;margin:0 auto;padding:28px 18px 56px;}}
h1{{font-size:1.55rem;font-weight:700;letter-spacing:-.01em;}}
h2{{font-size:.82rem;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.07em;margin:36px 0 14px;border-bottom:1px solid var(--border);padding-bottom:6px;}}
.meta{{color:var(--muted);font-size:.82rem;margin:5px 0 18px;}}
.disclaimer{{background:rgba(248,81,73,.1);border:1px solid rgba(248,81,73,.3);padding:9px 14px;border-radius:6px;font-size:.8rem;color:#ffa198;margin-bottom:16px;}}
.question-box{{background:rgba(210,153,34,.08);border-left:3px solid var(--yellow);padding:11px 16px;border-radius:4px;font-style:italic;margin-bottom:24px;color:#e3b341;}}
.hero-box{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:18px 22px;margin-bottom:6px;}}
.hero-headline{{font-size:1.05rem;font-weight:600;color:var(--text);margin-bottom:14px;line-height:1.5;}}
.hero-box ul{{padding-left:18px;}}
.hero-box li{{font-size:.875rem;margin-bottom:8px;color:#c9d1d9;line-height:1.55;}}
.stats-row{{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:6px;}}
.stat-box{{flex:1;min-width:110px;background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:14px 16px;text-align:center;}}
.stat-num{{font-size:1.9rem;font-weight:700;}}
.stat-lbl{{font-size:.75rem;color:var(--muted);margin-top:3px;}}
.dist-wrap{{display:grid;grid-template-columns:260px 1fr;gap:14px;margin-bottom:6px;align-items:start;}}
.seg-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;}}
.chart-box{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:16px;}}
.chart-box canvas{{max-height:220px;}}
.chart-title{{font-size:.8rem;font-weight:600;color:var(--muted);margin-bottom:6px;}}
.chart-desc{{font-size:.72rem;color:#6e7681;margin-bottom:8px;}}
.quote-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:14px;margin-bottom:6px;}}
.quote-card{{background:var(--surface);border:1px solid var(--border);border-radius:8px;padding:18px 20px;display:flex;flex-direction:column;}}
.quote-label{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px;}}
.quote-text{{font-size:.93rem;line-height:1.75;color:#c9d1d9;font-style:italic;flex:1;}}
.quote-profile{{font-size:.74rem;color:var(--muted);margin-top:12px;padding-top:10px;border-top:1px solid var(--border);}}
.filter-bar{{display:flex;gap:8px;margin:18px 0 12px;flex-wrap:wrap;}}
.filter-btn{{padding:5px 16px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--muted);cursor:pointer;font-size:.82rem;transition:.15s;}}
.filter-btn:hover{{border-color:var(--text);color:var(--text);}}
.filter-btn.active{{background:var(--text);color:var(--bg);border-color:var(--text);}}
.card{{border-radius:6px;padding:12px 16px;margin-bottom:10px;}}
.card.hidden{{display:none;}}
.card-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;gap:8px;}}
.profile{{font-size:.78rem;color:var(--muted);flex:1;}}
.badge{{font-size:.72rem;color:#000;padding:2px 9px;border-radius:12px;font-weight:700;white-space:nowrap;}}
.answer{{font-size:.88rem;line-height:1.7;color:#c9d1d9;}}
footer{{text-align:center;font-size:.72rem;color:#6e7681;margin-top:40px;}}
@media(max-width:700px){{.dist-wrap{{grid-template-columns:1fr;}}}}
</style>
</head>
<body>
<div class="wrap">
  <h1>{_he(title)}</h1>
  <div class="meta">{today} · Claude Code Agents · LLM 시뮬 · {n}명</div>
  <div class="disclaimer">⚠ AI가 AI 페르소나를 연기하는 구조입니다. 실제 소비자 조사를 대체하지 않으며 통계적 대표성이 없습니다.</div>
  <div class="question-box">Q. {_he(question or '(질문 미입력)')}</div>

  <h2>핵심 발견</h2>
  <div class="hero-box">
    <div class="hero-headline">{_he(headline)}</div>
    <ul>{insight_html}</ul>
  </div>

  <h2>핵심 지표</h2>
  <div class="stats-row">
    {stats_html}
  </div>

  <h2>{dist_h2}</h2>
  {dist_section}

  <h2>주목할 응답</h2>
  <div class="quote-grid">{quotes_html}</div>

  <h2>개별 응답 ({n}건)</h2>
  <div class="filter-bar">
    {filter_bar_html}
  </div>
  <div id="cards">{cards_joined}</div>

  <footer>market-simulation v0.9 · LLM 시뮬 기반 가설 · 실제 시장 데이터 아님</footer>
</div>
<script>
Chart.defaults.color='#8b949e';
const DS={{
  x:{{grid:{{color:'rgba(255,255,255,0.06)'}},ticks:{{color:'#8b949e'}}}},
  y:{{grid:{{color:'rgba(255,255,255,0.06)'}},ticks:{{color:'#8b949e'}}}}
}};
{pie_chart_js}
{theme_chart_js}
{chr(10).join(seg_js_parts)}
function filterCards(s){{
  document.querySelectorAll('.card').forEach(c=>{{
    if(s==='all'){{c.classList.remove('hidden');return;}}
    const themes=c.dataset.themes?c.dataset.themes.split(','):[];
    c.classList.toggle('hidden',c.dataset.sentiment!==s&&!themes.includes(s));
  }});
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.toggle('active',b.textContent.startsWith(s==='all'?'전체':s)));
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
