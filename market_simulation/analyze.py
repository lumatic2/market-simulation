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
    n = len(df)
    sent = df['sentiment'].value_counts() if 'sentiment' in df.columns else {}
    pos = sent.get('긍정', 0)
    neg = sent.get('부정', 0)
    neu = sent.get('중립', 0)

    bar_w = 20

    def bar(count: int) -> str:
        filled = round(count / n * bar_w) if n else 0
        return '█' * filled + '░' * (bar_w - filled)

    kws = top_keywords(df['answer'].dropna().tolist(), 3)
    kw_str = '  '.join(f"{w}({c})" for w, c in kws)

    pos_df = df[df['sentiment'] == '긍정'] if 'sentiment' in df.columns else pd.DataFrame()
    neg_df = df[df['sentiment'] == '부정'] if 'sentiment' in df.columns else pd.DataFrame()
    age_insight = ''
    if len(pos_df) and len(neg_df):
        age_insight = f"  긍정 평균나이 {pos_df['age'].mean():.1f}세  부정 {neg_df['age'].mean():.1f}세"

    title = (topic.replace('_', ' ') or '시뮬 결과')[:30]
    w = 52
    print('━' * w)
    print(f"  {title}")
    print('━' * w)
    print(f"  응답    {n:2d}명")
    print(f"  긍정    {pos:2d}명  ({pos/n:.0%})  {bar(pos)}")
    print(f"  중립    {neu:2d}명  ({neu/n:.0%})  {bar(neu)}")
    print(f"  부정    {neg:2d}명  ({neg/n:.0%})  {bar(neg)}")
    print('─' * w)
    if kw_str:
        print(f"  키워드  {kw_str}")
    if age_insight:
        print(f" {age_insight}")
    print('─' * w)
    print(f"  리포트  {report_path}")
    print('━' * w)


# ── HTML 리포트 ───────────────────────────────────────────────────────────────

