# Naver Blog Fetcher

Web Clipper 없이 네이버 블로그 글 URL(또는 카테고리 전체)만으로 본문을
`raw/블로그 스터디/`에 Markdown으로 저장한다. `raw/유튜브 스터디/`와 같은
발상의 블로그판이다.

```
blog.naver.com/<id>/<logNo> (frameset 껍데기)
        ↓ iframe
PostView.naver?blogId=...&logNo=...  (실제 본문 HTML) ← 이 스크립트가 직접 요청
        ↓ 파싱
raw/블로그 스터디/<블로거 컬렉션>/*.md
```

## 왜 필요한가

Obsidian Web Clipper로 네이버 블로그를 클리핑하면 종종 frameset 페이지만
저장되어, 본문 대신 `<iframe src="...PostView.naver...">` 한 줄만 raw
파일에 남는다(2026-08-23 실제 발견 — 4건 모두 본문 없이 iframe만 저장됨,
그나마도 iframe src가 4건 전부 동일한 글로 고정되는 오류까지 있었다).
이 스크립트는 그 iframe이 가리키는 PostView.naver를 직접 요청해서
스마트에디터 HTML을 파싱해 실제 본문을 뽑아낸다 — Web Clipper 자체를
아예 거치지 않고 URL 하나로 끝난다.

## 사용법

```powershell
# 새 글 하나를 raw/블로그 스터디/정찬우 회계사 블로그 스터디/ 에 저장
python automation/naver_blog/fetch_naver_blog.py "https://blog.naver.com/아이디/글번호"

# 카테고리(예: 낙서장) 전체 글을 일괄 수집한다.
# 이미 수집된 글은 source: URL(logNo) 기준으로 자동 건너뛴다 —
# 나중에 새 글이 올라오면 같은 명령으로 신규분만 추가된다.
python automation/naver_blog/fetch_naver_blog.py --category-url "https://blog.naver.com/PostList.naver?blogId=아이디&categoryNo=28"

# 이번 실행에서 새로 받을 글 수를 제한 / 글 사이 대기시간 조절(기본 1.0초)
python automation/naver_blog/fetch_naver_blog.py --category-url "<URL>" --limit 5 --delay 1.5

# 무엇이 바뀔지만 보고 파일은 쓰지 않는다
python automation/naver_blog/fetch_naver_blog.py --category-url "<URL>" --dry-run
python automation/naver_blog/fetch_naver_blog.py "<URL>" --dry-run

# 다른 블로거·다른 폴더로 저장하려면 --out-dir 로 덮어쓴다
python automation/naver_blog/fetch_naver_blog.py "<URL>" --out-dir "raw/블로그 스터디/다른 블로거"
```

카테고리 URL은 블로그 화면에서 왼쪽 카테고리 메뉴를 클릭했을 때 주소창에
뜨는 `blogId=...&categoryNo=...` 를 그대로 쓰면 된다.

### `--fill-clippings` — 별도 유틸리티 (Web Clipper 복구용)

우리 자체 수집 경로와는 별개로, 누군가 Obsidian Web Clipper로 네이버
블로그를 클리핑해서 `raw/Clippings/` 에 iframe-only 플레이스홀더가 생겼을
때 복구하는 용도다. 이 저장소의 기존 4건이 이렇게 만들어졌었고, 지금은
`raw/블로그 스터디/정찬우 회계사 블로그 스터디/` 로 이전 완료된 상태다.

```powershell
# raw/Clippings/ 안의 iframe-only 플레이스홀더를 실제 본문으로 채운다
# (frontmatter의 source: 를 읽어 자동으로 URL을 알아낸다)
python automation/naver_blog/fetch_naver_blog.py --fill-clippings

# 이미 본문이 채워진 파일도 source: URL로 다시 가져와 덮어쓴다
# (파서를 고친 뒤 기존 raw를 재추출할 때, 또는 네이버 원문이 수정됐을 때)
python automation/naver_blog/fetch_naver_blog.py --fill-clippings --refresh
```

Python 3.9+ 필요. **외부 의존성 없음** — 표준 라이브러리(`urllib`,
`html.parser`, `re`, `base64`, `json`)만 쓴다. API 키·로그인 쿠키 모두
불필요(공개 글만 대상).

## 동작 원칙

### 저장 위치

기본값은 두 갈래다:

