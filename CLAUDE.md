# CLAUDE.md

本文件为 Claude Code（claude.ai/code）在此仓库中工作时提供指导。

## 项目概览

一个极简的 Python 项目（"vibe-coding-book-master"），无任何依赖。入口文件为 `main.py`。

## 常用命令

```bash
# 运行主脚本
python main.py

# 虚拟环境（如使用）
source .venv/Scripts/activate  # Windows Git Bash
```

## 架构

- **`main.py`** — 单文件应用入口。包含一个 `print_hi(name)` 函数，以及 `__name__ == '__main__'` 保护块，调用时传入 `'PyCharm'`。
- **`pyproject.toml`** — 仅包含项目元数据（Python ≥ 3.12，无依赖）。未配置构建系统、代码检查工具或测试运行器。
- **`.venv/`** — 本地虚拟环境。

无测试、无包结构、无额外模块。

## 自定义约束

- 删除文件时需给我提示，得到我的允许后才能删除
- 每次 review 以后，请告知我任务完成了。也就是要给我一个 ACK。ACK 的内容为：您好！当前任务已完成！