def _he(s: str) -> str:
    """HTML 이스케이프."""
    return (str(s)
            .replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _jss(s) -> str:
    """JSON 문자열 이스케이프 (따옴표 없이)."""
    return str(s).replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').replace('\r', '')


def write_html_report(
    csv_path: str,
    df: pd.DataFrame,
    topic: str = '',
    question: str = '',
    auto_open: bool = True,
) -> str:
    """시뮬 결과 DataFrame → self-contained HTML 리포트 생성 + 브라우저 자동 열기."""
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
    pie_data = json.dumps([int(sent.get('긍정', 0)), int(sent.get('부정', 0)), int(sent.get('중립', 0))])

    # 나이대×감성 스택 바
    df2 = df.copy()
    df2['나이대'] = df2['age'].apply(_age_group)
    age_groups = ['20대', '30대', '40대', '50대', '60대+', '10대']
    age_groups = [g for g in age_groups if g in df2['나이대'].values]
    ag_pos = [int(((df2['나이대'] == g) & (df2['sentiment'] == '긍정')).sum()) for g in age_groups]
    ag_neg = [int(((df2['나이대'] == g) & (df2['sentiment'] == '부정')).sum()) for g in age_groups]
    ag_neu = [int(((df2['나이대'] == g) & (df2['sentiment'] == '중립')).sum()) for g in age_groups]
    age_labels = json.dumps(age_groups)

    # 키워드 바차트 (상위 10)
    def kw_chart_data(texts: list[str]):
        kws = top_keywords(texts, 10)
        return json.dumps([w for w, _ in kws]), json.dumps([c for _, c in kws])

    kw_labels_all, kw_vals_all = kw_chart_data(df['answer'].dropna().tolist())
    pos_texts = df[df['sentiment'] == '긍정']['answer'].tolist() if 'sentiment' in df.columns else []
    neg_texts = df[df['sentiment'] == '부정']['answer'].tolist() if 'sentiment' in df.columns else []
    kw_labels_pos, kw_vals_pos = kw_chart_data(pos_texts)
    kw_labels_neg, kw_vals_neg = kw_chart_data(neg_texts)

    # ── 응답 카드 HTML ────────────────────────────────────────────────────────
    SENT_COLOR = {'긍정': '#16a34a', '부정': '#dc2626', '중립': '#64748b'}
    SENT_BG    = {'긍정': '#f0fdf4', '부정': '#fef2f2', '중립': '#f8fafc'}

    cards_html = []
    for _, r in df.iterrows():
        sent_label = r.get('sentiment', '중립')
        color  = SENT_COLOR.get(sent_label, '#64748b')
        bg     = SENT_BG.get(sent_label, '#f8fafc')
        geo1   = _he(str(r[geo_col]))  if geo_col  else ''
        geo2   = f" {_he(str(r[loc2_col]))}" if loc2_col else ''
        answer_text = _he(str(r['answer'])) if r['answer'] else '<em style="color:#aaa">응답 없음</em>'
        cards_html.append(f"""
        <div class="card" data-sentiment="{_he(sent_label)}"
             style="border-left:4px solid {color}; background:{bg}">
          <div class="card-header">
            <span class="profile">{_he(str(r['age']))}세 {_he(str(r['sex']))}
              · {_he(str(r['occupation']))}
              · {geo1}{geo2}</span>
            <span class="badge" style="background:{color}">{_he(sent_label)}</span>
          </div>
          <p class="answer">{answer_text}</p>
        </div>""")
    cards_joined = '\n'.join(cards_html)

    # ── HTML 본문 ──────────────────────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_he(title)} — market-simulation</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, 'Malgun Gothic', sans-serif; background: #f1f5f9; color: #1e293b; }}
  .wrap {{ max-width: 960px; margin: 0 auto; padding: 24px 16px; }}
  h1 {{ font-size: 1.6rem; font-weight: 700; }}
  h2 {{ font-size: 1.1rem; font-weight: 600; margin: 28px 0 12px; color: #334155; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
  .meta {{ color: #64748b; font-size: .85rem; margin: 6px 0 16px; }}
  .question-box {{ background:#fffbeb; border-left:4px solid #f59e0b; padding:12px 16px; border-radius:4px; font-style:italic; margin-bottom:8px; }}
  .disclaimer {{ background:#fef2f2; border:1px solid #fca5a5; padding:10px 14px; border-radius:6px; font-size:.82rem; color:#991b1b; margin-bottom:20px; }}
  .stats-row {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px; }}
  .stat-box {{ flex:1; min-width:120px; background:#fff; border-radius:8px; padding:14px 16px; box-shadow:0 1px 3px rgba(0,0,0,.08); text-align:center; }}
  .stat-num {{ font-size:1.8rem; font-weight:700; }}
  .stat-lbl {{ font-size:.78rem; color:#64748b; margin-top:2px; }}
  .charts-row {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-bottom:8px; }}
  .chart-box {{ background:#fff; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .chart-box canvas {{ max-height:240px; }}
  .kw-row {{ display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px; margin-bottom:8px; }}
  .kw-box {{ background:#fff; border-radius:8px; padding:14px; box-shadow:0 1px 3px rgba(0,0,0,.08); }}
  .kw-box canvas {{ max-height:180px; }}
  .kw-title {{ font-size:.82rem; font-weight:600; margin-bottom:8px; color:#475569; }}
  .filter-bar {{ display:flex; gap:8px; margin:16px 0 10px; }}
  .filter-btn {{ padding:5px 14px; border-radius:20px; border:1px solid #cbd5e1; background:#fff; cursor:pointer; font-size:.84rem; }}
  .filter-btn.active {{ background:#1e293b; color:#fff; border-color:#1e293b; }}
  .card {{ border-radius:6px; padding:12px 16px; margin-bottom:10px; transition:.15s; }}
  .card.hidden {{ display:none; }}
  .card-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
  .profile {{ font-size:.82rem; color:#475569; }}
  .badge {{ font-size:.75rem; color:#fff; padding:2px 8px; border-radius:12px; font-weight:600; }}
  .answer {{ font-size:.9rem; line-height:1.65; color:#334155; }}
  footer {{ text-align:center; font-size:.75rem; color:#94a3b8; margin-top:32px; }}
  @media(max-width:640px) {{ .charts-row,.kw-row {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <h1>{_he(title)}</h1>
  <div class="meta">{today} · Claude Code Agents · LLM 시뮬</div>
  <div class="disclaimer">⚠ AI가 AI 페르소나를 연기하는 구조입니다. 실제 소비자 조사를 대체하지 않습니다. 찬성 비율은 LLM positive bias로 과대 추정될 수 있습니다.</div>
  <div class="question-box">Q. {_he(question or '(질문 미입력)')}</div>

  <h2>핵심 지표</h2>
  <div class="stats-row">
    <div class="stat-box"><div class="stat-num">{n}</div><div class="stat-lbl">응답 수</div></div>
    <div class="stat-box"><div class="stat-num" style="color:#16a34a">{sent.get('긍정',0)}</div><div class="stat-lbl">긍정 ({sent.get('긍정',0)/n:.0%})</div></div>
    <div class="stat-box"><div class="stat-num" style="color:#dc2626">{sent.get('부정',0)}</div><div class="stat-lbl">부정 ({sent.get('부정',0)/n:.0%})</div></div>
    <div class="stat-box"><div class="stat-num" style="color:#64748b">{sent.get('중립',0)}</div><div class="stat-lbl">중립 ({sent.get('중립',0)/n:.0%})</div></div>
  </div>

  <h2>차트</h2>
  <div class="charts-row">
    <div class="chart-box">
      <div style="font-size:.82rem;font-weight:600;color:#475569;margin-bottom:8px">감성 분포</div>
      <canvas id="pieChart"></canvas>
    </div>
    <div class="chart-box">
      <div style="font-size:.82rem;font-weight:600;color:#475569;margin-bottom:8px">나이대 × 감성</div>
      <canvas id="ageChart"></canvas>
    </div>
  </div>

  <h2>키워드 분석</h2>
  <div class="kw-row">
    <div class="kw-box"><div class="kw-title">전체</div><canvas id="kwAll"></canvas></div>
    <div class="kw-box"><div class="kw-title" style="color:#16a34a">긍정 응답</div><canvas id="kwPos"></canvas></div>
    <div class="kw-box"><div class="kw-title" style="color:#dc2626">부정 응답</div><canvas id="kwNeg"></canvas></div>
  </div>

  <h2>응답 카드 ({n}건)</h2>
  <div class="filter-bar">
    <button class="filter-btn active" onclick="filter('all')">전체</button>
    <button class="filter-btn" onclick="filter('긍정')" style="color:#16a34a">긍정</button>
    <button class="filter-btn" onclick="filter('부정')" style="color:#dc2626">부정</button>
    <button class="filter-btn" onclick="filter('중립')" style="color:#64748b">중립</button>
  </div>
  <div id="cards">
{cards_joined}
  </div>

  <footer>market-simulation · LLM 시뮬 기반 가설 · 실제 시장 데이터 아님</footer>
</div>

<script>
// 파이차트
new Chart(document.getElementById('pieChart'), {{
  type: 'doughnut',
  data: {{ labels: ['긍정','부정','중립'], datasets: [{{
    data: {pie_data}, backgroundColor: ['#16a34a','#dc2626','#94a3b8'], borderWidth: 2
  }}] }},
  options: {{ plugins: {{ legend: {{ position: 'bottom' }} }}, responsive: true }}
}});

// 나이대 바차트
new Chart(document.getElementById('ageChart'), {{
  type: 'bar',
  data: {{
    labels: {age_labels},
    datasets: [
      {{ label:'긍정', data:{json.dumps(ag_pos)}, backgroundColor:'#16a34a' }},
      {{ label:'부정', data:{json.dumps(ag_neg)}, backgroundColor:'#dc2626' }},
      {{ label:'중립', data:{json.dumps(ag_neu)}, backgroundColor:'#94a3b8' }}
    ]
  }},
  options: {{ scales: {{ x: {{ stacked:true }}, y: {{ stacked:true }} }}, plugins: {{ legend: {{ position:'bottom' }} }}, responsive:true }}
}});

// 키워드 바차트
function kwChart(id, labels, vals, color) {{
  new Chart(document.getElementById(id), {{
    type: 'bar',
    data: {{ labels: labels, datasets: [{{ data: vals, backgroundColor: color }}] }},
    options: {{ indexAxis:'y', plugins:{{ legend:{{ display:false }} }}, responsive:true,
                scales:{{ x:{{ ticks:{{ font:{{ size:10 }} }} }}, y:{{ ticks:{{ font:{{ size:10 }} }} }} }} }}
  }});
}}
kwChart('kwAll', {kw_labels_all}, {kw_vals_all}, '#3b82f6');
kwChart('kwPos', {kw_labels_pos}, {kw_vals_pos}, '#16a34a');
kwChart('kwNeg', {kw_labels_neg}, {kw_vals_neg}, '#dc2626');

// 필터
function filter(sent) {{
  document.querySelectorAll('.card').forEach(c => {{
    c.classList.toggle('hidden', sent !== 'all' && c.dataset.sentiment !== sent);
  }});
  document.querySelectorAll('.filter-btn').forEach(b => {{
    b.classList.toggle('active', b.textContent.trim() === (sent === 'all' ? '전체' : sent));
  }});
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
