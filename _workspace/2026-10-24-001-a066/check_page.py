import json
import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

run = Path(__file__).parent

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.hrefs, self.scripts, self.text = [], [], [], []
        self.capture, self.skip, self.part = False, False, ''
    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if 'id' in data: self.ids.append(data['id'])
        if tag == 'a': self.hrefs.append(data.get('href', ''))
        if tag in ('script', 'style'): self.skip = True
        if tag == 'script' and data.get('type') == 'application/ld+json': self.capture, self.part = True, ''
    def handle_data(self, data):
        if self.capture: self.part += data
        if not self.skip: self.text.append(data)
    def handle_endtag(self, tag):
        if tag == 'script' and self.capture:
            self.scripts.append(json.loads(self.part))
            self.capture = False
        if tag in ('script', 'style'): self.skip = False

page = Page()
html = urllib.request.urlopen('http://127.0.0.1:5187/services/project-cost-settlement/').read().decode()
page.feed(html)
before = json.loads((run / 'page_before.json').read_text(encoding='utf8'))
assert before['ids'] == page.ids, 'Page IDs/order changed'
assert before['hrefs'] == page.hrefs, 'Links/order changed'
assert len(page.ids) == len(set(page.ids)), 'Duplicate IDs'
assert all(href[1:] in page.ids for href in page.hrefs if href.startswith('#')), 'Missing anchor'
assert 'COPY_0001' not in html and 'HUMANIZE-SUMMARY' not in html, 'Internal marker exposed'
faqs = [item for item in page.scripts if item.get('@type') == 'FAQPage']
assert len(faqs) == 1
questions = faqs[0]['mainEntity']
assert len(questions) == 12
normalize = lambda value: re.sub(r'\s+', '', value)
visible = normalize(''.join(page.text))
llms = normalize(urllib.request.urlopen('http://127.0.0.1:5187/llms-full.txt').read().decode())
for item in questions:
    for value in (item['name'], item['acceptedAnswer']['text']):
        assert normalize(value) in visible, 'Visible FAQ differs from structured data'
        assert normalize(value) in llms, 'LLMs FAQ differs from structured data'
result = dict(ids=len(page.ids), links=len(page.hrefs), faqCount=len(questions), idsAndLinksUnchanged=True, faqVisibleSchemaLlmsMatch=True, internalMarkersAbsent=True)
(run / 'page_verification.json').write_text(json.dumps(result, indent=2), encoding='utf8')
print(json.dumps(result))
