"""探测香书小说网排行榜页面结构（临时脚本）"""
import httpx
import ssl
from bs4 import BeautifulSoup

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

def fetch(url):
    with httpx.Client(timeout=30, follow_redirects=True, verify=ctx, headers=headers) as c:
        r = c.get(url)
        print(f"[{url}] status={r.status_code} len={len(r.text)}")
        return r.text

# 探测排行榜页面结构
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

html = fetch("http://www.xbiqugu.la/paihangbang/")
soup = BeautifulSoup(html, "html.parser")

print("\n=== 页面标题/板块标题 ===")
for tag in soup.select("h1, h2, h3, .title, .top-title, .rank-title"):
    print(f"  <{tag.name} class={tag.get('class')}> {tag.get_text(strip=True)[:50]}")

print("\n=== 主要列表容器（含 >=5 个链接的 ul/div） ===")
for el in soup.select("ul, div, ol"):
    links = el.select("a")
    cls = " ".join(el.get("class", []))
    if 5 <= len(links) <= 60 and el.find_parent(class_=cls) is None:
        texts = [a.get_text(strip=True) for a in links[:5]]
        print(f"  <{el.name} id={el.get('id')} class={cls}> {len(links)} links, 样例: {texts}")

print("\n=== 页内链接（含小说详情页特征）前 30 ===")
import re
for a in soup.select("a")[:80]:
    href = a.get("href", "")
    if re.search(r"/(xiaoshuo|book|read|\d+)", href):
        print(f"  {a.get_text(strip=True)[:30]!r} -> {href}")
