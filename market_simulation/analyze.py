"""
시뮬 결과 CSV → 통계 리포트 .report.md 자동 생성.

CSV 컬럼: id, age, sex, occupation, province, district, answer

독립 실행:
    python src/analyze.py output/2026-05-02_coffee.csv "커피숍 월정액" "월 9,900원에 커피 구독 쓰시겠어요?"
"""
from __future__ import annotations
import datetime
import pandas as pd

SHORT_THRESHOLD = 20

REPORT_TEMPLATE = """# {title}

- **일시**: {today}
- **샘플 N**: {n} (시도 최빈={province_top} / 직업 상위3={occ_top})
- **엔진**: Claude Code Agents (배치 5명 × {n_batches}개 병렬)
- **응답률**: {ok}/{n} ({rate:.0%}) · 평균 {mean_len:.0f}자 · 중앙값 {med_len:.0f}자
- **LLM 시뮬 기반 가설 — 실제 시장 데이터 아님**

## 질문

> {question}

## 인구통계 분포

{demo_table}

## 정상 응답 (N={ok})

{quotes}

## 짧·빈 응답 ({n_short}건)

{short_table}

## 자기진단

{diag}

## 패턴 군집 (Claude 세션에서 정리)

이 리포트는 통계와 인용만 자동 생성.
응답 내용을 읽고 다음을 별도 `<같은이름>.summary.md` 로 정리하라:

- 가격대·장소·시간 등 정량 패턴 군집
- 세그먼트별 차이 (직업·연령·지역)
- 핵심 인용 3~5개
- 미충족 니즈·거부 사유
"""


REQUIRED_COLS = {'age', 'sex', 'occupation', 'province', 'district', 'answer'}
_MD_ESCAPE = str.maketrans({'|': '/', '\n': ' ', '\r': ' '})


def _md_safe(s: str, max_len: int = 0) -> str:
    cleaned = str(s).translate(_MD_ESCAPE)
    return cleaned[:max_len] if max_len else cleaned


def write_report(csv_path: str, topic: str = '', question: str = '') -> str:
    """CSV 옆에 .report.md 통계 리포트를 생성하고 그 경로를 반환."""
    import os
    from pandas.errors import EmptyDataError

    os.makedirs(os.path.dirname(csv_path) or '.', exist_ok=True)

    try:
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
    except EmptyDataError:
        md_path = csv_path.replace('.csv', '.report.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f'# {topic or "시뮬 결과"}\n\n빈 CSV — 시뮬레이션 결과가 없습니다.\n')
        return md_path

    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        md_path = csv_path.replace('.csv', '.report.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f'# {topic or "시뮬 결과"}\n\n필수 컬럼 누락: {missing}\n')
        return md_path

    n = len(df)
    if n == 0:
        md_path = csv_path.replace('.csv', '.report.md')
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f'# {topic or "시뮬 결과"}\n\n행 없음 — 시뮬레이션 결과가 없습니다.\n')
        return md_path

    df['answer'] = df['answer'].fillna('')

    is_short = df['answer'].str.len() < SHORT_THRESHOLD
    ok_df = df[~is_short]
    n_ok = len(ok_df)
    n_short = n - n_ok
    n_batches = -(-n // 5)

    mean_len = df['answer'].str.len().mean()
    med_len  = df['answer'].str.len().median()
    rate     = n_ok / n

    province_top = df['province'].mode().iat[0]
    occ_top = ', '.join(df['occupation'].value_counts().head(3).index.tolist())

    demo_lines = ['| 항목 | 분포 |', '|---|---|']
    demo_lines.append(
        f"| 나이 | min={df['age'].min()}, mean={df['age'].mean():.1f}, max={df['age'].max()} |"
    )
    for col, label in [('sex', '성별'), ('province', '시도'), ('occupation', '직업'),
                       ('family_type', '가구'), ('education_level', '학력')]:
        if col in df.columns:
            vals = df[col].value_counts().head(5).to_dict()
            demo_lines.append(f"| {label} | " + ', '.join(f"{_md_safe(k)}({v})" for k, v in vals.items()) + ' |')
    demo_table = '\n'.join(demo_lines)

    quote_blocks = []
    for _, r in ok_df.iterrows():
        quote_blocks.append(
            f"### [{r['age']}세 {_md_safe(r['sex'])} · {_md_safe(r['occupation'])} · {_md_safe(r['district'])}]\n"
            f"> {_md_safe(r['answer'])}\n"
        )
    quotes = '\n'.join(quote_blocks) if quote_blocks else '_정상 응답 없음._'

    if n_short > 0:
        short_rows = df[is_short]
        short_lines = ['| 나이 | 직업 | 응답(앞 40자) |', '|---|---|---|']
        for _, r in short_rows.iterrows():
            short_lines.append(f"| {r['age']} | {_md_safe(r['occupation'])} | {_md_safe(r['answer'], 40)} |")
        short_table = '\n'.join(short_lines)
    else:
        short_table = '_없음._'

    diag_lines = [f"- 응답률 {rate:.0%} ({n_ok}/{n})"]
    if rate < 0.7:
        diag_lines.append("- ⚠ 응답률 70% 미만 — 에이전트 응답 파싱 오류 가능. 원본 에이전트 출력을 확인하세요.")
    if rate >= 0.9:
        diag_lines.append("- 안정적. 현재 설정 그대로 다음 시뮬에 사용 가능.")
    diag = '\n'.join(diag_lines)

    body = REPORT_TEMPLATE.format(
        title=topic.replace('_', ' ') if topic else '시뮬 결과',
        today=datetime.date.today().isoformat(),
        n=n, n_batches=n_batches,
        province_top=province_top, occ_top=occ_top,
        ok=n_ok, rate=rate,
        mean_len=mean_len, med_len=med_len,
        n_short=n_short,
        question=question,
        demo_table=demo_table,
        quotes=quotes,
        short_table=short_table,
        diag=diag,
    )

    md_path = csv_path.replace('.csv', '.report.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(body)
    return md_path


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('usage: python src/analyze.py <csv_path> [topic] [question]')
        sys.exit(1)
    out = write_report(
        sys.argv[1],
        topic=sys.argv[2] if len(sys.argv) > 2 else '',
        question=sys.argv[3] if len(sys.argv) > 3 else '',
    )
    print(f'wrote {out}')
