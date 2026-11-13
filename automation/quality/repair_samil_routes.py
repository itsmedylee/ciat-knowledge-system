"""Rebuild V001-V051 cross-check routes from question ownership, without changing raw.

The response sometimes renumbered a subset of the question. Explicit mappings below
come from the response's section headings, not list position alone. Run --write after
reviewing the proposed routes. This script does not accept an LLM verdict as law.
"""
from pathlib import Path
import argparse
import collections
import json
import re

ROOT = Path(__file__).resolve().parents[2]
WIKI = ROOT / "wiki"
OVERRIDES = {
    "V017": [1, 3, 4, 5, 6, 7, 8],
    "V024": [1, 2, 3, 7],
    "V028": [6, 6, 6, 6],
    "V030": [4, 5, 6],
    "V031": [2, 3, 4, 5],
    "V032": [2, 3, 4, 5],
    "V034": [1, 3],
    "V035": [2, 3],
    "V046": [1, 2, 3, 4, 5, 7, 8],
}
QUARANTINE = {
    "V006": "질문 본문에 검증 명제가 없고 취소 이력이 있어 답변의 소유 문서를 확정하지 않는다.",
    "V051": "연금·급여 관련 질문에 부가가치세 등 다른 주제의 답이 돌아와 질문과 답변이 대응하지 않는다.",
}

def norm(value):
    return re.sub(r"[^0-9a-z가-힣]", "", value.lower())

