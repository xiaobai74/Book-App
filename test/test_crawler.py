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
    assert len(engine.rules) >= 8, f"Expected >=8 rules, got {len(engine.rules)}"
    print(f"  [PASS] Loaded {len(engine.rules)} rules")


def test_rule_matching():
    """测试规则匹配"""
    engine = get_rule_engine()

    rule = engine.match_rule("http://www.ibiqugu.net/123/456.html")
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
    assert len(searchable) >= 5, f"Expected >=5 searchable, got {len(searchable)}"
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

    # 中文数字章节：从小到大
    assert _chapter_sort_key("第一章 重生") < _chapter_sort_key("第十一章 短命")
    assert _chapter_sort_key("第九章 夺命") < _chapter_sort_key("第十章 平定")
    assert _chapter_sort_key("第二十九章 皇陵") < _chapter_sort_key("第三十章 许国")
    assert _chapter_sort_key("第29章 皇陵") < _chapter_sort_key("第三十章 许国")
    # 混合阿拉伯数字与中文数字：第一章应排在第11章之前
    assert _chapter_sort_key("第一章 重生") < _chapter_sort_key("第11章 短命")
    assert _chapter_sort_key("第9章 xxx") < _chapter_sort_key("第十一章 yyy")
    print("  [PASS] Chinese numeral chapter sort OK")


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


def test_filter_element_removal():
    """测试 filterElement 整块删除推广元素"""
    from app.services.crawler_service import CrawlerService

    svc = CrawlerService()
    rule = {
        "chapter": {
            "title": ".bookname > h1",
            "content": "#content",
            "paragraphTagClosed": False,
            "paragraphTag": "<br>+",
            "filterElement": "#content_tip, #content > p",
            "filterTag": "div, p, script",
        }
    }
    html = (
        '<div id="content"><div id="content_tip"><b>最新网址：www.xbiqugu.la</b></div>'
        "正文第一段。<br>正文第二段。"
        '<p><a href="http://koubei.baidu.com/s/xbiqugu.la">亲,点击进去,给个好评呗</a>'
        "<br>手机站全新改版升级地址：http://wap.xbiqugu.la，无广告清新阅读！</p></div>"
    )
    content = svc._parse_chapter_content(html, rule)
    assert "最新网址" not in content, f"content_tip 未移除: {content[:50]}"
    assert "好评" not in content, f"好评推广未移除: {content[-80:]}"
    assert "手机站" not in content, f"手机站推广未移除: {content[-80:]}"
    assert "正文第一段。" in content, "正文被误删"
    assert "正文第二段。" in content, "正文被误删"
    print("  [PASS] filterElement 整块删除推广元素 OK")


def test_chapter_sort_with_volume_reset():
    """测试卷重置感知排序：多卷小说每卷从第一章重新计数时不打乱顺序"""
    from app.services.crawler_service import sort_chapter_pairs

    def titles(pairs):
        return [t for t, _ in pairs]

    # 1) 《诛仙》类：每卷 10 章重新计数，应完全保持原顺序
    zx = [(f"第{n}章 标题", "u") for n in range(1, 11)]
    zx += [(f"第{n}章 标题", "u") for n in range(1, 11)]
    zx += [(f"第{n}章 标题", "u") for n in range(1, 11)]
    assert titles(sort_chapter_pairs(zx)) == titles(zx)
    print("  [PASS] Volume reset keeps original order OK")

    # 2) 整页倒序（最新章在前），应纠正为升序
    rev = [(f"第{n}章 标题", "u") for n in range(31, 0, -1)]
    sorted_titles = titles(sort_chapter_pairs(rev))
    assert sorted_titles[0].startswith("第1章")
    assert sorted_titles[-1].startswith("第31章")
    print("  [PASS] Fully reversed page corrected to ascending OK")

    # 3) 浮动项（序幕/尾声）固定在原位置
    with_pro = [("序幕", "u")] + [(f"第{n}章 标题", "u") for n in range(1, 6)]
    result = sort_chapter_pairs(with_pro)
    assert result[0][0] == "序幕"
    assert result[1][0].startswith("第1章")
    print("  [PASS] Floating prologue pinned OK")

    # 4) 卷标题（第三卷）不参与序号比较，不打断回落判断
    vol = [("第三卷 青云", "u")] + [(f"第{n}章 标题", "u") for n in range(1, 4)]
    vol += [("第四卷 迷局", "u")] + [(f"第{n}章 标题", "u") for n in range(1, 4)]
    assert titles(sort_chapter_pairs(vol)) == titles(vol)
    print("  [PASS] Volume headers keep order OK")

    # 5) 中文数字与阿拉伯数字混合，回落判断一致
    mixed = [("第一章 重生", "u"), ("第十章 平定", "u"), ("第11章 短命", "u"), ("第12章 南明", "u")]
    assert titles(sort_chapter_pairs(mixed)) == titles(mixed)
    print("  [PASS] Mixed Chinese/Arabic numerals keep order OK")

    # 6) 倒序的「第x卷 第y章」格式也能纠正
    vrev = [(f"第{v}卷 第{c}章", "u") for v in range(5, 0, -1) for c in range(1, 3)]
    sorted_v = titles(sort_chapter_pairs(vrev))
    assert sorted_v[0].startswith("第1卷 第1章")
    assert sorted_v[-1].startswith("第5卷 第2章")
    print("  [PASS] Volume-chapter format reversed corrected OK")


