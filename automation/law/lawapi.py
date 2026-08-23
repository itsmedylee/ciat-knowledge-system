# -*- coding: utf-8 -*-
"""법제처 Open API 클라이언트 (외부 의존성 없음).

법제처 국가법령정보 공동활용 Open API를 직접 호출한다.
제3자 중계서버를 거치지 않으므로 조회 내역이 외부로 나가지 않고,
사무소의 OC(인증 ID)와 할당량을 그대로 사용한다.

OC 결정 순서: 환경변수 LAW_OC → automation/law/oc.txt → 기본값.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "http://www.law.go.kr/DRF"
HERE = Path(__file__).resolve().parent
CACHE = HERE / ".cache"
CACHE_TTL = 24 * 60 * 60  # 법령 본문 캐시 수명(초). 하루.
TIMEOUT = 60

# 검색 대상 → (API target, 응답 루트 키, 항목 키, 표시 이름)
TARGETS = {
    "법령": ("law", "LawSearch", "law", "법령"),
    "판례": ("prec", "PrecSearch", "prec", "판례"),
    "해석례": ("expc", "Expc", "expc", "법령해석례"),
    "행정규칙": ("admrul", "AdmRulSearch", "admrul", "행정규칙(훈령·예규·고시)"),
    "자치법규": ("ordin", "OrdinSearch", "ordin", "자치법규(조례·규칙)"),
}


class LawError(Exception):
    """조회 실패. 메시지를 그대로 사용자에게 보여도 되는 오류."""


def get_oc() -> str:
    oc = os.environ.get("LAW_OC", "").strip()
    if oc:
        return oc
    f = HERE / "oc.txt"
    if f.exists():
        oc = f.read_text(encoding="utf-8").strip()
        if oc:
            return oc
    return "ciatpartners"


def _get(path: str, params: dict) -> dict:
    params = {"OC": get_oc(), "type": "JSON", **params}
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params, encoding="utf-8")
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            raw = r.read().decode("utf-8", "replace")
    except Exception as e:
        raise LawError(f"법제처 API 호출 실패: {e!r}") from e
    if not raw.strip().startswith("{"):
        raise LawError(
            "법제처가 JSON이 아닌 응답을 반환했다"
            "(점검 중이거나 OC가 유효하지 않을 수 있다).\n"
            f"응답 앞부분: {raw[:200]!r}"
        )
    return json.loads(raw)


# ────────────────────────────── 검색 ──────────────────────────────

def search(query: str, kind: str = "법령", display: int = 20) -> list:
    if kind not in TARGETS:
        raise LawError(f"알 수 없는 검색 대상 {kind!r}. 가능: {', '.join(TARGETS)}")
    target, root, item, _ = TARGETS[kind]
    d = _get("lawSearch.do", {"target": target, "query": query, "display": display})
    inner = d.get(root) or {}
    rows = inner.get(item) or []
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def format_search(rows: list, kind: str) -> str:
    if not rows:
        return "검색 결과 없음. 검색어를 넓히거나 약칭 대신 정식 명칭을 시도한다."
    label = TARGETS[kind][3]
    out = [f"{label} 검색 결과 {len(rows)}건"]
    for i, r in enumerate(rows, 1):
        if kind == "법령":
            out.append(
                f"{i}. {r.get('법령명한글')}  [{r.get('제개정구분명', '')}]\n"
                f"     MST={r.get('법령일련번호')}  법령ID={r.get('법령ID')}  "
                f"시행일={r.get('시행일자')}  소관={r.get('소관부처명', '')}"
            )
        elif kind == "판례":
            src = r.get("데이터출처명", "")
            # 국세법령정보시스템 출처 판례는 상세 API가 HTML만 제공한다(본문 조회 불가).
            warn = "  ⚠️본문조회불가(HTML전용)" if "국세법령정보" in src else ""
            out.append(
                f"{i}. {r.get('사건명')}\n"
                f"     ID={r.get('판례일련번호')}  {r.get('법원명') or src} "
                f"{r.get('선고일자', '')} {r.get('사건번호', '')}{warn}"
            )
        elif kind == "해석례":
            org = r.get("회신기관명") or r.get("해석기관명") or ""
            day = r.get("회신일자") or r.get("해석일자") or ""
            out.append(
                f"{i}. {r.get('안건명')}\n"
                f"     ID={r.get('법령해석례일련번호')}  {org} {day} "
                f"{r.get('안건번호', '')}"
            )
        elif kind == "행정규칙":
            out.append(
                f"{i}. {r.get('행정규칙명')}  [{r.get('행정규칙종류', '')}]\n"
                f"     ID={r.get('행정규칙일련번호')}  시행일={r.get('시행일자', '')}"
            )
        else:
            out.append(f"{i}. {r.get('자치법규명')}  ID={r.get('자치법규일련번호')}")
    return "\n".join(out)


# ──────────────────────────── 법령 본문 ────────────────────────────

def law_json(mst: str, refresh: bool = False) -> dict:
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"law-{mst}.json"
    if f.exists() and not refresh and (time.time() - f.stat().st_mtime) < CACHE_TTL:
        return json.loads(f.read_text(encoding="utf-8"))
    d = _get("lawService.do", {"target": "law", "MST": mst})
    if "법령" not in d:
        raise LawError(
            f"MST={mst} 에 대한 법령 본문을 법제처가 반환하지 않았다.\n"
            "MST가 유효한지 search 로 먼저 확인한다. 조문을 추측해서 쓰지 말 것."
        )
    f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


def _articles(d: dict) -> list:
    jo = d.get("법령", d).get("조문", {}).get("조문단위", [])
    return [jo] if isinstance(jo, dict) else jo


def _article_text(a: dict) -> str:
    out = []
    if a.get("조문내용"):
        out.append(str(a["조문내용"]).strip())
    hangs = a.get("항", [])
    hangs = [hangs] if isinstance(hangs, dict) else hangs
    for h in hangs:
        if h.get("항내용"):
            out.append(str(h["항내용"]).strip())
        hos = h.get("호", [])
        hos = [hos] if isinstance(hos, dict) else hos
        for ho in hos:
            if ho.get("호내용"):
                out.append("   " + str(ho["호내용"]).strip())
            moks = ho.get("목", [])
            moks = [moks] if isinstance(moks, dict) else moks
            for m in moks:
                mc = m.get("목내용")
                if isinstance(mc, list):
                    mc = " ".join(str(x) for x in mc)
                if mc:
                    out.append("      " + str(mc).strip())
    return "\n".join(out)


def _header(d: dict) -> str:
    bi = d.get("법령", d).get("기본정보", {})
    dept = bi.get("소관부처")
    if isinstance(dept, dict):
        dept = dept.get("content", "")
    return (f"■ {bi.get('법령명_한글')} | 공포 {bi.get('공포일자')} "
            f"| 시행 {bi.get('시행일자', '?')} | 소관 {dept or ''}")


def _label(a: dict) -> str:
    num = str(a.get("조문번호", "")).lstrip("0")
    br = str(a.get("조문가지번호", "") or "").lstrip("0")
    return f"제{num}조" + (f"의{br}" if br else "")


def article(mst: str, jo: str, refresh: bool = False) -> str:
    """조문 한 개의 본문. jo 예: '제13조', '제23조의2'."""
    d = law_json(mst, refresh)
    arts = _articles(d)

    m = re.match(r"\s*제?\s*(\d+)\s*조(?:\s*의\s*(\d+))?", jo)
    if not m:
        raise LawError(
            f"조문 표기를 해석할 수 없다: {jo!r}. "
            "'제13조' 또는 '제23조의2' 형식으로 쓴다."
        )
    num, branch = m.group(1), m.group(2) or ""

    hits = [
        a for a in arts
        if str(a.get("조문번호", "")).lstrip("0") == num
        and str(a.get("조문가지번호", "") or "").lstrip("0") == branch
    ]
    if not hits:
        label = f"제{num}조" + (f"의{branch}" if branch else "")
        raise LawError(
            f"{label} 을(를) 찾지 못했다(이 법령의 조문 {len(arts)}개 중 없음).\n"
            "삭제된 조문이거나 조번호가 틀렸을 수 있다. list_articles 로 목록을 확인한다.\n"
            "⚠️ 조문을 추측해서 만들어내지 말 것."
        )
    return _header(d) + "\n\n" + "\n\n".join(_article_text(a) for a in hits)


def list_articles(mst: str, keyword: str = "", refresh: bool = False) -> str:
    d = law_json(mst, refresh)
    rows = []
    for a in _articles(d):
        if a.get("조문여부") != "조문":
            continue
        label = _label(a)
        title = (a.get("조문제목") or "").strip()
        if keyword and keyword not in title and keyword not in label:
            continue
        rows.append(f"  {label:14} {title}")
    head = _header(d) + f"\n조문 {len(rows)}개"
    if keyword:
        head += f" (키워드 {keyword!r} 필터)"
    return head + "\n" + ("\n".join(rows) if rows else "  (해당 없음)")


def search_in_law(mst: str, keyword: str, refresh: bool = False) -> str:
    """법령 본문 전체에서 키워드가 나오는 조문을 찾는다. 조번호를 모를 때 쓴다."""
    d = law_json(mst, refresh)
    hits = []
    for a in _articles(d):
        if a.get("조문여부") != "조문":
            continue
        txt = _article_text(a)
        if keyword in txt:
            idx = txt.index(keyword)
            snip = txt[max(0, idx - 60): idx + 120].replace("\n", " ")
            hits.append(
                f"  {_label(a):14} {(a.get('조문제목') or '').strip()}\n"
                f"      …{snip}…"
            )
    head = _header(d) + f"\n키워드 {keyword!r} 포함 조문 {len(hits)}개"
    if not hits:
        head += ("\n  (없음) — 이 법령에 그 표현이 없다는 뜻이다. "
                 "다른 법령·시행령을 확인한다.")
    return head + "\n" + "\n".join(hits)


# ───────────────────── 판례 · 해석례 본문 ─────────────────────

def _detail(target: str, ident: str, root_keys: list, fields: list) -> str:
    d = _get("lawService.do", {"target": target, "ID": ident})

    # 실패 시 법제처는 {"Law": "일치하는 …이 없습니다"} 형태의 문자열을 준다.
    if len(d) == 1 and isinstance(next(iter(d.values())), str):
        msg = next(iter(d.values())).strip()
        extra = ""
        if target == "prec":
            extra = ("\n⚠️ 국세법령정보시스템 출처 판례는 상세 API가 HTML만 제공해 "
                     "본문을 가져올 수 없다. 검색 결과의 '⚠️본문조회불가' 표시를 확인하고, "
                     "https://taxlaw.nts.go.kr 에서 직접 확인한다.")
        raise LawError(f"ID={ident}: {msg}{extra}")

    body = None
    for k in root_keys:
        if k in d:
            body = d[k]
            break
    if body is None:
        body = d
    out = []
    for f in fields:
        v = body.get(f)
        if isinstance(v, list):
            v = "\n".join(str(x) for x in v)
        if v:
            out.append(f"[{f}]\n{str(v).strip()}")
    if not out:
        raise LawError(f"ID={ident} 본문을 가져오지 못했다. 응답 키: {list(body)[:12]}")
    return "\n\n".join(out)


def precedent(ident: str) -> str:
    return _detail("prec", ident, ["PrecService", "Prec", "prec"],
                   ["사건명", "사건번호", "법원명", "선고일자", "사건종류명",
                    "판시사항", "판결요지", "참조조문", "참조판례", "판례내용"])


def interpretation(ident: str) -> str:
    return _detail("expc", ident, ["ExpcService", "Expc", "expc"],
                   ["안건명", "안건번호", "해석기관명", "질의기관명", "해석일자",
                    "질의요지", "회답", "이유"])
