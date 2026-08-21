"""특정 YouTube 재생목록의 영상들을 raw/ 로 수집한다.

    python automation/youtube/playlist_fetch.py --channel "채널명" --playlist-url "URL"
    python automation/youtube/playlist_fetch.py --channel "채널명" --playlist-url "URL" --dry-run

channels.yaml 의 채널 설정(raw_dir·timestamp_style·min_duration_sec)과 동일 채널의
ledger(state/<채널>.json)를 그대로 재사용한다. 채널 watcher(RSS 기반)가 이미 받은
영상은 중복 다운로드하지 않고, 여기서 받은 영상은 video_id 기준으로 같은 ledger에
기록되므로 이후 채널 watcher도 다시 받지 않는다.

이 스크립트는 raw/ 에 원본 transcript를 넣는 것까지만 한다.
지식 가공(sources → topics → index/log)은 기존 /ingest 가 수동으로 담당한다.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

from ledger import Ledger, now_kst
from youtube_watcher import REPO_ROOT, STATE_DIR, load_config, log, process_video, setup_logging


def fetch_playlist_entries(playlist_url: str) -> list[tuple[str, str]]:
    """재생목록 영상의 (video_id, title) 목록을 재생목록 순서대로 반환한다."""
    try:
        with YoutubeDL(
            {"quiet": True, "no_warnings": True, "skip_download": True,
             "extract_flat": "in_playlist",
             # 지정하지 않으면 YouTube가 제목을 자동 번역해서 준다 (captions.py와 동일 조치)
             "extractor_args": {"youtube": {"lang": ["ko"]}}}
        ) as ydl:
            info = ydl.extract_info(playlist_url, download=False)
    except DownloadError as exc:
        raise SystemExit(f"재생목록 조회 실패: {playlist_url} — {exc}") from exc

    entries: list[tuple[str, str]] = []
    for entry in info.get("entries") or []:
        if not entry or not entry.get("id"):
            continue
        entries.append((entry["id"], (entry.get("title") or entry["id"]).strip()))
    return entries


def main() -> int:
    parser = argparse.ArgumentParser(description="특정 재생목록의 transcript를 raw/ 에 수집한다.")
    parser.add_argument("--playlist-url", required=True)
    parser.add_argument("--channel", required=True,
                        help="channels.yaml 의 채널 name (raw_dir·설정·ledger 재사용)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    defaults = cfg.get("defaults") or {}
    channel_cfg = next((c for c in cfg["channels"] if c.get("name") == args.channel), None)
    if channel_cfg is None:
        log.error("채널을 찾을 수 없다: %s", args.channel)
        return 1

    raw_rel = channel_cfg.get("raw_dir")
    if not raw_rel:
        log.error("[%s] raw_dir 미지정", args.channel)
        return 1
    raw_dir = (REPO_ROOT / raw_rel).resolve()

    entries = fetch_playlist_entries(args.playlist_url)
    log.info("재생목록 조회 %d건 — %s", len(entries), args.playlist_url)

    ledger = Ledger(STATE_DIR, args.channel)
    merged_cfg = {**defaults, **channel_cfg}

    stats: dict[str, int] = {}
    for video_id, title in entries:
        rec = ledger.get(video_id)
        if rec and rec.get("status") == "success":
            log.info("  · %s 이미 수집됨 — 건너뜀 (%s)", video_id, rec.get("file"))
            stats["already"] = stats.get("already", 0) + 1
            continue
        # baseline(채널 RSS 첫 실행 시 스킵 표시)·no_caption·failed 는 재생목록을
        # 명시적으로 지정한 이상 백오프·baseline 정책과 무관하게 다시 시도한다.

        status = process_video(
            video_id=video_id,
            feed_title=title,
            feed_published=datetime.min,
            channel_cfg=merged_cfg,
            ledger=ledger,
            raw_dir=raw_dir,
            dry_run=args.dry_run,
        )
        stats[status] = stats.get(status, 0) + 1
        if not args.dry_run:
            ledger.save()

    # 재생목록 수집도 baseline 등록 분기를 거치지 않는다 — 채널 watcher 가 이후
    # "최초 실행"으로 오인해 이력을 덮어쓰지 않도록 baseline_at 을 확정한다.
    if not args.dry_run and ledger.baseline_at is None:
        ledger.set_baseline(now_kst())
        ledger.save()
        log.info("[%s] baseline_at 확정 — 이후 일반 실행이 이력을 덮어쓰지 않는다", args.channel)

    summary = " · ".join(f"{k} {v}" for k, v in stats.items() if v)
    log.info("=== 완료: %s ===", summary or "변경 없음")
    return 1 if stats.get("failed") else 0


if __name__ == "__main__":
    sys.exit(main())
