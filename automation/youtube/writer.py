"""Markdown 조립 + 원자적 저장.

OneDrive 동기화 폴더에서 동작하므로:
  - 같은 디렉터리에 .tmp 작성 → os.replace (동일 볼륨 → Windows에서도 원자적)
  - 동기화 잠금(PermissionError) 시 지수 백오프 재시도
  - 경로 260자 제한 대비 제목 절단
"""

from __future__ import annotations

import os
import re
import time
import unicodedata
from pathlib import Path

# Windows 금지 문자
_ILLEGAL = re.compile(r'[<>:"/\\|?*]')
# 제어문자
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
# Obsidian 위키링크를 깨는 문자 — 파일 시스템은 허용하지만 [[링크]]로 가리킬 수 없다.
#   #  : 이후가 heading anchor로 해석된다. 이스케이프 수단이 없다.
#   ^  : 이후가 block reference로 해석된다.
#   [] : 선행 대괄호는 링크 여는 괄호에 먹혀 깨진 링크 → 클릭 시 유령 노트가 생성된다.
# (CLAUDE.md 「대괄호로 시작하는 파일명」 참조)
_LINK_HOSTILE = re.compile(r"[#^\[\]]")
# Windows 예약 파일명
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

# 제목 부분 최대 길이 (경로 260자 제한 + 한글 폴더명 대비)
MAX_TITLE_LEN = 80


def sanitize_title(title: str) -> str:
    """파일명에 쓸 수 있게 만든다. 제목을 임의로 변형하지 않는다 —
    금지 문자 제거와 길이 절단만 수행한다."""
    name = unicodedata.normalize("NFC", title)
    name = _CONTROL.sub("", name)
    name = _ILLEGAL.sub("", name)
    name = _LINK_HOSTILE.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    name = name.rstrip(". ")  # Windows는 마침표/공백으로 끝나는 이름을 거부

    if name.upper() in _RESERVED or name.split(".")[0].upper() in _RESERVED:
        name = f"_{name}"

    if len(name) > MAX_TITLE_LEN:
        name = name[:MAX_TITLE_LEN].rstrip(". ")

    return name or "untitled"


def build_filename(published: str, title: str, video_id: str, taken: set[str]) -> str:
    """YYYY-MM-DD-제목.md — 충돌 시 video_id 앞 6자를 덧붙인다."""
    base = f"{published}-{sanitize_title(title)}"
    candidate = f"{base}.md"
    if candidate not in taken:
        return candidate

    candidate = f"{base}-{video_id[:6]}.md"
    if candidate not in taken:
        return candidate

    # 극히 예외적인 경우에만 도달
    n = 2
    while f"{base}-{video_id[:6]}-{n}.md" in taken:
        n += 1
    return f"{base}-{video_id[:6]}-{n}.md"


def _yaml_quote(value: str) -> str:
    """frontmatter 값 안전 인용 (제목에 콜론·따옴표가 흔하다)."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_markdown(
    *,
    title: str,
    channel: str,
    video_id: str,
    published: str,
    collected: str,
    language: str,
    transcript_source: str,
    transcript: str,
    duration: int | None = None,
) -> str:
    url = f"https://www.youtube.com/watch?v={video_id}"
    label = {
        "manual-caption": "제작자 업로드 자막",
        "auto-caption": "자동생성 자막",
        "whisper": "Whisper 전사",
    }.get(transcript_source, transcript_source)

    lines = [
        "---",
        "type: youtube-transcript",
        "source_type: youtube",
        f"channel: {_yaml_quote(channel)}",
        f"title: {_yaml_quote(title)}",
        f"video_id: {_yaml_quote(video_id)}",
        f"url: {_yaml_quote(url)}",
        f"published: {published}",
        f"collected: {collected}",
        f"language: {language}",
        f"transcript_source: {transcript_source}",
        "status: raw",
        "---",
        "",
        f"# {title}",
        "",
        "## 영상 정보",
        "",
        f"- 채널: {channel}",
        f"- 게시일: {published}",
        f"- YouTube: {url}",
        f"- 자막 유형: {label} ({language})",
    ]
    if duration:
        h, rem = divmod(int(duration), 3600)
        m, s = divmod(rem, 60)
        lines.append(f"- 길이: {h}:{m:02d}:{s:02d}" if h else f"- 길이: {m}:{s:02d}")

    if transcript_source == "auto-caption":
        lines += [
            "",
            "> ⚠️ 자동생성 자막이다. 세법·회계 전문용어, 수치, 법령명에 "
            "**오인식 가능성**이 있다. ingest 시 확정 서술로 승격하기 전에 "
            "원문 대조가 필요하다.",
        ]

    lines += ["", "## Transcript", "", transcript, ""]
    return "\n".join(lines)


def atomic_write(path: Path, content: str, retries: int = 4) -> None:
    """같은 디렉터리에 임시파일을 쓴 뒤 원자적으로 교체한다.

    OneDrive 동기화가 대상 파일을 잠그면 잠시 후 재시도한다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.stem}.{os.getpid()}.tmp")

    # 개행은 LF로 고정 (기존 위키 파일과 일치)
    tmp.write_text(content, encoding="utf-8", newline="\n")

    delay = 0.5
    for attempt in range(retries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == retries - 1:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(delay)
            delay *= 2
        except Exception:
            tmp.unlink(missing_ok=True)
            raise
