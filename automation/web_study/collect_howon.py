"""Collect a dated public reference pack, without archiving full article bodies."""
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
import datetime, hashlib, json, re, time
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[2]
DATE='2026-11-15'
BASE='https://howontax.co.kr/'
OUT=ROOT/'raw/웹 스터디/호원투데이'
STATE=Path(__file__).parent/'state'/f'howon-{DATE}.json'
UA='Mozilla/5.0 (compatible; CIAT-Study-Reference/1.0)'

def fetch(url):
 for attempt in range(3):
  try:
   with urlopen(Request(url,headers={'User-Agent':UA}),timeout=25) as r:
    return r.read().decode('utf-8'),r.geturl()
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)

def read_jsonld(soup):
 result=[]
 for node in soup.select('script[type="application/ld+json"]'):
  try:
   obj=json.loads(node.get_text())
   result.extend(obj if isinstance(obj,list) else [obj])
  except (ValueError,TypeError):pass
 return result

def scan_list():
 html,_=fetch(BASE+'tax-insights');b=BeautifulSoup(html,'html.parser');items={}
 for card in b.select('article.today-story'):
  a=card.select_one('h3 a[href]')
  if not a:continue
  url=urljoin(BASE,a['href'])
  if urlparse(url).netloc!='howontax.co.kr':continue
  items[url]={'url':url,'title':a.get_text(' ',strip=True),'published':card.get('data-published',''),'category':card.get('data-category',''),'topic':card.get('data-topic',''),'tax':card.get('data-tax','').split(),'list_source_links':sorted({urljoin(BASE,x['href']) for x in card.select('a[href]') if x is not a and x['href'].startswith('http')})}
 list_unique=len(items)
 xml,_=fetch(BASE+'sitemap.xml');x=BeautifulSoup(xml,'xml');sitemap={n.text.strip() for n in x.find_all('loc') if '/insight-' in n.text}
 for url in sorted(sitemap-set(items)):
  items[url]={'url':url,'title':'','published':'','category':'sitemap-only','topic':'','tax':[],'list_source_links':[]}
 return list(items.values()),{'list_unique':list_unique,'union_unique':len(items),'sitemap_insights':len(sitemap),'listing_sha256':hashlib.sha256(html.encode()).hexdigest(),'sitemap_sha256':hashlib.sha256(xml.encode()).hexdigest()}

def collect(item):
 url=item['url'];html,resolved=fetch(url);b=BeautifulSoup(html,'html.parser');article=b.find('article') or b.find('main')
 if article is None:raise ValueError('No article or main element')
 h=article.find('h1') or b.find('h1');title=h.get_text(' ',strip=True) if h else item['title']
 ld=next((x for x in read_jsonld(b) if x.get('@type') in ['Article','BlogPosting','NewsArticle']),{})
 content=article.select_one('section.content') or article
 summary=article.select_one('section.summary p') or content.find('p')
 if summary is None:
  meta=b.find('meta',attrs={'name':'description'});summary_text=meta.get('content','') if meta else ''
 else:summary_text=summary.get_text(' ',strip=True)
 # At most 24 source words across the title and the single short excerpt.
 budget=max(0,24-len(title.split()));excerpt=' '.join(summary_text.split()[:budget])
 if len(summary_text.split())>budget and excerpt:excerpt+=' …'
 external=sorted({urljoin(resolved,a['href']) for a in content.select('a[href]') if a['href'].startswith(('http://','https://')) and urlparse(a['href']).netloc not in ('howontax.co.kr','www.howontax.co.kr')})
 official=[u for u in external if any(v in (urlparse(u).hostname or '') for v in ['go.kr','law.go.kr','scourt.go.kr'])]
 texts=content.get_text(' ',strip=True)
 author=ld.get('author',{});author=author.get('name','') if isinstance(author,dict) else ''
 time_node=article.find('time')
 published=ld.get('datePublished') or item['published'] or (time_node.get('datetime','') if time_node else '')
 record={**item,'title':title,'resolved_url':resolved,'published':published,'modified':ld.get('dateModified',''),'author':author,'original_url':ld.get('isBasedOn',''),'excerpt':excerpt,'excerpt_source_words':len(excerpt.replace(' …','').split()),'official_source_links':official,'external_source_links':external,'body_characters':len(texts),'section_count':len(content.find_all(['h2','h3'])),'body_sha256':hashlib.sha256(texts.encode()).hexdigest(),'page_sha256':hashlib.sha256(html.encode()).hexdigest(),'collected_date':DATE,'status':'reference-collected-not-reviewed','storage_mode':'metadata-short-excerpt-links-no-fulltext'}
 assert len(title.split())+record['excerpt_source_words']<=24 or not excerpt
 return record

