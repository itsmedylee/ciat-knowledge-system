"""YouTube 채널 신규 영상 → transcript → raw/ 자동 수집.

    python automation/youtube/youtube_watcher.py
    python automation/youtube/youtube_watcher.py --dry-run
    python automation/youtube/youtube_watcher.py --channel "세무법인다솔"
    python automation/youtube/youtube_watcher.py --retry-failed
    python automation/youtube/youtube_watcher.py --backfill 10

이 스크립트는 raw/ 에 원본 transcript를 넣는 것까지만 한다.
지식 가공(sources → topics → index/log)은 기존 /ingest 가 수동으로 담당한다.
"""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from captions import (
    CaptionError,
    NoCaptionError,
    VideoUnavailableError,
    fetch_meta_and_transcript,
)
from ledger import KST, Ledger, iso, now_kst
from normalize import normalize
from resolver import (
    ChannelResolver,
    ResolveError,
    fetch_feed,
    fetch_recent_via_ytdlp,
)
from writer import atomic_write, build_filename, build_markdown

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
CONFIG_PATH = HERE / "channels.yaml"
STATE_DIR = HERE / "state"
LOG_DIR = HERE / "logs"

log = logging.getLogger("youtube-watcher")

# 로그에서 지워야 할 민감 패턴 (쿠키·토큰·서명된 URL 파라미터)
_SENSITIVE = re.compile(
    r"(cookie|authorization|token|signature|__Secure|SAPISID|sig=|key=)[^\s&\"']*",
    re.IGNORECASE,
)


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE.sub(r"\1<redacted>", record.msg)
        return True


