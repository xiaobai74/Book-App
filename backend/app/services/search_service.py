"""
外部源站搜索服务

遍历所有启用的源站规则（含 search 配置的），发起并发搜索请求，
解析 HTML 结果，提取书籍信息，合并去重后返回。
"""

import asyncio
import logging
import random
import re
import ssl
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urljoin

import httpx
from bs4 import BeautifulSoup

from rules.rule_engine import get_rule_engine

logger = logging.getLogger(__name__)


class SearchCache:
    """外部搜索结果的内存 LRU + TTL 缓存。

    - 仅依赖 ``collections.OrderedDict``，无外部缓存库依赖。
    - 命中时将 key 移动到末尾（最近使用），超出容量时淘汰最久未用项。
    - 读取时惰性检查 TTL，过期项立即剔除。
    - asyncio 单线程模型下读写均为同步原子操作，无需额外加锁。
    """

    def __init__(self, max_size: int = 200, ttl: int = 300):
        # 值为 (写入时间戳, SearchResult 列表)；SearchResult 在下方定义，使用 Any 避免前向引用
        self._cache: "OrderedDict[str, tuple[float, Any]]" = OrderedDict()
        self._max_size = max(1, int(max_size))
        self._ttl = max(1, int(ttl))
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """读取缓存；命中返回结果列表副本（避免外部修改污染缓存），未命中或过期返回 None。"""
        item = self._cache.get(key)
        if item is None:
            self._misses += 1
            return None
        timestamp, value = item
        if time.monotonic() - timestamp >= self._ttl:
            # 过期：惰性删除
            del self._cache[key]
            self._misses += 1
            return None
        # LRU: 命中移到末尾
        self._cache.move_to_end(key)
        self._hits += 1
        # 返回浅拷贝，防止调用方修改 list 影响缓存
        return list(value)

    def set(self, key: str, value: Any) -> None:
        """写入缓存；超出容量时淘汰最久未使用项。"""
        if key in self._cache:
            del self._cache[key]
        self._cache[key] = (time.monotonic(), list(value))
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, key: str) -> None:
        """显式失效某个缓存项（保留接口，便于将来支持 force 刷新场景）。"""
        self._cache.pop(key, None)

    def clear(self) -> None:
        """清空缓存。"""
        self._cache.clear()

    @property
    def stats(self) -> dict[str, int]:
        """返回命中统计，便于日志/监控。"""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl": self._ttl,
            "hits": self._hits,
            "misses": self._misses,
        }


# 模块级缓存单例：仅用于外部源站搜索结果，不影响书架内 DB 搜索。
# 容量 200，TTL 5 分钟，与 ranking_service 的全局单例模式保持一致。
search_cache = SearchCache(max_size=200, ttl=300)


def _build_search_cache_key(keyword: str, source_id: int | None) -> str:
    """生成缓存键：keyword 归一化（去首尾空格、转小写） + 源站 ID。

    source_id 为 None 表示搜索全部源站，键中以字面量 "None" 占位，
    与指定具体源站的结果天然区分。
    """
    normalized = (keyword or "").strip().lower()
    return f"{normalized}:{source_id}"

_CURRENT_UA_VERSION = "131"
_USER_AGENTS = [
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
]


@dataclass
class SearchResult:
    """外部搜索结果"""
    title: str
    author: str = "未知"
    source_url: str = ""  # 书籍详情页/目录页 URL
    source_name: str = ""  # 源站名称
    source_id: int = 0  # 源站 ID
    category: str = ""
    word_count: str = ""
    status: str = ""  # 连载状态
    latest_chapter: str = ""
    last_update_time: str = ""
    cover_url: str = ""
    intro: str = ""

    @property
    def unique_key(self) -> str:
        """用于去重的唯一键（书名+作者）。"""
        return f"{self.title.strip()}_{self.author.strip()}"


