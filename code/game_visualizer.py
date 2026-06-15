"""
게임 살까 말까 판단기 — 시각화 모듈
game_advisor.py와 같은 폴더에 두고 실행하세요.
출력: game_dashboard.png
"""

import math
import warnings
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
from matplotlib.patches import FancyBboxPatch
import pandas as pd

warnings.filterwarnings("ignore")

# ── 한글 폰트 자동 설정 (Windows / macOS / Linux 공통) ──────
import os, sys, matplotlib.font_manager as _fm

def _setup_korean_font():
    """OS별 한글 폰트를 자동으로 찾아 matplotlib에 등록."""

    # 1) 스크립트 옆에 OTF를 직접 놓은 경우 (배포 시 권장)
    _here = os.path.dirname(os.path.abspath(__file__))
    _bundled = os.path.join(_here, "NotoSansCJKKR-Regular.otf")
    if os.path.exists(_bundled):
        _fm.fontManager.addfont(_bundled)
        return "Noto Sans CJK KR"

    # 2) OS별 후보 폰트 (설치되어 있으면 바로 사용)
    _candidates = []
    if sys.platform == "win32":
        _win = os.environ.get("WINDIR", "C:/Windows")
        _candidates = [
            # 맑은 고딕 (Windows 기본 한글 폰트)
            os.path.join(_win, "Fonts", "malgun.ttf"),
            os.path.join(_win, "Fonts", "malgunbd.ttf"),
            # NanumGothic (설치한 경우)
            os.path.join(_win, "Fonts", "NanumGothic.ttf"),
        ]
        _name_map = {
            "malgun.ttf":    "Malgun Gothic",
            "malgunbd.ttf":  "Malgun Gothic",
            "NanumGothic.ttf": "NanumGothic",
        }
    elif sys.platform == "darwin":
        _candidates = [
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",
            "/Library/Fonts/NanumGothic.ttf",
        ]
        _name_map = {
            "AppleSDGothicNeo.ttc": "Apple SD Gothic Neo",
            "NanumGothic.ttf":      "NanumGothic",
        }
    else:  # Linux
        _candidates = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        ]
        _name_map = {
            "NanumGothic.ttf":           "NanumGothic",
            "NotoSansCJK-Regular.ttc":   None,  # TTC 추출 필요
        }

    for path in _candidates:
        if not os.path.exists(path):
            continue
        fname = os.path.basename(path)

        # Linux의 TTC는 KR 서브폰트(index 1) 추출
        if path.endswith(".ttc") and sys.platform != "darwin":
            try:
                from fontTools.ttLib import TTCollection
                otf_out = os.path.join(_here, "NotoSansCJKKR-Regular.otf")
                if not os.path.exists(otf_out):
                    ttc = TTCollection(path)
                    ttc.fonts[1].save(otf_out)
                _fm.fontManager.addfont(otf_out)
                return "Noto Sans CJK KR"
            except Exception:
                continue

        _fm.fontManager.addfont(path)
        mapped = _name_map.get(fname)
        if mapped:
            return mapped

    # 3) 시스템에 등록된 폰트에서 한글 지원 폰트 검색
    _ko_keywords = ["Malgun", "Gothic", "Gulim", "Dotum", "Batang",
                    "Nanum", "Apple SD", "Noto Sans CJK"]
    for f in _fm.fontManager.ttflist:
        if any(k.lower() in f.name.lower() for k in _ko_keywords):
            return f.name

    # 4) 최후 수단: DejaVu (한글 깨지지만 에러는 막음)
    print("[경고] 한글 폰트를 찾지 못했습니다. 한글이 깨질 수 있습니다.")
    return "DejaVu Sans"

_KO_FONT = _setup_korean_font()
matplotlib.rcParams['font.family'] = _KO_FONT
matplotlib.rcParams['axes.unicode_minus'] = False

from game_advisor import DataLoader, GameFinder, Scorer, Recommender, Game, ScoreResult

# ─── 팔레트 ───────────────────────────────────────────────
BG      = "#0f1117"
PANEL   = "#1a1d27"
BORDER  = "#2a2d3a"
ACCENT  = "#7c6af7"    # 보라
GREEN   = "#3dcf8e"
AMBER   = "#f5a623"
RED     = "#e05c5c"
MUTED   = "#6b7280"
WHITE   = "#e8e8f0"
LBLUE   = "#5ba4f5"

