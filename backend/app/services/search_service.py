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
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, urljoin as _urljoin

import httpx
from bs4 import BeautifulSoup

from rules.rule_engine import RuleEngine, get_rule_engine

logger = logging.getLogger(__name__)

_CURRENT_UA_VERSION = "131"
_USER_AGENTS = [
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CURRENT_UA_VERSION}.0.0.0 Safari/537.36",
    f"Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:135.0) Gecko/20100101 Firefox/135.0",
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
            timeout=httpx.Timeout(30.0, connect=15.0),
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
    ) -> list[SearchResult]:
        """对外部源站发起搜索请求，合并去重结果。

        Args:
            keyword: 搜索关键词
            source_id: 指定源站 ID，None 则搜索所有源站
            search_limit: 每个源站最大结果数

        Returns:
            去重后的搜索结果列表
        """
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
        return all_results

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
                            from urllib.parse import urlencode
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

            # 需要 HTML 来查找下一页链接
            from bs4 import BeautifulSoup
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
                from urllib.parse import urljoin
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
                import re
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
