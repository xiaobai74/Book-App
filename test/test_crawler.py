"""
规则引擎与爬虫服务单元测试
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from rules.rule_engine import RuleEngine, get_rule_engine


def test_rule_loading():
    """测试规则加载"""
    engine = get_rule_engine()
    assert engine.loaded
    assert len(engine.rules) >= 10, f"Expected >=10 rules, got {len(engine.rules)}"
    print(f"  [PASS] Loaded {len(engine.rules)} rules")


def test_rule_matching():
    """测试规则匹配"""
    engine = get_rule_engine()

    rule = engine.match_rule("http://www.xbiqugu.la/123/456.html")
    assert rule is not None
    assert rule["name"] == "香书小说", f"Expected '香书小说', got '{rule['name']}'"
    print(f"  [PASS] Exact domain match: {rule['name']}")

    rule = engine.match_rule("https://www.shuhaige.net/book/123/")
    assert rule is not None
    assert rule["name"] == "书海阁小说网"
    print(f"  [PASS] Exact domain match: {rule['name']}")

    rule = engine.match_rule("https://www.unknown-example.com/")
    assert rule is None
    print(f"  [PASS] Unknown domain returns None")


def test_list_sources():
    """测试源站列表"""
    engine = get_rule_engine()
    sources = engine.list_sources()
    assert len(sources) > 0
    for s in sources:
        assert "id" in s
        assert "name" in s
        assert "url" in s
        assert isinstance(s["has_search"], bool)
    print(f"  [PASS] {len(sources)} sources format OK")


def test_list_searchable_sources():
    """测试可搜索源站"""
    engine = get_rule_engine()
    searchable = engine.list_searchable_sources()
    assert len(searchable) >= 7, f"Expected >=7 searchable, got {len(searchable)}"
    for sid, rule in searchable:
        assert "search" in rule
        assert not (rule.get("search") or {}).get("disabled", False)
    print(f"  [PASS] {len(searchable)} searchable sources")


def test_chapter_sort_key():
    """测试章节排序"""
    from app.services.crawler_service import _chapter_sort_key

    assert _chapter_sort_key("第1章 测试") < _chapter_sort_key("第10章 测试")
    assert _chapter_sort_key("第29卷 第18章") < _chapter_sort_key("第30卷 第1章")
    print("  [PASS] Volume/chapter sort OK")

    assert _chapter_sort_key("1. 引子") < _chapter_sort_key("10. 正文")
    print("  [PASS] Numeric prefix sort OK")

    assert _chapter_sort_key("001") < _chapter_sort_key("002")
    print("  [PASS] Pure numeric sort OK")


def test_crawler_import():
    """测试爬虫服务导入"""
    from app.services.crawler_service import CrawlerService, crawler

    assert crawler is not None
    assert isinstance(crawler, CrawlerService)
    assert crawler.concurrency == 5
    assert crawler.min_interval == 0.2
    assert crawler.max_interval == 0.4
    print("  [PASS] CrawlerService import and config OK")


def test_search_service_import():
    """测试搜索服务导入"""
    from app.services.search_service import SearchService, search_service

    assert search_service is not None
    assert isinstance(search_service, SearchService)
    print("  [PASS] SearchService import OK")


def test_cookies_parsing():
    """测试 Cookies 解析"""
    from app.services.crawler_service import CrawlerService

    svc = CrawlerService()
    cookies = svc._parse_cookies("waf_sc=''; HMACCOUNT=''")
    assert cookies == {"waf_sc": "", "HMACCOUNT": ""}, f"Cookies parse failed: {cookies}"
    print(f"  [PASS] Cookies parse: {cookies}")

    cookies2 = svc._parse_cookies("k1=v1; k2='v2'")
    assert cookies2 == {"k1": "v1", "k2": "v2"}
    print(f"  [PASS] Cookies parse: {cookies2}")


def test_form_data_parsing():
    """测试 Form Data 解析"""
    from app.services.search_service import SearchService

    svc = SearchService()
    data = svc._parse_form_data("{searchkey: doupo, searchtype: all}")
    assert data == {"searchkey": "doupo", "searchtype": "all"}, f"Form data parse failed: {data}"
    print(f"  [PASS] Form data parse: {data}")


def run_all():
    tests = [
        test_rule_loading,
        test_rule_matching,
        test_list_sources,
        test_list_searchable_sources,
        test_chapter_sort_key,
        test_crawler_import,
        test_search_service_import,
        test_cookies_parsing,
        test_form_data_parsing,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            failed += 1
            print(f"  [FAIL] {test.__name__}: {e}")

    print(f"\n{'='*50}")
    print(f"Result: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
