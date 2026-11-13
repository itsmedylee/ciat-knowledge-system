from pathlib import Path
import re, html, json, hashlib
from html.parser import HTMLParser
import markdown

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent.parent / '2026-11-10-부과제척기간-징수권-소멸시효.md'
raw = SOURCE.read_text(encoding='utf-8-sig')
text = raw[raw.index('# [국세기본법]'):raw.index('\n---\n\n## 내부용')].strip()
lines = text.splitlines()
title = lines[0][2:]
body_md = '\n'.join(lines[1:]).strip()
tags_line = next(line for line in body_md.splitlines() if line.startswith('#씨앗세무회계'))
body_md = body_md.replace(tags_line, '').strip()
parts = re.split(r'(?m)^## (\d+)\. (.+)$', body_md)
intro_md = parts[0].strip()
sections = [(parts[i], parts[i+1], parts[i+2].strip()) for i in range(1,len(parts),3)]
def md(s): return markdown.markdown(s, extensions=['tables'])

def svg(label, desc, shapes, view='0 0 680 160'):
    key = re.sub(r'\W','',label)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view}" role="img" aria-labelledby="{key}-title {key}-desc"><title id="{key}-title">{label}</title><desc id="{key}-desc">{desc}</desc>{shapes}</svg>'

flow = svg('성립확정징수', '납세의무가 성립하고 세액이 확정된 뒤 세금을 징수하는 기본 구조입니다. 구체적인 기산점은 본문의 조문 설명을 확인합니다.', '''
<path d="M178 64h70m178 0h70" fill="none" stroke="#a7b9b3" stroke-width="2"/><path d="m238 58 10 6-10 6m248-12 10 6-10 6" fill="none" stroke="#a7b9b3" stroke-width="2"/>
<rect x="8" y="18" width="170" height="94" rx="16" fill="#edf2ef"/><rect x="248" y="18" width="178" height="94" rx="16" fill="#183b34"/><rect x="496" y="18" width="176" height="94" rx="16" fill="#edf2ef"/>
<g text-anchor="middle" font-family="Malgun Gothic, sans-serif"><g font-size="27" font-weight="700"><text x="93" y="60" fill="#183b34">성립</text><text x="337" y="60" fill="#fff">확정</text><text x="584" y="60" fill="#183b34">징수</text></g><g font-size="19"><text x="93" y="91" fill="#566961">납세의무 발생</text><text x="337" y="91" fill="#dbe9df">구체적인 세액 결정</text><text x="584" y="91" fill="#566961">세금의 납부·수령</text></g></g>''')

hero_svg = svg('부과와징수', '부과제척기간은 세금을 매길 수 있는 시간이며, 징수권 소멸시효는 확정된 세금을 걷을 수 있는 시간입니다. 두 기간은 기산점과 법적 효과가 다릅니다.', '''
<g fill="none" stroke="#b7c8bc" stroke-width="1"><circle cx="190" cy="131" r="113"/><circle cx="190" cy="131" r="91"/><path d="M24 131h332M190 11v240" stroke-dasharray="3 8"/></g>
<circle cx="108" cy="122" r="68" fill="#f4f2e9"/><circle cx="273" cy="144" r="68" fill="#183b34"/>
<path d="M103 47v-7m5 165v-7M33 122h7m136 0h7M268 69v-7m5 165v-7m-75-76h7m136 0h7" stroke="#8caa9a" stroke-width="2"/>
<g font-family="Malgun Gothic, sans-serif" text-anchor="middle"><text x="108" y="119" font-size="29" fill="#183b34" font-weight="700">부과</text><text x="108" y="146" font-size="15" fill="#60726a">매기는 시간</text><text x="273" y="141" font-size="29" fill="#fff" font-weight="700">징수</text><text x="273" y="168" font-size="15" fill="#d7e5db">걷는 시간</text></g>
<path d="M101 68h14m151 132h14" stroke="#b89761" stroke-width="3" stroke-linecap="round"/>''', '0 0 380 264')

