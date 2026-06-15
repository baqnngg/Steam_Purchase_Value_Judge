import pandas as pd
import math


# ─────────────────────────────────────────────────────────
# DataLoader
# ─────────────────────────────────────────────────────────
class DataLoader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = None

    def load(self):
        raw = pd.read_csv(self.filepath, low_memory=False)
        raw['AppID_num'] = raw.index.astype(str)   # 실제 AppID 숫자 보존
        df = raw.reset_index(drop=True)
        self.df = self._clean(df)
        return self.df

    def _clean(self, df):
        df = df.drop(columns=['Movies', 'Score rank'], errors='ignore')
        df = df.dropna(subset=['AppID'])  # 'AppID' = 실제 Name

        for col in ['Developers', 'Publishers', 'Categories', 'Genres']:
            if col in df.columns:
                df[col] = df[col].fillna('Unknown')

        for col in ['Reviews', 'Metacritic url', 'Notes', 'Website', 'Support url',
                    'Support email', 'About the game', 'Screenshots', 'Header image',
                    'Tags', 'Supported languages', 'Full audio languages']:
            if col in df.columns:
                df[col] = df[col].fillna('')

        return df


# ─────────────────────────────────────────────────────────
# Game — 도메인 모델
# ─────────────────────────────────────────────────────────
class Game:
    def __init__(self, app_id, name, price, positive, negative,
                 playtime_forever, peak_ccu, recommendations,
                 metacritic_score, achievements, genres, developers, release_date):
        self.app_id = app_id
        self.name = name
        self.price = price
        self.positive = positive
        self.negative = negative
        self.playtime_forever = playtime_forever
        self.peak_ccu = peak_ccu
        self.recommendations = recommendations
        self.metacritic_score = metacritic_score
        self.achievements = achievements
        self.genres = genres
        self.developers = developers
        self.release_date = release_date

    @classmethod
    def from_row(cls, row):
        def si(v, d=0):
            try: return int(float(v))
            except: return d

        def sf(v, d=0.0):
            try: return float(v)
            except: return d

        return cls(
            app_id           = str(row.get('AppID_num', '')),
            name             = str(row.get('AppID', '알 수 없음')),   # shift: AppID = Name
            release_date     = str(row.get('Name', '')),              # shift: Name = Release date
            price            = sf(row.get('Required age', 0)),        # shift: Required age = Price
            positive         = si(row.get('Positive', 0)),
            negative         = si(row.get('Negative', 0)),
            playtime_forever = si(row.get('Average playtime forever', 0)),
            peak_ccu         = si(row.get('Estimated owners', 0)),    # shift: Estimated owners = Peak CCU
            recommendations  = si(row.get('Recommendations', 0)),
            metacritic_score = si(row.get('Metacritic score', 0)),
            achievements     = si(row.get('Achievements', 0)),
            genres           = str(row.get('Genres', '')),
            developers       = str(row.get('Developers', '')),
        )

    def __repr__(self):
        return f"Game({self.name!r}, ${self.price:.2f})"


# ─────────────────────────────────────────────────────────
# GameFinder
# ─────────────────────────────────────────────────────────
class GameFinder:
    def __init__(self, df):
        self.df = df

    def find(self, query):
        mask = self.df['AppID'].str.contains(query, case=False, na=False)
        return [Game.from_row(row) for _, row in self.df[mask].head(10).iterrows()]

    def find_by_id(self, app_id):
        mask = self.df['AppID_num'] == str(app_id)
        rows = self.df[mask]
        return None if rows.empty else Game.from_row(rows.iloc[0])


# ─────────────────────────────────────────────────────────
# ScoreResult
# ─────────────────────────────────────────────────────────
class ScoreResult:
    def __init__(self, review, value, popularity, quality):
        self.review     = review      # 0~40
        self.value      = value       # 0~30
        self.popularity = popularity  # 0~20
        self.quality    = quality     # 0~10

    def total(self):
        return self.review + self.value + self.popularity + self.quality


