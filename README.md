# 🎮 Steam 게임 살까 말까 판단기

Steam 게임 데이터(122,000+개)를 기반으로 **리뷰·가성비·인기도·완성도** 4가지 지표를 계산해
게임 구매 여부를 자동으로 판정하는 Python 프로젝트입니다.

---

## 📁 프로젝트 구조

```
project/
├── games.csv             # Steam 게임 원본 데이터
├── games_eda.py          # 1단계: 탐색적 데이터 분석 (EDA)
├── games_cleaning.py     # 2단계: 데이터 정제
├── game_advisor.py       # 3단계: 핵심 클래스 구현 (OOP)
├── game_visualizer.py    # 4단계: 시각화 대시보드
└── README.md
```

---

## 🚀 빠른 시작

### 요구 사항

```bash
pip install pandas matplotlib numpy
```

### 실행 순서

```bash
# 1. 데이터 구조 파악
python games_eda.py

# 2. 데이터 정제 (games_cleaned.csv 생성)
python games_cleaning.py

# 3. 게임 판단기 실행
python game_advisor.py

# 4. 시각화 대시보드 생성 (game_dashboard.png 생성)
python game_visualizer.py
```

---

## 🗂️ 단계별 설명

### 1단계 — 탐색적 데이터 분석 (`games_eda.py`)

`games.csv`를 Pandas로 로드해 데이터 구조를 파악합니다.

- 총 **122,611행 × 39열** 확인
- 컬럼별 데이터 타입 및 의미 정리
- 결측치 현황 분석 및 정제 계획 수립
- 정제 실행 후 잔여 결측치 **0개** 달성

| 컬럼 | 결측률 | 처리 방식 |
|------|--------|-----------|
| `Movies` | 100% | 컬럼 삭제 |
| `Score rank` | 99.97% | 컬럼 삭제 |
| `Reviews` | 90.16% | `fillna('')` |
| `Developers` | 6.88% | `fillna('Unknown')` |
| `AppID` | 0.001% | 해당 행 삭제 |

---

### 2단계 — 데이터 정제 (`games_cleaning.py`)

EDA 계획을 바탕으로 정제 파이프라인을 실행합니다.

```python
# 주요 정제 로직
df.drop(columns=['Movies', 'Score rank'])          # 불필요 컬럼 제거
df.dropna(subset=['AppID'])                         # PK 결측 행 제거
df[fill_unknown] = df[fill_unknown].fillna('Unknown')
df['Release date'] = pd.to_datetime(...)            # 타입 변환
```

정제 결과: **122,610행 × 37열**, 결측치 0개 → `games_cleaned.csv` 저장

---

### 3단계 — OOP 설계 및 구현 (`game_advisor.py`)

6개의 클래스로 구성된 객체지향 구조입니다.

```
DataLoader → GameFinder → Game → Scorer → ScoreResult → Recommender → ReportPrinter
```

#### 클래스 요약

| 클래스 | 역할 | 주요 메서드 |
|--------|------|-------------|
| `DataLoader` | CSV 로드 및 정제 | `load()` |
| `GameFinder` | 게임 이름/ID 검색 | `find(query)`, `find_by_id(id)` |
| `Game` | 게임 도메인 모델 | `from_row(row)` |
| `Scorer` | 4가지 지표 점수 계산 | `score(game) → ScoreResult` |
| `ScoreResult` | 점수 결과 객체 | `total()` |
| `Recommender` | 구매 판정 | `judge(result)`, `verdict_msg(verdict)` |
| `ReportPrinter` | 터미널 출력 | `print(game, result, verdict, msg)` |

#### 점수 계산 방식

| 지표 | 만점 | 계산식 |
|------|------|--------|
| 리뷰 점수 | 40점 | `긍정 / (긍정 + 부정) × 40` |
| 가성비 | 30점 | `플레이시간(h) / 가격($) / 10 × 30` (무료 게임 = 만점) |
| 인기도 | 20점 | `log(Peak CCU) + log(추천 수)` 정규화 |
| 완성도 | 10점 | 메타크리틱 점수 우선, 없으면 업적 수 보완 |

#### 판정 기준

| 판정 | 조건 | 메시지 |
|------|------|--------|
| ✓ 구매 추천 | 70점 이상 | 지금 사세요! |
| △ 할인 대기 | 40~69점 | 세일 때 구매 고려 |
| ✗ 비추천 | 40점 미만 | 이 게임은 넘기세요 |