def test_normalize_content():
    """测试正文规范化：\r\n / NBSP / HTML 实体 / 残留标签 / 脏缩进"""
    from app.services.crawler_service import CrawlerService

    raw = "第一段。\r\n \n\xa0\xa0\xa0\xa0第二段&nbsp;结束。<p>第三段</p>&#26085;"
    out = CrawlerService._normalize_content(raw)
    assert "\r" not in out, f"残留回车符: {out!r}"
    assert "\xa0" not in out, f"残留 NBSP: {out!r}"
    assert "<" not in out and ">" not in out, f"残留标签: {out!r}"
    assert "&#" not in out and "&nbsp;" not in out, f"残留实体: {out!r}"
    assert "第一段。" in out and "第二段" in out and "第三段" in out, f"正文丢失: {out!r}"
    assert "日" in out, f"数字实体未解码: {out!r}"
    assert "\n\n\n" not in out, f"空行未折叠: {out!r}"
    # 幂等：再规范化一次结果不变
    assert CrawlerService._normalize_content(out) == out, "规范化非幂等"
    print("  [PASS] _normalize_content 规范化 OK")


def test_extract_page_title():
    """测试章节标题提取（去除页码后缀）"""
    from app.services.crawler_service import CrawlerService

    svc = CrawlerService()
    html = '<div class="bookname"><h1>第一章 青云(2/3)</h1></div><div id="content">正文</div>'
    rule = {"chapter": {"title": ".bookname > h1", "content": "#content"}}
    assert svc._extract_page_title(html, rule) == "第一章 青云"
    # 无 title 选择器 → ""
    assert svc._extract_page_title(html, {"chapter": {"content": "#content"}}) == ""
    # 选择器未命中 → ""
    assert svc._extract_page_title(html, {"chapter": {"title": "#nope"}}) == ""
    print("  [PASS] _extract_page_title 标题提取/去页码 OK")


def test_pagination_chapter_boundary():
    """分页遇到“下一章”（标题变化）应停止合并，避免多章合并"""
    import asyncio

    from app.services.crawler_service import CrawlerService

    svc = CrawlerService()
    svc.min_interval = 0
    svc.max_interval = 0

    base = "http://x.com/book/"
    pages = {
        base + "1.html": '<div class="bookname"><h1>第一章 青云(1/2)</h1></div>'
                         '<div id="content">第一章正文A</div>'
                         '<a id="pager_next" href="2.html">下一页</a>',
        base + "2.html": '<div class="bookname"><h1>第一章 青云(2/2)</h1></div>'
                         '<div id="content">第一章正文B</div>'
                         '<a id="pager_next" href="3.html">下一页</a>',
        base + "3.html": '<div class="bookname"><h1>第二章 迷局</h1></div>'
                         '<div id="content">第二章正文C</div>'
                         '<a id="pager_next" href="4.html">下一页</a>',
    }

    async def fake_get(client, url, retries=None):
        return pages[url]

    svc._get = fake_get
    rule = {"chapter": {
        "title": ".bookname > h1",
        "content": "#content",
        "paragraphTagClosed": True,
        "pagination": True,
        "nextPage": "#pager_next",
    }}
    result = asyncio.run(
        svc._crawl_chapter_with_pagination(None, base + "1.html", rule)
    )
    assert "第一章正文A" in result, result
    assert "第一章正文B" in result, result
    assert "第二章正文C" not in result, f"下一章被错误合并: {result}"
    assert "第二章" not in result, f"下一章标题混入: {result}"
    print("  [PASS] 分页章节边界停止（不多章合并）OK")


def test_check_connectivity_dns_failure():
    """DNS 解析失效应归类为域名失效并给出“换源”建议"""
    import asyncio

    import httpx

    from app.services.crawler_service import CrawlerService

    svc = CrawlerService()
    svc._connectivity_cache.clear()

    class FakeStreamCtx:
        async def __aenter__(self):
            raise httpx.ConnectError("[Errno 11004] getaddrinfo failed")

        async def __aexit__(self, *a):
            return False

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def stream(self, *a, **k):
            return FakeStreamCtx()

    svc._make_client = lambda cookies=None: FakeClient()
    result = asyncio.run(svc.check_connectivity("http://www.dead-source-xyz.la/1/"))
    assert result.reachable is False
    assert "无法解析" in (result.error_message or ""), result.error_message
    assert "换用其它源站" in (result.suggested_fix or ""), result.suggested_fix
    print("  [PASS] check_connectivity DNS 失效提示 OK")


def run_all():
    tests = [
        test_rule_loading,
        test_rule_matching,
        test_list_sources,
        test_list_searchable_sources,
        test_chapter_sort_key,
        test_chapter_sort_with_volume_reset,
        test_crawler_import,
        test_search_service_import,
        test_cookies_parsing,
        test_form_data_parsing,
        test_filter_element_removal,
        test_normalize_content,
        test_extract_page_title,
        test_pagination_chapter_boundary,
        test_check_connectivity_dns_failure,
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