reset_svg = svg('시효중단', '중단은 중단 전의 경과기간을 이어 계산하지 않고 법에서 정한 시점부터 새로 계산하는 방식입니다.', '''
<g font-family="Malgun Gothic, sans-serif"><text x="10" y="31" font-size="25" font-weight="700" fill="#183b34">중단</text><text x="10" y="62" font-size="19" fill="#61736a">법에서 정한 시점부터 새로 진행</text>
<path d="M18 112h195" stroke="#c9d2cc" stroke-width="12" stroke-linecap="round"/><path d="M288 112h346" stroke="#183b34" stroke-width="12" stroke-linecap="round"/>
<path d="m624 100 18 12-18 12" fill="none" stroke="#183b34" stroke-width="4"/>
<circle cx="252" cy="112" r="24" fill="#f7f3e9" stroke="#b89761" stroke-width="2"/><path d="M260 104a11 11 0 1 0 2 13m-2-19v10h-10" fill="none" stroke="#997a47" stroke-width="2"/>
<text x="18" y="149" font-size="18" fill="#65776c">기존 경과기간</text><text x="288" y="149" font-size="18" fill="#183b34">새로 계산</text></g>''', '0 0 680 170')
pause_svg = svg('시효정지', '정지는 정지기간 동안 시효가 진행하지 않으며 정지 전에 지난 기간은 유지하고 이후 기간과 이어 계산하는 방식입니다.', '''
<g font-family="Malgun Gothic, sans-serif"><text x="10" y="31" font-size="25" font-weight="700" fill="#183b34">정지</text><text x="10" y="62" font-size="19" fill="#61736a">정지 전 경과기간을 유지하고 이어 계산</text>
<path d="M18 112h195" stroke="#183b34" stroke-width="12" stroke-linecap="round"/><path d="M288 112h90" stroke="#c8ae7e" stroke-width="12" stroke-linecap="round" stroke-dasharray="1 20"/><path d="M445 112h189" stroke="#183b34" stroke-width="12" stroke-linecap="round"/>
<path d="m624 100 18 12-18 12" fill="none" stroke="#183b34" stroke-width="4"/>
<text x="18" y="149" font-size="18" fill="#183b34">경과기간 유지</text><text x="281" y="149" font-size="18" fill="#8a6d3c">진행하지 않음</text><text x="445" y="149" font-size="18" fill="#183b34">이어서 계산</text></g>''', '0 0 680 170')

def figure(svg_markup, title, caption):
    return f'<figure class="diagram"><div class="figure-label">{title}</div>{svg_markup}<figcaption>{caption}</figcaption></figure>'

insertions = {
 '1':figure(flow, '기본 구조', '성립·확정·징수는 서로 다른 단계입니다. 실제 기간의 기산점은 세목과 신고·고지 방식에 따라 확인해야 합니다.'),
 '3':'''<div class="case-comparison" aria-label="가상 사례 비교">
<div class="case-card"><span class="case-id">사례 A · 추가 과세</span><div class="case-amount">추가 <b>500</b><span>만 원</span></div><p>신고·납부한 1,000만 원 외에<br>누락된 세금을 더 매길 수 있을까요?</p><strong>부과제척기간을 확인합니다.</strong></div>
<div class="case-card collection"><span class="case-id">사례 B · 신고 후 미납</span><div class="case-amount">미납 <b>1,000</b><span>만 원</span></div><p>이미 신고로 확정된 세금을<br>지금도 걷을 수 있을까요?</p><strong>징수권 소멸시효를 확인합니다.</strong></div></div><p class="visual-note">본문의 가상 사례를 비교한 도식이며, 가산세는 제외했습니다.</p>''',
 '8':figure(reset_svg, '중단과 정지, 계산 방식의 차이', '중단은 새로 계산하고, 정지는 경과기간을 유지합니다.')+figure(pause_svg, '정지기간은 계산에서 제외', '개별 사건의 중단·정지 사유와 구체적인 기간은 별도로 확인해야 합니다.')
}

