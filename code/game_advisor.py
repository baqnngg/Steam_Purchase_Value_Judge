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
# GenreBonus — 장르 인기도 가산점
# ─────────────────────────────────────────────────────────
class GenreBonus:
    """
    Steam 장르 인기도 기반 가산점 (최대 +10점)
    
    S티어 (+10): 현재 Steam에서 가장 인기 있는 장르
    A티어 (+7) : 꾸준히 높은 수요를 가진 장르
    B티어 (+4) : 중간 수준 인기 장르
    C티어 (+1) : 비교적 낮은 수요 장르
    미분류(+0) : 위 티어에 해당 없음
    """

    TIER_S = {
        'action', 'rpg', 'adventure', 'strategy', 'indie'
    }
    TIER_A = {
        'simulation', 'sports', 'casual', 'racing', 'massively multiplayer'
    }
    TIER_B = {
        'early access', 'free to play', 'puzzle', 'platformer', 'shooter'
    }
    TIER_C = {
        'education', 'animation & modeling', 'utilities', 'video production',
        'audio production', 'photo editing', 'software training', 'accounting'
    }

    TIER_BONUS = {
        'S': 10,
        'A': 7,
        'B': 4,
        'C': 1,
    }

    def calculate(self, genres_str: str):
        """
        게임의 장르 문자열을 받아 최고 티어 가산점을 반환.
        여러 장르가 있을 경우 가장 높은 티어 점수 적용.
        """
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
    def __init__(self, review, value, popularity, genre_bonus, genre_tier, genre_matched):
        self.review        = review        # 0~40
        self.value         = value         # 0~35
        self.popularity    = popularity    # 0~25
        self.genre_bonus   = genre_bonus   # 0~10 (가산점)
        self.genre_tier    = genre_tier    # 'S'/'A'/'B'/'C'/'미분류'
        self.genre_matched = genre_matched # 가산점 기준이 된 장르명

    def base_total(self):
        """기본 점수 합계 (100점 만점)"""
        return self.review + self.value + self.popularity

    def total(self):
        """장르 가산점 포함 최종 점수 (최대 110점)"""
        return self.base_total() + self.genre_bonus


# ─────────────────────────────────────────────────────────
# Scorer
# ─────────────────────────────────────────────────────────
class Scorer:
    def __init__(self):
        # 기본 배점: 리뷰 40 + 가성비 35 + 인기도 25 = 100
        self.weights = {'review': 40, 'value': 35, 'popularity': 25}
        self.genre_bonus_calc = GenreBonus()

    def score(self, game):
        bonus, tier, matched = self.genre_bonus_calc.calculate(game.genres)
        return ScoreResult(
            review        = self._review_score(game),
            value         = self._value_score(game),
            popularity    = self._popularity_score(game),
            genre_bonus   = bonus,
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
    # 장르 가산점 포함 기준 (최대 110점)
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

        # 장르 가산점 표시 문자열
        if result.genre_tier and result.genre_tier != '미분류':
            tier_label = self.TIER_LABEL.get(result.genre_tier, result.genre_tier)
            genre_bonus_str = (
                f"+{result.genre_bonus:.0f}점  [{tier_label}]  ({result.genre_matched})"
            )
        else:
            genre_bonus_str = f"+0점  [미분류]"

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
        print(f"  가성비       {self._bar(result.value,      35)}  {result.value:5.1f} / 35")
        print(f"  인기도       {self._bar(result.popularity, 25)}  {result.popularity:5.1f} / 25")
        print("-" * 60)
        print(f"  기본 점수    {self._bar(result.base_total(), 100)}  {result.base_total():5.1f} / 100")
        print(f"  장르 가산점  {genre_bonus_str}")
        print(f"  최종 점수    {self._bar(result.total(), 110)}  {result.total():5.1f} / 110")
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
    print("─" * 32)

    print("데이터 로딩 중...", end=" ", flush=True)
    df = DataLoader(".\\games_cleaned.csv").load()
    print(f"완료 ({len(df):,}개 게임)\n")

    finder         = GameFinder(df)
    scorer         = Scorer()
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