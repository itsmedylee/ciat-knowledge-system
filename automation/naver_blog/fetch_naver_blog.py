"""네이버 블로그 글 수집 — Web Clipper 없이 URL만으로 본문을 raw/에 저장한다.

blog.naver.com/<blogId>/<logNo> 페이지는 frameset 껍데기이고, 실제 본문은
그 안의 iframe이 불러오는 PostView.naver 안에 있다. Obsidian Web Clipper는
이 frameset만 긁어서 iframe 태그 한 줄만 저장하는 경우가 있다(본문 없음).

이 스크립트는 PostView.naver를 직접 요청해 스마트에디터 HTML에서 본문
텍스트를 뽑아 Markdown으로 저장한다. 표는 " | " 로 셀을 구분한 한 줄로,
이미지는 다운로드하지 않고 `![이미지](URL)` 마크다운 링크로 남긴다
(postfiles.pstatic.net 공개 CDN — 원본이 삭제되면 링크도 죽을 수 있다).

수집 결과는 raw/유튜브 스터디/ 와 같은 방식으로 raw/블로그 스터디/<블로거
컬렉션>/ 에 쌓인다(기본값: raw/블로그 스터디/정찬우 회계사 블로그 스터디/).

사용법:
    # 새 글 하나를 raw/블로그 스터디/정찬우 회계사 블로그 스터디/ 에 저장
    python automation/naver_blog/fetch_naver_blog.py "https://blog.naver.com/아이디/글번호"

    # 카테고리 전체 글을 일괄 수집 (이미 있는 글은 자동으로 건너뜀)
    python automation/naver_blog/fetch_naver_blog.py --category-url "https://blog.naver.com/PostList.naver?blogId=아이디&categoryNo=번호"

    # raw/Clippings/ 안에 Obsidian Web Clipper가 남긴 iframe-only 플레이스홀더를 채운다
    # (우리 자체 수집 경로가 아니라, 별도로 클리핑된 글을 복구할 때만 쓴다)
    python automation/naver_blog/fetch_naver_blog.py --fill-clippings

    # 무엇이 바뀔지만 보고 파일은 쓰지 않는다
    python automation/naver_blog/fetch_naver_blog.py --category-url "<URL>" --dry-run

이 도구는 수집만 한다. raw는 여전히 사람이 확인 후 /ingest 로 wiki에
반영해야 한다 — youtube_watcher.py 와 동일한 원칙(수집 자동화와 지식
가공 자동화의 분리).
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
# 우리 자체 수집(단건 URL·카테고리 일괄)의 기본 저장 위치.
DEFAULT_OUT_DIR = REPO_ROOT / "raw" / "블로그 스터디" / "정찬우 회계사 블로그 스터디"
# Obsidian Web Clipper가 만든 iframe-only 플레이스홀더를 복구하는 --fill-clippings 전용 기본값.
DEFAULT_CLIPPINGS_DIR = REPO_ROOT / "raw" / "Clippings"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "param", "source", "track", "wbr",
}

# 파일명에 쓸 수 없는 문자 (Windows 금지 문자 + 위키링크를 깨는 문자).
_ILLEGAL = re.compile(r'[<>:"/\\|?*]')
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_LINK_HOSTILE = re.compile(r"[#^\[\]]")
MAX_TITLE_LEN = 80


# ---------------------------------------------------------------------------
# URL 파싱
# ---------------------------------------------------------------------------

_URL_PATTERNS = [
    re.compile(r"blog\.naver\.com/PostView\.naver\?[^ ]*blogId=(?P<id>[^&\s]+)[^ ]*logNo=(?P<no>\d+)"),
    re.compile(r"(?:m\.)?blog\.naver\.com/(?P<id>[^/?\s]+)/(?P<no>\d+)"),
]


def parse_blog_url(url: str) -> tuple[str, str]:
    for pat in _URL_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group("id"), m.group("no")
    raise ValueError(f"네이버 블로그 URL에서 blogId/logNo를 찾지 못했다: {url}")


# ---------------------------------------------------------------------------
# 가져오기
# ---------------------------------------------------------------------------

def fetch_postview_html(blog_id: str, log_no: str) -> str:
    url = (
        "https://blog.naver.com/PostView.naver"
        f"?blogId={blog_id}&logNo={log_no}"
        "&redirect=Dlog&widgetTypeCall=true&directAccess=false"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"PostView.naver 요청 실패 (HTTP {e.code}): {url}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"PostView.naver 요청 실패: {e.reason}") from e
    return raw.decode(charset, errors="replace")


# ---------------------------------------------------------------------------
# 메타데이터 (og: 태그 — 정규식으로 충분히 안정적으로 뽑힌다)
# ---------------------------------------------------------------------------

def _og(html_text: str, prop: str) -> str | None:
    m = re.search(
        rf'<meta\s+property="og:{prop}"\s+content="(.*?)"\s*/?>',
        html_text,
    )
    return html.unescape(m.group(1)) if m else None


def guess_published_date(image_url: str | None) -> str | None:
    """og:image 썸네일 URL의 첫 경로 세그먼트는 base64(YYYYMMDD_nnn) 형태다.

    네이버 blogthumb CDN 경로 관례에 의존하는 휴리스틱이라 실패해도
    조용히 None을 반환한다 — published는 원래 비워둘 수 있는 필드다.
    """
    if not image_url:
        return None
    m = re.search(r"blogthumb\.pstatic\.net/([A-Za-z0-9+/]{8,})/", image_url)
    if not m:
        return None
    seg = m.group(1)
    try:
        padded = seg + "=" * (-len(seg) % 4)
        decoded = base64.b64decode(padded).decode("ascii", errors="strict")
    except Exception:
        return None
    m2 = re.match(r"(\d{4})(\d{2})(\d{2})_", decoded)
    if not m2:
        return None
    y, mo, d = m2.groups()
    try:
        return date(int(y), int(mo), int(d)).isoformat()
    except ValueError:
        return None


def extract_author(html_text: str) -> str | None:
    site_name = _og(html_text, "site_name")
    if site_name and "|" in site_name:
        return site_name.split("|", 1)[1].strip()
    return site_name


# ---------------------------------------------------------------------------
# 본문 추출 — 스마트에디터(se-main-container) HTML → 평문 Markdown
# ---------------------------------------------------------------------------

class _NaverBodyExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.in_container = False
        self.container_marker = 0
        self.skip_depth = 0
        self.in_p = False
        self.para_buffer: list[str] = []
        self.in_cell = False
        self.cell_parts: list[str] = []
        self.current_row: list[str] = []
        self.blocks: list[str] = []
        self.image_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrd = dict(attrs)
        cls = attrd.get("class") or ""

        if tag == "div" and "se-main-container" in cls and not self.in_container:
            self.in_container = True
            self.container_marker = len(self.stack)

        if tag in ("script", "style"):
            self.skip_depth += 1

        if self.in_container and self.skip_depth == 0:
            if tag == "tr":
                self.current_row = []
            elif tag in ("td", "th"):
                self.in_cell = True
                self.cell_parts = []
            elif tag == "p":
                self.in_p = True
                self.para_buffer = []
            elif tag == "br" and self.in_p:
                self.para_buffer.append("\n")
            elif tag == "img":
                # src는 지연로딩용 블러 placeholder(?type=w80_blur)라 data-lazy-src의
                # 실제 표시용 이미지(?type=w773, postfiles.pstatic.net 공개 CDN)를 쓴다.
                # 다운로드는 하지 않고 원본 URL만 마크다운 이미지 링크로 남긴다.
                url = attrd.get("data-lazy-src") or attrd.get("src")
                if url:
                    self.image_count += 1
                    marker = f"![이미지]({url})"
                    if self.in_cell:
                        self.cell_parts.append(marker)
                    else:
                        self.blocks.append(marker)

        if tag not in _VOID_TAGS:
            self.stack.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self.skip_depth = max(0, self.skip_depth - 1)

        if self.in_container and self.skip_depth == 0:
            if tag == "p":
                text = "".join(self.para_buffer).strip()
                if self.in_cell:
                    if text:
                        self.cell_parts.append(text)
                else:
                    if text or (self.blocks and self.blocks[-1] != ""):
                        self.blocks.append(text)
                self.in_p = False
            elif tag in ("td", "th"):
                # 한 셀 안에 여러 <p>가 있으면(예: 소제목+본문 2줄 셀) "; "로 이어붙인다 —
                # 원문 소스의 개행을 그대로 흡수하면 표 한 줄이 파일에서 여러 줄로 쪼개진다.
                self.current_row.append("; ".join(self.cell_parts))
                self.cell_parts = []
                self.in_cell = False
            elif tag == "tr":
                if any(c for c in self.current_row):
                    self.blocks.append(" | ".join(self.current_row))
                self.current_row = []

        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
            if tag == "div" and self.in_container and len(self.stack) == self.container_marker:
                self.in_container = False
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.stack.pop()
            if self.stack:
                self.stack.pop()

    def handle_data(self, data: str) -> None:
        # <p> 안에 있을 때만 받는다 — 태그 사이 순수 서식용 개행/공백(예: </p>\n<div>)까지
        # 주우면 표 셀·문단 텍스트에 의도치 않은 줄바꿈이 섞인다.
        if not self.in_container or self.skip_depth > 0 or not self.in_p:
            return
        self.para_buffer.append(data)

    _HEADING_RE = re.compile(r"^\d+\.\s")

    def get_text(self) -> str:
        # 번호 매긴 소제목("1. 사실관계", "7. 요약 ...") 앞에 빈 줄이 없는 경우가
        # 있다 — 원문에 스페이서 문단이 없기 때문. 가독성을 위해 앞에 빈 줄을 넣는다.
        spaced: list[str] = []
        for b in self.blocks:
            if self._HEADING_RE.match(b) and spaced and spaced[-1] != "":
                spaced.append("")
            spaced.append(b)

        text = "\n".join(spaced)
        text = text.replace("\xa0", " ")
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip("\n")


def extract_body(html_text: str) -> tuple[str, int]:
    parser = _NaverBodyExtractor()
    parser.feed(html_text)
    return parser.get_text(), parser.image_count


# ---------------------------------------------------------------------------
# 파일명
# ---------------------------------------------------------------------------

def sanitize_title(title: str) -> str:
    name = unicodedata.normalize("NFC", title)
    name = _CONTROL.sub("", name)
    name = _ILLEGAL.sub("", name)
    name = _LINK_HOSTILE.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(". ")
    if len(name) > MAX_TITLE_LEN:
        name = name[:MAX_TITLE_LEN].rstrip(". ")
    return name or "untitled"


def build_filename(title: str, log_no: str, taken: set[str]) -> str:
    base = sanitize_title(title)
    candidate = f"{base}.md"
    if candidate not in taken:
        return candidate
    candidate = f"{base}-{log_no}.md"
    if candidate not in taken:
        return candidate
    n = 2
    while f"{base}-{log_no}-{n}.md" in taken:
        n += 1
    return f"{base}-{log_no}-{n}.md"


# ---------------------------------------------------------------------------
# Markdown 조립
# ---------------------------------------------------------------------------

def _yaml_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_markdown(
    *,
    title: str,
    url: str,
    author: str | None,
    published: str | None,
    created: str,
    body: str,
) -> str:
    description = re.sub(r"\s+", " ", body).strip()[:150]
    lines = [
        "---",
        f"title: {_yaml_quote(title)}",
        f"source: {_yaml_quote(url)}",
        "source_type: naver-blog",
        f"author: {_yaml_quote(author) if author else ''}",
        f"published: {published or ''}",
        f"created: {created}",
        f"description: {_yaml_quote(description) if description else ''}",
        "tags:",
        '  - "clippings"',
        "---",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.tmp")
    tmp.write_text(content, encoding="utf-8", newline="\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# 모드 A: 새 URL 저장
# ---------------------------------------------------------------------------

def fetch_and_save(url: str, out_dir: Path, dry_run: bool) -> Path:
    blog_id, log_no = parse_blog_url(url)
    html_text = fetch_postview_html(blog_id, log_no)

    title = _og(html_text, "title") or f"네이버블로그 {blog_id} {log_no}"
    author = extract_author(html_text)
    published = guess_published_date(_og(html_text, "image"))
    body, image_count = extract_body(html_text)

    if not body:
        raise RuntimeError(
            f"본문을 추출하지 못했다 (blogId={blog_id}, logNo={log_no}). "
            "네이버가 페이지 구조를 바꿨거나 비공개 글일 수 있다."
        )

    canonical_url = f"https://blog.naver.com/{blog_id}/{log_no}"
    md = build_markdown(
        title=title,
        url=canonical_url,
        author=author,
        published=published,
        created=date.today().isoformat(),
        body=body,
    )

    taken = {p.name for p in out_dir.glob("*.md")} if out_dir.exists() else set()
    filename = build_filename(title, log_no, taken)
    out_path = out_dir / filename

    print(f"제목: {title}")
    print(f"작성자: {author or '(확인 안 됨)'}")
    print(f"작성일 추정: {published or '(확인 안 됨)'}")
    print(f"본문: {len(body)}자, 이미지 {image_count}개 (URL 링크만, 다운로드 안 함)")
    print(f"저장 경로: {out_path}")

    if dry_run:
        print("[dry-run] 파일을 쓰지 않았다.")
    else:
        atomic_write(out_path, md)
        print("저장 완료.")
    return out_path


# ---------------------------------------------------------------------------
# 모드 C: 카테고리(예: 낙서장) 전체 글 일괄 수집
# ---------------------------------------------------------------------------

_CATEGORY_URL_RE_BLOG = re.compile(r"blogId=([^&\s]+)")
_CATEGORY_URL_RE_CAT = re.compile(r"categoryNo=(\d+)")


def parse_category_url(url: str) -> tuple[str, str]:
    blog_m = _CATEGORY_URL_RE_BLOG.search(url)
    cat_m = _CATEGORY_URL_RE_CAT.search(url)
    if not blog_m or not cat_m:
        raise ValueError(
            f"카테고리 URL에서 blogId/categoryNo를 찾지 못했다: {url}\n"
            "예: https://blog.naver.com/PostList.naver?blogId=아이디&categoryNo=28"
        )
    return blog_m.group(1), cat_m.group(1)


def list_category_posts(blog_id: str, category_no: str, count_per_page: int = 30) -> list[dict]:
    """PostTitleListAsync.naver 로 카테고리의 전체 글 목록(logNo·제목·날짜)을 모은다.

    이 엔드포인트는 응답 JSON 안에 홑따옴표를 \\' 로 이스케이프하는데, 이는
    표준 JSON에서 무효한 이스케이프라 json.loads가 그대로는 실패한다.
    파싱 전에 \\' → ' 로 되돌린다(값 자체에 홑따옴표가 남는 것 외엔 안전).
    """
    import json as _json

    posts: list[dict] = []
    page = 1
    total_count = None
    while True:
        url = (
            "https://blog.naver.com/PostTitleListAsync.naver"
            f"?blogId={blog_id}&categoryNo={category_no}"
            f"&currentPage={page}&countPerPage={count_per_page}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        cleaned = raw.replace("\\'", "'")
        data = _json.loads(cleaned)

        page_posts = data.get("postList") or []
        if total_count is None:
            total_count = int(data.get("totalCount") or 0)
        if not page_posts:
            break

        for p in page_posts:
            posts.append({
                "logNo": p["logNo"],
                "title": urllib.parse.unquote(p.get("title", "")),
                "addDate": p.get("addDate", ""),
            })

        if len(posts) >= total_count:
            break
        page += 1

    return posts


def existing_lognos(out_dir: Path) -> set[str]:
    """out_dir 안의 .md 파일 중 source: 필드에서 이미 수집된 logNo 집합을 만든다."""
    seen: set[str] = set()
    if not out_dir.exists():
        return seen
    for path in out_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        m = _SOURCE_RE.search(text)
        if not m:
            continue
        try:
            _, log_no = parse_blog_url(m.group(1))
            seen.add(log_no)
        except ValueError:
            continue
    return seen


def fetch_category(
    category_url: str,
    out_dir: Path,
    dry_run: bool,
    limit: int | None = None,
    delay: float = 1.0,
) -> None:
    blog_id, category_no = parse_category_url(category_url)
    print(f"카테고리 글 목록 조회 중: blogId={blog_id}, categoryNo={category_no}")
    posts = list_category_posts(blog_id, category_no)
    print(f"전체 {len(posts)}건 확인됨.")

    already = existing_lognos(out_dir)
    todo = [p for p in posts if p["logNo"] not in already]
    print(f"이미 수집됨: {len(already & {p['logNo'] for p in posts})}건 / 신규 대상: {len(todo)}건")

    if limit is not None:
        todo = todo[:limit]
        print(f"--limit {limit} 적용 → 이번 실행 대상 {len(todo)}건")

    ok, failed = 0, 0
    for i, p in enumerate(todo, 1):
        url = f"https://blog.naver.com/{blog_id}/{p['logNo']}"
        print(f"[{i}/{len(todo)}] {p['title'][:50]} ({p['addDate']})")
        try:
            fetch_and_save(url, out_dir, dry_run)
            ok += 1
        except Exception as e:
            print(f"  [실패] {e}")
            failed += 1
        if i < len(todo):
            time.sleep(delay)

    print(f"완료: 성공 {ok}건, 실패 {failed}건.")


# ---------------------------------------------------------------------------
# 모드 B: raw/Clippings/ 안의 iframe-only 플레이스홀더 채우기
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_SOURCE_RE = re.compile(r'^source:\s*"?(.*?)"?\s*$', re.MULTILINE)


def _is_iframe_only_placeholder(body: str) -> bool:
    stripped = body.strip()
    return stripped.startswith("<iframe") and len(stripped) < 800


def fill_clippings(out_dir: Path, dry_run: bool, refresh: bool = False) -> None:
    """iframe-only 플레이스홀더를 채운다.

    refresh=True 면 이미 본문이 채워진 파일도 source: URL로 다시 가져와
    본문을 덮어쓴다 — 파서를 고친 뒤 기존 raw를 재추출할 때 쓴다.
    """
    if not out_dir.exists():
        print(f"{out_dir} 없음.")
        return

    candidates = sorted(out_dir.glob("*.md"))
    if not candidates:
        print(f"{out_dir} 에 .md 파일이 없다.")
        return

    for path in candidates:
        text = path.read_text(encoding="utf-8")
        m = _FRONTMATTER_RE.match(text)
        if not m:
            continue
        frontmatter, body = m.group(1), m.group(2)

        if not refresh and not _is_iframe_only_placeholder(body):
            continue  # 이미 실제 본문이 채워져 있음 — 건드리지 않는다

        src_m = _SOURCE_RE.search(frontmatter)
        if not src_m:
            print(f"[건너뜀] source 없음: {path.name}")
            continue
        url = src_m.group(1)

        try:
            blog_id, log_no = parse_blog_url(url)
            html_text = fetch_postview_html(blog_id, log_no)
            new_body, image_count = extract_body(html_text)
        except Exception as e:
            print(f"[실패] {path.name}: {e}")
            continue

        if not new_body:
            print(f"[실패] {path.name}: 본문 추출 결과가 비어 있음")
            continue

        published = guess_published_date(_og(html_text, "image"))
        # published 필드가 비어 있으면 채운다. 기존 값이 있으면 보존한다.
        new_frontmatter = frontmatter
        if published and re.search(r"^published:\s*$", frontmatter, re.MULTILINE):
            new_frontmatter = re.sub(
                r"^published:\s*$", f"published: {published}", frontmatter, flags=re.MULTILINE
            )

        new_text = f"---\n{new_frontmatter}\n---\n\n{new_body}\n"

        print(f"{path.name}: 본문 {len(new_body)}자, 이미지 {image_count}개 (URL 링크만)")
        if not dry_run:
            atomic_write(path, new_text)
            print("  저장 완료.")
        else:
            print("  [dry-run] 파일을 쓰지 않았다.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    # Windows 콘솔(cp949)은 em-dash 등 흔한 문장부호를 인코딩하지 못해 print()가
    # 그대로 죽는다 — 배경 실행 중 제목 하나 때문에 전체 배치가 중단되는 걸
    # 막기 위해 stdout/stderr를 UTF-8(대체 문자 허용)로 강제한다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", nargs="?", help="네이버 블로그 글 URL")
    ap.add_argument("--fill-clippings", action="store_true", help="raw/Clippings/ 의 iframe-only 플레이스홀더를 채운다")
    ap.add_argument("--refresh", action="store_true", help="--fill-clippings 와 함께: 이미 채워진 파일도 source: URL로 다시 가져와 덮어쓴다")
    ap.add_argument("--category-url", help="카테고리 전체 글 수집. 예: https://blog.naver.com/PostList.naver?blogId=아이디&categoryNo=28")
    ap.add_argument("--limit", type=int, default=None, help="--category-url 과 함께: 이번 실행에서 새로 받을 글 수 제한")
    ap.add_argument("--delay", type=float, default=1.0, help="--category-url 과 함께: 글 사이 대기시간(초, 기본 1.0)")
    ap.add_argument(
        "--out-dir",
        default=None,
        help=(
            f"저장 위치. 기본: --fill-clippings 는 {DEFAULT_CLIPPINGS_DIR}, "
            f"그 외(단건 URL·--category-url)는 {DEFAULT_OUT_DIR}"
        ),
    )
    ap.add_argument("--dry-run", action="store_true", help="파일을 쓰지 않고 무엇을 할지만 출력한다")
    args = ap.parse_args()

    if args.out_dir is not None:
        out_dir = Path(args.out_dir)
    elif args.fill_clippings:
        out_dir = DEFAULT_CLIPPINGS_DIR
    else:
        out_dir = DEFAULT_OUT_DIR

    if args.category_url:
        try:
            fetch_category(args.category_url, out_dir, args.dry_run, limit=args.limit, delay=args.delay)
        except Exception as e:
            print(f"오류: {e}", file=sys.stderr)
            return 1
        return 0

    if args.fill_clippings:
        fill_clippings(out_dir, args.dry_run, refresh=args.refresh)
        return 0

    if not args.url:
        ap.error("URL을 주거나 --fill-clippings 를 지정해야 한다.")

    try:
        fetch_and_save(args.url, out_dir, args.dry_run)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
