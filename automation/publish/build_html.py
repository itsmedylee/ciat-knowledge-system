"""위키 학습 문서(Markdown)를 개인 복습용 정적 HTML로 변환한다.

사용법:
    python automation/publish/build_html.py            # 전체 재생성
    python automation/publish/build_html.py 파일.md ... # 지정 문서만(시범 변환용, 검색·목록은 전체 기준)

원칙
- Markdown이 유일한 정본이다. 이 스크립트는 wiki/ 를 읽기만 하고 exports/html/ 에만 쓴다.
- 대상 레이어: topics · practice · notes · business · entities (sources 제외).
- 오프라인 동작: Mermaid·MathJax는 automation/publish/vendor/ 의 고정 버전을 복사해 쓴다.
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import urllib.request
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "wiki"
OUT = ROOT / "exports" / "html"
VENDOR = Path(__file__).resolve().parent / "vendor"
ASSETS_SRC = Path(__file__).resolve().parent / "assets"
LAYERS = ["topics", "practice", "notes", "business", "entities"]
LAYER_LABEL = {"topics": "지식 (topics)", "practice": "실무 (practice)", "notes": "가이드·종합 (notes)",
               "business": "비즈니스 (business)", "entities": "개체 (entities)"}
VENDOR_FILES = {
    "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js",
    "tex-svg.js": "https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js",
}

CALLOUT = {
    "info": ("ℹ️", "개요"), "summary": ("📌", "요약"), "abstract": ("📌", "요약"),
    "warning": ("⚠️", "주의"), "caution": ("🔎", "검증 상태"), "success": ("✅", "확인"),
    "tip": ("💡", "팁"), "quote": ("❝", "출처"), "example": ("🧮", "사례"),
    "note": ("📝", "참고"), "failure": ("⛔", "오류"), "danger": ("⛔", "위험"),
    "question": ("❓", "질문"),
}
# 표지(마커) 분류: 원문 텍스트는 그대로 두고 배지 모양만 입힌다.
MARK_RE = re.compile(r"\[(원문[^\]\n]*|현행[^\]\n]*|강의 시점[^\]\n]*|강사[^\]\n]*|LLM[^\]\n]*|자동자막[^\]\n]*|"
                     r"개정안[^\]\n]*|사무소 방침[^\]\n]*|실무[^\]\n]*|가설|검증됨|반증됨|강사 계산[^\]\n]*|"
                     r"20\d\d (?:교재 )?기준[^\]\n]*|시점 의존[^\]\n]*)\]")


def mark_kind(text: str) -> str:
    if text.startswith(("원문", "현행", "자동자막", "시점")):
        return "unverified"
    if text.startswith(("강사", "강의")):
        return "opinion"
    if text.startswith("LLM"):
        return "llm"
    if text.startswith("개정안"):
        return "draft"
    if text.startswith("검증됨"):
        return "ok"
    return "neutral"


# ---------------------------------------------------------------- 공통 유틸
def slugify(value: str, separator: str = "-") -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    return re.sub(r"[\s]+", separator, value) or "section"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not m:
        return {}, text
    meta: dict = {}
    for line in m.group(1).splitlines():
        mm = re.match(r"([A-Za-z_]+):\s*(.*)$", line)
        if not mm:
            continue
        k, v = mm.group(1), mm.group(2).strip()
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1]
            items = re.findall(r'"([^"]*)"|\'([^\']*)\'|([^,]+)', inner)
            meta[k] = [next(x for x in it if x).strip() for it in items if any(x.strip() for x in it)]
        else:
            meta[k] = v.strip('"').strip("'")
    return meta, text[m.end():]


class Doc:
    def __init__(self, path: Path):
        self.path = path
        self.rel = path.relative_to(WIKI).as_posix()
        self.stem = path.stem
        raw = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
        self.meta, self.body = parse_frontmatter(raw)
        self.title = self.meta.get("title") or self.stem
        self.out_rel = self.rel[:-3] + ".html"
        self.links: set[str] = set()
        self.plain = ""
        self.headings: list[str] = []


def collect_docs() -> list[Doc]:
    docs = []
    for layer in LAYERS:
        for p in sorted((WIKI / layer).rglob("*.md")):
            docs.append(Doc(p))
    return docs


def all_basenames() -> dict[str, str]:
    """wiki 전체의 basename → 상대경로 (sources 포함: 링크 해석용)."""
    m = {}
    for p in WIKI.rglob("*"):
        if p.is_file():
            m.setdefault(p.stem if p.suffix == ".md" else p.name, p.relative_to(WIKI).as_posix())
    return m


def relpath(from_out: str, to_out: str) -> str:
    depth = from_out.count("/")
    return "../" * depth + to_out


# ---------------------------------------------------------------- 변환기
class Converter:
    def __init__(self, docs: list[Doc]):
        self.by_stem = {d.stem: d for d in docs}
        self.names = all_basenames()
        self.ph: list[str] = []

    def hold(self, html_text: str) -> str:
        self.ph.append(html_text)
        # Python-Markdown이 \x02·\x03을 내부 표시로 쓰므로 사용자 영역 문자(U+E000·U+E001)를 쓴다
        return f"{len(self.ph) - 1}"

    def restore(self, text: str) -> str:
        for _ in range(6):  # 중첩 복원
            new = re.sub(r"(\d+)", lambda m: self.ph[int(m.group(1))], text)
            if new == text:
                break
            text = new
        return text

    # -- 인라인 요소
    def link_html(self, doc: Doc, target: str, label: str | None, embed: bool) -> str:
        target = target.strip()
        name, _, frag = target.partition("#")
        name = name.strip()
        shown = html.escape(label if label else (frag if not name else name))
        if embed:
            rel = self.names.get(name)
            if rel and rel.startswith("attachments/"):
                src = relpath(doc.out_rel, rel)
                return (f'<figure class="embed"><img src="{html.escape(src)}" alt="{html.escape(name)}" loading="lazy">'
                        f'</figure>')
            return f'<span class="broken" title="첨부를 찾을 수 없음">{html.escape(target)}</span>'
        if not name:  # 같은 문서 heading
            return f'<a class="wl" href="#{slugify(frag)}">{shown}</a>'
        if name == "index":
            return f'<a class="wl" href="{relpath(doc.out_rel, "index.html")}">{shown}</a>'
        tgt = self.by_stem.get(name)
        if tgt:
            doc.links.add(tgt.stem)
            href = relpath(doc.out_rel, tgt.out_rel) + (f"#{slugify(frag)}" if frag else "")
            return f'<a class="wl" href="{html.escape(href)}" title="{html.escape(tgt.title)}">{shown}</a>'
        rel = self.names.get(name)
        if rel and rel.startswith("sources/"):
            short = re.sub(r"-소스요약$", "", name)
            disp = html.escape(label) if label else html.escape(short)
            return f'<span class="src" title="소스요약: {html.escape(rel)}">📄 {disp}</span>'
        if rel:
            return f'<span class="ext" title="{html.escape(rel)}">{shown}</span>'
        return f'<span class="todo-link" title="아직 없는 문서">{shown}</span>'

    def badge(self, text: str) -> str:
        return f'<span class="mk mk-{mark_kind(text)}">[{html.escape(text)}]</span>'

    def inline_pass(self, doc: Doc, text: str) -> str:
        # 코드 스팬 보호(표지 문자열만 배지로)
        def code(m):
            inner = m.group(2)
            mm = MARK_RE.fullmatch(inner)
            if mm:
                return self.hold(self.badge(mm.group(1)))
            return self.hold(f"<code>{html.escape(inner)}</code>")
        text = re.sub(r"(`+)(.+?)\1", code, text)
        # 수식
        text = re.sub(r"\$\$(.+?)\$\$", lambda m: self.hold(f'<div class="math">\\[{html.escape(m.group(1))}\\]</div>'), text, flags=re.S)
        def inline_math(m):
            body = m.group(1)
            if re.search(r"[가-힣]", body) or not re.search(r"[\\^_=A-Za-z]", body):
                return m.group(0)
            return self.hold(f'<span class="math">\\({html.escape(body)}\\)</span>')
        text = re.sub(r"(?<![\$\w])\$([^\$\n]+?)\$(?![\$\w])", inline_math, text)
        # 위키링크·임베드 (표 안의 \| 이스케이프 포함)
        def wl(m):
            embed = m.group(1) == "!"
            inner = m.group(2)
            parts = re.split(r"\\?\|", inner, maxsplit=1)
            return self.hold(self.link_html(doc, parts[0], parts[1] if len(parts) > 1 else None, embed))
        text = re.sub(r"(!?)\[\[((?:[^\[\]\n]|\[[^\[\]\n]*\])+?)\]\]", wl, text)
        # URL이 아닌 대상의 [글자](글자)는 링크가 아니라 본문으로 둔다(예: [별표1](제7조 관련))
        text = re.sub(r"\[([^\]\n]+)\]\(([^)\n]*)\)",
                      lambda m: m.group(0) if re.match(r"(https?:|mailto:|#|\.{0,2}/)", m.group(2).strip())
                      else self.hold(html.escape(m.group(0))), text)
        # 굵은 글씨는 직접 변환한다(따옴표·괄호에 붙은 **를 Python-Markdown이 놓치는 경우 보정)
        text = re.sub(r"\*\*(?=\S)([^\n]+?)(?<=\S)\*\*", r"<strong>\1</strong>", text)
        # 기울임(*…*)도 직접 변환한다(한글 조사가 바로 붙으면 Python-Markdown이 놓친다)
        text = re.sub(r"(?<![\*\])\*(?=[^\s\*])([^\*\n]+?)(?<=[^\s\*])\*(?!\*)", r"<em>\1</em>", text)
        # 표지 배지
        text = MARK_RE.sub(lambda m: self.hold(self.badge(m.group(1))), text)
        return text

    # -- 블록 정규화 (Obsidian ↔ Python-Markdown 차이 보정)
    @staticmethod
    def normalize_blocks(text: str) -> str:
        lines = text.split("\n")
        out: list[str] = []
        list_re = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+")
        prev = ""
        in_list = False
        for line in lines:
            exp = line.replace("\t", "    ")
            m = list_re.match(exp)
            lead = len(exp) - len(exp.lstrip(" "))
            is_list = bool(m)
            # 2칸 들여쓰기 하위 목록 → 4칸
            if lead and (is_list or in_list):
                exp = " " * (lead * 2) + exp.lstrip(" ")
            is_table = exp.lstrip().startswith("|")
            prev_s = prev.strip()
            if prev_s:
                if is_list and not list_re.match(prev.replace("\t", "    ")) and not in_list:
                    out.append("")
                elif is_table and not prev_s.startswith("|"):
                    out.append("")
                elif exp.startswith("#") and re.match(r"#{1,6} ", exp):
                    out.append("")
                elif not is_table and prev_s.startswith("|") and exp.strip():
                    out.append("")
            if is_list:
                in_list = True
            elif not exp.strip():
                pass
            elif lead == 0:
                in_list = False
            out.append(exp)
            prev = exp
        return "\n".join(out)

    # -- Callout
    def callouts(self, doc: Doc, text: str) -> str:
        lines = text.split("\n")
        out, i = [], 0
        head = re.compile(r"^>\s?\[!([A-Za-z-]+)\]([+-]?)\s*(.*)$")
        while i < len(lines):
            m = head.match(lines[i])
            if not m:
                out.append(lines[i]); i += 1; continue
            kind, fold, title = m.group(1).lower(), m.group(2), m.group(3).strip()
            body = []
            i += 1
            while i < len(lines) and lines[i].startswith(">"):
                body.append(re.sub(r"^> ?", "", lines[i])); i += 1
            icon, default = CALLOUT.get(kind, ("📝", kind))
            inner = self.render_block(doc, "\n".join(body)) if any(b.strip() for b in body) else ""
            t = self.render_inline(doc, title) if title else html.escape(default)
            cls = f"callout c-{kind}"
            if fold:
                tag = "details" + (" open" if fold == "+" else "")
                h = (f'<{tag} class="{cls}"><summary class="c-title"><span class="c-ico">{icon}</span>{t}</summary>'
                     f'<div class="c-body">{inner}</div></details>')
            else:
                h = (f'<div class="{cls}"><div class="c-title"><span class="c-ico">{icon}</span>{t}</div>'
                     + (f'<div class="c-body">{inner}</div>' if inner else "") + "</div>")
            out.append(""); out.append(self.hold(h)); out.append("")
        return "\n".join(out)

    def render_inline(self, doc: Doc, text: str) -> str:
        t = self.inline_pass(doc, text)
        h = markdown.markdown(t, extensions=["sane_lists"])
        h = re.sub(r"^<p>(.*)</p>$", r"\1", h.strip(), flags=re.S)
        return self.restore(h)

    def render_block(self, doc: Doc, text: str, toc: bool = False):
        # 0) Obsidian 숨김 주석(%% … %%)은 화면에 보이지 않으므로 제외한다
        text = re.sub(r"%%.*?%%", "", text, flags=re.S)
        # 1) 펜스 코드 보호
        def fence(m):
            lang, code = m.group(2).strip(), m.group(3)
            if lang == "mermaid":
                return "\n" + self.hold(f'<div class="mermaid-wrap"><pre class="mermaid">{html.escape(code)}</pre></div>') + "\n"
            return "\n" + self.hold(f'<pre class="code"><code>{html.escape(code)}</code></pre>') + "\n"
        text = re.sub(r"^([ \t]*)```([^\n]*)\n(.*?)^\1```[ \t]*$", fence, text, flags=re.S | re.M)
        # 2) callout → 3) 인라인 보호 → 4) 블록 정규화
        text = self.callouts(doc, text)
        text = self.inline_pass(doc, text)
        text = self.normalize_blocks(text)
        md = markdown.Markdown(extensions=["tables", "sane_lists", "nl2br", "toc"],
                               extension_configs={"toc": {"slugify": slugify, "toc_depth": "2-3"}})
        h = md.convert(text)
        # 블록 플레이스홀더가 <p>로 감싸진 경우 해제
        h = re.sub(r"<p>(\d+)</p>", r"\1", h)
        h = self.restore(h)
        h = re.sub(r"<table>", '<div class="tbl"><table>', h).replace("</table>", "</table></div>")
        h = re.sub(r"<li>\[( |x|X)\]\s?", lambda m: '<li class="task"><input type="checkbox" disabled'
                   + (" checked" if m.group(1).lower() == "x" else "") + "> ", h)
        h = re.sub(r"<li><p>\[( |x|X)\]\s?", lambda m: '<li class="task"><p><input type="checkbox" disabled'
                   + (" checked" if m.group(1).lower() == "x" else "") + "> ", h)
        if toc:
            return h, md.toc_tokens
        return h


# ---------------------------------------------------------------- 페이지 조립
def meta_card(doc: Doc, out_html: str) -> str:
    m = doc.meta
    chips = []
    for key, label in (("type", "유형"), ("domain", "도메인"), ("taxType", "세목"), ("business_type", "비즈니스"),
                       ("status", "상태"), ("case_type", "사례"), ("updated", "갱신")):
        if m.get(key):
            chips.append(f'<span class="chip"><b>{label}</b> {html.escape(str(m[key]))}</span>')
    if m.get("relatedTaxTypes"):
        chips.append(f'<span class="chip"><b>관련 세목</b> {html.escape(", ".join(m["relatedTaxTypes"]))}</span>')
    tags = "".join(f'<span class="tag">#{html.escape(t)}</span>' for t in m.get("tags", []) if isinstance(m.get("tags"), list))
    n_src = len(m.get("sources", [])) if isinstance(m.get("sources"), list) else 0
    counts = {k: len(re.findall(f'class="mk mk-{k}"', out_html)) for k in ("unverified", "opinion", "llm", "draft")}
    stat = []
    if counts["unverified"]:
        stat.append(f'<a class="st st-unverified" href="#" data-jump="unverified">확인 필요 {counts["unverified"]}</a>')
    if counts["opinion"]:
        stat.append(f'<a class="st st-opinion" href="#" data-jump="opinion">강사 견해 {counts["opinion"]}</a>')
    if counts["llm"]:
        stat.append(f'<a class="st st-llm" href="#" data-jump="llm">LLM 해석 {counts["llm"]}</a>')
    if counts["draft"]:
        stat.append(f'<a class="st st-draft" href="#" data-jump="draft">개정안 {counts["draft"]}</a>')
    verified = len(re.findall(r'class="callout c-success"', out_html))
    if verified:
        stat.append(f'<span class="st st-ok">검증 박스 {verified}</span>')
    if n_src:
        stat.append(f'<span class="st">원본 소스 {n_src}</span>')
    return (f'<div class="meta">{"".join(chips)}</div>'
            + (f'<div class="tags">{tags}</div>' if tags else "")
            + (f'<div class="status" title="표지를 누르면 해당 위치로 순서대로 이동합니다">{"".join(stat)}</div>' if stat else ""))


def toc_html(tokens) -> str:
    def walk(ts):
        if not ts:
            return ""
        items = "".join(f'<li><a href="#{t["id"]}">{t["name"]}</a>{walk(t.get("children"))}</li>' for t in ts)
        return f"<ul>{items}</ul>"
    # h1 하나 아래에 h2가 있는 구조면 h1을 건너뛴다
    if len(tokens) == 1 and tokens[0]["level"] == 1:
        tokens = tokens[0].get("children", [])
    return walk(tokens)


def nav_html(docs: list[Doc], current: Doc | None) -> str:
    tree: dict = {}
    for d in docs:
        parts = d.rel.split("/")
        node = tree
        for p in parts[:-1]:
            node = node.setdefault(p, {})
        node.setdefault("__docs", []).append(d)
    base = current.out_rel if current else "index.html"

    def render(node, depth, path):
        h = ""
        keys = [k for k in node if k != "__docs"]
        order = (lambda k: (LAYERS.index(k) if k in LAYERS else 99, k)) if depth == 0 else (lambda k: k)
        for key in sorted(keys, key=order):
            sub = node[key]
            label = LAYER_LABEL.get(key, key) if depth == 0 else key
            here = current is not None and current.rel.startswith("/".join(path + [key]) + "/")
            cnt = sum(1 for _ in _iter_docs(sub))
            h += (f'<details{" open" if here else ""}><summary>{html.escape(label)} <small>{cnt}</small></summary>'
                  f'{render(sub, depth + 1, path + [key])}</details>')
        docs_here = sorted(node.get("__docs", []), key=lambda d: d.title)
        if docs_here:
            h += "<ul>" + "".join(
                f'<li><a class="{"cur" if current is d else ""}" href="{html.escape(relpath(base, d.out_rel))}">'
                f'{html.escape(d.title)}</a></li>' for d in docs_here) + "</ul>"
        return h
    return render(tree, 0, [])


def _iter_docs(node):
    for k, v in node.items():
        if k == "__docs":
            yield from v
        else:
            yield from _iter_docs(v)


def page(title: str, body: str, nav: str, toc: str, rel_root: str, crumbs: str = "", extra_head: str = "") -> str:
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} · 학습 위키</title>
<link rel="stylesheet" href="{rel_root}assets/style.css">{extra_head}
</head><body>
<header class="top">
  <button class="btn-nav" aria-label="문서 목록">☰</button>
  <a class="brand" href="{rel_root}index.html">학습 위키</a>
  <div class="search"><input id="q" type="search" placeholder="전체 검색 (공백으로 여러 단어)" autocomplete="off"><div id="results" hidden></div></div>
  <button class="btn-theme" aria-label="화면 테마">◐</button>
</header>
<div class="layout">
  <nav class="side" aria-label="문서 목록">{nav}</nav>
  <main class="doc">{crumbs}{body}</main>
  <aside class="toc">{('<div class="toc-h">이 문서의 목차</div>' + toc) if toc else ''}</aside>
</div>
<div class="scrim"></div>
<script>window.__ROOT="{rel_root}";</script>
<script src="{rel_root}assets/app.js"></script>
</body></html>"""


