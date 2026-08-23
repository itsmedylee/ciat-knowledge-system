# -*- coding: utf-8 -*-
"""법제처 조회 CLI — MCP가 안 될 때의 대체 경로이자 수동 확인용.

  python law.py 검색 상속세및증여세법
  python law.py 검색 "부담부증여" --종류 판례
  python law.py 조문 276123 제23조의2
  python law.py 찾기 276123 동거주택
  python law.py 목차 276123 --키워드 공제
  python law.py 판례 12345
  python law.py 해석례 12345
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lawapi as L  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="법제처 국가법령정보 조회")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("검색", help="법령·판례·해석례 등을 검색해 MST/ID를 얻는다")
    p.add_argument("query")
    p.add_argument("--종류", default="법령", choices=list(L.TARGETS))
    p.add_argument("--개수", type=int, default=20)

    p = sub.add_parser("조문", help="조문 본문")
    p.add_argument("mst")
    p.add_argument("jo")
    p.add_argument("--새로", action="store_true", help="캐시 무시")

    p = sub.add_parser("찾기", help="법령 본문에서 키워드가 든 조문 찾기")
    p.add_argument("mst")
    p.add_argument("keyword")
    p.add_argument("--새로", action="store_true")

    p = sub.add_parser("목차", help="조문 목록")
    p.add_argument("mst")
    p.add_argument("--키워드", default="")
    p.add_argument("--새로", action="store_true")

    p = sub.add_parser("판례", help="판례 본문")
    p.add_argument("id")

    p = sub.add_parser("해석례", help="법령해석례 본문")
    p.add_argument("id")

    a = ap.parse_args()
    try:
        if a.cmd == "검색":
            print(L.format_search(L.search(a.query, a.종류, a.개수), a.종류))
        elif a.cmd == "조문":
            print(L.article(a.mst, a.jo, a.새로))
        elif a.cmd == "찾기":
            print(L.search_in_law(a.mst, a.keyword, a.새로))
        elif a.cmd == "목차":
            print(L.list_articles(a.mst, a.키워드, a.새로))
        elif a.cmd == "판례":
            print(L.precedent(a.id))
        elif a.cmd == "해석례":
            print(L.interpretation(a.id))
    except L.LawError as e:
        print(f"[조회 실패] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