toc=''.join(f'<li><a href="#section-{n}"><span>{int(n):02d}</span>{html.escape(t)}</a></li>' for n,t,_ in sections)
article='<div class="opening" data-source-content>'+md(intro_md)+'</div>'
for n, heading, content in sections:
    article+=f'<section class="article-section" id="section-{n}"><h2><span class="section-no">{int(n):02d}</span>{html.escape(heading)}</h2><div data-source-content>'+md(content)+'</div>'+insertions.get(n,'')+'</section>'
article=re.sub(r'<table>(.*?)</table>',r'<div class="table-wrap" tabindex="0" role="region" aria-label="설명 표"><table>\1</table></div>',article,flags=re.S)
tags=''.join(f'<span>{html.escape(t)}</span>' for t in tags_line.split())

css='''
:root{--ink:#1c332d;--green:#183b34;--muted:#65766c;--line:#dce4de;--paper:#fff;--pale:#f3f5ef;--sand:#b89761;--sans:"Pretendard","Malgun Gothic","Apple SD Gothic Neo",sans-serif}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}body{margin:0;color:var(--ink);background:#e9ede8;font-family:var(--sans);-webkit-font-smoothing:antialiased}a{color:inherit;text-decoration-thickness:1px;text-underline-offset:4px}button{font:inherit;cursor:pointer}button:focus-visible,a:focus-visible,summary:focus-visible,.table-wrap:focus-visible{outline:3px solid #b89761;outline-offset:5px}.preview-tools{max-width:1256px;margin:20px auto;display:flex;justify-content:space-between;align-items:center;padding:0 26px;gap:16px;font-size:12px;color:#52665b}.preview-tools .preview-caption{display:flex;gap:10px;align-items:center}.status-dot{width:6px;height:6px;background:#607b69;border-radius:50%}.view-controls{display:flex;background:#dce4dc;border-radius:7px;padding:3px;gap:2px}.view-controls button{border:0;background:none;color:#50645a;padding:8px 13px;border-radius:5px;font-size:12px}.view-controls button[aria-pressed="true"]{background:#fff;box-shadow:0 1px 4px #183b3412;color:#183b34}.site-frame{container-type:inline-size;width:min(1256px,100% - 40px);margin:0 auto 40px;background:var(--paper);box-shadow:0 15px 60px #19392d0c;border:1px solid #d7dfd8}.mobile-preview .site-frame{width:min(420px,100% - 24px)}.site-header{display:flex;justify-content:space-between;align-items:center;margin:0 62px;padding:28px 0;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:11px;font-weight:700;letter-spacing:-.5px;font-size:19px;text-decoration:none}.brand svg{width:27px;height:30px}.brand small{font-size:10px;letter-spacing:2px;color:#698173;font-weight:500;margin-left:4px}.header-label{font-size:11px;letter-spacing:2px;color:var(--muted)}.hero{background:linear-gradient(115deg,#fbfcf8,#eef3eb);padding:64px 62px 48px;border-bottom:1px solid var(--line);position:relative;overflow:hidden}.hero-topline{display:flex;gap:12px;align-items:center;font-size:11px;letter-spacing:1.5px;color:#62786b;margin-bottom:26px}.hero-topline .pill{padding:6px 11px;border:1px solid #c7d4c7;border-radius:3px;letter-spacing:.5px}.hero-grid{display:grid;grid-template-columns:1.45fr 1fr;gap:35px;align-items:center}h1{font-size:clamp(35px,4.3vw,52px);line-height:1.38;letter-spacing:-2.5px;font-weight:700;margin:0 0 24px;word-break:keep-all;overflow-wrap:break-word}.hero-deck{font-size:16px;line-height:1.95;word-break:keep-all;color:#566d5f;margin:0;max-width:560px}.hero-visual{border-left:1px solid #d5dfd2;padding-left:25px}.hero-visual svg{width:100%;display:block}.hero-visual p{text-align:center;font-size:12px;line-height:1.8;color:#63776a;margin:5px 0 0}.hero-meta{display:flex;gap:22px;flex-wrap:wrap;margin-top:36px;color:#667c6f;font-size:11px}.hero-meta strong{color:#395547;font-weight:600}.key-takeaway{display:grid;grid-template-columns:repeat(3,1fr);margin:0 62px;border-bottom:1px solid var(--line)}.takeaway{padding:24px 22px 23px 0}.takeaway+.takeaway{border-left:1px solid var(--line);padding-left:26px}.takeaway span{display:block;font-size:10px;letter-spacing:1.4px;color:#92a28e;margin-bottom:9px}.takeaway p{font-size:14px;font-weight:600;line-height:1.7;word-break:keep-all;margin:0}.reading-layout{display:grid;grid-template-columns:213px minmax(0,1fr);gap:48px;padding:56px 62px 64px}.contents{position:sticky;top:28px;align-self:start}.contents summary{font-size:12px;font-weight:700;letter-spacing:.5px;cursor:pointer;list-style:none;padding-bottom:18px;border-bottom:1px solid var(--line)}.contents summary::-webkit-details-marker{display:none}.contents summary:after{content:"−";float:right;color:#97a492}.contents details:not([open]) summary:after{content:"+"}.contents ol{list-style:none;margin:10px 0 0;padding:0}.contents li{margin:0}.contents a{display:flex;gap:10px;line-height:1.65;font-size:12px;text-decoration:none;color:#6b7d71;padding:9px 6px;border-left:2px solid transparent}.contents a span{font-size:10px;color:#9ba997;padding-top:2px;font-variant-numeric:tabular-nums}.contents a:hover,.contents a.active{color:var(--green);background:#f3f6ef;border-left-color:var(--green)}.contents-note{color:#7e8b80;font-size:11px;line-height:1.8;margin-top:21px}.article{min-width:0;font-size:16px;line-height:1.95;letter-spacing:-.2px;word-break:keep-all;overflow-wrap:break-word}.article p{margin:0 0 20px}.article strong{color:#173e30;font-weight:700}.opening{padding:0 0 30px}.opening>p:first-child{font-size:19px;line-height:1.9;letter-spacing:-.6px}.opening>p:nth-child(3){font-size:25px;font-weight:650;letter-spacing:-.8px;margin-top:-7px}.article ol,.article ul{padding-left:23px;margin:20px 0 28px}.article li{padding-left:3px;margin:8px 0}.opening ol{background:#f6f7f1;border-left:3px solid #a5b7a1;padding:19px 22px 19px 44px;font-size:15px}.article-section{padding:35px 0 8px;border-top:1px solid var(--line);scroll-margin-top:30px}.article h2{font-size:25px;line-height:1.55;letter-spacing:-1px;margin:0 0 26px;display:flex;gap:14px;align-items:baseline;font-weight:700}.section-no{font-size:12px;letter-spacing:0;color:#95a98f;flex:0 0 21px;font-weight:500}.article h3{font-size:18px;margin:32px 0 18px;letter-spacing:-.5px}.table-wrap{margin:27px 0 30px;overflow-x:auto;border-top:2px solid #375d46;border-bottom:1px solid #dce4dc}table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.85}th,td{padding:16px 18px;text-align:left;vertical-align:top;border-bottom:1px solid #e2e7e0}tr:last-child td{border-bottom:0}th{background:#f2f5ec;font-weight:650;color:#365444}td:first-child{width:52%}th+th,td+td{border-left:1px solid #e3e8df}.diagram{margin:29px 0 32px;padding:25px 23px 19px;border:1px solid #dce4d8;background:#fcfdf9;border-radius:5px}.figure-label{font-size:12px;font-weight:650;color:#526d5a;margin-bottom:18px}.diagram svg{display:block;width:100%;height:auto}.diagram figcaption{font-size:12px;color:#7a8c7b;line-height:1.8;margin:12px 0 0}.case-comparison{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:30px 0 0}.case-card{background:#f2f5ec;border:1px solid #dce4d5;border-radius:5px;padding:25px 23px}.case-card.collection{background:#f7f4ed;border-color:#e9e0cd}.case-id{font-size:11px;letter-spacing:.3px;color:#698264}.case-amount{font-size:17px;margin:14px 0 12px;color:#3d6148}.case-amount b{font-size:34px;letter-spacing:-1.5px;margin-left:2px}.case-amount span{font-size:14px;margin-left:5px}.case-card p{font-size:13px;line-height:1.95;color:#677567;margin:0 0 13px}.case-card strong{font-size:13px}.article .visual-note{font-size:11px;color:#85917f;margin-top:8px}.keyword-list{display:flex;gap:7px;flex-wrap:wrap;padding:26px 0;border-top:1px solid var(--line);margin-top:38px}.keyword-list span{font-size:11px;color:#7a897b;background:#f3f5ef;border-radius:3px;padding:4px 8px;line-height:1.65}.article-footer{border-top:1px solid #d9e2d4;padding:31px 62px;display:flex;align-items:center;justify-content:space-between;background:#f8faf5;font-size:12px;line-height:1.8;color:#73846f}.article-footer strong{display:block;font-size:14px;color:#375641}.top-link{border:1px solid #cdd9c7;border-radius:50%;padding:9px 14px;text-decoration:none;color:#526b4b;font-size:17px}.reading-progress{height:2px;background:#a9b69b;width:0;position:fixed;top:0;left:0;z-index:20}.print-note{display:none}::selection{background:#e1ebd5}
@container (max-width:850px){.site-header{margin:0 28px;padding:24px 0}.hero{padding:38px 28px 32px}.hero-grid{grid-template-columns:1fr;gap:28px}.hero h1{font-size:36px;letter-spacing:-1.8px;max-width:580px}.hero-visual{border:0;padding:0;max-width:330px;justify-self:center;width:100%}.hero-visual svg{max-height:210px}.hero-topline{font-size:10px;gap:8px;margin-bottom:22px}.hero-deck{font-size:15px}.key-takeaway{margin:0 28px;grid-template-columns:1fr}.takeaway{padding:19px 0;display:flex;gap:16px;align-items:baseline}.takeaway+.takeaway{padding:19px 0;border-left:0;border-top:1px solid var(--line)}.takeaway span{margin:0;min-width:74px}.takeaway p{font-size:13px}.reading-layout{display:block;padding:32px 28px 40px}.contents{position:static;margin:0 0 35px}.contents-note{display:none}.contents summary{padding:0 0 16px}.contents ol{display:grid;grid-template-columns:1fr;gap:0;margin-top:9px}.contents a{font-size:13px;padding:8px 5px}.article{font-size:16px;line-height:1.95}.opening>p:first-child{font-size:18px}.article h2{font-size:23px;gap:10px}.section-no{font-size:11px;flex-basis:17px}.article-section{padding-top:28px}.case-comparison{grid-template-columns:1fr}.case-card{padding:21px}.case-card p br{display:none}th,td{padding:13px 12px;font-size:13px}.diagram{padding:18px 12px 15px}.figure-label{font-size:11px}.diagram figcaption{font-size:12px}.article-footer{padding:24px 28px;gap:20px}.brand{font-size:17px}.brand small{display:none}.header-label{font-size:9px;letter-spacing:1px}.hero-meta{gap:11px;font-size:10px;margin-top:24px}}
@media(max-width:600px){.preview-tools{padding:0 13px;flex-wrap:wrap;margin:14px auto;justify-content:center}.preview-caption{font-size:10px}.view-controls button{font-size:11px;padding:7px 12px}.site-frame{width:calc(100% - 16px);margin-bottom:14px}.preview-tools .status-text{display:none}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
@media print{body{background:#fff}.preview-tools,.contents,.reading-progress,.top-link{display:none!important}.site-frame,.mobile-preview .site-frame{width:100%;margin:0;border:0;box-shadow:none}.site-header{margin:0;padding:10px 0}.hero{padding:25px 0;background:none}.hero-grid{grid-template-columns:1.5fr 1fr}.hero h1{font-size:30px}.hero-visual svg{max-height:180px}.hero-meta{margin-top:15px}.key-takeaway{margin:0}.takeaway{padding-top:15px;padding-bottom:15px}.reading-layout{display:block;padding:25px 0}.article{font-size:11pt;line-height:1.8}.article h2{font-size:17pt;break-after:avoid}.article h3{break-after:avoid}.diagram,.case-comparison,tr{break-inside:avoid}.table-wrap{overflow:visible}.article-footer{padding:20px 0;background:none}.keyword-list{display:none}a{text-decoration:none;color:inherit}.print-note{display:block;font-size:9pt;color:#777}@page{size:A4;margin:17mm}}
'''