def plain_text(h: str) -> str:
    t = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", h)
    t = re.sub(r"<pre class=\"mermaid\">[\s\S]*?</pre>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def build(selected: list[str] | None = None) -> None:
    docs = collect_docs()
    conv = Converter(docs)
    # 1차: 전 문서 변환(링크·검색 색인·역링크 계산)
    rendered = {}
    for d in docs:
        conv.ph = []
        body_html, tokens = conv.render_block(d, d.body, toc=True)
        rendered[d.stem] = (body_html, tokens)
        d.plain = plain_text(body_html)
        d.headings = [re.sub(r"<[^>]+>", "", t["name"]) for t in _flat(tokens)]
    back: dict[str, list[Doc]] = {}
    for d in docs:
        for s in d.links:
            if s != d.stem:
                back.setdefault(s, []).append(d)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    for f in ASSETS_SRC.iterdir():
        shutil.copy2(f, OUT / "assets" / f.name)
    for name, url in VENDOR_FILES.items():
        if not (VENDOR / name).exists():
            VENDOR.mkdir(exist_ok=True)
            print(f"내려받는 중: {name}")
            urllib.request.urlretrieve(url, VENDOR / name)
        shutil.copy2(VENDOR / name, OUT / "assets" / name)
    if (WIKI / "attachments").exists():
        shutil.copytree(WIKI / "attachments", OUT / "attachments", dirs_exist_ok=True)

    targets = [d for d in docs if not selected or d.rel in selected or d.stem in selected]
    for d in targets:
        body_html, tokens = rendered[d.stem]
        rel_root = "../" * d.out_rel.count("/")
        bl = sorted(back.get(d.stem, []), key=lambda x: x.title)
        backlinks = ("<section class=\"backlinks\"><h2 id=\"backlinks\">이 문서를 참조하는 문서</h2><ul>"
                     + "".join(f'<li><a href="{html.escape(relpath(d.out_rel, b.out_rel))}">{html.escape(b.title)}</a>'
                               f' <small>{html.escape(b.rel.split("/")[0])}</small></li>' for b in bl)
                     + "</ul></section>") if bl else ""
        crumbs = '<div class="crumbs">' + " › ".join(html.escape(p) for p in d.rel.split("/")[:-1]) + "</div>"
        h1 = "" if re.search(r"<h1[ >]", body_html) else f"<h1>{html.escape(d.title)}</h1>"
        body = (h1 + meta_card(d, body_html) + f'<article class="content">{body_html}</article>' + backlinks)
        extra = ""
        if 'class="mermaid"' in body_html:
            extra += f'\n<script src="{rel_root}assets/mermaid.min.js" defer></script>'
        if 'class="math"' in body_html:
            extra += (f'\n<script>window.MathJax={{tex:{{inlineMath:[["\\\\(","\\\\)"]],displayMath:[["\\\\[","\\\\]"]]}},'
                      f'options:{{processHtmlClass:"math",ignoreHtmlClass:"content"}}}};</script>'
                      f'\n<script src="{rel_root}assets/tex-svg.js" defer></script>')
        html_out = page(d.title, body, nav_html(docs, d), toc_html(tokens), rel_root, crumbs, extra)
        dest = OUT / d.out_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html_out, encoding="utf-8", newline="\n")

    # 검색 색인 + 첫 화면
    idx = [{"t": d.title, "p": d.out_rel, "l": d.rel.split("/")[0], "g": d.meta.get("tags", []) if isinstance(d.meta.get("tags"), list) else [],
            "h": d.headings, "x": d.plain} for d in docs]
    (OUT / "assets" / "search-index.js").write_text("window.__IDX=" + json.dumps(idx, ensure_ascii=False) + ";",
                                                   encoding="utf-8", newline="\n")
    home = ['<h1>학습 위키</h1><p class="lead">위키 Markdown에서 생성한 개인 복습용 HTML입니다. 원본은 Obsidian 위키이며, '
            '이 화면은 <code>python automation/publish/build_html.py</code>로 언제든 다시 만들 수 있습니다.</p>',
            '<div class="legend"><span class="mk mk-unverified">[원문 확인 필요]</span> 원문·현행 대조 전 '
            '<span class="mk mk-opinion">[강사견해]</span> 강사 의견 <span class="mk mk-llm">[LLM 해석]</span> LLM 해석 '
            '<span class="mk mk-draft">[개정안]</span> 확정 전 개정안</div>']
    for layer in LAYERS:
        ds = [d for d in docs if d.rel.startswith(layer + "/")]
        home.append(f'<h2 id="{layer}">{LAYER_LABEL[layer]} <small>{len(ds)}</small></h2><div class="cards">')
        groups: dict[str, list[Doc]] = {}
        for d in ds:
            groups.setdefault("/".join(d.rel.split("/")[1:-1]) or "(루트)", []).append(d)
        for g in sorted(groups):
            items = "".join(f'<li><a href="{html.escape(d.out_rel)}">{html.escape(d.title)}</a></li>'
                            for d in sorted(groups[g], key=lambda x: x.title))
            home.append(f'<div class="card"><div class="card-h">{html.escape(g)} <small>{len(groups[g])}</small></div><ul>{items}</ul></div>')
        home.append("</div>")
    (OUT / "index.html").write_text(page("학습 위키", "".join(home), nav_html(docs, None), "", ""),
                                    encoding="utf-8", newline="\n")
    print(f"완료: 문서 {len(targets)}건 생성 (전체 {len(docs)}건 색인) → {OUT}")


def _flat(tokens):
    for t in tokens:
        yield t
        yield from _flat(t.get("children", []))


if __name__ == "__main__":
    build(sys.argv[1:] or None)
