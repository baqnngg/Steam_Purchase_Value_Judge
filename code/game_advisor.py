import pandas as pd
import math
import urllib.request
import urllib.parse
import json


# ─────────────────────────────────────────────────────────
# DataLoader
# ─────────────────────────────────────────────────────────
class DataLoader:
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.df = None

    def load(self):
        raw = pd.read_csv(self.filepath, low_memory=False)
        raw['AppID_num'] = raw.index.astype(str)
        df = raw.reset_index(drop=True)
        self.df = self._clean(df)
        return self.df

    def _clean(self, df):
        df = df.drop(columns=['Movies', 'Score rank'], errors='ignore')
        df = df.dropna(subset=['AppID'])

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
# Game
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
            name             = str(row.get('AppID', '알 수 없음')),
            release_date     = str(row.get('Name', '')),
            price            = sf(row.get('Required age', 0)),
            positive         = si(row.get('Positive', 0)),
            negative         = si(row.get('Negative', 0)),
            playtime_forever = si(row.get('Average playtime forever', 0)),
            peak_ccu         = si(row.get('Estimated owners', 0)),
            recommendations  = si(row.get('Recommendations', 0)),
            metacritic_score = si(row.get('Metacritic score', 0)),
            achievements     = si(row.get('Achievements', 0)),
            genres           = str(row.get('Genres', '')),
            developers       = str(row.get('Developers', '')),
        )

    def __repr__(self):
        return f"Game({self.name!r}, ${self.price:.2f})"


# ─────────────────────────────────────────────────────────
# SteamReviewFetcher
# ─────────────────────────────────────────────────────────
class SteamReviewFetcher:
    SEARCH_URL = "https://store.steampowered.com/api/storesearch/?term={}&l=english&cc=US"
    REVIEW_URL = "https://store.steampowered.com/appreviews/{}?json=1&language=all&purchase_type=all"

    def _get(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())

    def resolve_appid(self, game_name: str):
        try:
            encoded = urllib.parse.quote(game_name)
            data = self._get(self.SEARCH_URL.format(encoded))
            items = data.get("items", [])
            if items:
                return str(items[0]["id"])
        except Exception:
            pass
        return None

    def fetch_reviews(self, app_id: str):
        try:
            data = self._get(self.REVIEW_URL.format(app_id))
            summary = data.get("query_summary", {})
            return {
                "positive": summary.get("total_positive", 0),
                "negative": summary.get("total_negative", 0),
            }
        except Exception:
            return None

    def apply(self, game):
        app_id = self.resolve_appid(game.name)
        if not app_id:
            return False, None
        reviews = self.fetch_reviews(app_id)
        if reviews:
            game.positive = reviews["positive"]
            game.negative = reviews["negative"]
            return True, app_id
        return False, None


# ─────────────────────────────────────────────────────────
# GenreBonus — 장르 인기도 점수 산출
# ─────────────────────────────────────────────────────────
class GenreBonus:
    TIER_S = {'action', 'rpg', 'adventure', 'strategy', 'indie'}
    TIER_A = {'simulation', 'sports', 'casual', 'racing', 'massively multiplayer'}
    TIER_B = {'early access', 'free to play', 'puzzle', 'platformer', 'shooter'}
    TIER_C = {
        'education', 'animation & modeling', 'utilities', 'video production',
        'audio production', 'photo editing', 'software training', 'accounting'
    }

    TIER_BONUS = {'S': 10, 'A': 7, 'B': 4, 'C': 1}

    def calculate(self, genres_str: str):
        if not genres_str or genres_str.lower() in ('', 'unknown', 'nan'):
            return 0.0, '미분류', None

        genres = [g.strip().lower() for g in genres_str.split(',')]

        best_tier = None
        best_bonus = 0.0
        matched_genre = None

        for genre in genres:
            if genre in self.TIER_S:
                tier, bonus = 'S', self.TIER_BONUS['S']
            elif genre in self.TIER_A:
                tier, bonus = 'A', self.TIER_BONUS['A']
            elif genre in self.TIER_B:
                tier, bonus = 'B', self.TIER_BONUS['B']
            elif genre in self.TIER_C:
                tier, bonus = 'C', self.TIER_BONUS['C']
            else:
                tier, bonus = None, 0

            if bonus > best_bonus:
                best_bonus = bonus
                best_tier = tier
                matched_genre = genre

        if best_tier is None:
            return 0.0, '미분류', None

        return float(best_bonus), best_tier, matched_genre


