"""
规则模块

提供源站规则的加载、匹配和管理功能。
规则文件位于 rules/ 目录下，JSON 格式，兼容 SoNovel 的规则语法。
"""

from .rule_engine import RuleEngine, get_rule_engine

__all__ = ["RuleEngine", "get_rule_engine"]
