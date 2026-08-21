# YouTube Transcript Watcher

특정 YouTube 채널의 신규 영상을 감지해 자막을 `raw/` 에 Markdown으로 수집한다.

**이 도구는 수집만 한다.** 지식 가공(sources → topics → index/log)은 기존 `/ingest` 가
수동으로 담당한다. 수집 자동화와 지식 가공 자동화는 의도적으로 분리되어 있다.

```
YouTube → Watcher(RSS) → Caption Extractor(yt-dlp) → Normalizer → Writer → raw/
                                                                            ↓
                                                            (수동) /ingest → wiki/
```

---

## 설치

```powershell
python -m pip install -r automation/youtube/requirements.txt
```

Python 3.12+ 필요. API 키·로그인 쿠키 모두 사용하지 않는다.

## 사용법

```powershell
# 신규 영상 확인 및 수집
python automation/youtube/youtube_watcher.py

# 무엇이 처리될지만 보고 파일은 만들지 않는다
python automation/youtube/youtube_watcher.py --dry-run

# 특정 채널만
python automation/youtube/youtube_watcher.py --channel "세무법인다솔"

# no_caption·failed 항목의 재시도 대기를 즉시 해제
python automation/youtube/youtube_watcher.py --retry-failed

# 과거 영상 N건 수집 (baseline 무시)
python automation/youtube/youtube_watcher.py --backfill 10
```

## 채널 추가

`channels.yaml` 만 고치면 된다. **Python 코드는 건드리지 않는다.**

```yaml
channels:
  - name: 채널이름                     # state 파일명·로그에 쓰인다
    url: "https://www.youtube.com/@handle"   # @handle · /channel/UC... · /c/... 모두 가능
    category: 세무자문
    raw_dir: "raw/유튜브 스터디/채널이름 유튜브 스터디"  # 저장소 루트 기준 저장 위치
    enabled: true
```

`url` 은 최초 1회만 yt-dlp로 채널 ID를 해석하고 `state/resolved_channels.json` 에 캐시한다.
이후 폴링은 RSS만 사용한다.

---

## 동작 원칙

### 최초 실행은 아무것도 받지 않는다

채널을 처음 만나면 현재 RSS 목록(최신 15건)을 `baseline` 로 기록만 하고 **다운로드하지
않는다.** 과거 영상 수백 개가 한꺼번에 들어오는 사고를 막기 위해서다.
이후 실행부터 baseline 시점 이후의 신규 영상만 수집한다.
과거분이 필요하면 `--backfill N` 을 명시적으로 쓴다.

### 자막 우선순위

| 순위 | 트랙 | `transcript_source` |
|---|---|---|
| 1 | 제작자 업로드 한국어 자막 | `manual-caption` |
| 2 | 한국어 자동생성 자막(원어) | `auto-caption` |
| 3 | 제작자 업로드 영어 자막 | `manual-caption` |
| 4 | 영어 자동생성 자막(원어) | `auto-caption` |
| 5 | 없음 | 저장 안 함 → `no_caption` 기록 후 재시도 |

⚠️ **기계번역 자막은 절대 받지 않는다.** YouTube는 자동자막에 100여 개 언어의 자동
번역본을 함께 노출한다. 영어 영상의 한국어 자동자막은 ASR이 아니라 기계번역이며,
그것을 raw에 넣으면 source of truth 원칙이 깨진다. 자동자막은 **영상 원어와 일치할
때만** 채택한다.

같은 이유로 yt-dlp에 `lang=ko` 를 지정한다. 지정하지 않으면 YouTube가 제목과 챕터를
자동 번역해서 반환한다(실측 확인됨).

### 정제 원칙 — raw는 원문이다

허용하는 것은 **기계적 정리뿐이다.**

- VTT/SRT 헤더·타이밍 행·큐 번호 제거
- 인라인 태그 제거 (`<c>`, `<00:00:01.234>`)
- 자동자막 롤링 중복 제거 (완전 일치 행만)
- HTML entity 해제
- 과도한 빈 줄 정리

**하지 않는 것**: 요약 · 전문용어 추정 교정 · 세법/회계 용어 임의 수정 ·
문장 재작성 · 화자 주장 보정 · 틀렸다고 판단한 내용 삭제.

정제는 이후 `/ingest` 단계의 일이다.

### 상태와 재시도

`state/<채널>.json` 이 `video_id` 기준으로 이력을 관리한다.

| status | 의미 | 재시도 |
|---|---|---|
| `success` | 저장 완료 | 종결 |
| `no_caption` | 자막 없음 | ✅ 30분 → 2h → 6h → 24h (최대 8회) |
| `failed` | 네트워크·yt-dlp 오류 | ✅ 동일 백오프 |
| `skipped` | Shorts·비공개·삭제 | `--force` 로만 |
| `baseline` | 최초 실행 시점 기존 영상 | `--backfill` 로만 |

