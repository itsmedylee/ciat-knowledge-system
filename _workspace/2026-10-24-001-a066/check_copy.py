import json
import re
from pathlib import Path

run = Path(__file__).parent
mapping = json.loads((run / 'copy_map.json').read_text(encoding='utf-8-sig'))
body = (run / 'final.md').read_text(encoding='utf-8-sig').split('<!-- HUMANIZE-SUMMARY')[0]
matches = list(re.finditer(r'^## (COPY_\d{4})\s*$', body, re.M))
assert [m.group(1) for m in matches] == [x['id'] for x in mapping['entries']], 'COPY IDs/order mismatch'
changes = []
for i, entry in enumerate(mapping['entries']):
    after = body[matches[i].end():matches[i + 1].start() if i + 1 < len(matches) else len(body)].strip()
    before = entry['text']
    if entry['protect']:
        assert before == after, f"Protected copy changed: {entry['id']}"
    assert re.findall(r'\d+(?:[.,:]\d+)*', before) == re.findall(r'\d+(?:[.,:]\d+)*', after), f"Numbers changed: {entry['id']}"
    assert re.findall(r'\"[^\"]*\"|“[^”]*”|「[^」]*」|『[^』]*』', before) == re.findall(r'\"[^\"]*\"|“[^”]*”|「[^」]*」|『[^』]*』', after), f"Quotes changed: {entry['id']}"
    assert re.findall(r'[A-Za-z][A-Za-z0-9_-]*', before) == re.findall(r'[A-Za-z][A-Za-z0-9_-]*', after), f"Latin terms changed: {entry['id']}"
    if before != after:
        changes.append(dict(id=entry['id'], file=entry['file'], before=before, after=after))
(run / 'copy_changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(total=len(matches), protected=sum(x['protect'] for x in mapping['entries']), changed=len(changes)), ensure_ascii=False))
for item in changes:
    print(f"\n{item['id']} ({item['file']})\n- {item['before']}\n+ {item['after']}")
