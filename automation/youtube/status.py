"""각 채널의 수집 상태를 점검하고 backfill 필요 여부를 판정한다.

    python automation/youtube/status.py

수집 자체는 하지 않는다 — 읽기 전용이다.

RSS는 최신 15건만 반환하고 Shorts도 그 15건을 차지한다. 오래 쉬었다가 일반 실행을
돌리면 그 사이 영상이 창 밖으로 밀려나 영구 누락된다. 이 스크립트는 그 상황을
"RSS 창의 가장 오래된 영상이 마지막 수집분보다 나중인가"로 판정한다 — 그렇다면
두 시점 사이에 RSS로 볼 수 없는 구멍이 있다는 뜻이다.

판정 결과:
  OK       일반 실행으로 충분하다
  BACKFILL RSS 창 밖으로 밀려난 구간이 있다 → --backfill N 을 함께 쓴다
  NEW      아직 수집 이력이 없다 → --backfill 로 시작한다
"""

from __future__ import annotations

import sys
import unicodedata
from datetime import datetime
from pathlib import Path

from ledger import KST, Ledger
from resolver import ChannelResolver, ResolveError, fetch_feed
from youtube_watcher import STATE_DIR, load_config


def _w(text: str) -> int:
    """한글·전각 문자를 2칸으로 세는 표시 폭."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _w(text))


def _last_collected(ledger: Ledger) -> tuple[str | None, int]:
    """(가장 최근 수집 영상의 게시일, success 건수)"""
    dates = [v.get("published") for v in ledger.all_items().values()
             if v.get("status") == "success" and v.get("published")]
    return (max(dates) if dates else None, len(dates))


def _pending(ledger: Ledger) -> int:
    return sum(1 for v in ledger.all_items().values()
               if v.get("status") in ("no_caption", "failed"))


def main() -> int:
    cfg = load_config()
    # enabled: false 채널도 표에는 남긴다 — 목록에서 조용히 사라지면
    # "감시하지 않기로 한 채널"과 "설정을 실수로 빠뜨린 채널"을 구분할 수 없다.
    channels = cfg["channels"]
    resolver = ChannelResolver(STATE_DIR)
    today = datetime.now(KST).date()

    rows: list[tuple[str, str, str, str, str, str]] = []
    actions: list[str] = []

    for ch in channels:
        name = ch["name"]
        ledger = Ledger(STATE_DIR, name)
        last, n_success = _last_collected(ledger)
        pending = _pending(ledger)

        if not ch.get("enabled", True):
            rows.append((name, last or "-", "-", "-", "OFF",
                         f"채널 감시 안 함 · 수집 {n_success}건 · 재생목록만 수동 수집"))
            continue

        try:
            channel_id = resolver.resolve(ch["url"])
            items = fetch_feed(channel_id)
        except (ResolveError, OSError) as exc:
            rows.append((name, last or "-", "-", "?", "ERROR", str(exc)[:40]))
            continue

        published = sorted(i.published for i in items if i.published.year > 1)
        if not published:
            rows.append((name, last or "-", "-", "?", "ERROR", "RSS 게시일 없음"))
            continue

        rss_oldest = published[0].astimezone(KST).date()
        rss_newest = published[-1].astimezone(KST).date()
        window = (rss_newest - rss_oldest).days

        if last is None:
            verdict, note = "NEW", "수집 이력 없음"
            actions.append(f'python automation/youtube/youtube_watcher.py --channel "{name}" --backfill 50')
        else:
            last_date = datetime.strptime(last, "%Y-%m-%d").date()
            idle = (today - last_date).days
            if rss_oldest > last_date:
                # RSS 창의 하단이 마지막 수집분보다 뒤 → 사이 구간을 볼 수 없다
                gap = (rss_oldest - last_date).days
                verdict = "BACKFILL"
                note = f"{gap}일치 구간이 RSS 창 밖"
                # 창 밖 구간 + 창 안 15건을 함께 덮도록 여유 있게 잡는다
                actions.append(
                    f'python automation/youtube/youtube_watcher.py --channel "{name}" --backfill 50')
            else:
                verdict = "OK"
                note = f"미수집 {idle}일 (창 여유 {(last_date - rss_oldest).days}일)"

        if pending:
            note += f" · 재시도대기 {pending}건"

        rows.append((name, last or "-", f"{rss_oldest}~{rss_newest}",
                     f"{window}일", verdict, note))

    width = max(_w(r[0]) for r in rows) + 2
    header = (f"{_pad('채널', width)} {_pad('마지막수집', 12)} {_pad('RSS 창', 24)} "
              f"{_pad('폭', 6)} {_pad('판정', 9)} 비고")
    print(header)
    print("-" * _w(header))
    for name, last, rng, window, verdict, note in rows:
        print(f"{_pad(name, width)} {_pad(last, 12)} {_pad(rng, 24)} "
              f"{_pad(window, 6)} {_pad(verdict, 9)} {note}")

    if actions:
        print("\n권장 실행:")
        for a in dict.fromkeys(actions):
            print(f"  {a}")
    else:
        print("\n권장 실행: python automation/youtube/youtube_watcher.py  (전 채널 일반 실행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
