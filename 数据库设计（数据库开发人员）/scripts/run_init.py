#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MySQL 数据库初始化执行器

读取 scripts/init_db.sql 并连接到本地 MySQL 执行建库建表操作。

用法:
    python scripts/run_init.py

环境变量 (可选):
    DB_HOST     — MySQL 主机地址 (默认: localhost)
    DB_PORT     — MySQL 端口     (默认: 3306)
    DB_USER     — 数据库用户名   (默认: root)
    DB_PASSWORD — 数据库密码     (默认: 123456)
    DB_NAME     — 数据库名称     (默认: book)
"""

import os
import subprocess
import sys
from pathlib import Path

# Windows GBK 编码兼容：运行时强制 stdout/stderr 使用 utf-8
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ---- 数据库连接配置 ------------------------------------------
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"
DB_PASSWORD = "123456"
DB_NAME = "book"
# -------------------------------------------------------------

# 脚本所在目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQL_FILE = PROJECT_ROOT / "scripts" / "init_db.sql"


def check_mysql_client() -> bool:
    """检查 mysql 命令行客户端是否可用."""
    try:
        subprocess.run(
            ["mysql", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return True
    except FileNotFoundError:
        return False


def run_sql() -> int:
    """执行初始化 SQL 脚本."""
    if not SQL_FILE.exists():
        print(f"[ERROR] SQL file not found: {SQL_FILE}", file=sys.stderr)
        return 1

    print(f"Connecting to MySQL: {DB_USER}@{DB_HOST}:{DB_PORT}")
    print(f"Target database: {DB_NAME}")
    print(f"Executing script: {SQL_FILE}")
    print("-" * 50)

    cmd = [
        "mysql",
        f"--host={DB_HOST}",
        f"--port={DB_PORT}",
        f"--user={DB_USER}",
        f"--password={DB_PASSWORD}",
        "--default-character-set=utf8mb4",
    ]

    # 使用兼容 GBK 的 locale 绕过 Windows 子进程编码问题
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"

    try:
        result = subprocess.run(
            cmd,
            input=SQL_FILE.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )

        stdout_text = result.stdout or ""
        stderr_text = result.stderr or ""

        # MySQL 8.0 安全警告：在命令行输入密码会输出 warning
        # 仅当输出中包含 "ERROR" 才算真正失败
        real_errors = [line for line in stderr_text.split("\n") if "ERROR" in line.upper()]

        if real_errors:
            print("\n[ERROR] SQL execution failed:", file=sys.stderr)
            for error in real_errors:
                print(f"  {error}", file=sys.stderr)
            return 1

        # 仅为 MySQL 安全警告（不影响执行）
        for line in stderr_text.split("\n"):
            stripped = line.strip()
            if stripped:
                print(f"  [INFO] {stripped}")

        if stdout_text.strip():
            print(stdout_text)

        print()
        print("[OK] Database initialization completed!")
        print(f"     Database: {DB_NAME}")
        print()
        print("Verification command:")
        print(f'  mysql -u{DB_USER} -p -e "USE {DB_NAME}; SHOW TABLES;"')
        return 0

    except subprocess.TimeoutExpired:
        print("[ERROR] MySQL connection timeout", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return 1


def main() -> int:
    print("=" * 50)
    print("  小说管理App — MySQL 数据库初始化")
    print("=" * 50)
    print()

    if not check_mysql_client():
        print("[ERROR] mysql CLI not found", file=sys.stderr)
        print("Make sure MySQL is installed and in PATH", file=sys.stderr)
        print("Alternatively run manually:")
        print(f"  mysql -u{DB_USER} -p < {SQL_FILE}")
        return 1

    return run_sql()


if __name__ == "__main__":
    sys.exit(main())