script='''
const desk=document.getElementById('desktop-view'),mobile=document.getElementById('mobile-view'),contents=document.querySelector('.contents details');
function mode(isMobile){document.body.classList.toggle('mobile-preview',isMobile);desk.setAttribute('aria-pressed',String(!isMobile));mobile.setAttribute('aria-pressed',String(isMobile));contents.open=!isMobile&&window.innerWidth>900;}
desk.addEventListener('click',()=>mode(false));mobile.addEventListener('click',()=>mode(true));document.getElementById('print-view').addEventListener('click',()=>window.print());
document.querySelectorAll('.contents a').forEach(a=>a.addEventListener('click',()=>{if(document.body.classList.contains('mobile-preview')||innerWidth<850)contents.open=false;}));
const links=[...document.querySelectorAll('.contents a')];
if('IntersectionObserver' in window){const obs=new IntersectionObserver(entries=>{const entry=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top)[0];if(entry)links.forEach(a=>a.classList.toggle('active',a.hash==='#'+entry.target.id));},{rootMargin:'-10% 0px -65% 0px'});document.querySelectorAll('.article-section').forEach(s=>obs.observe(s));}
window.addEventListener('scroll',()=>{const max=document.documentElement.scrollHeight-innerHeight;document.querySelector('.reading-progress').style.width=(max>0?scrollY/max*100:0)+'%';},{passive:true});mode(false);
'''

