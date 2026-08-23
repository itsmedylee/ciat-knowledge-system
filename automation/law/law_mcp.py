# -*- coding: utf-8 -*-
"""법제처 조문조회 MCP 서버 (stdio, 외부 의존성 없음).

Claude Code가 이 스크립트를 stdio로 띄우고 JSON-RPC로 대화한다.
mcp 패키지를 쓰지 않고 표준 라이브러리만으로 프로토콜을 구현한다 —
pip install 없이 파이썬만 있으면 동작하게 하기 위해서다.

수동 점검:
    echo {"jsonrpc":"2.0","id":1,"method":"tools/list"} | python law_mcp.py
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lawapi as L  # noqa: E402

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "law-kr", "version": "1.0.0"}

_KINDS = list(L.TARGETS)

TOOLS = [
    {
        "name": "law_search",
        "description": (
            "법제처 검색 — 법령·판례·법령해석례·행정규칙(훈령/예규/고시)·자치법규를 "
            "이름이나 키워드로 찾아 MST(법령일련번호) 또는 ID를 얻는다. "
            "조문 본문을 보려면 먼저 이걸로 MST를 확보한다. "
            "법령은 본법·시행령·시행규칙이 각각 별도 MST를 가지므로 어느 것인지 확인할 것."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string",
                          "description": "검색어. 예: '상속세및증여세법', '지방세법 시행령'"},
                "kind": {"type": "string", "enum": _KINDS, "default": "법령",
                         "description": "검색 대상. 기본 '법령'"},
                "display": {"type": "integer", "default": 20,
                            "description": "최대 결과 수"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "law_article",
        "description": (
            "법령 조문 본문 조회. mst와 조문번호가 필요하다. "
            "jo는 '제13조'·'제23조의2'처럼 자연어로 쓴다. "
            "⚠️ 이 도구가 조문을 반환하지 않으면 조문을 추측해 쓰지 말고 실패로 처리할 것."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mst": {"type": "string", "description": "법령일련번호(law_search로 획득)"},
                "jo": {"type": "string", "description": "조문 번호. 예: '제13조', '제23조의2'"},
                "refresh": {"type": "boolean", "default": False,
                            "description": "캐시를 무시하고 다시 받아온다"},
            },
            "required": ["mst", "jo"],
        },
    },
    {
        "name": "law_find",
        "description": (
            "법령 본문 전체에서 키워드가 들어간 조문을 찾는다. 조번호를 모를 때 쓴다. "
            "결과가 0건이면 '그 법령에 그 표현이 없다'는 근거로 삼을 수 있다 — "
            "어떤 규정의 부존재를 확인할 때 유용하다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mst": {"type": "string", "description": "법령일련번호"},
                "keyword": {"type": "string", "description": "찾을 표현. 예: '동거주택', '먼저 사망'"},
                "refresh": {"type": "boolean", "default": False},
            },
            "required": ["mst", "keyword"],
        },
    },
    {
        "name": "law_toc",
        "description": "법령의 조문 목록(조번호 + 제목). 구조를 훑거나 조번호를 찾을 때 쓴다.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mst": {"type": "string", "description": "법령일련번호"},
                "keyword": {"type": "string", "default": "",
                            "description": "조문 제목 필터(선택)"},
                "refresh": {"type": "boolean", "default": False},
            },
            "required": ["mst"],
        },
    },
    {
        "name": "law_precedent",
        "description": "판례 본문 조회(판시사항·판결요지·참조조문·전문). ID는 law_search(kind='판례')로 얻는다.",
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "판례일련번호"}},
            "required": ["id"],
        },
    },
    {
        "name": "law_interpretation",
        "description": (
            "법령해석례 본문 조회(질의요지·회답·이유). ID는 law_search(kind='해석례')로 얻는다. "
            "⚠️ 국세청 질의회신(서면/사전답변)은 법제처 소관이 아니라 "
            "국세법령정보시스템에 있으므로 여기서 조회되지 않는다."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"id": {"type": "string", "description": "법령해석례일련번호"}},
            "required": ["id"],
        },
    },
]


def _dispatch(name: str, args: dict) -> str:
    if name == "law_search":
        kind = args.get("kind", "법령")
        rows = L.search(args["query"], kind, int(args.get("display", 20)))
        return L.format_search(rows, kind)
    if name == "law_article":
        return L.article(args["mst"], args["jo"], bool(args.get("refresh")))
    if name == "law_find":
        return L.search_in_law(args["mst"], args["keyword"], bool(args.get("refresh")))
    if name == "law_toc":
        return L.list_articles(args["mst"], args.get("keyword", ""),
                               bool(args.get("refresh")))
    if name == "law_precedent":
        return L.precedent(args["id"])
    if name == "law_interpretation":
        return L.interpretation(args["id"])
    raise L.LawError(f"알 수 없는 도구: {name}")


def handle(msg: dict):
    """요청 하나를 처리한다. 알림(notification)이면 None을 돌려준다."""
    method = msg.get("method")
    mid = msg.get("id")

    if method == "initialize":
        result = {"protocolVersion": PROTOCOL_VERSION,
                  "capabilities": {"tools": {}},
                  "serverInfo": SERVER_INFO}
    elif method in ("notifications/initialized", "initialized"):
        return None
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            text = _dispatch(name, args)
            result = {"content": [{"type": "text", "text": text}]}
        except L.LawError as e:
            result = {"content": [{"type": "text", "text": f"[조회 실패] {e}"}],
                      "isError": True}
        except KeyError as e:
            result = {"content": [{"type": "text",
                                   "text": f"[필수 인자 누락] {e}"}],
                      "isError": True}
        except Exception:
            result = {"content": [{"type": "text",
                                   "text": "[예외]\n" + traceback.format_exc()[-1200:]}],
                      "isError": True}
    else:
        if mid is None:
            return None
        return {"jsonrpc": "2.0", "id": mid,
                "error": {"code": -32601, "message": f"Method not found: {method}"}}

    if mid is None:
        return None
    return {"jsonrpc": "2.0", "id": mid, "result": result}


def main() -> None:
    # Windows 콘솔 기본 인코딩(cp949)으로는 한글 조문이 깨진다.
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", newline="\n")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        for one in (msg if isinstance(msg, list) else [msg]):
            try:
                resp = handle(one)
            except Exception:
                resp = {"jsonrpc": "2.0", "id": one.get("id"),
                        "error": {"code": -32603,
                                  "message": traceback.format_exc()[-500:]}}
            if resp is not None:
                sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    main()
