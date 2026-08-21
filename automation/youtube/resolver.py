"""채널 URL 정규화 + RSS 기반 신규 영상 감지.

채널 ID 해석은 yt-dlp를 쓰지만 **채널당 1회**만 하고 캐시한다.
이후 폴링은 RSS만 사용한다 (API 키 불필요, rate limit 사실상 없음).

RSS는 최신 15건만 제공한다 — 1시간 폴링에는 충분하다.
과거 영상은 --backfill 이 yt-dlp 로 별도 조회한다.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "yt": "http://www.youtube.com/xml/schemas/2015",
    "media": "http://search.yahoo.com/mrss/",
}
_UC_RE = re.compile(r"(UC[0-9A-Za-z_-]{22})")
_USER_AGENT = "Mozilla/5.0 (compatible; llm-wiki-youtube-watcher/1.0)"


class ResolveError(Exception):
    pass


@dataclass
class FeedItem:
    video_id: str
    title: str
    published: datetime


class ChannelResolver:
    """URL → UC 채널 ID. 결과를 state/resolved_channels.json 에 캐시한다.

    channels.yaml 을 코드가 다시 쓰지 않는다 — PyYAML 왕복은 주석과
    서식을 지우기 때문에, 사용자가 관리하는 설정파일은 읽기 전용으로 둔다.
    """

    def __init__(self, state_dir: Path):
        self.path = state_dir / "resolved_channels.json"
        try:
            self._cache = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            self._cache = {}

    def resolve(self, url: str) -> str:
        # 이미 UC ID를 포함하는 URL이면 yt-dlp 호출 자체가 불필요하다
        direct = _UC_RE.search(url)
        if direct:
            return direct.group(1)

        if url in self._cache:
            return self._cache[url]

        try:
            with YoutubeDL(
                {"quiet": True, "no_warnings": True, "skip_download": True,
                 "extract_flat": True, "playlistend": 1}
            ) as ydl:
                info = ydl.extract_info(url, download=False)
        except DownloadError as exc:
            raise ResolveError(f"채널 URL 해석 실패: {url} — {exc}") from exc

        channel_id = info.get("channel_id") or info.get("uploader_id") or ""
        if not _UC_RE.fullmatch(channel_id or ""):
            found = _UC_RE.search(json.dumps(info, default=str)[:20000])
            if not found:
                raise ResolveError(f"채널 ID를 찾지 못했다: {url}")
            channel_id = found.group(1)

        self._cache[url] = channel_id
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
        )
        return channel_id


def fetch_feed(channel_id: str, timeout: int = 30) -> list[FeedItem]:
    """RSS로 최신 영상 목록을 가져온다 (최대 15건)."""
    req = urllib.request.Request(
        RSS_URL.format(channel_id), headers={"User-Agent": _USER_AGENT}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ResolveError(f"채널을 찾을 수 없다(404): {channel_id}") from exc
        raise ResolveError(f"RSS HTTP {exc.code}: {channel_id}") from exc
    except urllib.error.URLError as exc:
        raise ResolveError(f"RSS 네트워크 오류: {exc.reason}") from exc

    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError as exc:
        raise ResolveError(f"RSS 파싱 실패: {exc}") from exc

    items: list[FeedItem] = []
    for entry in root.findall("atom:entry", _NS):
        vid = entry.findtext("yt:videoId", namespaces=_NS)
        title = entry.findtext("atom:title", namespaces=_NS)
        published = entry.findtext("atom:published", namespaces=_NS)
        if not (vid and title and published):
            continue
        items.append(
            FeedItem(
                video_id=vid,
                title=title.strip(),
                published=datetime.fromisoformat(published.replace("Z", "+00:00")),
            )
        )
    return items


def fetch_recent_via_ytdlp(channel_url: str, limit: int) -> list[FeedItem]:
    """--backfill 전용. RSS 15건 창을 넘어 과거 영상을 조회한다."""
    url = channel_url.rstrip("/")
    if not url.endswith(("/videos", "/streams", "/shorts")):
        url += "/videos"
    try:
        with YoutubeDL(
            {"quiet": True, "no_warnings": True, "skip_download": True,
             "extract_flat": "in_playlist", "playlistend": limit,
             # 지정하지 않으면 YouTube가 제목을 자동 번역해서 준다
             # (captions.py·playlist_fetch.py와 동일 조치)
             "extractor_args": {"youtube": {"lang": ["ko"]}}}
        ) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        raise ResolveError(f"채널 목록 조회 실패: {channel_url} — {exc}") from exc

    items: list[FeedItem] = []
    for entry in (info.get("entries") or [])[:limit]:
        if not entry or not entry.get("id"):
            continue
        # flat 추출은 게시일을 주지 않는 경우가 많다 → 개별 처리 단계에서 확정한다
        items.append(
            FeedItem(
                video_id=entry["id"],
                title=(entry.get("title") or entry["id"]).strip(),
                published=datetime.min.replace(tzinfo=None),
            )
        )
    return items