def q(v):return json.dumps(v,ensure_ascii=False)
def write_once(path,text):
 if path.exists():
  if path.read_text(encoding='utf-8')!=text:raise RuntimeError(f'Refusing to overwrite immutable raw: {path.name}')
  return
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('x',encoding='utf-8',newline='\n') as f:f.write(text)

def article_md(r):
 lines=['---',f'title: {q(r["title"])}','type: web-reference','status: raw',f'url: {q(r["url"])}',f'collected: {DATE}',f'published: {q(r["published"])}',f'author: {q(r["author"])}','review_status: unreviewed','storage_mode: short-excerpt-and-source-links',f'body_sha256: {r["body_sha256"]}','---','',f'# {r["title"]}','','## 出典'.replace('出典','출처'),'',f'- 홈페이지: {r["url"]}',f'- 게시일: {r["published"] or "표시 없음"}',f'- 수정일: {r["modified"] or "표시 없음"}',f'- 수집일: {DATE}',f'- 목록 분류: {r["category"]} / {r["topic"]}',f'- 확인한 본문 길이: {r["body_characters"]:,}자 / 소제목 {r["section_count"]}개']
 if r['original_url']:lines.append(f'- 연동 원문: {r["original_url"]}')
 for u in r['list_source_links']:
  if u!=r['original_url']:lines.append(f'- 목록 참조: {u}')
 lines+=['','## 짧은 원문 발췌','',f'> {r["excerpt"]}' if r['excerpt'] else '발췌하지 않았다. 원문 링크에서 본문을 확인한다.','','제목과 발췌를 합해 출처별 짧은 인용 범위로 제한했다. 전체 본문·표·이미지는 저장하지 않았다.','','## 학습 시 확인할 사항','','1. 위 원문을 열어 결론이 성립하는 사실관계와 예외를 확인한다.','2. 게시일과 법령 시행일을 구분하고 개정안인지 시행 법령인지 확인한다.','3. 아래 공식 근거의 조문·판결·회신을 직접 대조한다.','4. 기존 위키 정본과 같은 설명, 보완할 설명, 충돌하는 설명을 구분한다.','','## 본문에서 연결한 공식 자료','']
 lines += [f'- {u}' for u in r['official_source_links']] or ['본문에서 공식 도메인 링크를 추출하지 못했다. 이는 근거가 없다는 판정이 아니다.']
 others=[u for u in r['external_source_links'] if u not in r['official_source_links']]
 if others:lines+=['','## 그 밖의 본문 참조 링크','']+[f'- {u}' for u in others]
 lines+=['','## 처리 상태','','참조자료 수집만 완료했다. 본문 전체 보관, 법리 검증, 개인 학습, 위키 정본 반영은 완료하지 않았다. 출처의 설명을 현행 법령의 확정 결론으로 취급하지 않는다.','']
 return '\n'.join(lines)

