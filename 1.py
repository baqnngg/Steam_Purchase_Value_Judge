"""
Steam 게임 데이터셋 탐색적 데이터 분석 (EDA)
games.csv 기준 | 총 122,611행 X 39열
"""

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────────────────────
df = pd.read_csv('games.csv', low_memory=False)

print("=" * 60)
print("  Steam 게임 데이터셋 EDA")
print("=" * 60)

# ─────────────────────────────────────────────
# 2. 기본 구조 파악
# ─────────────────────────────────────────────
print(f"\n[1] 기본 구조")
print(f"  총 행 수  : {len(df):,}개")
print(f"  총 열 수  : {len(df.columns)}개")

# ─────────────────────────────────────────────
# 3. 컬럼별 의미 및 데이터 타입
# ─────────────────────────────────────────────
COLUMN_DESCRIPTIONS = {
    "AppID"                    : ("str",     "Steam 앱 고유 ID"),
    "Name"                     : ("str",     "게임 이름"),
    "Release date"             : ("str",     "출시일 (예: 'Aug 1, 2023') → datetime 변환 필요"),
    "Estimated owners"         : ("int64",   "추정 소유자 수 (구간 형태)"),
    "Peak CCU"                 : ("int64",   "최고 동시 접속자 수"),
    "Required age"             : ("float64", "이용 가능 최소 연령"),
    "Price"                    : ("int64",   "가격 (달러 × 100 정수 표현)"),
    "DiscountDLC count"        : ("int64",   "DLC 수"),
    "About the game"           : ("str",     "게임 설명 텍스트"),
    "Supported languages"      : ("str",     "지원 언어 목록 (JSON 문자열)"),
    "Full audio languages"     : ("str",     "전체 음성 지원 언어 목록"),
    "Reviews"                  : ("str",     "리뷰 요약 텍스트 (결측 90%)"),
    "Header image"             : ("str",     "헤더 이미지 URL"),
    "Website"                  : ("str",     "공식 웹사이트 URL"),
    "Support url"              : ("str",     "고객 지원 URL"),
    "Support email"            : ("str",     "고객 지원 이메일"),
    "Windows"                  : ("bool",    "Windows 지원 여부"),
    "Mac"                      : ("bool",    "Mac 지원 여부"),
    "Linux"                    : ("bool",    "Linux 지원 여부"),
    "Metacritic score"         : ("int64",   "메타크리틱 점수 (0 = 데이터 없음)"),
    "Metacritic url"           : ("str",     "메타크리틱 페이지 URL (결측 97%)"),
    "User score"               : ("int64",   "사용자 점수"),
    "Positive"                 : ("int64",   "긍정 리뷰 수"),
    "Negative"                 : ("int64",   "부정 리뷰 수"),
    "Score rank"               : ("float64", "점수 순위 (결측 100% → 제거 대상)"),
    "Achievements"             : ("int64",   "업적 수"),
    "Recommendations"          : ("int64",   "추천 수"),
    "Notes"                    : ("str",     "부가 정보 메모 (결측 82%)"),
    "Average playtime forever" : ("int64",   "전체 기간 평균 플레이 시간(분)"),
    "Average playtime two weeks": ("int64",  "최근 2주 평균 플레이 시간(분)"),
    "Median playtime forever"  : ("int64",   "전체 기간 중앙값 플레이 시간(분)"),
    "Median playtime two weeks": ("int64",   "최근 2주 중앙값 플레이 시간(분)"),
    "Developers"               : ("str",     "개발사"),
    "Publishers"               : ("str",     "퍼블리셔"),
    "Categories"               : ("str",     "게임 카테고리 (쉼표 구분 문자열)"),
    "Genres"                   : ("str",     "장르 (쉼표 구분 문자열)"),
    "Tags"                     : ("str",     "사용자 태그 (쉼표 구분 문자열)"),
    "Screenshots"              : ("str",     "스크린샷 URL 목록 (쉼표 구분)"),
    "Movies"                   : ("float64", "예고편 정보 (결측 100% → 제거 대상)"),
}

print(f"\n[2] 컬럼별 데이터 타입 및 의미")
print(f"  {'컬럼명':<30} {'타입':<10} 설명")
print(f"  {'-'*28} {'-'*8} {'-'*35}")
for col, (dtype, desc) in COLUMN_DESCRIPTIONS.items():
    print(f"  {col:<30} {dtype:<10} {desc}")

# ─────────────────────────────────────────────
# 4. 결측치 현황
# ─────────────────────────────────────────────
null_counts = df.isnull().sum()
null_pct    = (null_counts / len(df) * 100).round(2)
null_df = pd.DataFrame({'결측치 수': null_counts, '결측 비율(%)': null_pct})
null_df = null_df[null_df['결측치 수'] > 0].sort_values('결측 비율(%)', ascending=False)

