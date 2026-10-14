"""법령 수치에서 위키 첨부 SVG를 생성한다. 수치를 손으로 옮기지 않고 아래 표에서 좌표를 계산한다.

사용법: python automation/publish/charts/make_charts.py
출력: wiki/attachments/*.svg (Obsidian과 HTML 학습본에서 함께 쓴다)
근거는 각 함수의 docstring과 그래프 하단 주석에 적는다.
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[3] / "wiki" / "attachments"
FONT = 'font-family="Pretendard, Apple SD Gothic Neo, Malgun Gothic, sans-serif"'
INK, SUB, GRID = "#1d2521", "#5f6b65", "#e3e1d9"
C1, C2 = "#c0702a", "#1f5f4a"


def svg(w, h, body, label):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-label="{label}">'
            f'<rect width="{w}" height="{h}" rx="16" fill="#ffffff"/>{body}</svg>\n')


def t(x, y, s, size=13, fill=SUB, anchor="start", weight=400):
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" font-weight="{weight}" {FONT}>{s}</text>'


# ------------------------------------------------------------------ 장기보유특별공제
def lthd():
    """소득세법 §95② 표1·표2 (2026-10-14 법제처 조문 대조).
    표1: 3년 이상 6% … 1년마다 2%p, 15년 이상 30%.
    표2: 보유 3년 12% … 1년마다 4%p, 10년 이상 40% + 거주 3년 12% … 10년 이상 40% (거주 2~3년 8%는 보유 3년 이상 한정).
    그래프의 표2 선은 '보유기간 = 거주기간'으로 가정한다."""
    t1 = lambda y: 0 if y < 3 else min(2 * y, 30)
    t2hold = lambda y: 0 if y < 3 else min(4 * y, 40)
    t2res = lambda y: 0 if y < 2 else (8 if y < 3 else min(4 * y, 40))
    t2 = lambda y: t2hold(y) + (t2res(y) if y >= 3 else 0)
    W, H, L, R, T, B = 1000, 500, 80, 960, 70, 420
    X = lambda y: L + (R - L) * y / 16
    Y = lambda p: B - (B - T) * p / 90
    b = [t(L, 36, "장기보유특별공제율: 표1(일반) vs 표2(1세대1주택)", 19, INK, weight=700)]
    for p in range(0, 91, 10):
        b.append(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{R}" y2="{Y(p):.1f}" stroke="{GRID}"/>')
        b.append(t(L - 10, Y(p) + 4, f"{p}%", 12, anchor="end"))
    for y in range(0, 17, 1):
        b.append(t(X(y), B + 20, str(y), 12, anchor="middle"))
    b.append(t((L + R) / 2, B + 44, "보유기간 (년) · 표2는 거주기간이 보유기간과 같다고 가정", 13, anchor="middle"))

    def step(f, color):
        pts = []
        for y in range(0, 16):
            pts += [(X(y), Y(f(y))), (X(y + 1), Y(f(y)))]
        d = "M" + " L".join(f"{x:.1f},{yv:.1f}" for x, yv in pts)
        return f'<path d="{d}" fill="none" stroke="{color}" stroke-width="4" stroke-linejoin="round"/>'
    b.append(step(t1, C1))
    b.append(step(t2, C2))
    for y, f, c, dy in ((3, t1, C1, 18), (10, t1, C1, 18), (15, t1, C1, -10), (3, t2, C2, -10), (10, t2, C2, -10)):
        b.append(f'<circle cx="{X(y):.1f}" cy="{Y(f(y)):.1f}" r="5" fill="{c}" stroke="#fff" stroke-width="2"/>')
        b.append(t(X(y) + 6, Y(f(y)) + dy, f"{y}년 {f(y)}%", 13, c, weight=700))
    b.append(f'<rect x="{L + 16}" y="92" width="14" height="5" fill="{C2}"/>' + t(L + 36, 99, "표2: 보유 4%p + 거주 4%p/년 (최대 80%)", 13, INK))
    b.append(f'<rect x="{L + 16}" y="114" width="14" height="5" fill="{C1}"/>' + t(L + 36, 121, "표1: 2%p/년 (최대 30%)", 13, INK))
    b.append(t(L, H - 12, "근거: 소득세법 §95② 표1·표2 (2026-10-14 법제처 대조). 3년 미만은 공제 없음. 표2 적용 요건은 본문 참조.", 11.5))
    return svg(W, H, "".join(b), "보유기간에 따른 장기보유특별공제율 표1과 표2 비교 계단 그래프")


# ------------------------------------------------------------------ 종합소득세 세율
BRACKETS = [(1400, 6), (5000, 15), (8800, 24), (15000, 35), (30000, 38), (50000, 40), (100000, 42), (None, 45)]


def income_tax(base):
    """소득세법 §55① 종합소득세 기본세율 (단위 만원)."""
    tax, prev = 0.0, 0
    for top, rate in BRACKETS:
        hi = base if top is None else min(base, top)
        if hi > prev:
            tax += (hi - prev) * rate / 100
        if top is None or base <= top:
            break
        prev = top
    return tax


def rates():
    # 조문의 누진 기준금액과 일치하는지 자체 확인(84, 624, 1,536, 3,706, 9,406, 17,406, 38,406만원)
    for base, want in ((1400, 84), (5000, 624), (8800, 1536), (15000, 3706), (30000, 9406), (50000, 17406), (100000, 38406)):
        assert abs(income_tax(base) - want) < 1e-6, (base, income_tax(base))
    W, H, L, R, T, B = 1000, 520, 80, 960, 70, 430
    lo, hi = math.log10(500), math.log10(200000)
    X = lambda v: L + (R - L) * (math.log10(v) - lo) / (hi - lo)
    Y = lambda p: B - (B - T) * p / 50
    b = [t(L, 36, "종합소득세 기본세율: 한계세율과 실효세율", 19, INK, weight=700)]
    for p in range(0, 51, 10):
        b.append(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{R}" y2="{Y(p):.1f}" stroke="{GRID}"/>')
        b.append(t(L - 10, Y(p) + 4, f"{p}%", 12, anchor="end"))
    ticks = [(1400, "1,400만"), (5000, "5,000만"), (8800, "8,800만"), (15000, "1.5억"), (30000, "3억"), (50000, "5억"), (100000, "10억")]
    for v, s in ticks:
        b.append(f'<line x1="{X(v):.1f}" y1="{T}" x2="{X(v):.1f}" y2="{B}" stroke="{GRID}" stroke-dasharray="4,5"/>')
        b.append(t(X(v), B + 20, s, 12, anchor="middle"))
    b.append(t((L + R) / 2, B + 44, "종합소득 과세표준 (로그 눈금)", 13, anchor="middle"))
    # 한계세율 계단
    pts, prev = [], 500
    for top, rate in BRACKETS:
        end = 200000 if top is None else top
        pts += [(X(prev), Y(rate)), (X(end), Y(rate))]
        prev = end
    b.append('<path d="M' + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" stroke="{C1}" stroke-width="4"/>')
    for (top, rate), (_, s) in zip(BRACKETS, [(500, "")] + ticks):
        pass
    prev = 500
    for top, rate in BRACKETS:
        end = 200000 if top is None else top
        mid = 10 ** ((math.log10(prev) + math.log10(end)) / 2)
        b.append(t(X(mid), Y(rate) - 8, f"{rate}%", 13, C1, "middle", 700))
        prev = end
    # 실효세율 곡선
    vs = [10 ** (lo + (hi - lo) * i / 300) for i in range(301)]
    d = "M" + " L".join(f"{X(v):.1f},{Y(income_tax(v) / v * 100):.1f}" for v in vs)
    b.append(f'<path d="{d}" fill="none" stroke="{C2}" stroke-width="3.5"/>')
    for v in (5000, 15000, 50000, 100000):
        e = income_tax(v) / v * 100
        b.append(f'<circle cx="{X(v):.1f}" cy="{Y(e):.1f}" r="4.5" fill="{C2}" stroke="#fff" stroke-width="2"/>')
        b.append(t(X(v) + 7, Y(e) + 17, f"{e:.1f}%", 12.5, C2, weight=700))
    b.append(f'<rect x="{L + 10}" y="56" width="14" height="5" fill="{C1}"/>' + t(L + 30, 63, "한계세율 (추가 1원에 붙는 세율)", 13, INK))
    b.append(f'<rect x="{L + 10}" y="78" width="14" height="5" fill="{C2}"/>' + t(L + 30, 85, "실효세율 = 산출세액 ÷ 과세표준", 13, INK))
    b.append(t(L, H - 12, "근거: 소득세법 §55① (2026-10-14 법제처 대조, 2023년 귀속부터 적용 구간). 지방소득세·공제·감면 제외.", 11.5))
    return svg(W, H, "".join(b), "종합소득세 과세표준 구간별 한계세율 계단과 실효세율 곡선")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "장기보유특별공제-표1-표2-공제율.svg").write_text(lthd(), encoding="utf-8", newline="\n")
    (OUT / "종합소득세-기본세율-한계-실효세율.svg").write_text(rates(), encoding="utf-8", newline="\n")
    for v in (5000, 15000, 50000, 100000):
        print(f"과세표준 {v:,}만원 → 산출세액 {income_tax(v):,.0f}만원, 실효 {income_tax(v) / v * 100:.2f}%")
    print("생성 완료:", OUT)
