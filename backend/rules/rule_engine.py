"""
规则引擎

负责加载、匹配和管理源站抓取规则。
规则格式兼容 SoNovel 的 JSON 配置。
"""

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# 规则文件目录
_RULES_DIR = Path(__file__).resolve().parent

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
        for i, rule in enumerate(raw_rules):
            if not isinstance(rule, dict):
                continue
            if rule.get("disabled"):
                continue
            self._rules.append(rule)

            # 按域名索引
            domain = self._extract_domain(rule.get("url", ""))
            if domain:
                self._rules_by_domain[domain] = rule

            # 按 ID 索引
            self._rules_by_id[i] = rule

        self._loaded = True
        logger.info(f"已加载 {len(self._rules)} 条源站规则 (来自 {filename})")

    def _load_custom_rules(self) -> None:
        """从 custom_sources.json 加载用户自定义的源站规则。"""
        filepath = _RULES_DIR / _CUSTOM_RULES_FILE
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

    def _save_custom_rules(self) -> None:
        """将当前自定义规则持久化到 custom_sources.json。"""
        filepath = _RULES_DIR / _CUSTOM_RULES_FILE
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._custom_rules, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error(f"保存自定义规则失败: {e}")

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

    def reload(self, filename: str | None = None) -> None:
        """重新加载规则文件。"""
        self._rules.clear()
        self._rules_by_domain.clear()
        self._rules_by_id.clear()
        self._load_rules(filename or _DEFAULT_RULES_FILE)

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

    def get_source_by_name(self, name: str) -> dict[str, Any] | None:
        """按源站名称查找规则（内置 + 自定义）。"""
        for rule in self._rules:
            if rule.get("name") == name:
                return rule
        for rule in self._custom_rules:
            if rule.get("name") == name:
                return rule
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

    # ── 自定义源站管理 ──────────────────────────────

    def add_custom_source(self, rule: dict[str, Any]) -> int:
        """添加一条自定义源站规则并持久化。

        Args:
            rule: 规则字典，需包含 name, url 等字段

        Returns:
            新规则的 ID（在自定义规则列表中的索引 + 基础偏移量）
        """
        rule["custom"] = True  # 标记为自定义规则
        self._custom_rules.append(rule)

        # 更新索引
        new_id = len(self._rules) + len(self._custom_rules) - 1
        self._rules_by_id[new_id] = rule

        # 更新域名索引
        domain = self._extract_domain(rule.get("url", ""))
        if domain:
            self._rules_by_domain[domain] = rule

        self._save_custom_rules()
        logger.info(f"已添加自定义源站: {rule.get('name', '未知')} (domain={domain}, id={new_id})")
        return new_id

    def update_custom_source(self, index: int, rule: dict[str, Any]) -> bool:
        """更新一条自定义源站规则。

        Args:
            index: 自定义规则列表中的索引
            rule: 新的规则字典

        Returns:
            是否成功
        """
        if index < 0 or index >= len(self._custom_rules):
            return False

        # 移除旧域名索引
        old_domain = self._extract_domain(self._custom_rules[index].get("url", ""))
        if old_domain and old_domain in self._rules_by_domain:
            del self._rules_by_domain[old_domain]

        rule["custom"] = True
        self._custom_rules[index] = rule

        # 更新 _rules_by_id 索引
        global_id = len(self._rules) + index
        self._rules_by_id[global_id] = rule

        # 添加新域名索引
        domain = self._extract_domain(rule.get("url", ""))
        if domain:
            self._rules_by_domain[domain] = rule

        self._save_custom_rules()
        logger.info(f"已更新自定义源站: {rule.get('name', '未知')}")
        return True

    def remove_custom_source(self, index: int) -> bool:
        """移除一条自定义源站规则。

        Args:
            index: 自定义规则列表中的索引

        Returns:
            是否成功
        """
        if index < 0 or index >= len(self._custom_rules):
            return False

        rule = self._custom_rules.pop(index)

        # 清理 _rules_by_id 索引
        old_global_id = len(self._rules) + index
        if old_global_id in self._rules_by_id:
            del self._rules_by_id[old_global_id]
        # 移除后，后续自定义规则的 ID 都减 1，需要重建它们的索引
        for i in range(index, len(self._custom_rules)):
            new_global_id = len(self._rules) + i
            if new_global_id in self._rules_by_id:
                del self._rules_by_id[new_global_id]
            self._rules_by_id[new_global_id] = self._custom_rules[i]

        # 清理域名索引
        domain = self._extract_domain(rule.get("url", ""))
        if domain and domain in self._rules_by_domain:
            del self._rules_by_domain[domain]

        self._save_custom_rules()
        logger.info(f"已移除自定义源站: {rule.get('name', '未知')}")
        return True

    def get_custom_sources(self) -> list[dict[str, Any]]:
        """返回所有自定义源站的摘要信息。"""
        return [
            {
                "id": i + len(self._rules),
                "name": r.get("name", "未知"),
                "url": r.get("url", ""),
                "has_search": "search" in r and not r.get("search", {}).get("disabled", False),
                "comment": r.get("comment", ""),
                "is_custom": True,
                "rule": r,  # 包含完整规则，供前端编辑
            }
            for i, r in enumerate(self._custom_rules)
        ]

    @property
    def rules(self) -> list[dict[str, Any]]:
        return self._rules

    @property
    def custom_rules(self) -> list[dict[str, Any]]:
        return self._custom_rules

    @property
    def loaded(self) -> bool:
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