VERDICT_COLOR = {"BUY": GREEN, "WAIT": AMBER, "PASS": RED}

# ─── 분석 대상 게임 ────────────────────────────────────────
TARGET_GAMES = [
    "Stardew Valley",
    "Hollow Knight",
    "Counter-Strike 2",
    "Cyberpunk 2077",
    "Terraria",
    "^Hades$",
    "DOOM Eternal",
    "Celeste",
]


def load_data():
    print("데이터 로딩 중...", end=" ", flush=True)
    df = DataLoader("code/games_cleaned.csv").load()
    print(f"완료 ({len(df):,}개)")
    return df


def compute_scores(df, game_names):
    finder = GameFinder(df)
    scorer = Scorer()
    recommender = Recommender()
    rows = []
    for name in game_names:
        results = finder.find(name)
        if not results:
            continue
        g = next((x for x in results if x.name == name), results[0])
        r = scorer.score(g)
        v = recommender.judge(r)
        rows.append({
            "name":       g.name,
            "price":      g.price,
            "playtime_h": g.playtime_forever / 60,
            "positive":   g.positive,
            "negative":   g.negative,
            "pos_ratio":  g.positive / max(g.positive + g.negative, 1),
            "review":     r.review,
            "value":      r.value,
            "popularity": r.popularity,
            "quality":    r.quality,
            "total":      r.total(),
            "verdict":    v,
        })
    return pd.DataFrame(rows).sort_values("total", ascending=False)


def compute_distribution(df):
    """리뷰 1000개 이상 게임의 전체 점수 분포"""
    scorer = Scorer()
    df2 = df.copy()
    df2["_pos"] = pd.to_numeric(df2["Positive"], errors="coerce").fillna(0)
    df2["_neg"] = pd.to_numeric(df2["Negative"], errors="coerce").fillna(0)
    df2["_total_rev"] = df2["_pos"] + df2["_neg"]
    df2["_price"]    = pd.to_numeric(df2["Required age"], errors="coerce").fillna(0)
    df2["_playtime"] = pd.to_numeric(df2["Average playtime forever"], errors="coerce").fillna(0)
    df2["_ccu"]      = pd.to_numeric(df2["Estimated owners"], errors="coerce").fillna(0)
    df2["_recs"]     = pd.to_numeric(df2["Recommendations"], errors="coerce").fillna(0)
    df2["_meta"]     = pd.to_numeric(df2["Metacritic score"], errors="coerce").fillna(0)
    df2["_ach"]      = pd.to_numeric(df2["Achievements"], errors="coerce").fillna(0)

    filtered = df2[df2["_total_rev"] >= 1000].copy()

    totals = []
    for _, row in filtered.iterrows():
        pos = row["_pos"]; neg = row["_neg"]; total_rev = pos + neg
        if total_rev < 10: rev_s = 0
        else: rev_s = pos / total_rev * 40

        price = row["_price"]; pt = row["_playtime"]
        if price == 0: val_s = 30 if pt > 0 else 0
        else:
            hours = pt / 60
            val_s = min(hours / price / 10.0, 1.0) * 30 if hours > 0 else 0

        ccu = min(math.log1p(row["_ccu"]) / math.log1p(100_000), 1.0)
        rec = min(math.log1p(row["_recs"]) / math.log1p(50_000), 1.0)
        pop_s = (ccu * 0.5 + rec * 0.5) * 20

        meta = row["_meta"]
        qual_s = (meta / 100 * 10) if meta > 0 else min(row["_ach"] / 50, 1.0) * 0.5 * 10

        totals.append(rev_s + val_s + pop_s + qual_s)

    return np.array(totals), filtered


# ─── 그리기 ───────────────────────────────────────────────

