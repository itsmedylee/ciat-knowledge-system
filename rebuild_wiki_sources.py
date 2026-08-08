from pathlib import Path
import re

src_dir = Path(r"c:\Users\Elite 600 G9\OneDrive - 씨앗세무회계\0. 씨앗세무회계\0. 기타업무\세무법인다솔 유튜브 스터디")
out_dir = Path(r"c:\Users\Elite 600 G9\OneDrive - 씨앗세무회계\0. LLM WIKI\wiki\sources\세무법인다솔 유튜브 스터디")
out_dir.mkdir(parents=True, exist_ok=True)

for src_path in sorted(src_dir.glob('*.txt')):
    text = src_path.read_text(encoding='utf-8-sig')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            lines.append('')
            continue
        line = re.sub(r'[ \t]{2,}', ' ', line)
        line = line.replace('  ', ' ')
        lines.append(line)
    body = '\n'.join(lines).strip()
    title = src_path.stem
    out_path = out_dir / f"{src_path.name[:-4]}.md"
    content = f"""---
title: {title}
type: source
created: 2026-08-08
updated: 2026-08-08
tags: [세무, 유튜브, 원문전사정제]
sources: [{src_path.name}]
---

# {title}

원본 txt의 전사 내용을 최대한 그대로 보존하고, 음성 인식 오타와 띄어쓰기 오류만 최소 범위에서 정리한 전사 정제본입니다.

{body}
"""
    out_path.write_text(content, encoding='utf-8')

print(f"rewrote {len(list(src_dir.glob('*.txt')))} files")