**`no_caption` 은 종결 상태가 아니다.** 업로드 직후 영상은 자동자막 생성에 수십 분~수
시간이 걸리므로 반드시 재시도해야 한다.

---

## 실행 주기

**기본은 수동 실행이다.** 필요할 때 `youtube_watcher.py` 를 직접 돌린다. 상주시키지도,
잦은 주기로 자동 실행하지도 않는다.

### 운영 방식 — "유튜브 업데이트해줘"

사용자는 주기를 계산하지 않는다. **오래 안 돌렸다 싶으면 "유튜브 업데이트해줘" 라고만
말한다.** 날짜 계산과 backfill 필요 여부 판정은 LLM이 `status.py` 로 처리한다.

```powershell
# 1) 먼저 상태를 본다 — 읽기 전용, 수집하지 않는다
python automation/youtube/status.py

# 2) status.py 가 출력한 "권장 실행" 을 그대로 돌린다
```

`status.py` 는 채널마다 **마지막 수집 영상의 게시일**과 **현재 RSS 창(최신 15건이 덮는
기간)** 을 대조해 판정한다:

| 판정 | 의미 | 조치 |
|---|---|---|
| `OK` | RSS 창이 마지막 수집분까지 덮는다 | 일반 실행 |
| `BACKFILL` | 창 밖으로 밀려난 구간이 있다 | `--backfill N` 병행 |
| `NEW` | 수집 이력이 없는 채널 | `--backfill` 로 시작 |
| `OFF` | `enabled: false` — 채널 감시 대상이 아니다 | 조치 없음 (재생목록만 수동 수집) |

판정 기준은 경과일이 아니라 **"RSS 창의 가장 오래된 영상이 마지막 수집분보다 뒤인가"**
다. 경과일로 판단하면 업로드가 잦은 채널을 놓친다 — 같은 7일이라도 채널마다 15건이
덮는 기간이 9일과 85일로 다르기 때문이다(아래 실측표).

자동화가 필요해지면 **주 1회**로 등록한다. 그 이상 자주 돌릴 이유가 없다 — 수집한
transcript는 어차피 수동 `/ingest` 를 거쳐야 지식이 되므로, 수집 주기를 가공 주기보다
촘촘하게 잡아도 raw만 쌓일 뿐이다. rate limit 위험만 는다.

### ⚠️ RSS 창은 최신 15건뿐이다

`fetch_feed` 가 보는 RSS는 **최신 15건**만 반환하고, **Shorts도 이 15건에 포함된다.**
실행 간격 동안 채널이 15건을 넘게 올리면 그 사이 영상은 창 밖으로 밀려나 **영구히
수집되지 않는다.**

2026-08-21 실측 — 각 채널의 RSS 15건이 덮는 기간:

| 채널 | RSS 창 |
|---|---|
| 세금전문회계사김희연 | 9일 |
| 택스인사이드 | 15일 |
| 로뎀세무법인 | 20일 |
| 상속마스터 정변 | 31일 |
| 세무법인다솔 | 85일 |

**김희연 채널이 9일**이므로 주 1회(7일)는 여유가 이틀뿐이다. 한 번 건너뛰면 유실된다.
수동 실행이라면 **최소 주 1회**를 기준으로 삼고, 오래 쉬었다면 다음 실행 때
`--backfill N` 으로 창 밖으로 밀려난 분량을 함께 회수한다.

```powershell
# 3주 쉬었다면 — baseline을 무시하고 과거 40건까지 훑어 누락분을 채운다
python automation/youtube/youtube_watcher.py --channel "세금전문회계사김희연" --backfill 40
```

#### baseline_at 은 backfill·재생목록 수집 후 자동 확정된다 (2026-08-21 수정)

`--backfill` 과 `playlist_fetch.py` 는 baseline 등록 분기를 거치지 않아 `baseline_at` 이
`None` 으로 남았다. 그 상태에서 다음 일반 실행이 돌면 **"최초 실행"으로 오인해 RSS
15건의 ledger 상태를 `baseline` 으로 덮어썼다**(`record()` 는 status를 무조건 덮어쓴다).
수집된 raw 파일은 남지만 `success` 기록과 `no_caption` 재시도 대상이 지워진다.

2026-08-21 `상속마스터 정변` 채널에서 실제로 4건이 이렇게 손상됐다(raw 파일 기준으로
복구 완료). 이후 `_seal_baseline()` 이 backfill·재생목록 수집 직후 `baseline_at` 을
자동으로 확정하므로 **더 이상 수동 조치가 필요하지 않다.**

ledger가 raw와 어긋났다면 **raw 파일의 frontmatter가 정본**이다 — `video_id`·`title`·
`published`·`transcript_source` 가 모두 들어 있으므로 ledger를 그것으로 되맞춘다.