# ─────────────────────────────────────────────────────────
# ScoreResult
# ─────────────────────────────────────────────────────────
class ScoreResult:
    def __init__(self, review, value, popularity, genre, genre_tier, genre_matched):
        self.review        = review        # 0 ~ 40
        self.value         = value         # 0 ~ 30
        self.popularity    = popularity    # 0 ~ 20
        self.genre         = genre         # 0 ~ 10
        self.genre_tier    = genre_tier    # 'S'/'A'/'B'/'C'/'미분류'
        self.genre_matched = genre_matched # 점수 기준이 된 장르명

    def total(self):
        return self.review + self.value + self.popularity + self.genre


# ─────────────────────────────────────────────────────────
# Scorer (가성비 모델 반영 버전)
# ─────────────────────────────────────────────────────────
class Scorer:
    def __init__(self, df):
        self.weights = {'review': 40, 'value': 30, 'popularity': 20, 'genre': 10}
        self.genre_calc = GenreBonus()
        self.genre_avg_prices = self._calculate_genre_avg_prices(df)

    def _calculate_genre_avg_prices(self, df):
        price_col = 'Required age' if 'Required age' in df.columns else 'Price'
        temp_df = df[[price_col, 'Genres']].copy()
        temp_df[price_col] = pd.to_numeric(temp_df[price_col], errors='coerce').fillna(0.0)
        
        temp_df['Genre_List'] = temp_df['Genres'].fillna('Unknown').str.split(',')
        exploded = temp_df.explode('Genre_List')
        exploded['Genre_List'] = exploded['Genre_List'].str.strip().str.lower()
        
        return exploded.groupby('Genre_List')[price_col].mean().to_dict()

    def _get_game_genre_avg_price(self, genres_str):
        if not genres_str or genres_str.lower() in ('', 'unknown', 'nan'):
            return self.genre_avg_prices.get('unknown', 0.0)
        
        genres = [g.strip().lower() for g in genres_str.split(',')]
        prices = [self.genre_avg_prices.get(g, 0.0) for g in genres if g in self.genre_avg_prices]
        
        if not prices:
            return 0.0
        return sum(prices) / len(prices)

    def score(self, game):
        genre_score, tier, matched = self.genre_calc.calculate(game.genres)
        return ScoreResult(
            review        = self._review_score(game),
            value         = self._value_score(game),
            popularity    = self._popularity_score(game),
            genre         = genre_score,
            genre_tier    = tier,
            genre_matched = matched,
        )

    def _review_score(self, game):
        total = game.positive + game.negative
        if total < 10:
            return 0.0
        ratio_score = (game.positive / total) * 0.5
        VOL_REF = 10_000
        vol_score = min(math.log1p(total) / math.log1p(VOL_REF), 1.0) * 0.5
        return round((ratio_score + vol_score) * self.weights["review"], 2)

    # 💡 [핵심 수정] 3번 옵션: 가성비(만족도 반영) 모델 구현
    def _value_score(self, game):
        avg_price = self._get_game_genre_avg_price(game.genres)
        
        # 1. 만족도(긍정 리뷰 비율) 산출 (리뷰가 아예 없으면 기본 평점 50% 가정)
        total_reviews = game.positive + game.negative
        satisfaction_ratio = (game.positive / total_reviews) if total_reviews > 0 else 0.5
        
        # 2. 플레이 타임 가져오기 (시간 단위)
        hours = game.playtime_forever / 60
        if hours == 0:
            return 0.0

        # 3. 가성비 분자: 진짜 유저가 만족하며 보낸 '유효 플레이 타임'
        effective_hours = hours * satisfaction_ratio
        
        # 4. 무료 게임 예외 처리 (만족도가 높고 플레이했다면 만점 제공)
        if game.price == 0:
            return round(satisfaction_ratio * self.weights['value'], 2)
        
        # 5. 가성비 분모: 장르 평균가 대비 이 게임의 상대적 가격 비율
        price_ratio = game.price / avg_price if avg_price > 0 else 1.0
        
        # 6. 최종 가성비 계산 (유효 타임 기준선을 15시간으로 잡아 밸런싱)
        return round(min((effective_hours / price_ratio) / 15.0, 1.0) * self.weights['value'], 2)

    def _popularity_score(self, game):
        ccu = min(math.log1p(game.peak_ccu) / math.log1p(100_000), 1.0)
        rec = min(math.log1p(game.recommendations) / math.log1p(50_000), 1.0)
        return round((ccu * 0.5 + rec * 0.5) * self.weights['popularity'], 2)


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
# Recommender
# ─────────────────────────────────────────────────────────
class Recommender:
    def __init__(self):
        self.thresholds = {'buy': 72, 'wait': 42}

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
    TIER_LABEL = {
        'S': 'S티어 (최고 인기)',
        'A': 'A티어 (높은 인기)',
        'B': 'B티어 (중간 인기)',
        'C': 'C티어 (낮은 인기)',
    }

    def print(self, game, result, verdict, verdict_msg):
        price_str = f"${game.price:.2f}" if game.price > 0 else "무료"
        hours = game.playtime_forever // 60
        total_rev = game.positive + game.negative
        ratio_str = (
            f"{game.positive / total_rev * 100:.0f}% 긍정 ({total_rev:,}개)"
            if total_rev >= 10 else "리뷰 없음"
        )

        if result.genre_tier and result.genre_tier != '미분류':
            tier_label = self.TIER_LABEL.get(result.genre_tier, result.genre_tier)
            genre_score_str = f"{result.genre:.0f}점  [{tier_label}]  ({result.genre_matched})"
        else:
            genre_score_str = f"0점  [미분류]"

        print()
        print("=" * 60)
        print(f"  {game.name}")
        print("=" * 60)
        print(f"  개발사      : {game.developers}")
        print(f"  장르        : {game.genres}")
        print(f"  출시일      : {game.release_date}")
        print(f"  가격        : {price_str}")
        print(f"  평균 플레이 : {hours}시간")
        print(f"  리뷰        : {ratio_str}")
        print("-" * 60)
        print(f"  리뷰 점수    {self._bar(result.review,     40)}  {result.review:5.1f} / 40")
        print(f"  가성비       {self._bar(result.value,      30)}  {result.value:5.1f} / 30")
        print(f"  인기도       {self._bar(result.popularity, 20)}  {result.popularity:5.1f} / 20")
        print(f"  장르 점수    {self._bar(result.genre,      10)}  {result.genre:5.1f} / 10")
        print("-" * 60)
        print(f"  최종 점수    {self._bar(result.total(),   100)}  {result.total():5.1f} / 100")
        print("=" * 60)
        print(f"  판정: {verdict_msg}")
        print("=" * 60)
        print()

    def _bar(self, value, max_val, width=16):
        filled = int(round(value / max_val * width))
        return "[" + "█" * filled + "░" * (width - filled) + "]"


# ─────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────
def main():
    print("\n  게임 살까 말까 판단기")
    print("─" * 36)

    print("데이터 로딩 중...", end=" ", flush=True)
    df = DataLoader(".\\games_cleaned.csv").load()
    print(f"완료 ({len(df):,}개 게임)\n")

    finder         = GameFinder(df)
    scorer         = Scorer(df)
    recommender    = Recommender()
    printer        = ReportPrinter()
    review_fetcher = SteamReviewFetcher()

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

        print("  Steam 실시간 리뷰 조회 중...", end=" ", flush=True)
        ok, resolved_id = review_fetcher.apply(game)
        if ok:
            print(f"완료 (AppID: {resolved_id})")
        else:
            print("실패 (CSV 데이터 사용)")

        result  = scorer.score(game)
        verdict = recommender.judge(result)
        printer.print(game, result, verdict, recommender.verdict_msg(verdict))


if __name__ == "__main__":
    main()