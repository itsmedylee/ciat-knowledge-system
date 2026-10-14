"""문장 다듬기(고도화) 전후 wiki 문서의 불변 요소를 대조한다.

문체만 바꾸는 작업에서 다음이 달라지면 FAIL로 보고한다.
  - frontmatter (updated 값 제외)
  - 제목(#) 줄의 순서와 내용 (구두점·공백 차이는 허용)
  - 위키링크 [[...]] 집합(개수 포함)
  - 숫자 토큰 집합(금액·세율·조문번호·날짜)
  - 코드블록(Mermaid 포함) 본문
  - Callout 머리줄 (> [!type] 라벨)
  - 검증 표지 ([원문 확인 필요] 등 대괄호 표지)
  - 표의 행 수

사용법:
  python automation/quality/verify_rewrite.py <백업 폴더> <wiki 폴더>
  python automation/quality/verify_rewrite.py <원본 파일> <수정 파일>
"""
import re
import sys
from collections import Counter
from pathlib import Path

FM_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
CODE_RE = re.compile(r"^```.*?^```", re.S | re.M)
LINK_RE = re.compile(r"\[\[[^\]]+?\]\](?!\])|\[\[\[[^\]]+?\][^\]]*?\]\]")
NUM_RE = re.compile(r"\d[\d,.]*")
MARK_RE = re.compile(r"\[(?:원문|현행|강의|강사|LLM|자동자막|사무소|실무)[^\]\n]*\]")
CALLOUT_RE = re.compile(r"^>\s*\[![^\]]+\][^\n]*", re.M)
HEAD_RE = re.compile(r"^#{1,6} .*$", re.M)
PUNCT_RE = re.compile(r"[\s—:,.]")
TABLE_RE = re.compile(r"^\|.*\|\s*$", re.M)


def split(text: str):
    text = text.replace("\r\n", "\n")
    m = FM_RE.match(text)
    fm = m.group(1) if m else ""
    fm = re.sub(r"^updated:.*$", "", fm, flags=re.M)
    body = text[m.end():] if m else text
    return fm, body


def features(text: str) -> dict:
    fm, body = split(text)
    codes = CODE_RE.findall(body)
    prose = CODE_RE.sub("", body)
    return {
        "frontmatter": fm,
        # 제목은 구두점(엠대시·콜론·쉼표·마침표)과 공백 차이만 허용한다
        "headings": [PUNCT_RE.sub("", h) for h in HEAD_RE.findall(prose)],
        "wikilinks": Counter(LINK_RE.findall(body)),
        "numbers": Counter(n.rstrip(",.") for n in NUM_RE.findall(prose)),
        "codeblocks": codes,
        "callouts": CALLOUT_RE.findall(prose),
        "markers": Counter(MARK_RE.findall(prose)),
        "table_rows": len(TABLE_RE.findall(prose)),
    }


def diff_counter(a: Counter, b: Counter) -> str:
    lost = a - b
    added = b - a
    parts = []
    if lost:
        parts.append("사라짐 " + ", ".join(f"{k}×{v}" for k, v in list(lost.items())[:8]))
    if added:
        parts.append("추가됨 " + ", ".join(f"{k}×{v}" for k, v in list(added.items())[:8]))
    return " / ".join(parts)


def compare(old: Path, new: Path) -> list[str]:
    fa = features(old.read_text(encoding="utf-8"))
    fb = features(new.read_text(encoding="utf-8"))
    problems = []
    for key in ("frontmatter", "headings", "codeblocks", "callouts", "table_rows"):
        if fa[key] != fb[key]:
            problems.append(f"{key} 변경")
    for key in ("wikilinks", "numbers", "markers"):
        if fa[key] != fb[key]:
            problems.append(f"{key}: {diff_counter(fa[key], fb[key])}")
    return problems


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    a, b = Path(sys.argv[1]), Path(sys.argv[2])
    if a.is_file():
        pairs = [(a, b)]
    else:
        pairs = [(p, b / p.relative_to(a)) for p in sorted(a.rglob("*.md"))]
    failed = 0
    for old, new in pairs:
        if not new.exists():
            print(f"MISSING {new}")
            failed += 1
            continue
        problems = compare(old, new)
        if problems:
            failed += 1
            print(f"FAIL {new}")
            for p in problems:
                print(f"     - {p}")
    print(f"\n검사 {len(pairs)}건 / 실패 {failed}건")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