# ─────────────────────────────────────────────────────────
# Scorer
# ─────────────────────────────────────────────────────────
class Scorer:
    def __init__(self):
        self.weights = {'review': 40, 'value': 30, 'popularity': 20, 'quality': 10}

    def score(self, game):
        return ScoreResult(
            review     = self._review_score(game),
            value      = self._value_score(game),
            popularity = self._popularity_score(game),
            quality    = self._quality_score(game),
        )

    def _review_score(self, game):
        total = game.positive + game.negative
        if total < 10:
            return 0.0
        return round(game.positive / total * self.weights['review'], 2)

    def _value_score(self, game):
        if game.price == 0:
            return self.weights['value'] if game.playtime_forever > 0 else 0.0
        hours = game.playtime_forever / 60
        if hours == 0:
            return 0.0
        return round(min(hours / game.price / 10.0, 1.0) * self.weights['value'], 2)

    def _popularity_score(self, game):
        ccu = min(math.log1p(game.peak_ccu) / math.log1p(100_000), 1.0)
        rec = min(math.log1p(game.recommendations) / math.log1p(50_000), 1.0)
        return round((ccu * 0.5 + rec * 0.5) * self.weights['popularity'], 2)

    def _quality_score(self, game):
        if game.metacritic_score > 0:
            return round(game.metacritic_score / 100 * self.weights['quality'], 2)
        return round(min(game.achievements / 50, 1.0) * 0.5 * self.weights['quality'], 2)


# ─────────────────────────────────────────────────────────
# Recommender
# ─────────────────────────────────────────────────────────
class Recommender:
    def __init__(self):
        self.thresholds = {'buy': 70, 'wait': 40}

    def judge(self, result):
        t = result.total()
        if t >= self.thresholds['buy']:  return 'BUY'
        if t >= self.thresholds['wait']: return 'WAIT'
        return 'PASS'

    def verdict_msg(self, verdict):
        return {
            'BUY':  '✓  구매 추천 — 지금 사세요!',
            'WAIT': '△  할인 대기 — 세일 때 구매 고려',
            'PASS': '✗  비추천 — 이 게임은 넘기세요',
        }.get(verdict, '알 수 없음')


# ─────────────────────────────────────────────────────────
# ReportPrinter
# ─────────────────────────────────────────────────────────
class ReportPrinter:
    def print(self, game, result, verdict, verdict_msg):
        price_str = f"${game.price:.2f}" if game.price > 0 else "무료"
        hours = game.playtime_forever // 60
        total_rev = game.positive + game.negative
        ratio_str = (
            f"{game.positive / total_rev * 100:.0f}% 긍정 ({total_rev:,}개)"
            if total_rev >= 10 else "리뷰 없음"
        )
        print()
        print("=" * 56)
        print(f"  {game.name}")
        print("=" * 56)
        print(f"  개발사      : {game.developers}")
        print(f"  장르        : {game.genres}")
        print(f"  출시일      : {game.release_date}")
        print(f"  가격        : {price_str}")
        print(f"  평균 플레이 : {hours}시간")
        print(f"  리뷰        : {ratio_str}")
        print("-" * 56)
        print(f"  리뷰 점수    {self._bar(result.review,    40)}  {result.review:5.1f} / 40")
        print(f"  가성비       {self._bar(result.value,     30)}  {result.value:5.1f} / 30")
        print(f"  인기도       {self._bar(result.popularity,20)}  {result.popularity:5.1f} / 20")
        print(f"  완성도       {self._bar(result.quality,   10)}  {result.quality:5.1f} / 10")
        print("-" * 56)
        print(f"  종합 점수    {self._bar(result.total(), 100)}  {result.total():5.1f} / 100")
        print("=" * 56)
        print(f"  판정: {verdict_msg}")
        print("=" * 56)
        print()

    def _bar(self, value, max_val, width=16):
        filled = int(round(value / max_val * width))
        return "[" + "█" * filled + "░" * (width - filled) + "]"


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────
def main():
    print("\n  게임 살까 말까 판단기")
    print("─" * 32)

    print("데이터 로딩 중...", end=" ", flush=True)
    df = DataLoader("code/games_cleaned.csv").load()
    print(f"완료 ({len(df):,}개 게임)\n")

    finder      = GameFinder(df)
    scorer      = Scorer()
    recommender = Recommender()
    printer     = ReportPrinter()

    while True:
        print("게임 이름을 입력하세요 (종료: q)")
        query = input("  > ").strip()
        if query.lower() == 'q':
            print("종료합니다.")
            break
        if not query:
            continue

        results = finder.find(query)
        if not results:
            print("  검색 결과가 없습니다.\n")
            continue

        if len(results) == 1:
            game = results[0]
        else:
            print(f"\n  {len(results)}개 검색됨. 번호를 선택하세요:")
            for i, g in enumerate(results, 1):
                p = f"${g.price:.2f}" if g.price > 0 else "무료"
                print(f"  {i:2}. {g.name}  ({p})")
            try:
                game = results[int(input("  번호 > ").strip()) - 1]
            except (ValueError, IndexError):
                print("  잘못된 선택입니다.\n")
                continue

        result  = scorer.score(game)
        verdict = recommender.judge(result)
        printer.print(game, result, verdict, recommender.verdict_msg(verdict))


if __name__ == "__main__":
    main()