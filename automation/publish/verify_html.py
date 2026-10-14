"""생성된 HTML이 Markdown 원본과 일치하는지 대조한다.

사용법: python automation/publish/verify_html.py [파일.md ...]   (생략하면 exports/html 에 있는 전 문서)

검사 항목
1. 본문 낱말(한글·숫자·영문) 누락: 원본에 있는 낱말이 HTML에 같은 횟수 이상 있는가
2. 구조 개수: 표·Mermaid·Callout·위키링크·제목·체크박스·수식
3. 변환되지 않고 남은 Markdown 문법: [[ ]] · > [! · ** · |--- · ```
4. 내부 링크·이미지 경로가 실제 파일을 가리키는가
"""
from __future__ import annotations

import html
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_html as B  # noqa: E402

EXPECTED = {(B.OUT / d.out_rel).resolve() for d in B.collect_docs()}
TOKEN = re.compile(r"[가-힣]+|\d+(?:[.,]\d+)*|[A-Za-z]{2,}")


def src_text(body: str) -> str:
    t = re.sub(r"%%.*?%%", "", body, flags=re.S)   # 숨김 주석
    t = re.sub(r"!\[\[[^\]\n]+\]\]", " ", t)                 # 임베드(이미지 파일명)는 화면 글자가 아니다
    t = re.sub(r"^([ \t]*)```[^\n]*", r"\1", t, flags=re.M)     # 코드블록 언어 표시
    t = re.sub(r"^([>\s]*)\d+\.\s", r"\1", t, flags=re.M)        # 번호 목록 번호는 <ol>이 만든다
    held = []
    def _hold(m):
        held.append(m.group(2)); return f"\ue010{len(held) - 1}\ue011"
    t = re.sub(r"(`+)(.+?)\1", _hold, t)                      # 코드 안의 글자는 그대로 보존
    t = re.sub(r"!?\[\[((?:[^\[\]\n]|\[[^\[\]\n]*\])+?)\]\]", lambda m: (re.split(r"\\?\|", m.group(1), maxsplit=1) + [""])[1] or
               re.sub(r"-소스요약$", "", m.group(1).split("#")[0]) or m.group(1).split("#")[-1], t)
    t = re.sub(r"^>\s?\[![A-Za-z-]+\][+-]?", " ", t, flags=re.M)
    t = re.sub(r"\[([^\]\n]+)\]\((?:https?:|mailto:|#|\.{0,2}/)[^)]*\)", r"\1", t)   # 마크다운 링크는 글자만
    t = re.sub(r"^(\s*)\*\s", r"\1- ", t, flags=re.M).replace("*", "").replace("`", "")   # 인라인 서식 기호는 띄어쓰기 없이 제거
    t = re.sub(r"<br\s*/?>", " ", t)
    return re.sub(r"(\d+)", lambda m: held[int(m.group(1))], t)


def html_text(h: str) -> str:
    m = re.search(r'<main class="doc">([\s\S]*?)</main>', h)
    h = m.group(1) if m else h
    h = re.sub(r'<section class="backlinks">[\s\S]*?</section>', " ", h)
    h = re.sub(r'<div class="(meta|tags|status|crumbs)">[\s\S]*?</div>', " ", h)
    h = re.sub(r'<span class="src"[^>]*title="소스요약: [^"]*"', "<span", h)
    h = re.sub(r"</?(a|span|strong|em|code|b|i|mark)\b[^>]*>", "", h)   # 인라인 태그는 띄어쓰기 없이 제거
    t = re.sub(r"<[^>]+>", " ", h)
    return html.unescape(t)


def check(doc: B.Doc) -> list[str]:
    out = B.OUT / doc.out_rel
    if not out.exists():
        return ["HTML 없음"]
    h = out.read_text(encoding="utf-8")
    probs = []
    # 1) 낱말
    s_tok = Counter(TOKEN.findall(src_text(doc.body)))
    h_tok = Counter(TOKEN.findall(html_text(h)))
    miss = {w: c - h_tok[w] for w, c in s_tok.items() if h_tok[w] < c}
    if miss:
        probs.append("낱말 누락: " + ", ".join(f"{w}×{n}" for w, n in sorted(miss.items(), key=lambda x: -x[1])[:15]))
    # 2) 구조
    body = re.sub(r"^([ \t]*)```.*?^\1```", "", doc.body, flags=re.S | re.M)  # 코드 안은 제외
    exp = {
        "표": len(re.findall(r"^[>\s]*\|?\s*:?-{3,}:?\s*\|", body, flags=re.M)),
        "Mermaid": doc.body.count("```mermaid"),
        "Callout": len(re.findall(r"^>\s?\[![A-Za-z-]+\]", body, flags=re.M)),
        "제목": len(re.findall(r"^[>\s]*#{1,6} ", body, flags=re.M)),
        "체크박스": len(re.findall(r"^\s*(?:[-*+]|\d+\.)\s+\[[ xX]\]", body, flags=re.M)),
        "위키링크": len(re.findall(r"!?\[\[", re.sub(r"(`+).+?\1", "", body))),
    }
    main = re.search(r'<article class="content">([\s\S]*)</article>', h).group(1)
    got = {
        "표": main.count("<table>"),
        "Mermaid": main.count('class="mermaid"'),
        "Callout": len(re.findall(r'class="callout ', main)),
        "제목": len(re.findall(r"<h[1-6][ >]", main)),
        "체크박스": main.count('type="checkbox"'),
        "위키링크": len(re.findall(r'class="(wl|src|ext|todo-link|broken)"|<figure class="embed">', main)),
    }
    for k in exp:
        if exp[k] != got[k]:
            probs.append(f"{k} 개수 불일치: 원본 {exp[k]} / HTML {got[k]}")
    # 3) 남은 문법
    vis = re.sub(r"<(pre|code)[\s\S]*?</\1>", " ", main)
    vis = html.unescape(re.sub(r"<[^>]+>", " ", vis))
    for pat, label in ((r"\[\[", "[["), (r"\]\]", "]]"), (r"\[![a-z]+\]", "[!callout]"), (r"\*\*", "**"),
                       (r"\|\s*-{3,}", "|---"), (r"```", "```"), (r"\d+", "자리표시")):
        n = len(re.findall(pat, vis))
        if n:
            probs.append(f"변환 안 된 문법 '{label}' {n}건")
    # 4) 링크·이미지
    for attr in re.findall(r'(?:href|src)="([^"#]+)(?:#[^"]*)?"', h):
        if attr.startswith(("http", "mailto:")):
            continue
        tgt = (out.parent / unquote(attr)).resolve()
        if not tgt.exists() and tgt not in EXPECTED:
            probs.append(f"깨진 경로: {attr}")
    return probs


def main(argv):
    docs = B.collect_docs()
    if argv:
        docs = [d for d in docs if d.rel in argv or d.stem in argv]
    else:
        docs = [d for d in docs if (B.OUT / d.out_rel).exists()]
    bad = 0
    for d in docs:
        p = check(d)
        if p:
            bad += 1
            print(f"FAIL {d.rel}")
            for x in p:
                print("     -", x)
        else:
            print(f"OK   {d.rel}")
    print(f"\n검사 {len(docs)}건 / 문제 {bad}건")


if __name__ == "__main__":
    main(sys.argv[1:])