---

## Windows 작업 스케줄러 등록 (선택 — 주 1회)

자동화를 쓰지 않는 동안에는 이 절을 건너뛴다. 등록한다면 **월요일 오전 9시 주 1회**를
기본값으로 한다.

### PowerShell로 등록 (권장)

```powershell
$py   = "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe"
$repo = "$env:USERPROFILE\OneDrive - 씨앗세무회계\0. LLM WIKI"

$action  = New-ScheduledTaskAction -Execute $py `
    -Argument "`"$repo\automation\youtube\youtube_watcher.py`"" `
    -WorkingDirectory $repo

# 주 1회 — 월요일 09:00
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9am

$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName "LLM-WIKI YouTube Watcher" `
    -Action $action -Trigger $trigger -Settings $settings `
    -Description "다솔세무TV 등 감시 채널의 신규 영상 transcript를 raw/에 수집"
```

`pythonw.exe` 를 쓰면 실행할 때마다 콘솔 창이 뜨지 않는다.

### GUI로 등록

1. `작업 스케줄러` → **작업 만들기**
2. **일반**: 이름 `LLM-WIKI YouTube Watcher`, "사용자가 로그온할 때만 실행"
3. **트리거**: 매주 → `월요일` `09:00` (반복 간격은 설정하지 않는다)
4. **동작**: 프로그램 시작
   - 프로그램: `%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe`
   - 인수: `"automation\youtube\youtube_watcher.py"`
   - 시작 위치: 저장소 루트 (⚠️ 반드시 지정)
5. **조건**: "네트워크 연결이 가능할 때만 시작" 체크
6. **설정**: "예약 시간이 지난 후 가능한 한 빨리 시작" 체크

### 확인

```powershell
Get-ScheduledTask -TaskName "LLM-WIKI YouTube Watcher" | Get-ScheduledTaskInfo
Get-Content "automation\youtube\logs\youtube-watcher.log" -Tail 30
```

`LastTaskResult` 가 `0` 이면 정상, `1` 이면 실패 항목이 있다는 뜻이다.

---

## 로그

`logs/youtube-watcher.log` — 5MB 로테이션, 3세대 보관.
실행시간 · 채널 · video_id · 제목 · 처리결과 · 자막 유형/언어 · 출력 파일 · 오류를 남긴다.

쿠키·토큰·서명 URL 파라미터는 정규식으로 마스킹한다. 인증정보는 애초에 쓰지 않는다.

---

## OneDrive 주의사항

이 저장소는 OneDrive 동기화 폴더 안에 있다.

- 파일 저장은 **같은 디렉터리에 `.tmp` 작성 → `os.replace`** (원자적). 중간에 죽어도
  반쪽 파일이 남지 않는다.
- 동기화 잠금(`PermissionError`)은 지수 백오프로 4회까지 재시도한다.
- **여러 PC에서 동시에 돌리지 않는다.** 동기화 충돌 사본
  (`세무법인다솔-DESKTOP.json`)이 생기면 이력이 갈린다. 채널별 상태 파일로 피해
  범위는 제한해 두었다.
- `raw/` 와 `automation/` 은 OneDrive에서 **"항상 이 장치에 유지"** 로 설정할 것.
  Files On-Demand 플레이스홀더 상태면 읽기가 실패할 수 있다.
- 경로 260자 제한 대비로 파일명의 제목 부분은 80자에서 자른다.

## 파일 구조

```
automation/youtube/
├── youtube_watcher.py   진입점 + CLI + 오케스트레이션
├── resolver.py          채널 URL 해석 + RSS 조회
├── captions.py          yt-dlp 자막 추출 (기계번역 배제)
├── normalize.py         VTT/SRT → 평문 (의미 불변)
├── writer.py            Markdown 조립 + 원자적 저장
├── status.py            수집 상태 점검 + backfill 필요 판정 (읽기 전용)
├── playlist_fetch.py    특정 재생목록 일괄 수집 (ledger 공유)
├── ledger.py            중복 방지 · 상태 · 재시도 백오프
├── channels.yaml        ← 채널 추가는 여기만
├── requirements.txt
├── state/               채널별 이력 + 해석 캐시 (자동 생성)
└── logs/                실행 로그 (git 제외)
```

## 향후 확장 (Whisper)

자막이 아예 없는 영상은 현재 `no_caption` 으로 남는다. V3에서 오디오 추출 → Whisper
전사를 붙일 수 있도록 `captions.py` 를 인터페이스
(`fetch_meta_and_transcript(video_id) -> (VideoMeta, TranscriptResult)`)로 분리해 두었다.
`WhisperProvider` 를 같은 형태로 만들어 체인 뒤에 추가하면 나머지 모듈은 수정이 필요 없다.
`transcript_source: whisper` 값은 이미 writer가 지원한다.