- 단건 URL·`--category-url`: `raw/블로그 스터디/정찬우 회계사 블로그 스터디/`
- `--fill-clippings`: `raw/Clippings/`

둘 다 `--out-dir` 로 덮어쓸 수 있다. 다른 블로거를 수집하려면
`raw/블로그 스터디/<블로거 이름>/` 형태로 새 폴더를 지정하면 된다
(`raw/유튜브 스터디/<채널 컬렉션>/` 과 동일한 조직 방식).

### 정제 원칙 — 텍스트 중심, 기계적 변환만

- 본문 단락(`se-text-paragraph`)을 그대로 텍스트로 옮긴다.
- 표(`<table class="se-table-content">`)는 각 행을 `셀1 | 셀2 | 셀3`
  한 줄로 변환한다. 한 셀 안에 문단이 여러 개면 `;`로 이어붙인다.
  병합 셀(rowspan/colspan)은 완벽히 복원되지 않으니 숫자를 인용할 땐
  원문(`source:` URL)을 대조한다.
- 이미지는 다운로드하지 않고 `![이미지](URL)` 마크다운 링크로만 남긴다
  (`postfiles.pstatic.net` 공개 CDN, 인증 불필요). 원본 그대로가 아니라
  `?type=w773`(표시용 리사이즈본) 해상도다. **링크 부패 위험**이 있다 —
  네이버가 원본을 지우거나 글이 삭제되면 이 링크도 죽는다. 이미지 자체를
  영구 보존해야 하면(예: 스크린샷이 유일한 정보원인 경우) 별도로 다운로드
  받아야 한다.
- 번호 매긴 소제목("1. 사실관계" 등) 앞에는 빈 줄을 자동으로 넣는다
  (원문에 스페이서 문단이 없는 경우가 있어서 가독성을 위해 보정).
- HTML 태그·인라인 스타일은 전부 제거한다. 문장·법령 인용·숫자는 원문
  그대로 보존한다(요약·재작성 없음).

### 작성일 추정은 휴리스틱이다

`published`는 og:image 썸네일 URL 경로에 인코딩된 날짜를 디코딩해
채운다(네이버 CDN 경로 관례에 의존 — 실패해도 조용히 빈 값으로 남긴다).
**확정 정보가 아니다.** 정확한 작성일이 중요하면 `source:` URL을 열어
확인한다.

### 카테고리 수집은 중복을 자동으로 건너뛴다

`--category-url` 은 대상 폴더의 기존 `.md` 파일들을 frontmatter
`source:` 로 스캔해 이미 수집된 `logNo` 집합을 만들고, 새 글만 받는다.
같은 명령을 나중에 다시 돌리면 그 사이 올라온 신규 글만 추가된다 —
YouTube watcher의 상태 관리와 달리 별도 state 파일 없이 raw 자체가
진행 상태를 겸한다.

글 사이 기본 1초 대기(`--delay`)를 둔다 — 짧은 시간에 수십 건을 연속
요청하는 걸 피하기 위해서다.

### 파일명

`sanitize_title()` 이 Windows 금지 문자와 위키링크를 깨는 문자
(`#^[]`)를 제거하고 80자로 자른다 — `automation/youtube/writer.py` 와
동일한 규칙(CLAUDE.md 「위키링크를 깨는 파일명 문자」 참조). 이름이
겹치면 `logNo`를 접미사로 붙인다.

## 이 도구가 하지 않는 것

**수집만 한다.** `youtube_watcher.py` 와 같은 원칙 — 지식 가공
(sources → topics/practice → index/log)은 여전히 `/ingest` 가 수동으로
담당한다. 자동 스케줄러도 두지 않는다: 필요할 때 직접 실행한다.

## 한계

- 비공개 글, 서로이웃 공개 글은 가져오지 못한다(로그인 불필요 = 공개
  글만 대상).
- 네이버가 스마트에디터 HTML 구조(`se-main-container` 등 클래스명)나
  `PostTitleListAsync.naver` 응답 형식을 바꾸면 각각 본문 파서·카테고리
  목록 조회가 깨질 수 있다.
- 표의 병합 셀은 근사치로만 복원된다(위 참조).
- Windows 콘솔(cp949) 환경에서 배경 실행 시 이모지·특수 문장부호가 있는
  제목을 출력하다 죽는 문제가 있었다 — `main()` 시작 시 stdout/stderr를
  UTF-8(errors="replace")로 강제해 해결했다(2026-08-23).