def draw(scores_df: pd.DataFrame, dist: np.ndarray):
    fig = plt.figure(figsize=(18, 13), facecolor=BG)
    fig.subplots_adjust(left=0.05, right=0.97, top=0.93, bottom=0.06,
                        hspace=0.55, wspace=0.35)

    gs = gridspec.GridSpec(3, 3, figure=fig,
                           height_ratios=[1.1, 1.1, 1])

    # 제목
    fig.text(0.5, 0.965, "Steam 게임 살까 말까 판단기 — 데이터 대시보드",
             ha="center", fontsize=17, color=WHITE, fontweight="bold")
    fig.text(0.5, 0.945, f"분석 대상 {len(scores_df)}개 게임  ·  전체 데이터 {len(dist):,}개 기준",
             ha="center", fontsize=10, color=MUTED)

    # ── 1. 종합 점수 순위 바 차트 ───────────────────────
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.set_facecolor(PANEL)
    for spine in ax1.spines.values(): spine.set_color(BORDER)

    names  = scores_df["name"].tolist()
    totals = scores_df["total"].tolist()
    verdicts = scores_df["verdict"].tolist()
    colors = [VERDICT_COLOR[v] for v in verdicts]
    y = np.arange(len(names))

    bars = ax1.barh(y, totals, color=colors, height=0.6,
                    alpha=0.9, edgecolor="none")
    # 배경 트랙
    ax1.barh(y, [100]*len(y), color=BORDER, height=0.6,
             alpha=0.4, edgecolor="none", zorder=0)

    for i, (bar, val, name, verdict) in enumerate(zip(bars, totals, names, verdicts)):
        ax1.text(val + 1.5, i, f"{val:.1f}", va="center",
                 color=VERDICT_COLOR[verdict], fontsize=9.5, fontweight="bold")
        ax1.text(-1, i, name, va="center", ha="right",
                 color=WHITE, fontsize=9)

    ax1.set_xlim(-2, 108)
    ax1.set_yticks([]); ax1.set_xticks([])
    ax1.axvline(70, color=GREEN, lw=1, ls="--", alpha=0.5)
    ax1.axvline(40, color=AMBER, lw=1, ls="--", alpha=0.5)
    ax1.text(70.5, -0.8, "구매(70)", color=GREEN, fontsize=7.5, alpha=0.8)
    ax1.text(40.5, -0.8, "대기(40)", color=AMBER, fontsize=7.5, alpha=0.8)
    ax1.set_title("종합 점수 순위", color=WHITE, fontsize=11,
                  pad=8, loc="left", fontweight="bold")

    legend_items = [
        mpatches.Patch(color=GREEN, label="구매 추천 (70+)"),
        mpatches.Patch(color=AMBER, label="할인 대기 (40–69)"),
        mpatches.Patch(color=RED,   label="비추천 (40 미만)"),
    ]
    ax1.legend(handles=legend_items, loc="lower right",
               framealpha=0, fontsize=8, labelcolor=WHITE)

    # ── 2. 레이더 차트 (상위 4개 게임) ─────────────────
    ax2 = fig.add_subplot(gs[0, 2], polar=True)
    ax2.set_facecolor(PANEL)

    cats = ["리뷰\n점수", "가성비", "인기도", "완성도"]
    maxv = [40, 30, 20, 10]
    N = len(cats)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    radar_colors = [ACCENT, GREEN, LBLUE, AMBER]
    top4 = scores_df.head(4)
    for i, (_, row) in enumerate(top4.iterrows()):
        vals = [row["review"]/maxv[0], row["value"]/maxv[1],
                row["popularity"]/maxv[2], row["quality"]/maxv[3]]
        vals += vals[:1]
        ax2.plot(angles, vals, color=radar_colors[i], lw=1.5, alpha=0.9)
        ax2.fill(angles, vals, color=radar_colors[i], alpha=0.08)

    ax2.set_xticks(angles[:-1])
    ax2.set_xticklabels(cats, color=WHITE, fontsize=8.5)
    ax2.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax2.set_yticklabels(["25%","50%","75%","100%"],
                         color=MUTED, fontsize=6.5)
    ax2.grid(color=BORDER, lw=0.8)
    ax2.spines["polar"].set_color(BORDER)
    ax2.set_facecolor(PANEL)
    ax2.set_title("상위 4개 지표 비교", color=WHITE, fontsize=10,
                  pad=14, fontweight="bold")

    radar_leg = [mpatches.Patch(color=radar_colors[i],
                                label=top4.iloc[i]["name"].split(":")[0][:14])
                 for i in range(len(top4))]
    ax2.legend(handles=radar_leg, loc="lower left", bbox_to_anchor=(-0.25, -0.15),
               framealpha=0, fontsize=7.5, labelcolor=WHITE, ncol=2)

    # ── 3. 지표별 스택 바 (100% 기준) ─────────────────
    ax3 = fig.add_subplot(gs[1, :2])
    ax3.set_facecolor(PANEL)
    for spine in ax3.spines.values(): spine.set_color(BORDER)

    cats2 = ["리뷰(40)", "가성비(30)", "인기도(20)", "완성도(10)"]
    keys  = ["review", "value", "popularity", "quality"]
    stk_colors = [ACCENT, GREEN, LBLUE, AMBER]
    names2 = scores_df["name"].tolist()
    y2 = np.arange(len(names2))
    left = np.zeros(len(names2))

    for key, color, cat in zip(keys, stk_colors, cats2):
        vals2 = scores_df[key].values
        ax3.barh(y2, vals2, left=left, color=color,
                 height=0.55, alpha=0.85, edgecolor="none", label=cat)
        left += vals2

    ax3.set_xlim(0, 108)
    ax3.set_yticks(y2)
    ax3.set_yticklabels(names2, color=WHITE, fontsize=8.5)
    ax3.set_xticks([])
    for spine in ["top","right","bottom"]: ax3.spines[spine].set_visible(False)
    ax3.legend(loc="lower right", framealpha=0, fontsize=8,
               labelcolor=WHITE, ncol=4)
    ax3.set_title("지표별 점수 구성", color=WHITE, fontsize=11,
                  pad=8, loc="left", fontweight="bold")

    # ── 4. 전체 점수 분포 히스토그램 ──────────────────
    ax4 = fig.add_subplot(gs[1, 2])
    ax4.set_facecolor(PANEL)
    for spine in ax4.spines.values(): spine.set_color(BORDER)

    bins = np.linspace(0, 100, 26)
    n, edges, patches = ax4.hist(dist, bins=bins, color=ACCENT,
                                  alpha=0.7, edgecolor=PANEL, lw=0.4)
    for patch, left_edge in zip(patches, edges[:-1]):
        if left_edge >= 70:   patch.set_facecolor(GREEN)
        elif left_edge >= 40: patch.set_facecolor(AMBER)
        else:                 patch.set_facecolor(RED)

    # 분석 게임들 위치 표시
    for _, row in scores_df.iterrows():
        ax4.axvline(row["total"], color=WHITE, lw=0.8, ls=":", alpha=0.6)

    ax4.axvline(70, color=GREEN, lw=1.2, ls="--", alpha=0.7)
    ax4.axvline(40, color=AMBER, lw=1.2, ls="--", alpha=0.7)

    pct_buy  = (dist >= 70).mean() * 100
    pct_wait = ((dist >= 40) & (dist < 70)).mean() * 100
    pct_pass = (dist < 40).mean() * 100

    ax4.text(85, n.max()*0.88, f"구매\n{pct_buy:.0f}%", color=GREEN,
             fontsize=8, ha="center")
    ax4.text(55, n.max()*0.88, f"대기\n{pct_wait:.0f}%", color=AMBER,
             fontsize=8, ha="center")
    ax4.text(20, n.max()*0.88, f"비추\n{pct_pass:.0f}%", color=RED,
             fontsize=8, ha="center")

    ax4.set_xlabel("종합 점수", color=MUTED, fontsize=8)
    ax4.set_ylabel("게임 수",   color=MUTED, fontsize=8)
    ax4.tick_params(colors=MUTED, labelsize=7.5)
    ax4.set_title("전체 점수 분포\n(리뷰 1,000개+ 게임)", color=WHITE,
                  fontsize=10, pad=8, fontweight="bold")

    # ── 5. 가격 vs 긍정 비율 산점도 ───────────────────
    ax5 = fig.add_subplot(gs[2, 0])
    ax5.set_facecolor(PANEL)
    for spine in ax5.spines.values(): spine.set_color(BORDER)

    # 분석 게임 점 찍기
    for _, row in scores_df.iterrows():
        c = VERDICT_COLOR[row["verdict"]]
        ax5.scatter(row["price"], row["pos_ratio"]*100,
                    color=c, s=90, zorder=5, edgecolors=PANEL, lw=1)
        short = row["name"].split(":")[0][:12]
        ax5.annotate(short, (row["price"], row["pos_ratio"]*100),
                     xytext=(4, 2), textcoords="offset points",
                     color=WHITE, fontsize=6.5, alpha=0.9)

    ax5.set_xlabel("가격 ($)", color=MUTED, fontsize=8)
    ax5.set_ylabel("긍정 리뷰 비율 (%)", color=MUTED, fontsize=8)
    ax5.tick_params(colors=MUTED, labelsize=7.5)
    ax5.set_title("가격 vs 리뷰 평점", color=WHITE, fontsize=10,
                  pad=8, fontweight="bold")
    ax5.axhline(80, color=MUTED, lw=0.6, ls="--", alpha=0.4)
    ax5.text(0.5, 80.5, "80%", color=MUTED, fontsize=7)
    ax5.set_ylim(50, 102)

    # ── 6. 플레이타임 vs 종합점수 산점도 ──────────────
    ax6 = fig.add_subplot(gs[2, 1])
    ax6.set_facecolor(PANEL)
    for spine in ax6.spines.values(): spine.set_color(BORDER)

    for _, row in scores_df.iterrows():
        c = VERDICT_COLOR[row["verdict"]]
        ax6.scatter(row["playtime_h"], row["total"],
                    color=c, s=90, zorder=5, edgecolors=PANEL, lw=1)
        short = row["name"].split(":")[0][:12]
        ax6.annotate(short, (row["playtime_h"], row["total"]),
                     xytext=(4, 2), textcoords="offset points",
                     color=WHITE, fontsize=6.5, alpha=0.9)

    ax6.set_xlabel("평균 플레이타임 (시간)", color=MUTED, fontsize=8)
    ax6.set_ylabel("종합 점수", color=MUTED, fontsize=8)
    ax6.tick_params(colors=MUTED, labelsize=7.5)
    ax6.axhline(70, color=GREEN, lw=0.8, ls="--", alpha=0.5)
    ax6.axhline(40, color=AMBER, lw=0.8, ls="--", alpha=0.5)
    ax6.set_title("플레이타임 vs 종합 점수", color=WHITE, fontsize=10,
                  pad=8, fontweight="bold")

    # ── 7. 판정 파이 차트 ─────────────────────────────
    ax7 = fig.add_subplot(gs[2, 2])
    ax7.set_facecolor(PANEL)

    buy_n  = (scores_df["verdict"] == "BUY").sum()
    wait_n = (scores_df["verdict"] == "WAIT").sum()
    pass_n = (scores_df["verdict"] == "PASS").sum()

    sizes  = [buy_n, wait_n, pass_n]
    labels = [f"구매 추천\n{buy_n}개", f"할인 대기\n{wait_n}개", f"비추천\n{pass_n}개"]
    colors = [GREEN, AMBER, RED]
    explode = [0.04] * 3

    wedges, texts, autotexts = ax7.pie(
        sizes, labels=labels, colors=colors, explode=explode,
        autopct=lambda p: f"{p:.0f}%" if p > 0 else "",
        textprops={"color": WHITE, "fontsize": 8},
        wedgeprops={"edgecolor": PANEL, "linewidth": 1.5},
        startangle=90,
    )
    for at in autotexts:
        at.set_color(BG); at.set_fontsize(8.5); at.set_fontweight("bold")

    ax7.set_title("판정 분포", color=WHITE, fontsize=10,
                  pad=8, fontweight="bold")

    # 저장
    out = "game_dashboard.png"
    plt.savefig(out, dpi=160, bbox_inches="tight", facecolor=BG)
    print(f"\n저장 완료: {out}")
    plt.close()


def main():
    df = load_data()
    scores_df = compute_scores(df, TARGET_GAMES)
    dist, _ = compute_distribution(df)
    print("\n[점수 요약]")
    print(scores_df[["name","total","verdict"]].to_string(index=False))
    draw(scores_df, dist)


if __name__ == "__main__":
    main()
