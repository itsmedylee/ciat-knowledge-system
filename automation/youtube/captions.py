"""yt-dlp 기반 자막 추출 (TranscriptProvider).

우선순위:
  1. 제작자 업로드 한국어 자막   → manual-caption / ko
  2. 한국어 자동생성 자막(원어)  → auto-caption   / ko
  3. 제작자 업로드 영어 자막     → manual-caption / en
  4. 영어 자동생성 자막(원어)    → auto-caption   / en
  5. 없음                        → NoCaptionError

⚠️ 기계번역 자막은 절대 사용하지 않는다.
   YouTube는 automatic_captions에 100여 개 언어의 **자동 번역본**을 함께 노출한다.
   영어 영상의 'ko' 자동자막을 받으면 그것은 ASR 결과가 아니라 기계번역이며,
   raw = source of truth 원칙이 근본적으로 깨진다.
   따라서 자동자막은 **영상의 원어와 일치할 때만** 채택한다.

향후 Whisper fallback은 이 모듈과 같은 인터페이스
(fetch_transcript(video_id) -> TranscriptResult)를 구현해 체인 뒤에 붙이면 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

# 재시도가 무의미한 사유 (비공개·삭제·계정해지·지역차단).
# ⚠️ yt-dlp는 YouTube가 **로케일에 맞춰 반환한 사유 문자열**을 그대로 전달한다.
# 한국어 환경에서는 "Private video" 가 아니라 "비공개 동영상" 이 온다. 영어 키만 두면
# 이런 영상이 재시도 가치가 있는 CaptionError(=failed)로 오분류되어 MAX_ATTEMPTS 까지
# 헛되이 재시도한다. (2026-08-21 김희연 채널 3건이 실제로 이 경로로 failed 로 남았다.)
_UNAVAILABLE_KEYS = (
    # 영어
    "private video", "video unavailable", "removed", "terminated", "deleted",
    # 한국어
    "비공개 동영상", "사용할 수 없", "삭제된", "해지된", "차단된",
)

# 로그인을 요구하는 영상(비공개·멤버십 전용)도 재시도가 무의미하다 —
# 이 도구는 쿠키·로그인을 의도적으로 쓰지 않으므로 영구히 접근할 수 없다.
# yt-dlp가 사유를 "로그인하세요." 로만 잘라 주는 경우가 있어 별도로 잡는다.
_SIGNIN_KEYS = ("로그인", "sign in", "log in")

# ⚠️ 단, 봇 확인 요구는 **일시적 rate limit** 이므로 반드시 재시도해야 한다.
# 위 _SIGNIN_KEYS 보다 먼저 검사한다 — 두 메시지 모두 "로그인" 을 포함하기 때문이다.
_BOT_CHECK_KEYS = ("not a bot", "봇이 아닌지", "confirm you", "bot에 해당하지")

# 선호 자막 포맷 (파싱 가능한 것만, 선호 순)
_SUB_FORMATS = ("vtt", "srt", "ttml")


class CaptionError(Exception):
    """자막 추출 실패 (재시도 가치 있음)."""


class NoCaptionError(CaptionError):
    """사용 가능한 자막 트랙이 없음 (자동자막 생성 지연일 수 있어 재시도 대상)."""


class VideoUnavailableError(CaptionError):
    """비공개·삭제·지역차단 등 (재시도해도 무의미)."""


@dataclass
class TranscriptResult:
    raw_text: str          # 자막 원문 (VTT/SRT 등, 미가공)
    language: str          # "ko" | "en"
    source: str            # "manual-caption" | "auto-caption" | "whisper"
    ext: str               # "vtt" | "srt" | ...


@dataclass
class VideoMeta:
    video_id: str
    title: str
    upload_date: str | None    # "YYYYMMDD"
    duration: int | None       # 초
    channel: str | None
    is_live: bool
    live_status: str | None
    chapters: list[dict]       # 업로더가 작성한 챕터 (원본 메타데이터)


def _ydl(quiet: bool = True) -> YoutubeDL:
    return YoutubeDL(
        {
            "quiet": quiet,
            "no_warnings": quiet,
            "skip_download": True,
            "noplaylist": True,
            # 쿠키·인증 일절 사용하지 않는다 (익명 접근)
            "cookiefile": None,
            "cookiesfrombrowser": None,
            # ⚠️ 원문 보존: 지정하지 않으면 YouTube가 제목·챕터를 자동 번역해서 준다.
            #    (실측: 한국어 챕터가 영어로 치환되어 돌아왔다)
            #    원 업로더가 쓴 표기를 받기 위해 한국어를 명시한다.
            "extractor_args": {"youtube": {"lang": ["ko"]}},
        }
    )


def _base_lang(code: str) -> str:
    """'ko-KR' → 'ko', 'ko-orig' → 'ko', 'en-US' → 'en'"""
    return code.split("-")[0].lower()


def _pick_format(tracks: list[dict]) -> dict | None:
    """파싱 가능한 자막 포맷 중 선호도가 높은 것을 고른다."""
    for want in _SUB_FORMATS:
        for track in tracks:
            if track.get("ext") == want:
                return track
    return None


def _select_track(info: dict) -> tuple[dict, str, str] | None:
    """(track, language, source) 또는 None."""
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}

    # 영상의 원어. yt-dlp가 판정하지 못하면 None.
    native = info.get("language")
    native_base = _base_lang(native) if native else None

    def find_manual(lang: str) -> dict | None:
        for code, tracks in manual.items():
            if _base_lang(code) == lang and tracks:
                picked = _pick_format(tracks)
                if picked:
                    return picked
        return None

    def find_auto_native(lang: str) -> dict | None:
        """원어 자동자막만 반환. 기계번역본은 배제한다."""
        # 1) '-orig' 접미사는 yt-dlp가 원어 ASR임을 명시한 트랙
        for code, tracks in auto.items():
            if code.lower().endswith("-orig") and _base_lang(code) == lang and tracks:
                picked = _pick_format(tracks)
                if picked:
                    return picked
        # 2) orig 트랙이 없으면, 영상 원어가 확인되고 그것이 요청 언어와 같을 때만 허용
        if native_base is not None and native_base != lang:
            return None
        if native_base is None:
            # 원어를 알 수 없으면, '-orig' 트랙이 하나도 없는 경우에 한해
            # 단순 코드 자막을 원어로 간주한다(번역본은 보통 orig와 공존한다).
            if any(c.lower().endswith("-orig") for c in auto):
                return None
        for code, tracks in auto.items():
            if _base_lang(code) == lang and not code.lower().endswith("-orig") and tracks:
                picked = _pick_format(tracks)
                if picked:
                    return picked
        return None

    for lang in ("ko", "en"):
        track = find_manual(lang)
        if track:
            return track, lang, "manual-caption"
        track = find_auto_native(lang)
        if track:
            return track, lang, "auto-caption"

    return None


def fetch_meta_and_transcript(video_id: str) -> tuple[VideoMeta, TranscriptResult]:
    """영상 메타데이터와 자막 원문을 함께 가져온다.

    raises: VideoUnavailableError, NoCaptionError, CaptionError
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        with _ydl() as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        msg = str(exc).lower()
        if any(k in msg for k in _BOT_CHECK_KEYS):
            # 일시적 차단 — 재시도 대상
            raise CaptionError(str(exc)) from exc
        if any(k in msg for k in _UNAVAILABLE_KEYS) or any(k in msg for k in _SIGNIN_KEYS):
            raise VideoUnavailableError(str(exc)) from exc
        raise CaptionError(str(exc)) from exc

    meta = VideoMeta(
        video_id=info.get("id", video_id),
        title=info.get("title") or video_id,
        upload_date=info.get("upload_date"),
        duration=info.get("duration"),
        channel=info.get("channel") or info.get("uploader"),
        is_live=bool(info.get("is_live")),
        live_status=info.get("live_status"),
        chapters=list(info.get("chapters") or []),
    )

    # 라이브 진행중·예정(Premiere)은 자막이 확정되지 않았다 → 나중에 재시도
    if meta.is_live or meta.live_status in ("is_upcoming", "is_live"):
        raise NoCaptionError(f"live/premiere in progress (live_status={meta.live_status})")

    selected = _select_track(info)
    if selected is None:
        available = {
            "manual": sorted((info.get("subtitles") or {}).keys())[:10],
            "auto_has_ko": any(
                _base_lang(c) == "ko" for c in (info.get("automatic_captions") or {})
            ),
            "native": info.get("language"),
        }
        raise NoCaptionError(f"no usable native ko/en track; {available}")

    track, language, source = selected

    try:
        with _ydl() as ydl:
            data = ydl.urlopen(track["url"]).read()
    except Exception as exc:  # noqa: BLE001 - 네트워크 계열 전반
        raise CaptionError(f"subtitle download failed: {exc}") from exc

    return meta, TranscriptResult(
        raw_text=data.decode("utf-8", errors="replace"),
        language=language,
        source=source,
        ext=track.get("ext", "vtt"),
    )