def main():
 STATE.parent.mkdir(parents=True,exist_ok=True)
 items,coverage=scan_list();existing=json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {'records':{},'errors':{}}
 records=existing['records'];errors={};pending=[x for x in items if x['url'] not in records]
 print(f'Discovered {len(items)} articles; pending {len(pending)}; sitemap insights {coverage["sitemap_insights"]}',flush=True)
 with ThreadPoolExecutor(max_workers=3) as ex:
  futures={ex.submit(collect,item):item for item in pending}
  for i,f in enumerate(as_completed(futures),1):
   item=futures[f]
   try:records[item['url']]=f.result()
   except Exception as e:errors[item['url']]=str(e)
   if i%25==0 or i==len(pending):
    STATE.write_text(json.dumps({'records':records,'errors':errors},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Progress {i}/{len(pending)}; ok {len(records)}; errors {len(errors)}',flush=True)
 ordered=[records[x['url']] for x in items if x['url'] in records]
 for r in ordered:
  name=urlparse(r['url']).path.strip('/').replace('/','-')+'.md';r['file']='글별자료/'+name
  write_once(OUT/r['file'],article_md(r))
 counts=dict(Counter(r['category'] or 'unclassified' for r in ordered))
 intro=['---','title: 호원투데이 공개 글 학습용 참조자료 수집 목록','type: web-reference-catalog','status: raw',f'collected: {DATE}','review_status: unreviewed','url: https://howontax.co.kr/tax-insights','---','','# 호원투데이 학습용 참조자료','','## 범위와 현재 상태','',f'- 목록과 사이트맵을 대조한 고유 글: {len(items)}건',f'- 글별 페이지 확인 및 참조자료 저장: {len(ordered)}건',f'- 수집 실패: {len(errors)}건',f'- 사이트맵의 insight 글: {coverage["sitemap_insights"]}건','- 목록의 기존 세무안내 3건도 함께 포함한다. 계산기·소개·상담·개인정보처리방침은 학습 글 범위에 넣지 않는다.','- 목록 화면에 표시된 숫자와 실제 HTML 카드 수가 달라 고유 URL과 사이트맵을 기준으로 대조했다.','- 글별로 출처·제목·게시일·짧은 발췌·공식 참조 링크를 저장했다. 전체 본문을 복제한 자료가 아니다.','- 수집 완료와 학습·법리 검증·위키 반영 완료를 구분한다. 이 컬렉션은 미검토 상태다.','','## 공부하는 방법','','1. 아래 목록에서 주제를 고른다.','2. 글별 자료의 홈페이지·연동 원문을 열어 본문과 표를 읽는다.','3. 글별로 추출한 공식 근거를 대조한다.','4. 실제 검토를 마친 자료만 후속 ingest에서 기존 정본에 누적한다.','','## 분류별 건수','']+[f'- {k}: {v}건' for k,v in sorted(counts.items())]+['','## 글 목록','','| 번호 | 게시일 | 주제 | 글별 자료 |','|---:|---|---|---|']
 for i,r in enumerate(ordered,1):intro.append(f'| {i} | {r["published"] or "미표시"} | {r["title"].replace("|","/")} | [자료]({r["file"]}) |')
 if errors:intro+=['','## 실패 목록','']+[f'- {u}: {e}' for u,e in errors.items()]
 intro+=['','## 보관·검증','','원문 전문·HTML·이미지는 저장하지 않았으며, 원문 내용 변경 확인을 위한 해시만 보관했다. 재수집 시 기존 raw는 덮어쓰지 않고 새 판본으로 보관한다. 글의 주장·법령·판례의 정확성은 수집 단계에서 확정하지 않는다.','']
 write_once(OUT/'먼저-읽기.md','\n'.join(intro))
 manifest={'collected_date':DATE,'entry_url':BASE+'insight-naver-224423308524','listing_url':BASE+'tax-insights','coverage':coverage,'discovered':len(items),'saved':len(ordered),'failed':len(errors),'categories':counts,'errors':errors,'records':ordered,'storage_mode':'metadata-short-excerpt-links-no-fulltext','review_status':'unreviewed'}
 write_once(OUT/f'{DATE}-수집목록.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 assert len(ordered)+len(errors)==len(items)
 for r in ordered:assert (OUT/r['file']).exists()
 print(json.dumps({'discovered':len(items),'saved':len(ordered),'failed':len(errors),'categories':counts,'output':str(OUT)},ensure_ascii=False),flush=True)

if __name__=='__main__':main()
