"""
Steam 게임 데이터셋 정제 코드
입력: games.csv
출력: games_cleaned.csv
"""

import pandas as pd

# ─────────────────────────────────────────────
# 1. 데이터 로드
# ─────────────────────────────────────────────
df = pd.read_csv('code/games.csv', low_memory=False)
print(f"로드 완료: {len(df):,}행 * {len(df.columns)}열")

# ─────────────────────────────────────────────
# 2. 불필요 컬럼 삭제 (결측률 100% 또는 99.97%)
# ─────────────────────────────────────────────
df.drop(columns=['Movies', 'Score rank'], inplace=True)

# ─────────────────────────────────────────────
# 3. AppID 결측 행 제거 (기본키)
# ─────────────────────────────────────────────
df.dropna(subset=['AppID'], inplace=True)

# ─────────────────────────────────────────────
# 4. 분석 대상 컬럼 → 'Unknown' 대체
# ─────────────────────────────────────────────
fill_unknown = ['Developers', 'Publishers', 'Categories', 'Genres']
df[fill_unknown] = df[fill_unknown].fillna('Unknown')

# ─────────────────────────────────────────────
# 5. URL·텍스트 컬럼 → 빈 문자열 대체
# ─────────────────────────────────────────────
fill_empty = [
    'Reviews', 'Metacritic url', 'Notes', 'Website', 'Support url',
    'Support email', 'About the game', 'Screenshots', 'Header image',
    'Tags', 'Supported languages', 'Full audio languages',
]
df[fill_empty] = df[fill_empty].fillna('')

# ─────────────────────────────────────────────
# 6. Required age 결측 → 0 (연령 제한 없음)
# ─────────────────────────────────────────────
df['Required age'] = df['Required age'].fillna(0).astype(int)

# ─────────────────────────────────────────────
# 7. Release date → datetime 변환
# ─────────────────────────────────────────────
df['Release date'] = pd.to_datetime(df['Release date'], format='%b %d, %Y', errors='coerce')

# ─────────────────────────────────────────────
# 8. 검증 및 저장
# ─────────────────────────────────────────────
remaining = df.isnull().sum().sum()
print(f"정제 완료: {len(df):,}행 * {len(df.columns)}열 | 잔여 결측치: {remaining}개")

df.to_csv('code/games_cleaned.csv', index=False)
print("저장 완료: code/games_cleaned.csv")