#### 실행 예시

```
  게임 살까 말까 판단기
────────────────────────────────
데이터 로딩 중... 완료 (122,610개 게임)

게임 이름을 입력하세요 (종료: q)
  > Stardew Valley

========================================================
  Stardew Valley
========================================================
  개발사      : ConcernedApe
  장르        : Indie,RPG,Simulation
  출시일      : Feb 26, 2016
  가격        : $8.99
  평균 플레이 : 80시간
  리뷰        : 98% 긍정 (886,195개)
--------------------------------------------------------
  리뷰 점수    [████████████████]   39.4 / 40
  가성비       [██████████████░░]   26.9 / 30
  인기도       [████████████████]   19.4 / 20
  완성도       [██████████████░░]    8.9 / 10
--------------------------------------------------------
  종합 점수    [███████████████░]   94.6 / 100
========================================================
  판정: ✓  구매 추천 — 지금 사세요!
========================================================
```

---

### 4단계 — 시각화 (`game_visualizer.py`)

Matplotlib으로 7개 차트를 하나의 대시보드 이미지로 출력합니다.

| # | 차트 | 내용 |
|---|------|------|
| 1 | 종합 점수 순위 (가로 바) | 판정 색상으로 BUY/WAIT/PASS 구분 |
| 2 | 레이더 차트 | 상위 4개 게임 지표 비교 |
| 3 | 지표별 스택 바 | 리뷰·가성비·인기도·완성도 구성 비율 |
| 4 | 전체 점수 분포 히스토그램 | 리뷰 1,000개+ 전체 게임 7,206개 기준 |
| 5 | 가격 vs 리뷰 평점 산점도 | 가격과 평점의 관계 |
| 6 | 플레이타임 vs 종합점수 산점도 | 플레이타임과 총점의 관계 |
| 7 | 판정 분포 파이 차트 | BUY/WAIT/PASS 비율 |

분석 대상 게임을 바꾸려면 `game_visualizer.py` 상단의 `TARGET_GAMES` 리스트를 수정하세요.

```python
TARGET_GAMES = [
    "Stardew Valley",
    "Hollow Knight",
    "Counter-Strike 2",
    # 원하는 게임 이름 추가...
]
```

---

## 💡 주요 기술 노트

> **CSV 컬럼 구조 주의**
>
> `games.csv`는 Pandas로 읽을 때 첫 번째 컬럼인 `AppID`(숫자)가 자동으로 DataFrame index로
> 처리되어 나머지 컬럼이 한 칸씩 밀리는 구조를 가집니다.
> `DataLoader`가 `index`를 `AppID_num`으로 보존하고 `Game.from_row()`에서 실제 컬럼 위치를
> 명시적으로 매핑해 이 문제를 해결합니다.

---

## 📊 분석 결과 샘플

| 게임 | 종합 점수 | 판정 |
|------|-----------|------|
| Terraria | 96.1 | ✓ 구매 추천 |
| Stardew Valley | 94.6 | ✓ 구매 추천 |
| Counter-Strike 2 | 84.8 | ✓ 구매 추천 |
| Hades | 79.0 | ✓ 구매 추천 |
| Hollow Knight | 78.8 | ✓ 구매 추천 |
| Celeste | 77.8 | ✓ 구매 추천 |
| Cyberpunk 2077 | 72.9 | ✓ 구매 추천 |
| DOOM Eternal | 68.5 | △ 할인 대기 |

---

## 🔧 커스터마이징

**점수 가중치 변경** — `Scorer.__init__`의 `weights` 수정:

```python
self.weights = {
    'review':     40,   # 리뷰 비중 조정
    'value':      30,   # 가성비 비중 조정
    'popularity': 20,
    'quality':    10,
}
```

**판정 기준 변경** — `Recommender.__init__`의 `thresholds` 수정:

```python
self.thresholds = {'buy': 70, 'wait': 40}
```

---

## 📚 사용 데이터

- **출처**: Steam 게임 데이터셋 (`games.csv`)
- **규모**: 122,611개 게임, 39개 컬럼
- **주요 컬럼**: `Positive`, `Negative`, `Price`, `Average playtime forever`,
  `Peak CCU`, `Recommendations`, `Metacritic score`, `Achievements`