print(f"\n[3] 결측치 현황 (결측치가 존재하는 컬럼만 표시)")
print(f"  {'컬럼명':<30} {'결측치 수':>10} {'결측 비율(%)':>12}")
print(f"  {'-'*28} {'-'*10} {'-'*12}")
for col, row in null_df.iterrows():
    print(f"  {col:<30} {int(row['결측치 수']):>10,} {row['결측 비율(%)']:>11.2f}%")

# ─────────────────────────────────────────────
# 5. 결측치 정제 계획
# ─────────────────────────────────────────────
print(f"""
[4] 결측치 정제 계획
─────────────────────────────────────────────────────────────
컬럼              결측률   전략           상세 설명
─────────────────────────────────────────────────────────────
Movies           100.00%  dropna(col)    전체 결측 → 컬럼 자체 삭제
Score rank        99.97%  dropna(col)    사실상 전체 결측 → 컬럼 삭제
Metacritic url    96.53%  fillna('')     분석에 불필요, 빈 문자열로 대체
Reviews           90.16%  fillna('없음') 텍스트 분석 제외하거나 '없음' 처리
Notes             81.68%  fillna('')     보조 메모 → 빈 문자열 처리
Website           59.48%  fillna('')     URL → 빈 문자열 처리
Support url       55.84%  fillna('')     URL → 빈 문자열 처리
Tags              32.02%  fillna('')     문자열 집계 시 빈 값으로 대체
Support email     18.16%  fillna('')     이메일 → 빈 문자열 처리
About the game     6.89%  fillna('')     설명 없는 게임 → 빈 문자열 처리
Developers         6.88%  fillna('Unknown')  분석 대상 → 'Unknown' 처리
Genres             6.86%  fillna('Unknown')  분석 대상 → 'Unknown' 처리
Publishers         7.27%  fillna('Unknown')  분석 대상 → 'Unknown' 처리
Categories         7.30%  fillna('Unknown')  분석 대상 → 'Unknown' 처리
Screenshots        4.91%  fillna('')     URL 목록 → 빈 문자열 처리
Header image       0.07%  fillna('')     극소량 결측 → 빈 문자열 처리
AppID              0.00%  dropna(row)    PK 역할 → 해당 행 삭제
─────────────────────────────────────────────────────────────
""")

# ─────────────────────────────────────────────
# 6. 실제 정제 코드
# ─────────────────────────────────────────────
print("[5] 정제 실행")

# (1) 불필요 컬럼 삭제 (100% 결측)
DROP_COLS = ['Movies', 'Score rank']
df.drop(columns=DROP_COLS, inplace=True)
print(f"  컬럼 삭제 완료: {DROP_COLS}")

# (2) AppID 결측 행 제거 (PK)
before = len(df)
df.dropna(subset=['AppID'], inplace=True)
print(f"  AppID 결측 행 제거: {before - len(df)}행 삭제")

# (3) 빈 문자열로 대체 (정보 목적 URL·텍스트)
fill_empty = [
    'Reviews', 'Metacritic url', 'Notes', 'Website', 'Support url',
    'Support email', 'About the game', 'Screenshots', 'Header image',
    'Tags', 'Supported languages', 'Full audio languages',
]
df[fill_empty] = df[fill_empty].fillna('')
print(f"  빈 문자열('') 대체: {fill_empty}")

# (4) 'Unknown'으로 대체 (집계·분석 대상)
fill_unknown = ['Developers', 'Publishers', 'Categories', 'Genres']
df[fill_unknown] = df[fill_unknown].fillna('Unknown')
print(f"  'Unknown' 대체: {fill_unknown}")

# (5) 숫자형 결측 → 0 (Required age, Score rank 이미 삭제됨)
df['Required age'] = df['Required age'].fillna(0).astype(int)
print(f"  Required age 결측 → 0으로 대체")

# ─────────────────────────────────────────────
# 7. 정제 후 검증
# ─────────────────────────────────────────────
remaining_null = df.isnull().sum().sum()
print(f"\n[6] 정제 완료")
print(f"  최종 행 수  : {len(df):,}개")
print(f"  최종 열 수  : {len(df.columns)}개")
print(f"  잔여 결측치 : {remaining_null}개")

if remaining_null == 0:
    print("  ✓ 결측치 없음 — 정제 완료!")
else:
    print("  ✗ 잔여 결측치 확인 필요:")
    print(df.isnull().sum()[df.isnull().sum() > 0])