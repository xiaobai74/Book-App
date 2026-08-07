"""
E2E crawl test - English-only output.
Tests each enabled source with real book URLs.
"""
import asyncio
import sys, io
from pathlib import Path

# Force utf-8 stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rules.rule_engine import get_rule_engine
from app.services.crawler_service import CrawlerService

# Real book URLs tested against each source
TESTS = [
    ("xiangshu",        "http://www.xbiqugu.la/",        "http://www.xbiqugu.la/120/120345/"),
    ("shuhaige",        "https://www.shuhaige.net/",      "https://www.shuhaige.net/book/20024/"),
    ("mcxs",            "http://www.mcxs.info/",          "http://www.mcxs.info/book/10001/"),
    ("xbiquwk",         "http://www.xbiquwk.com/",        "http://www.xbiquwk.com/120/120345/"),
    ("ujxsw",           "http://www.ujxsw.org/",          "http://www.ujxsw.org/book/14410/"),
    ("yeudusk",         "http://www.yeudusk.com/",        "http://www.yeudusk.com/book/12345/"),
    ("biquge365",       "https://www.biquge365.net/",     "https://www.biquge365.net/book/17351/"),
]

async def test_one(engine, crawler_svc, key, domain, test_url):
    """Test crawl for one source. Returns {key: result_string}."""
    rule = engine.match_rule(domain)
    if not rule:
        return f"[{key}] FAIL: no rule matched for {domain}"

    rule_name = rule.get("name", "unknown")
    if rule.get("disabled"):
        return f"[{key}] SKIP: disabled ({rule_name})"

    # Connectivity
    conn = await crawler_svc.check_connectivity(domain)
    if not conn.reachable:
        return f"[{key}] FAIL: unreachable ({conn.error_message})"

    # Chapter list
    try:
        chapters = await crawler_svc.get_chapter_list(test_url, rule)
        if not chapters:
            return f"[{key}] FAIL: TOC returned 0 chapters"
        ch_count = len(chapters)
        first_title = chapters[0][0]
    except Exception as e:
        return f"[{key}] FAIL: TOC error: {e!s}"

    # Crawl first chapter
    try:
        content = await crawler_svc.crawl_chapter(chapters[0][1], rule)
        c_len = len(content)
        if c_len < 100:
            return f"[{key}] WARN: {ch_count} chapters, but content only {c_len} chars [{first_title}]"
        # Count Chinese characters
        cn = sum(1 for c in content if '一' <= c <= '鿿')
        return f"[{key}] OK: {ch_count} ch, ch1='{first_title}' content={c_len} chars ({cn} Chinese)"
    except Exception as e:
        return f"[{key}] WARN: {ch_count} ch OK, but crawl ch1 failed: {e!s}"

async def main():
    engine = get_rule_engine()
    crawler_svc = CrawlerService(concurrency=2, delay=0.5)

    print("="*70)
    print("E2E Crawl Test Results")
    print("="*70)

    results = []
    for key, domain, test_url in TESTS:
        print(f"  Testing {key}...")
        result = await test_one(engine, crawler_svc, key, domain, test_url)
        print(f"  {result}")
        results.append(result)

    print()
    ok = sum(1 for r in results if 'OK:' in r)
    warn = sum(1 for r in results if 'WARN' in r)
    fail = sum(1 for r in results if 'FAIL' in r)
    skip = sum(1 for r in results if 'SKIP' in r)
    print(f"Summary: {ok} OK, {warn} WARN, {fail} FAIL, {skip} SKIP")

asyncio.run(main())