def setup_logging(verbose: bool) -> None:
    # Windows 콘솔 기본 코드페이지(cp949)는 한글 로그와 em dash를 처리하지 못한다.
    # Task Scheduler에서 파이프로 실행될 때도 마찬가지라 명시적으로 UTF-8로 고정한다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / "youtube-watcher.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter("%(message)s"))
    console.setLevel(logging.DEBUG if verbose else logging.INFO)

    log.setLevel(logging.DEBUG)
    log.addFilter(_RedactFilter())
    log.addHandler(file_handler)
    log.addHandler(console)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"설정 파일이 없다: {CONFIG_PATH}")
    with CONFIG_PATH.open(encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    if not cfg.get("channels"):
        raise SystemExit("channels.yaml 에 channels 항목이 없다.")
    return cfg


def _published_str(item_published: datetime, upload_date: str | None) -> str:
    """게시일 YYYY-MM-DD. yt-dlp의 upload_date를 우선한다(RSS보다 정확)."""
    if upload_date and len(upload_date) == 8:
        return f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    if item_published and item_published.year > 1:
        return item_published.astimezone(KST).strftime("%Y-%m-%d")
    return now_kst().strftime("%Y-%m-%d")


def process_video(
    *,
    video_id: str,
    feed_title: str,
    feed_published: datetime,
    channel_cfg: dict,
    ledger: Ledger,
    raw_dir: Path,
    dry_run: bool,
) -> str:
    """한 영상을 처리하고 status를 반환한다."""
    channel_name = channel_cfg["name"]
    timestamp_style = channel_cfg.get("timestamp_style", "prefix")
    min_duration = channel_cfg.get("min_duration_sec", 0)

    if dry_run:
        log.info("  [DRY-RUN] 처리 예정: %s — %s", video_id, feed_title)
        return "dry_run"

    try:
        meta, result = fetch_meta_and_transcript(video_id)
    except VideoUnavailableError as exc:
        log.warning("  ✗ %s 접근 불가(비공개·삭제) — %s", video_id, exc)
        ledger.record(video_id, title=feed_title,
                      published=_published_str(feed_published, None),
                      status="skipped", error=str(exc))
        return "skipped"
    except NoCaptionError as exc:
        log.info("  · %s 자막 없음 → 나중에 재시도 — %s", video_id, exc)
        ledger.record(video_id, title=feed_title,
                      published=_published_str(feed_published, None),
                      status="no_caption", error=str(exc))
        return "no_caption"
    except CaptionError as exc:
        log.warning("  ✗ %s 추출 실패 — %s", video_id, exc)
        ledger.record(video_id, title=feed_title,
                      published=_published_str(feed_published, None),
                      status="failed", error=str(exc))
        return "failed"

    published = _published_str(feed_published, meta.upload_date)

    # Shorts 등 정책 제외
    if min_duration and meta.duration and meta.duration < min_duration:
        log.info("  · %s 제외(길이 %ss < %ss)", video_id, meta.duration, min_duration)
        ledger.record(video_id, title=meta.title, published=published,
                      status="skipped", error=f"duration {meta.duration}s")
        return "skipped"

    transcript = normalize(
        result.raw_text, timestamp_style=timestamp_style, chapters=meta.chapters
    )
    if not transcript.strip():
        log.info("  · %s 정규화 결과가 비었다 → 재시도 대상", video_id)
        ledger.record(video_id, title=meta.title, published=published,
                      status="no_caption", error="normalized transcript empty")
        return "no_caption"

    taken = ledger.taken_filenames() | {p.name for p in raw_dir.glob("*.md")}
    filename = build_filename(published, meta.title, video_id, taken)
    out_path = raw_dir / filename

    content = build_markdown(
        title=meta.title,
        channel=channel_name,
        video_id=video_id,
        published=published,
        collected=iso(now_kst()),
        language=result.language,
        transcript_source=result.source,
        transcript=transcript,
        duration=meta.duration,
    )

    try:
        atomic_write(out_path, content)
    except OSError as exc:
        log.error("  ✗ %s 저장 실패 — %s", video_id, exc)
        ledger.record(video_id, title=meta.title, published=published,
                      status="failed", error=f"write failed: {exc}")
        return "failed"

    # raw_dir 오설정(절대경로·상위경로)으로 저장소 밖을 가리켜도 여기서 죽지 않게 한다.
    # 파일은 이미 쓰인 뒤라, 여기서 예외가 나면 ledger 기록이 유실된다.
    try:
        rel = out_path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        rel = out_path.as_posix()
    log.info("  ✓ %s [%s/%s] → %s", video_id, result.source, result.language, rel)
    ledger.record(video_id, title=meta.title, published=published, status="success",
                  file=rel, language=result.language, transcript_source=result.source)
    return "success"


def _seal_baseline(ledger: Ledger, args: argparse.Namespace, name: str) -> None:
    """backfill 로 시작한 채널의 baseline_at 을 확정한다.

    --backfill 은 baseline 등록 분기를 건너뛰므로 baseline_at 이 None 으로 남는다.
    그대로 두면 다음 일반 실행이 "최초 실행"으로 오인해 RSS 15건의 ledger 상태를
    baseline 으로 덮어쓴다(record() 는 status 를 무조건 덮어쓴다). 수집된 raw 파일은
    남지만 success·no_caption 기록이 지워져 재시도 대상이 유실된다.
    2026-08-21 상속마스터 정변 채널에서 실제로 4건이 이 경로로 손상됐다.
    """
    if not args.backfill or args.dry_run or ledger.baseline_at is not None:
        return
    ledger.set_baseline(now_kst())
    ledger.save()
    log.info("[%s] baseline_at 확정 — 이후 일반 실행이 이력을 덮어쓰지 않는다", name)


def run_channel(channel_cfg: dict, args: argparse.Namespace, defaults: dict) -> dict:
    name = channel_cfg["name"]
    stats = {"success": 0, "no_caption": 0, "failed": 0, "skipped": 0,
             "dry_run": 0, "baseline": 0, "channel_error": 0}

    raw_rel = channel_cfg.get("raw_dir")
    if not raw_rel:
        log.error("[%s] raw_dir 미지정 — 건너뛴다", name)
        stats["channel_error"] = 1
        return stats
    raw_dir = (REPO_ROOT / raw_rel).resolve()

    ledger = Ledger(STATE_DIR, name)
    resolver = ChannelResolver(STATE_DIR)

    try:
        channel_id = resolver.resolve(channel_cfg["url"])
    except ResolveError as exc:
        log.error("[%s] %s", name, exc)
        stats["channel_error"] = 1
        return stats

    log.info("[%s] channel_id=%s → %s", name, channel_id, raw_rel)

    if args.retry_failed:
        n = ledger.clear_backoff()
        log.info("[%s] 재시도 대기 해제 %d건", name, n)

    # ---- 대상 수집 ----
    try:
        if args.backfill:
            items = fetch_recent_via_ytdlp(channel_cfg["url"], args.backfill)
            log.info("[%s] backfill 조회 %d건", name, len(items))
        else:
            items = fetch_feed(channel_id)
            log.debug("[%s] RSS %d건", name, len(items))
    except ResolveError as exc:
        log.error("[%s] %s", name, exc)
        stats["channel_error"] = 1
        return stats

    # ---- 최초 실행: baseline 등록만 하고 다운로드하지 않는다 ----
    if ledger.baseline_at is None and not args.backfill:
        now = now_kst()
        for item in items:
            ledger.record(item.video_id, title=item.title,
                          published=item.published.astimezone(KST).strftime("%Y-%m-%d"),
                          status="baseline")
            stats["baseline"] += 1
        ledger.set_baseline(now)
        if not args.dry_run:
            ledger.save()
        log.info(
            "[%s] 최초 실행 — baseline %d건 등록(다운로드 없음). "
            "이후 신규분부터 수집한다. 과거분은 --backfill N 사용.",
            name, stats["baseline"],
        )
        return stats

    baseline_dt = None
    if ledger.baseline_at:
        try:
            baseline_dt = datetime.fromisoformat(ledger.baseline_at)
        except ValueError:
            baseline_dt = None

    # ---- 처리 대상 선별 ----
    targets = []
    for item in items:
        rec = ledger.get(item.video_id)
        if rec and rec.get("status") == "success":
            continue
        if rec and not ledger.should_retry(item.video_id):
            continue
        if rec is None and baseline_dt and not args.backfill:
            # baseline 이전 영상은 신규가 아니다
            if item.published.year > 1 and item.published < baseline_dt - timedelta(minutes=5):
                ledger.record(item.video_id, title=item.title,
                              published=item.published.astimezone(KST).strftime("%Y-%m-%d"),
                              status="baseline")
                stats["baseline"] += 1
                continue
        targets.append(item)

    if not targets:
        log.info("[%s] 신규 영상 없음", name)
        _seal_baseline(ledger, args, name)
        if not args.dry_run:
            ledger.save()
        return stats

    log.info("[%s] 처리 대상 %d건", name, len(targets))
    for item in targets:
        status = process_video(
            video_id=item.video_id,
            feed_title=item.title,
            feed_published=item.published,
            channel_cfg={**defaults, **channel_cfg},
            ledger=ledger,
            raw_dir=raw_dir,
            dry_run=args.dry_run,
        )
        stats[status] = stats.get(status, 0) + 1
        if not args.dry_run:
            ledger.save()   # 영상마다 저장 — 중간에 죽어도 이력이 남는다

    _seal_baseline(ledger, args, name)
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="YouTube 채널 신규 영상 transcript를 raw/ 에 수집한다."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="파일을 만들지 않고 처리 대상만 보여준다")
    parser.add_argument("--channel", help="특정 채널만 처리 (channels.yaml 의 name)")
    parser.add_argument("--retry-failed", action="store_true",
                        help="no_caption·failed 항목의 재시도 대기를 즉시 해제")
    parser.add_argument("--backfill", type=int, metavar="N",
                        help="baseline을 무시하고 과거 N건을 수집")
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    setup_logging(args.verbose)
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    cfg = load_config()
    defaults = cfg.get("defaults") or {}
    channels = [c for c in cfg["channels"] if c.get("enabled", True)]

    if args.channel:
        channels = [c for c in channels if c.get("name") == args.channel]
        if not channels:
            log.error("채널을 찾을 수 없다: %s", args.channel)
            return 1

    if not channels:
        log.info("활성화된 채널이 없다.")
        return 0

    log.info("=== 실행 %s%s ===", now_kst().strftime("%Y-%m-%d %H:%M:%S"),
             " [DRY-RUN]" if args.dry_run else "")

    total: dict[str, int] = {}
    exit_code = 0
    for channel_cfg in channels:
        try:
            stats = run_channel(channel_cfg, args, defaults)
        except Exception as exc:  # noqa: BLE001 - 한 채널 실패가 전체를 막지 않는다
            log.exception("[%s] 예기치 못한 오류 — %s", channel_cfg.get("name"), exc)
            exit_code = 1
            continue
        for k, v in stats.items():
            total[k] = total.get(k, 0) + v

    summary = " · ".join(f"{k} {v}" for k, v in total.items() if v)
    log.info("=== 완료: %s ===", summary or "변경 없음")
    # 실패는 종료코드로 드러낸다 — Task Scheduler의 "마지막 실행 결과"에 표시된다
    if total.get("failed") or total.get("channel_error"):
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