def read(path):
    return path.read_text(encoding="utf-8-sig")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    docs = [p for p in WIKI.rglob("*.md") if "sources" not in p.relative_to(WIKI).parts]
    names = collections.defaultdict(set)
    for path in docs:
        title = re.search(r"^title: (.*)$", read(path), re.M)
        for name in [path.stem, title[1].strip("\"'") if title else ""]:
            if name:
                names[norm(name)].add(path)

    def resolve(name):
        key = norm(name)
        found = names.get(key, set())
        if not found:
            found = set().union(*(v for k, v in names.items() if k.startswith(key) or key.startswith(k)))
        if len(found) != 1:
            raise ValueError(f"Ambiguous question owner: {name}: {found}")
        return next(iter(found))

    by_doc = collections.defaultdict(list)
    sources = []
    routes = []
    for raw in sorted((ROOT / "raw/삼일 Tax Agent").glob("*-V0*-*.md")):
        text = read(raw)
        code = re.search(r"^question_id: (V\d+)$", text, re.M)
        if not code or int(code[1][1:]) > 51:
            continue
        code = code[1]
        matches = list((WIKI / "sources/삼일 Tax Agent").glob(f"{raw.stem}-소스요약.md"))
        if len(matches) != 1:
            raise ValueError(f"Summary count for {code}: {len(matches)}")
        source = matches[0]
        summary = read(source)
        rows = re.findall(r"^\d+\. \*\*(.*?)\*\* \((.*?)\): (.*)$", summary, re.M)
        if code in QUARANTINE:
            sources.append((source, summary, code, [], QUARANTINE[code]))
            continue
        if not rows:
            continue
        question = text.split("## 질문", 1)[1].split("## 답변", 1)[0]
        questions = dict((int(n), body) for n, body in re.findall(r"^(\d+)\.\s*(.*)$", question, re.M))
        target = re.search(r"^wiki_targets: (.*)$", text, re.M)
        targets = json.loads(target[1]) if target else []
        mapping = OVERRIDES.get(code, list(range(1, len(rows) + 1)))
        if len(mapping) != len(rows):
            raise ValueError(f"Mapping count for {code}")
        rebuilt = []
        owners = set()
        for answer_n, ((claim, verdict, correction), question_n) in enumerate(zip(rows, mapping), 1):
            claim = questions[question_n]
            match = re.match(r"「([^›」]+)(?:›|」)", claim)
            owner = resolve(match[1].strip()) if match else resolve(targets[0]) if len(targets) == 1 else None
            if owner is None:
                raise ValueError(f"No owner for {code} question {question_n}")
            owners.add(owner)
            rebuilt.append(f"{answer_n}. **{claim}** ({verdict}): {correction}")
            entry = {"code": code, "answer": answer_n, "question": question_n, "owner": owner.relative_to(WIKI).as_posix(), "source": source.stem, "claim": claim, "verdict": verdict, "correction": correction}
            routes.append(entry)
            if verdict != "맞음":
                by_doc[owner].append(entry)
        sources.append((source, summary, code, rebuilt, ""))

    # Remove only V blocks. W/R and later primary-source verification are preserved.
    block = re.compile(r"^\*\*V\d+\*\*[^\n]*\n.*?(?=^\*\*[A-Z]\d+\*\*|^#{1,6} |\Z)", re.M | re.S)
    changed = []
    for path in docs:
        old = read(path)
        text = block.sub("", old)
        entries = by_doc.get(path, [])
        if entries:
            parts = []
            for code in dict.fromkeys(x["code"] for x in entries):
                subset = [x for x in entries if x["code"] == code]
                parts.append(f'**{code}** [[{subset[0]["source"]}]] (질문·답변의 소유 문서를 2026-11-13 재확인)')
                parts += ["", "| 질문한 서술 | 삼일 판정 | 삼일 답 요지 |", "| --- | --- | --- |"]
                for item in subset:
                    escape = lambda s: s.replace("|", "\\|")
                    parts.append(f'| Q{item["question"]}: {escape(item["claim"][:220])} | {escape(item["verdict"])} | {escape(item["correction"])} |')
                parts.append("")
            section = "\n".join(parts) + "\n"
            heading = re.search(r"^## 삼일 Tax Agent 교차검증 \(2026-10-27~29\)\s*\n", text, re.M)
            if heading:
                # Insert before the next non-V review block, retaining the existing caution.
                pos = re.search(r"^\*\*[A-Z]\d+\*\*|^#{1,6} ", text[heading.end():], re.M)
                at = heading.end() + pos.start() if pos else len(text)
                text = text[:at] + section + text[at:]
            else:
                text += "\n## 삼일 Tax Agent 교차검증 (2026-10-27~29)\n\n> 이 표는 검토 전 LLM 답의 이력이다. 정본의 법령 근거를 대체하지 않으며 질문 소유 문서에 해당하는 행만 표시한다.\n\n" + section
        if text.rstrip("\n") != old.rstrip("\n"):
            text = re.sub(r"^updated: .*?$", "updated: 2026-11-13", text, count=1, flags=re.M)
            changed.append(path.relative_to(WIKI).as_posix())
            if args.write:
                path.write_text(text, encoding="utf-8")
    for path, old, code, rebuilt, reason in sources:
        if reason:
            note = f"\n> [!warning] 라우팅 보류 (2026-11-13)\n> {reason} 아래 기록을 다른 정본의 검증 결과로 사용하지 않는다. 원본은 보존한다.\n"
            text = old if note in old else old.replace("## 다룬 주제", note + "\n## 다룬 주제", 1)
        else:
            text = re.sub(r"(?ms)(^## 다룬 주제\s*\n).*?(?=^## )", lambda m: m[1] + "\n" + "\n".join(rebuilt) + "\n\n", old)
            if code in OVERRIDES:
                note = "\n> [!note] 번호 대응 정정 (2026-11-13)\n> 답변이 질문 일부를 생략하고 번호를 다시 매긴 점을 반영했다. 아래 명제는 실제 질문으로 복원했으며, 원문 답변 번호와 질문 번호는 별도 라우팅 기록에서 추적한다.\n"
                if note not in text:
                    text = text.replace("## 다룬 주제", note + "\n## 다룬 주제", 1)
        if text != old and args.write:
            text = re.sub(r"^updated: .*?$", "updated: 2026-11-13", text, count=1, flags=re.M)
            path.write_text(text, encoding="utf-8")
    result = {"checked": "2026-11-13", "routes": routes, "changedKnowledge": changed, "quarantined": QUARANTINE, "written": args.write}
    output = ROOT.parent / "시스템 검토/2026-11-13/교차검증-라우팅.json"
    if args.write:
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = collections.Counter(x["verdict"] for x in routes)
    print(json.dumps({"routes":len(routes),"documents":len(by_doc),"changedKnowledge":len(changed),"changedKnowledgePaths":changed,"verdicts":dict(counts),"quarantined":list(QUARANTINE),"written":args.write},ensure_ascii=False))

if __name__ == "__main__":
    main()
