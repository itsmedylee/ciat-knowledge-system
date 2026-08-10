"""VTT/SRT 자막 → 평문 transcript.

⚠️ 이 모듈은 **기계적 정리만** 수행한다. 의미를 바꾸는 어떤 조작도 하지 않는다.

허용:
  - VTT/SRT 헤더·NOTE·큐 번호·타이밍 행 제거
  - 인라인 태그 제거 (<c>, </c>, <00:00:01.234>, align:start 등)
  - 자동자막 롤링 중복 제거
  - HTML entity 해제 (&amp; → &)
  - 과도한 빈 줄 정리

금지 (절대 하지 않음):
  - 요약
  - 전문용어 추정 교정 (세법·회계 용어 임의 수정)
  - 문장 재작성
  - 내용 삭제
"""

from __future__ import annotations

import html
import re
from collections import deque

# 00:00:02.669 --> 00:00:05.190  /  00:00:02,669 --> 00:00:05,190
_TIMING = re.compile(
    r"(\d{1,2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[.,]\d{3})"
)
# <c>, </c>, <00:00:01.234>, <v Speaker> 등 모든 인라인 태그
_TAG = re.compile(r"<[^>]*>")
# 큐 설정 (align:start position:0% 등) — 타이밍 행 뒤에 붙는다
_CUE_SETTING = re.compile(r"\s+(align|position|size|line|vertical|region):\S+")


def _to_seconds(stamp: str) -> float:
    """'00:01:23.456' → 83.456"""
    stamp = stamp.replace(",", ".")
    h, m, s = stamp.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def format_timestamp(seconds: float) -> str:
    """기존 raw 코퍼스 표기에 맞춘다: 1시간 미만은 M:SS, 이상은 H:MM:SS."""
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _parse_cues(raw: str) -> list[tuple[float, list[str]]]:
    """자막 텍스트를 (시작초, [텍스트 행]) 목록으로 파싱한다."""
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    cues: list[tuple[float, list[str]]] = []

    for block in re.split(r"\n{2,}", raw):
        block = block.strip("\n")
        if not block:
            continue
        # WEBVTT 헤더, NOTE/STYLE/REGION 블록은 통째로 버린다
        head = block.lstrip()
        if head.startswith(("WEBVTT", "NOTE", "STYLE", "REGION")):
            continue

        lines = block.split("\n")
        timing_idx = next((i for i, ln in enumerate(lines) if _TIMING.search(ln)), None)
        if timing_idx is None:
            continue  # 타이밍 없는 블록(SRT 번호만 등)은 버린다

        start = _to_seconds(_TIMING.search(lines[timing_idx]).group(1))
        text_lines = lines[timing_idx + 1 :]
        cues.append((start, text_lines))

    return cues


def _clean_line(line: str) -> str:
    line = _TAG.sub("", line)          # 인라인 태그 제거
    line = _CUE_SETTING.sub("", line)  # 잔여 큐 설정 제거
    line = html.unescape(line)         # HTML entity 해제
    line = line.replace("​", "").replace("﻿", "")  # 제로폭 문자
    line = re.sub(r"[ \t ]+", " ", line)  # 연속 공백 → 1칸
    return line.strip()


def normalize(
    raw: str,
    timestamp_style: str = "line",
    chapters: list[dict] | None = None,
) -> str:
    """자막 원문을 평문 transcript로 변환한다.

    timestamp_style:
      "line"   — 타임스탬프를 별도 행으로 (기본. 기존 raw 코퍼스와 동일한 형태)
      "prefix" — 각 행 앞에 [M:SS]
      "none"   — 타임스탬프 제거

    chapters:
      yt-dlp의 info["chapters"]. 영상에 챕터가 있으면 해당 시점에 챕터 제목을
      단독 행으로 삽입한다(기존 코퍼스의 "인트로" 같은 행). 챕터 제목은 업로더가
      작성한 원본 메타데이터이므로 raw 보존 원칙에 어긋나지 않는다.
    """
    cues = _parse_cues(raw)

    # 롤링 중복 제거: 자동자막은 큐마다 직전 행을 반복 표시한다.
    # 최근 4행을 기억하며 완전 일치하는 행만 걸러낸다.
    # (부분 일치·유사도 판단은 하지 않는다 — 원문 손실 위험)
    recent: deque[str] = deque(maxlen=4)
    out: list[tuple[float, str]] = []

    for start, text_lines in cues:
        fresh: list[str] = []
        for line in text_lines:
            cleaned = _clean_line(line)
            if not cleaned:
                continue
            if cleaned in recent:
                continue
            recent.append(cleaned)
            fresh.append(cleaned)
        if fresh:
            out.append((start, " ".join(fresh)))

    if not out:
        return ""

    # 챕터 경계를 (시작초, 제목)으로 정리해 둔다
    marks: list[tuple[float, str]] = []
    for ch in chapters or []:
        title = (ch.get("title") or "").strip()
        start = ch.get("start_time")
        if title and start is not None:
            marks.append((float(start), title))
    marks.sort(key=lambda m: m[0])

    parts: list[str] = []
    mi = 0
    for start, text in out:
        # 이 큐 시점을 지난 챕터 제목을 먼저 흘려보낸다
        while mi < len(marks) and marks[mi][0] <= start:
            parts.append(marks[mi][1])
            mi += 1
        if timestamp_style == "none":
            parts.append(text)
        elif timestamp_style == "prefix":
            parts.append(f"[{format_timestamp(start)}] {text}")
        else:  # line
            parts.append(f"{format_timestamp(start)}\n{text}")

    body = "\n".join(parts)
    body = re.sub(r"\n{3,}", "\n\n", body)  # 과도한 빈 줄 정리
    return body.strip()