document=f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="description" content="부과제척기간과 징수권 소멸시효의 차이, 기산점, 납부고지·독촉·압류의 효과를 사례와 도식으로 설명합니다."><title>{html.escape(title)} | 씨앗세무회계</title><style>{css}</style></head>
<body id="top"><div class="reading-progress" aria-hidden="true"></div>
<div class="preview-tools" role="region" aria-label="미리보기 도구"><div class="preview-caption"><i class="status-dot" aria-hidden="true"></i><span>홈페이지 칼럼 미리보기</span><span class="status-text">· 아직 게시되지 않은 화면입니다</span></div><div class="view-controls"><button id="desktop-view" aria-pressed="true">데스크톱</button><button id="mobile-view" aria-pressed="false">모바일</button><button id="print-view">인쇄</button></div></div>
<div class="site-frame"><header class="site-header"><a class="brand" href="#top" aria-label="씨앗세무회계 글 처음으로"><svg viewBox="0 0 30 34" aria-hidden="true"><path d="M15 31V16M15 23C3 23 2 13 3 9c9-1 15 4 12 14ZM15 17C13 6 20 2 28 3c0 9-5 14-13 14Z" fill="none" stroke="#284e36" stroke-width="1.6" stroke-linejoin="round"/></svg>씨앗세무회계<small>CIAT</small></a><span class="header-label">TAX INSIGHTS</span></header>
<main><div class="hero"><div class="hero-topline"><span class="pill">국세기본법</span><span>납세의무의 성립부터 소멸까지</span></div><div class="hero-grid"><div><h1>{html.escape(title.replace('[국세기본법] ',''))}</h1><p class="hero-deck">세금을 매길 수 있는 시간과, 이미 확정된 세금을 걷을 수 있는 시간.<br>부과제척기간과 징수권 소멸시효를 구별해서 살펴봅니다.</p></div><div class="hero-visual">{hero_svg}<p>같은 세금, 서로 다른 기간의 문제입니다.</p></div></div><div class="hero-meta"><span><strong>씨앗세무회계</strong></span><span>법령 확인 기준 · 2026. 11. 10.</span><span>국세기본법 연재 · 후속편</span></div></div>
<div class="key-takeaway" aria-label="핵심 내용"><div class="takeaway"><span>QUESTION 01</span><p>세금을 더 매길 수 있을까요?<br>부과제척기간을 확인합니다.</p></div><div class="takeaway"><span>QUESTION 02</span><p>정해진 세금을 걷을 수 있을까요?<br>징수권 소멸시효를 확인합니다.</p></div><div class="takeaway"><span>CHECK POINT</span><p>기간의 숫자뿐 아니라<br>기산점과 징수 이력을 함께 봅니다.</p></div></div>
<div class="reading-layout"><aside class="contents"><details open><summary>이 글의 차례</summary><nav aria-label="본문 목차"><ol>{toc}</ol></nav></details><p class="contents-note">기간은 세목과 사실관계에 따라<br>달라질 수 있습니다.<br>본문의 적용 전제와 예외를<br>함께 확인해 주세요.</p></aside><article class="article" aria-label="칼럼 본문">{article}<div class="keyword-list" aria-label="관련 키워드">{tags}</div></article></div></main>
<footer class="article-footer"><div><strong>씨앗세무회계</strong>세무·회계의 복잡한 문제를 차근차근 살펴봅니다.</div><a class="top-link" href="#top" aria-label="맨 위로 이동">↑</a></footer></div><script>{script}</script></body></html>'''
(HERE/'index.html').write_text(document,encoding='utf-8')

class TextParser(HTMLParser):
    def __init__(self):super().__init__();self.data=[]
    def handle_data(self,data):self.data.append(data)
def plaintext(s):
    p=TextParser();p.feed(s);return re.sub(r'\s+','', ''.join(p.data))
class SourceParser(HTMLParser):
    def __init__(self):super().__init__();self.depth=0;self.data=[]
    def handle_starttag(self,tag,attrs):
        if self.depth:
            if tag not in ('br','hr','img','input','meta','link'):self.depth+=1
        elif 'data-source-content' in dict(attrs):self.depth=1
    def handle_endtag(self,tag):
        if self.depth:self.depth-=1
    def handle_data(self,data):
        if self.depth:self.data.append(data)
actual=SourceParser();actual.feed(document)
actual_text=''.join(actual.data)
original_html=md(body_md)
base_render=''.join(md(s) for s in [intro_md]+[content for _,_,content in sections])
base_text=plaintext(base_render)
actual_normalized=re.sub(r'\s+','',actual_text)
import xml.etree.ElementTree as ET
for svg_block in re.findall(r'<svg\b.*?</svg>',document,re.S):ET.fromstring(svg_block)
source_headings=[heading for _,heading,_ in sections]
ids=re.findall(r'\bid="([^"]+)"',document)
report={
    'source_sha256':hashlib.sha256(raw.encode('utf-8')).hexdigest(),
    'sections':len(sections), 'svg_count':document.count('<svg'),
    'self_contained':not bool(re.search(r'<(?:link|script)[^>]+(?:href|src)=',document)),
    'internal_notes_excluded':'내부용' not in document and '진행 내역' not in document and '제출원고판정' not in document,
    'tables':original_html.count('<table>'),
    'source_text_exact_match':base_text==actual_normalized,
    'source_numbers_preserved':re.findall(r'\d[\d,.]*',base_text)==re.findall(r'\d[\d,.]*',actual_normalized),
    'section_headings_preserved':all(html.escape(h) in article for h in source_headings),
    'unique_element_ids':len(ids)==len(set(ids)),
    'svg_xml_valid':True,
    'source_links_present':all(html.escape(u,quote=True) in document for u in re.findall(r'\]\(([^)]+)\)',body_md)),
    'responsive_styles': '@container (max-width:850px)' in document,
    'print_styles':'@media print' in document,
    'browser_visual_check':'not performed - browser access host unavailable',
}
assert report['sections']==10 and report['svg_count']==5
assert report['source_text_exact_match'] and report['source_numbers_preserved'] and report['source_links_present'] and report['internal_notes_excluded'] and report['unique_element_ids']
(HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