class SearchService:
    """外部源站搜索服务"""

    def __init__(self, rules_file: str | None = None):
        self._engine = get_rule_engine(rules_file)
        self._ssl_context = ssl.create_default_context()
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    def _make_client(self, cookies: dict[str, str] | None = None) -> httpx.AsyncClient:
        """创建 HTTP 客户端。"""
        headers = {
            "User-Agent": random.choice(_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "DNT": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": random.choice([
                "https://www.google.com/",
                "https://www.bing.com/",
                "https://www.baidu.com/",
            ]),
        }

        client_cookies = None
        if cookies:
            client_cookies = httpx.Cookies()
            for k, v in cookies.items():
                client_cookies.set(k, v, domain="")

        return httpx.AsyncClient(
            # v2.7 阶段1a：收紧单源超时（原 30s/15s）。慢源站由流式搜索按源增量下发，
            # 不再拖住整次搜索；超时源记为失败，用户已收到其他源站的结果。
            timeout=httpx.Timeout(10.0, connect=6.0),
            follow_redirects=True,
            max_redirects=5,
            verify=self._ssl_context,
            http2=False,
            headers=headers,
            cookies=client_cookies,
        )

    # ── 公共 API ───────────────────────────────────────

    async def search(
        self,
        keyword: str,
        source_id: int | None = None,
        search_limit: int = 30,
        force: bool = False,
    ) -> list[SearchResult]:
        """对外部源站发起搜索请求，合并去重结果。

        Args:
            keyword: 搜索关键词
            source_id: 指定源站 ID，None 则搜索所有源站
            search_limit: 每个源站最大结果数
            force: 为 True 时跳过内存缓存，强制重拉源站（仅供内部/调试使用，
                现有 HTTP API 未暴露此参数，API 响应结构保持不变）

        Returns:
            去重后的搜索结果列表
        """
        # ── 缓存层：仅适用于外部源站搜索，不影响书架内 DB 搜索 ──
        cache_key = _build_search_cache_key(keyword, source_id)
        if not force:
            cached = search_cache.get(cache_key)
            if cached is not None:
                logger.info(
                    f"搜索「{keyword}」命中缓存: {len(cached)} 条结果 (source_id={source_id})"
                )
                return cached

        if source_id is not None:
            rule = self._engine.get_rule_by_id(source_id)
            if rule is None:
                return []
            if not rule.get("search") or rule.get("search", {}).get("disabled"):
                return []
            searchable = [(source_id, rule)]
        else:
            searchable = self._engine.list_searchable_sources()

        if not searchable:
            logger.warning("没有可用的搜索源站")
            return []

        # 并发搜索所有源站
        tasks = [
            self._search_one_source(keyword, sid, rule, search_limit)
            for sid, rule in searchable
        ]
        source_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并去重
        all_results: list[SearchResult] = []
        seen: set[str] = set()

        for item in source_results:
            if isinstance(item, Exception):
                logger.warning(f"搜索源站异常: {item}")
                continue
            if not item:
                continue
            for result in item:
                key = result.unique_key
                if key not in seen:
                    seen.add(key)
                    all_results.append(result)

        logger.info(f"搜索「{keyword}」: {len(searchable)} 个源站, {len(all_results)} 条结果")

        # ── 写入缓存：仅缓存非空结果，避免临时性源站故障被缓存住 ──
        if all_results:
            search_cache.set(cache_key, all_results)

        return all_results

    # ── 流式搜索（v2.7 阶段1a）─────────────────────────

    # 整体流截止：超过后未完成源站按失败收尾，避免前端无限等待最慢源站
    STREAM_TOTAL_DEADLINE = 20.0

    async def search_stream(
        self,
        keyword: str,
        source_id: int | None = None,
        search_limit: int = 30,
    ):
        """按源站增量产出搜索结果（供 SSE 端点消费）。

        yield (kind, payload)：
          meta                {"sources": [{"id","name"}...], "cached": bool}
          source              {"source_id", "source_name", "results": list[SearchResult]}
                              —— 单源完成即推送（含空结果/失败，results 为空列表）
          ping                {} —— 心跳，API 层转为 SSE 注释行
          done                {"total": int} —— 合并去重后的总数

        与同步 search() 共用 LRU+TTL 缓存：命中时按源站分组回放，不触网。
        同步端点保持不变，旧客户端零影响。
        """
        cache_key = _build_search_cache_key(keyword, source_id)
        cached = search_cache.get(cache_key)
        if cached is not None:
            groups: "OrderedDict[tuple[int, str], list[SearchResult]]" = OrderedDict()
            for r in cached:
                groups.setdefault((r.source_id, r.source_name), []).append(r)
            yield ("meta", {
                "sources": [{"id": k[0], "name": k[1]} for k in groups],
                "cached": True,
            })
            for (gid, gname), rs in groups.items():
                yield ("source", {"source_id": gid, "source_name": gname, "results": rs})
            yield ("done", {"total": len(cached)})
            return

        if source_id is not None:
            rule = self._engine.get_rule_by_id(source_id)
            if rule is None or not rule.get("search") or rule.get("search", {}).get("disabled"):
                yield ("meta", {"sources": [], "cached": False})
                yield ("done", {"total": 0})
                return
            searchable = [(source_id, rule)]
        else:
            searchable = self._engine.list_searchable_sources()

        yield ("meta", {
            "sources": [{"id": sid, "name": rule.get("name", "")} for sid, rule in searchable],
            "cached": False,
        })
        if not searchable:
            logger.warning("流式搜索：没有可用的搜索源站")
            yield ("done", {"total": 0})
            return

        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.STREAM_TOTAL_DEADLINE
        tasks = {
            asyncio.create_task(
                self._search_one_source(keyword, sid, rule, search_limit)
            ): (sid, rule.get("name", "未知源站"))
            for sid, rule in searchable
        }
        merged: list[SearchResult] = []
        seen: set[str] = set()

        pending = set(tasks)
        try:
            while pending:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    for t in pending:
                        sid, sname = tasks[t]
                        logger.warning(f"流式搜索截止，未完成源站按失败处理: {sname}")
                        yield ("source", {"source_id": sid, "source_name": sname, "results": []})
                    break
                finished, pending = await asyncio.wait(
                    pending, timeout=min(5.0, remaining),
                )
                if not finished:
                    yield ("ping", {})
                    continue
                for t in finished:
                    sid, sname = tasks[t]
                    results: list[SearchResult] = []
                    if not t.cancelled() and t.exception() is None:
                        results = t.result()
                    elif t.exception() is not None:
                        logger.warning(f"流式搜索源站异常 [{sname}]: {t.exception()}")
                    for r in results:
                        if r.unique_key not in seen:
                            seen.add(r.unique_key)
                            merged.append(r)
                    yield ("source", {"source_id": sid, "source_name": sname, "results": results})
        finally:
            for t in pending:
                t.cancel()

        # 与同步 search() 相同的缓存语义：仅缓存非空结果
        if merged:
            search_cache.set(cache_key, merged)
        logger.info(f"流式搜索「{keyword}」完成: {len(searchable)} 源站, {len(merged)} 条结果")
        yield ("done", {"total": len(merged)})

    # ── 单源站搜索 ────────────────────────────────────

    async def _search_one_source(
        self,
        keyword: str,
        source_id: int,
        rule: dict[str, Any],
        search_limit: int,
    ) -> list[SearchResult]:
        """在单个源站搜索。"""
        search_rule = rule.get("search", {})
        if not search_rule:
            return []

        source_name = rule.get("name", "未知源站")
        search_url = search_rule.get("url", "")
        method = search_rule.get("method", "get").lower()
        result_selector = search_rule.get("result", "")

        if not search_url or not result_selector:
            return []

        # 构造请求数据
        data_template = search_rule.get("data", "")
        data = data_template.replace("%s", keyword) if data_template else None
        cookies_raw = search_rule.get("cookies", "")
        cookies = self._parse_cookies(cookies_raw) if cookies_raw else None

        try:
            async with self._make_client(cookies=cookies) as client:
                if method == "post":
                    # POST 请求: data 作为 form 提交
                    post_data = self._parse_form_data(data) if data else None
                    if post_data:
                        html = await self._post(client, search_url, post_data)
                    else:
                        html = await self._post(client, search_url, data)
                else:
                    # GET 请求: data 作为 query string 拼接
                    # search_url 可能已包含 %s 占位符
                    if "%s" in search_url:
                        url = search_url.replace("%s", quote(keyword))
                    else:
                        # 关键词不在 URL 中时，作为查询参数拼接
                        url = search_url
                        if data:
                            # data 模板中的 %s 也需编码
                            encoded_data = data.replace("%s", quote(keyword))
                            url = f"{url}?{encoded_data}"
                        else:
                            url = f"{url}?q={quote(keyword)}"
                    html = await self._get(client, url)

                results = self._parse_search_results(
                    html, rule, source_id, source_name, search_limit,
                )

                # 处理搜索结果分页
                if search_rule.get("pagination"):
                    next_selector = search_rule.get("nextPage", "")
                    if next_selector and len(results) < search_limit:
                        more = await self._fetch_search_pages(
                            client, search_url, method, data, rule,
                            source_id, source_name, search_limit,
                            results, html,
                        )
                        results.extend(more)

                return results

        except asyncio.TimeoutError:
            logger.warning(f"搜索源站超时: {source_name}")
            return []
        except Exception as e:
            logger.warning(f"搜索源站失败 [{source_name}]: {e}")
            return []

    async def _fetch_search_pages(
        self,
        client: httpx.AsyncClient,
        base_url: str,
        method: str,
        data: str | None,
        rule: dict,
        source_id: int,
        source_name: str,
        limit: int,
        existing: list[SearchResult],
        first_page_html: str = "",
    ) -> list[SearchResult]:
        """获取搜索结果的后续分页，最多翻 2 页。"""
        search_rule = rule.get("search", {})
        next_selector = search_rule.get("nextPage", "")
        if not next_selector:
            return []

        all_results: list[SearchResult] = list(existing)
        current_html = first_page_html
        max_extra_pages = 2

        for _ in range(max_extra_pages):
            if len(all_results) >= limit:
                break

            # 查找下一页链接
            soup = BeautifulSoup(current_html or "", "html.parser")

            # 查找下一页链接
            next_el = self._select_one(soup, next_selector)
            if not next_el:
                break

            next_url = None
            if next_el.name == "a":
                next_url = next_el.get("href", "")
            elif next_el.name == "option":
                next_url = next_el.get("value", "")

            if not next_url or next_url == "#":
                break

            # 补全相对 URL
            if not next_url.startswith("http"):
                from urllib.parse import urljoin
                next_url = urljoin(base_url, next_url)

            try:
                if method == "post":
                    resp = await client.post(next_url)
                else:
                    resp = await client.get(next_url)
                resp.raise_for_status()
                current_html = SearchService._decode_response(resp)
            except Exception as e:
                logger.warning(f"搜索分页请求失败: {e}")
                break

            # 解析当前页结果
            page_results = self._parse_search_results(
                current_html, rule, source_id, source_name, limit,
            )
            if not page_results:
                break

            # 去重后追加
            for r in page_results:
                if len(all_results) >= limit:
                    break
                key = r.unique_key
                if not any(x.unique_key == key for x in all_results):
                    all_results.append(r)

        # 返回新增的结果（不包括原本已有的）
        return all_results[len(existing):]

    # ── 结果解析 ──────────────────────────────────────

    def _parse_search_results(
        self,
        html: str,
        rule: dict,
        source_id: int,
        source_name: str,
        limit: int,
    ) -> list[SearchResult]:
        """从 HTML 中解析搜索结果。"""
        search_rule = rule.get("search", {})
        result_selector = search_rule.get("result", "")

        if not result_selector:
            return []

        soup = BeautifulSoup(html, "html.parser")
        row_elements = self._select_all(soup, result_selector)

        if not row_elements:
            logger.debug(f"选择器 '{result_selector}' 在搜索结果页未匹配到任何元素")
            return []

        results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for row in row_elements[:limit]:
            # 先提取 title，因为构造函数依赖它
            extracted_title = self._extract_field(row, search_rule, "bookName", "text") or ""
            if not extracted_title or len(extracted_title) < 1:
                continue

            result = SearchResult(
                title=extracted_title,
                source_name=source_name,
                source_id=source_id,
            )

            # 提取其他字段
            result.author = self._extract_field(row, search_rule, "author", "text") or "未知"
            result.category = self._extract_field(row, search_rule, "category", "text") or ""
            result.latest_chapter = self._extract_field(row, search_rule, "latestChapter", "text") or ""
            result.last_update_time = self._extract_field(row, search_rule, "lastUpdateTime", "text") or ""
            result.word_count = self._extract_field(row, search_rule, "wordCount", "text") or ""
            result.status = self._extract_field(row, search_rule, "status", "text") or ""

            # 提取详情页 URL
            result.source_url = self._extract_field(row, search_rule, "bookName", "href") or ""

            if result.source_url in seen_urls:
                continue
            seen_urls.add(result.source_url)

            # 如果 URL 是相对路径，补全
            base = rule.get("url", "")
            if result.source_url and not result.source_url.startswith("http"):
                result.source_url = urljoin(base, result.source_url)

            # 去重检查
            if not any(r.title == result.title and r.author == result.author for r in results):
                results.append(result)

        return results

    # ── 字段提取 ──────────────────────────────────────

    def _extract_field(
        self,
        row,
        search_rule: dict,
        field_name: str,
        extract_type: str = "text",
    ) -> str | None:
        """从搜索结果行中提取指定字段。

        Args:
            row: BeautifulSoup 元素（单行结果）
            search_rule: 搜索规则
            field_name: 字段名 (bookName, author, category 等)
            extract_type: "text" 获取文本, "href" 获取链接

        Returns:
            提取到的字符串，或 None
        """
        selector = search_rule.get(field_name, "")
        if not selector:
            return None

        el = self._select_one(row, selector)
        if not el:
            return None

        if extract_type == "href":
            return el.get("href", "") or None
        else:
            return el.get_text(strip=True) or None

    # ── 选择器工具 ────────────────────────────────────

    @staticmethod
    def _select_one(soup, selector: str):
        """选择单个元素（CSS Selector），支持 @attr 后缀提取属性值。"""
        if not selector:
            return None

        attr_name = None
        # 与 CrawlerService 一致：查找最后一个 @ 且不是 CSS 属性选择器
        last_at_idx = selector.rfind("@")
        if last_at_idx > 0:
            suffix = selector[last_at_idx + 1:]
            if not suffix.startswith("js:") and "=" not in suffix:
                attr_name = suffix.strip()
                selector = selector[:last_at_idx]

        result = soup.select_one(selector)
        if result and attr_name:
            return result.get(attr_name, "")
        return result

    @staticmethod
    def _select_all(soup, selector: str) -> list:
        """选择所有匹配元素（CSS Selector），支持 @attr 后缀提取属性值。"""
        if not selector:
            return []

        attr_name = None
        # 与 CrawlerService 一致：查找最后一个 @ 且不是 CSS 属性选择器
        last_at_idx = selector.rfind("@")
        if last_at_idx > 0:
            suffix = selector[last_at_idx + 1:]
            if not suffix.startswith("js:") and "=" not in suffix:
                attr_name = suffix.strip()
                selector = selector[:last_at_idx]

        results = soup.select(selector)
        if attr_name and results:
            return [r.get(attr_name, "") for r in results]
        return results

    # ── 编码检测 & 解码 ─────────────────────────────

    @staticmethod
    def _decode_response(resp: httpx.Response) -> str:
        """从 httpx Response 中安全解码 HTML 正文。

        优先使用服务器声明的 charset_encoding，其次从 HTML <meta> 标签检测，
        最后回退为 utf-8。必须先设置 encoding 再访问 .text，否则 httpx 会锁定编码。

        同时检测反爬/限流页面，如果页面内容主要是 JS 跳转或错误提示，
        抛出 RuntimeError 而不是返回空 HTML 让选择器静默失败。
        """
        encoding: str | None = resp.charset_encoding
        if not encoding:
            # 从原始字节中检测 HTML charset 声明（避免触发 .text 的编码锁定）
            encoding = SearchService._detect_encoding(resp.content[:4096])
        resp.encoding = encoding or "utf-8"
        text = resp.text

        # 检测反爬/限流页面
        error_msg = SearchService._check_block_page(text)
        if error_msg:
            raise RuntimeError(f"搜索被拦截: {error_msg}")

        return text

    @staticmethod
    def _check_block_page(html: str) -> str | None:
        """检测搜索页面是否被反爬或限流拦截。

        常见模式：
        - JS alert 提示搜索间隔
        - 错误提示页面（无搜索结果）
        - 验证码/人机验证页面
        - 页面重定向（无实际内容）

        Returns:
            拦截原因字符串，如果页面正常则返回 None。
        """
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # 模式 1: inline script alert
        for script in soup.find_all("script"):
            text = script.get_text(strip=True)
            if "alert(" in text and any(
                kw in text.lower() for kw in ("搜索间隔", "稍后", "请稍后", "频率", "太快")
            ):
                alert_text = re.search(r"alert\s*\(\s*['\"](.+?)['\"]\s*\)", text)
                if alert_text:
                    return alert_text.group(1)
                return "疑似搜索频率限制"

        # 模式 2: 页面标题是"错误提示"或类似
        title = soup.find("title")
        if title:
            title_text = title.get_text(strip=True)
            if "错误提示" in title_text:
                # 提取具体错误信息
                body = soup.find("body")
                if body:
                    error_parts = [p.get_text(strip=True) for p in body.find_all("p") if p.get_text(strip=True)]
                    if error_parts:
                        return f"源站返回错误页: {error_parts[0][:100]}"
                return "源站返回错误页"

        # 模式 3: 页面几乎为空，可能被跳转
        body = soup.find("body")
        if not body or len(body.get_text(strip=True)) < 5:
            return "返回页面内容为空，可能被拦截或跳转"

        return None

    # ── HTTP 请求 ─────────────────────────────────────

    async def _get(self, client: httpx.AsyncClient, url: str, retries: int = 2) -> str:
        """GET 请求（带重试）。"""
        last_err = None
        for attempt in range(retries):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                return SearchService._decode_response(resp)
            except RuntimeError:
                # 反爬/限流检测异常，不重试，直接抛出
                raise
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in (403, 404, 410):
                    raise RuntimeError(f"搜索请求被拒绝 (HTTP {e.response.status_code})")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_err = e
                if attempt < retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_err = e
                if attempt < retries - 1:
                    await asyncio.sleep(1)

        raise RuntimeError(f"搜索请求失败，已重试 {retries} 次: {last_err}")

    async def _post(
        self,
        client: httpx.AsyncClient,
        url: str,
        data: str | dict | None = None,
        retries: int = 2,
    ) -> str:
        """POST 请求（带重试）。"""
        last_err = None
        for attempt in range(retries):
            try:
                resp = await client.post(url, data=data)
                resp.raise_for_status()
                return SearchService._decode_response(resp)
            except RuntimeError:
                # 反爬/限流检测异常，不重试，直接抛出
                raise
            except httpx.HTTPStatusError as e:
                last_err = e
                if e.response.status_code in (403, 404, 410):
                    raise RuntimeError(f"搜索请求被拒绝 (HTTP {e.response.status_code})")
                if attempt < retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
                last_err = e
                if attempt < retries - 1:
                    await asyncio.sleep(1)
            except Exception as e:
                last_err = e
                if attempt < retries - 1:
                    await asyncio.sleep(1)

        raise RuntimeError(f"搜索请求失败，已重试 {retries} 次: {last_err}")

    @staticmethod
    def _detect_encoding(raw_bytes: bytes) -> str | None:
        """从 HTML meta 标签中检测编码，支持多编码回退。"""
        candidates = ["utf-8", "gbk", "gb2312", "gb18030", "big5", "latin-1"]
        head = raw_bytes[:4096]

        for encoding in candidates:
            try:
                fragment = head.decode(encoding)
                m = re.search(
                    r'<meta[^>]+charset\s*=\s*["\']?\s*([\w-]+)',
                    fragment,
                    re.IGNORECASE,
                )
                if m:
                    detected = m.group(1)
                    if detected.lower() in ("gb2312", "gbk", "gb18030"):
                        return "gbk"
                    return detected
            except (UnicodeDecodeError, LookupError):
                continue

        return None

    # ── Cookies/Data 解析 ─────────────────────────────

    @staticmethod
    def _parse_cookies(cookies_str: str) -> dict[str, str]:
        """解析 cookies 字符串。"""
        result: dict[str, str] = {}
        for part in cookies_str.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            result[k] = v
        return result

    @staticmethod
    def _parse_form_data(data_str: str) -> dict[str, str]:
        """将 SoNovel 格式的 data 字符串转为 POST form 字典。

        输入格式: "{searchkey: %s}" 或 "{searchkey: xx, searchtype: all}"
        输出格式: {"searchkey": "xx", "searchtype": "all"}
        """
        result: dict[str, str] = {}
        # 去外层的 JSON 风格括号
        data_str = data_str.strip().strip("{}")
        # 按逗号分割
        for part in data_str.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            k, v = part.split(":", 1)
            result[k.strip()] = v.strip()
        return result


# 全局单例
search_service = SearchService()
