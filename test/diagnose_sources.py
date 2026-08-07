"""
源站抓取全量诊断脚本 v2 — 测试每个源站的连通性和章节列表获取能力
打印英文避免 Windows GBK 编码问题
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rules.rule_engine import get_rule_engine
from app.services.crawler_service import CrawlerService


async def diagnose_all():
    engine = get_rule_engine()
    crawler_svc = CrawlerService(concurrency=3, delay=0.5)

    results = []

    # Known test URLs for each source (a real book page)
    book_test_urls = {
        "https://www.biquh.com/": "https://www.biquh.com/book/123456/",
        "http://www.xbiqugu.la/": "http://www.xbiqugu.la/120/120345/",
        "https://www.shuhaige.net/": "https://www.shuhaige.net/book/12345/",
        "http://www.mcxs.info/": "http://www.mcxs.info/book/12345/",
        "http://www.xbiquwk.com/": "http://www.xbiquwk.com/120/120345/",
        "http://www.ujxsw.org/": "http://www.ujxsw.org/book/12345/",
        "http://www.yeudusk.com/": "http://www.yeudusk.com/book/12345/",
        "https://www.biquge365.net/": "https://www.biquge365.net/book/12345/",
        "https://www.ranwen8.cc/": "https://www.ranwen8.cc/book/12345/",
    }

    for i, rule in enumerate(engine.rules):
        name = rule.get("name", "unknown")
        url = rule.get("url", "")
        disabled = rule.get("disabled", False)
        search_enabled = "search" in rule and not rule.get("search", {}).get("disabled", False)

        status = {
            "id": i, "name": name, "url": url,
            "disabled": disabled,
            "search_enabled": search_enabled,
            "connectivity": "not tested",
            "toc_test": "not tested",
            "sample_chapters": 0,
            "error": None,
        }

        if disabled:
            status["connectivity"] = "disabled"
            status["toc_test"] = "disabled"
            results.append(status)
            print(f"[{i}] {name}: SKIP (disabled)")
            continue

        # Step 1: Connectivity test
        print(f"[{i}] {name}: checking connectivity...")
        try:
            conn = await crawler_svc.check_connectivity(url)
            status["connectivity"] = f"HTTP {conn.status_code}" if conn.reachable else f"unreachable: {conn.error_message}"
            if conn.error_message:
                status["error"] = conn.error_message
        except Exception as e:
            status["connectivity"] = f"exception: {e}"
            status["error"] = str(e)
            results.append(status)
            print(f"  [FAIL] connectivity exception: {e}")
            continue

        print(f"  connectivity: {status['connectivity']}")

        if conn.status_code and conn.status_code >= 500:
            results.append(status)
            print(f"  [SKIP] TOC test skipped (HTTP {conn.status_code})")
            continue

        # Step 2: Chapter list test
        test_url = book_test_urls.get(url, url)
        print(f"  TOC test URL: {test_url}")
        try:
            chapters = await crawler_svc.get_chapter_list(test_url, rule)
            if chapters:
                status["toc_test"] = "OK"
                status["sample_chapters"] = len(chapters)
                for j, (t, u) in enumerate(chapters[:3]):
                    print(f"    [{j+1}] {t[:40]} -> {u[:80]}")
            else:
                status["toc_test"] = "empty"
                status["error"] = (status["error"] or "") + " | TOC returned empty"
        except Exception as e:
            status["toc_test"] = "FAIL"
            status["error"] = (status["error"] or "") + f" | TOC: {e!s}"
            print(f"  [FAIL] TOC: {e}")

        results.append(status)
        print()

    # Summary report
    print("\n" + "=" * 80)
    print("SOURCE CRAWL DIAGNOSIS REPORT")
    print("=" * 80)

    ok_count = 0
    fail_count = 0
    for r in results:
        if r["disabled"]:
            flag = "SKIP"
        elif r["toc_test"] == "OK":
            flag = "OK  "
            ok_count += 1
        else:
            flag = "FAIL"
            fail_count += 1

        print(f"[{flag}] [{r['id']}] {r['name']}")
        print(f"      URL: {r['url']}")
        print(f"      Conn: {r['connectivity']} | TOC: {r['toc_test']} ({r['sample_chapters']} chapters)")
        if r["error"]:
            print(f"      Error: {r['error'][:200]}")
        print(f"      Search: {'enabled' if r['search_enabled'] else 'disabled'}")

    total_enabled = sum(1 for r in results if not r["disabled"])
    print(f"\nTotal: {ok_count} OK, {fail_count} FAIL, {sum(1 for r in results if r['disabled'])} disabled (of {len(results)} sources)")
    print(f"Success rate: {ok_count}/{total_enabled} ({100*ok_count//max(1,total_enabled)}%) of enabled sources")
    return results


if __name__ == "__main__":
    asyncio.run(diagnose_all())
