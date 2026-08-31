"""
规则引擎

负责加载、匹配和管理源站抓取规则。
规则格式兼容 SoNovel 的 JSON 配置。
"""

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 内置规则文件目录（PyInstaller frozen 时从打包的 _MEIPASS 读取）
if getattr(sys, "frozen", False):
    _RULES_DIR = Path(sys._MEIPASS) / "rules"
else:
    _RULES_DIR = Path(__file__).resolve().parent

# 自定义规则持久化目录（桌面版写入用户数据目录，保证重启不丢失）
if getattr(sys, "frozen", False):
    from platformdirs import user_data_dir as _user_data_dir

    _WRITABLE_RULES_DIR = Path(_user_data_dir("NovelManager", appauthor=False))
    _WRITABLE_RULES_DIR.mkdir(parents=True, exist_ok=True)
else:
    _WRITABLE_RULES_DIR = _RULES_DIR

# 默认激活的规则文件
_DEFAULT_RULES_FILE = "main.json"

# 自定义源站持久化文件
_CUSTOM_RULES_FILE = "custom_sources.json"


class RuleEngine:
    """源站规则引擎

    根据 URL 或源站 ID 匹配对应的抓取/搜索规则。
    支持 CSS Selector 和 XPath 两种选择器语法。

    匹配策略（优先级从高到低）：
    1. 精确域名匹配
    2. book.url 正则匹配
    3. 域名模糊匹配
    4. 通用回退规则（自动生成，适用于任意小说网站）
    """

    def __init__(self, rules_file: str | None = None):
        self._rules: list[dict[str, Any]] = []
        self._rules_by_domain: dict[str, dict[str, Any]] = {}
        self._rules_by_id: dict[int, dict[str, Any]] = {}
        self._custom_rules: list[dict[str, Any]] = []  # 运行时添加的自定义规则
        self._loaded = False

        rules_file = rules_file or _DEFAULT_RULES_FILE
        self._load_rules(rules_file)
        self._load_custom_rules()

    # ── 加载 ──────────────────────────────────────────

    def _load_rules(self, filename: str) -> None:
        """从 JSON 文件加载规则列表。"""
        filepath = _RULES_DIR / filename
        if not filepath.exists():
            logger.warning(f"规则文件不存在: {filepath}")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_rules = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"规则文件 JSON 解析失败: {e}")
            return

        if not isinstance(raw_rules, list):
            logger.error("规则文件格式错误: 顶层应为数组")
            return

        self._rules = []
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("disabled"):
                continue
            self._rules.append(rule)

            # 按域名索引
            domain = self._extract_domain(rule.get("url", ""))
            if domain:
                self._rules_by_domain[domain] = rule

            # 按 ID 索引（用压缩后的索引，与 list_sources / list_ranking_sources
            # / list_searchable_sources 的 enumerate(_rules) 保持一致，
            # 避免禁用规则造成的索引错位）
            self._rules_by_id[len(self._rules) - 1] = rule

        self._loaded = True
        logger.info(f"已加载 {len(self._rules)} 条源站规则 (来自 {filename})")

    def _load_custom_rules(self) -> None:
        """从 custom_sources.json 加载用户自定义的源站规则。"""
        filepath = _WRITABLE_RULES_DIR / _CUSTOM_RULES_FILE
        if not filepath.exists():
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_rules = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"自定义规则文件加载失败: {e}")
            return

        if not isinstance(raw_rules, list):
            return

        count = 0
        for rule in raw_rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("disabled"):
                continue
            self._custom_rules.append(rule)

            domain = self._extract_domain(rule.get("url", ""))
            if domain:
                self._rules_by_domain[domain] = rule

            # 建立 ID 索引
            global_id = len(self._rules) + len(self._custom_rules) - 1
            self._rules_by_id[global_id] = rule
            count += 1

        if count > 0:
            logger.info(f"已加载 {count} 条自定义源站规则 (来自 {_CUSTOM_RULES_FILE})")

    # ── 通用回退规则 ──────────────────────────────────

    @staticmethod
    def _build_generic_rule(url: str) -> dict[str, Any]:
        """构建一条适用于任意小说网站的通用回退规则。

        该规则不指定具体的 CSS 选择器，依赖 CrawlerService 内置的
        通用章节列表解析和正文提取逻辑。

        返回的规则字典包含：
        - name: "通用规则（自动匹配）"
        - url: 从输入 URL 提取的域名
        - toc: {} (空 — 触发 _parse_chapter_list_generic)
        - chapter: {} (空 — 触发 _extract_text_generic)
        - comment: 说明这是自动生成的通用规则
        """
        domain = RuleEngine._extract_domain(url)
        return {
            "name": f"通用规则（{domain}）",
            "url": url,
            "comment": "自动生成的通用规则 — 使用内置通用解析逻辑，可能在部分网站效果不佳",
            "generic": True,  # 标记为通用规则
            "book": {},
            "toc": {},         # 空 → 触发通用章节解析
            "chapter": {},     # 空 → 触发通用正文提取
        }

    # ── 匹配 ──────────────────────────────────────────

    def match_rule(self, url: str, custom_rules: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
        """根据 URL 匹配最合适的源站规则。

        匹配策略:
        1. 精确域名匹配（含自定义规则）
        2. 若规则包含 book.url 正则，用正则匹配详情页 URL
        3. 回退到域名模糊匹配
        4. 返回 None（调用方应使用通用回退规则）

        Args:
            url: 要匹配的 URL
            custom_rules: 可选的额外规则列表（如当前用户的自定义规则）
        """
        if not url:
            return None

        domain = self._extract_domain(url)

        # 合并内置规则和传入的自定义规则
        all_rules = list(self._rules)
        if custom_rules:
            all_rules.extend(custom_rules)

        # 1. 精确域名匹配
        # 先查内置索引
        if domain in self._rules_by_domain:
            return self._rules_by_domain[domain]

        # 再查自定义规则
        for rule in (custom_rules or []):
            if self._extract_domain(rule.get("url", "")) == domain:
                return rule

        # 2. book.url 正则匹配
        for rule in all_rules:
            book_url_pattern = (rule.get("book") or {}).get("url")
            if book_url_pattern:
                try:
                    if re.search(book_url_pattern, url):
                        return rule
                except re.error:
                    pass

        # 3. 域名模糊匹配
        for rule_domain, rule in self._rules_by_domain.items():
            if domain and (rule_domain in domain or domain in rule_domain):
                return rule
        for rule in (custom_rules or []):
            rule_domain = self._extract_domain(rule.get("url", ""))
            if domain and (rule_domain in domain or domain in rule_domain):
                return rule

        return None

    def get_rule_by_id(self, source_id: int) -> dict[str, Any] | None:
        """按源站 ID 获取规则。

        支持内置规则（ID = 在 main.json 中的索引）和自定义规则
        （ID = len(_rules) + 在 _custom_rules 中的索引）。
        """
        rule = self._rules_by_id.get(source_id)
        if rule is not None:
            return rule
        # 自定义规则：ID 从 len(_rules) 开始偏移
        custom_index = source_id - len(self._rules)
        if 0 <= custom_index < len(self._custom_rules):
            return self._custom_rules[custom_index]
        return None

    # ── 查询 ──────────────────────────────────────────

    def list_sources(self) -> list[dict[str, Any]]:
        """返回所有可用源站的摘要信息（内置 + 自定义，不含详细规则）。"""
        sources: list[dict[str, Any]] = []
        for i, r in enumerate(self._rules):
            sources.append({
                "id": i,
                "name": r.get("name", "未知"),
                "url": r.get("url", ""),
                "has_search": "search" in r and not r.get("search", {}).get("disabled", False),
                "comment": r.get("comment", ""),
                "is_custom": False,
            })
        for i, r in enumerate(self._custom_rules):
            sources.append({
                "id": i + len(self._rules),
                "name": r.get("name", "未知"),
                "url": r.get("url", ""),
                "has_search": "search" in r and not r.get("search", {}).get("disabled", False),
                "comment": r.get("comment", ""),
                "is_custom": True,
            })
        return sources

    def list_searchable_sources(self) -> list[tuple[int, dict[str, Any]]]:
        """返回所有支持搜索的源站列表（内置 + 自定义）。"""
        result: list[tuple[int, dict[str, Any]]] = []
        for i, r in enumerate(self._rules):
            if "search" in r and not (r.get("search") or {}).get("disabled", False):
                result.append((i, r))
        for i, r in enumerate(self._custom_rules):
            if "search" in r and not (r.get("search") or {}).get("disabled", False):
                result.append((i + len(self._rules), r))
        return result

    def list_ranking_sources(self) -> list[dict[str, Any]]:
        """返回所有支持排行榜的源站（规则中含非空 ranking.boards）。"""
        sources: list[dict[str, Any]] = []
        for i, r in enumerate(self._rules):
            boards = (r.get("ranking") or {}).get("boards") or []
            if boards:
                sources.append({
                    "id": i,
                    "name": r.get("name", "未知"),
                    "url": r.get("url", ""),
                    "board_names": [b.get("name", "榜单") for b in boards],
                    "is_custom": False,
                })
        for i, r in enumerate(self._custom_rules):
            boards = (r.get("ranking") or {}).get("boards") or []
            if boards:
                sources.append({
                    "id": i + len(self._rules),
                    "name": r.get("name", "未知"),
                    "url": r.get("url", ""),
                    "board_names": [b.get("name", "榜单") for b in boards],
                    "is_custom": True,
                })
        return sources

    @property
    def rules(self) -> list[dict[str, Any]]:
        """内置规则列表（供测试与诊断脚本读取）"""
        return self._rules

    @property
    def custom_rules(self) -> list[dict[str, Any]]:
        """自定义规则列表"""
        return self._custom_rules

    @property
    def loaded(self) -> bool:
        """规则文件是否已加载"""
        return self._loaded

    # ── 工具 ──────────────────────────────────────────

    @staticmethod
    def _extract_domain(url: str) -> str:
        """从 URL 中提取域名（含 www）。"""
        if not url:
            return ""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower() or parsed.path.split("/")[0].lower()
        except Exception:
            return ""


# 全局单例
_rule_engine: RuleEngine | None = None


def get_rule_engine(rules_file: str | None = None) -> RuleEngine:
    """获取全局规则引擎单例。"""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine(rules_file)
    return _rule_engine
