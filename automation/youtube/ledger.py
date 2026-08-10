"""수집 이력 관리 (중복 방지 · 상태 · 재시도 백오프).

채널별 JSON 파일로 분리한다 — OneDrive 동기화 충돌 사본이 생겨도
피해 범위가 한 채널로 제한된다.

status:
  success   저장 완료               → 종결
  no_caption 자막 없음              → 백오프 재시도 (업로드 직후엔 자동자막이 아직 없다)
  failed    네트워크·yt-dlp 오류    → 백오프 재시도
  skipped   정책 제외(Shorts 등)    → --force 로만
  baseline  최초 실행 시점 기존영상 → --backfill 로만
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

KST = timezone(timedelta(hours=9))
SCHEMA = 1

# 재시도 간격: 30분 → 2시간 → 6시간 → 24시간 → 24시간 …
_BACKOFF_HOURS = [0.5, 2, 6, 24]
MAX_ATTEMPTS = 8          # 이후 포기
RETRYABLE = ("no_caption", "failed")


def now_kst() -> datetime:
    return datetime.now(KST)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _safe_stem(name: str) -> str:
    """채널명을 파일명으로 쓸 수 있게. 상태파일 전용이므로 보수적으로."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(". ") or "channel"


class Ledger:
    def __init__(self, state_dir: Path, channel: str):
        self.path = state_dir / f"{_safe_stem(channel)}.json"
        self.channel = channel
        self._data = self._load()

    def _load(self) -> dict:
        if not self.path.exists():
            return {"schema": SCHEMA, "channel": self.channel,
                    "baseline_at": None, "videos": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # 손상 시 백업 후 새로 시작 (수집 이력보다 계속 동작이 우선)
            if self.path.exists():
                self.path.replace(self.path.with_suffix(f".corrupt-{int(time.time())}.json"))
            return {"schema": SCHEMA, "channel": self.channel,
                    "baseline_at": None, "videos": {}}
        data.setdefault("videos", {})
        data.setdefault("baseline_at", None)
        return data

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f".{self.path.stem}.{os.getpid()}.tmp")
        tmp.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        delay = 0.5
        for attempt in range(4):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if attempt == 3:
                    tmp.unlink(missing_ok=True)
                    raise
                time.sleep(delay)
                delay *= 2

    # ---- baseline ----

    @property
    def baseline_at(self) -> str | None:
        return self._data.get("baseline_at")

    def set_baseline(self, when: datetime) -> None:
        self._data["baseline_at"] = iso(when)

    # ---- 조회 ----

    def get(self, video_id: str) -> dict | None:
        return self._data["videos"].get(video_id)

    def known(self, video_id: str) -> bool:
        return video_id in self._data["videos"]

    def all_items(self) -> dict[str, dict]:
        return self._data["videos"]

    def taken_filenames(self) -> set[str]:
        return {
            Path(v["file"]).name
            for v in self._data["videos"].values()
            if v.get("file")
        }

    def should_retry(self, video_id: str, now: datetime | None = None) -> bool:
        rec = self.get(video_id)
        if rec is None:
            return True
        if rec.get("status") not in RETRYABLE:
            return False
        if rec.get("attempts", 0) >= MAX_ATTEMPTS:
            return False
        nxt = rec.get("next_retry_after")
        if not nxt:
            return True
        now = now or now_kst()
        try:
            return now >= datetime.fromisoformat(nxt)
        except ValueError:
            return True

    # ---- 기록 ----

    def record(
        self,
        video_id: str,
        *,
        title: str,
        published: str,
        status: str,
        file: str | None = None,
        error: str | None = None,
        language: str | None = None,
        transcript_source: str | None = None,
    ) -> None:
        now = now_kst()
        rec = self._data["videos"].get(video_id, {})
        attempts = rec.get("attempts", 0) + 1 if status in RETRYABLE else rec.get("attempts", 0)

        entry = {
            "channel": self.channel,
            "title": title,
            "published": published,
            "status": status,
            "attempts": attempts,
            "first_seen": rec.get("first_seen", iso(now)),
            "last_attempt": iso(now),
            "file": file,
        }
        if language:
            entry["language"] = language
        if transcript_source:
            entry["transcript_source"] = transcript_source
        if status in RETRYABLE:
            if attempts < MAX_ATTEMPTS:
                hours = _BACKOFF_HOURS[min(attempts - 1, len(_BACKOFF_HOURS) - 1)]
                entry["next_retry_after"] = iso(now + timedelta(hours=hours))
            entry["last_error"] = (error or "")[:500]
        elif status == "success":
            entry.pop("last_error", None)
        elif error:
            entry["last_error"] = error[:500]

        self._data["videos"][video_id] = entry

    def clear_backoff(self) -> int:
        """--retry-failed: 재시도 가능 항목의 대기시간을 즉시 해제한다."""
        n = 0
        for rec in self._data["videos"].values():
            if rec.get("status") in RETRYABLE:
                rec.pop("next_retry_after", None)
                rec["attempts"] = 0
                n += 1
        return n
