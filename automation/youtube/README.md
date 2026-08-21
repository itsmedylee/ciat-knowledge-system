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

## Windows 작업 스케줄러 등록

무한 루프로 상주시키지 않는다. **1시간 간격으로 한 번 실행하고 종료**하는 방식이다.
(30분은 과잉이다 — 자동자막 생성 지연을 고려하면 이득이 없고 rate limit 위험만 는다.)

### PowerShell로 등록 (권장)

```powershell
$py   = "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe"
$repo = "$env:USERPROFILE\OneDrive - 씨앗세무회계\0. LLM WIKI"

$action  = New-ScheduledTaskAction -Execute $py `
    -Argument "`"$repo\automation\youtube\youtube_watcher.py`"" `
    -WorkingDirectory $repo

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) `
    -RepetitionInterval (New-TimeSpan -Hours 1)

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
3. **트리거**: 매일 → 반복 간격 `1시간`, 기간 `무기한`
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
