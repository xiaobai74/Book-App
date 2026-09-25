"""性能基线测量脚本（阶段0，优化前后各跑一次对比）

用法:
    python scripts/perf_baseline.py [--base http://localhost:8000] [--book-id UUID]

测量项与预算（阶段0定义）:
    - 书架列表 cold / 304 复用           预算: cold<800ms, 304<150ms
    - 章节目录(大书架) cold / 304        预算: cold<800ms, 304<150ms
    - 章节正文 cold / 304                预算: cold<300ms, 304<100ms
    - 排行榜源站列表 / 榜单二次进入       预算: 二次进入<300ms
    - 全网搜索 首次 / 缓存命中            预算: 首屏<1.5s(流式后), 缓存命中<300ms
    - 冷启动首个请求                      预算: <1s

输出: 终端表格 + scripts/perf_baseline_result.json
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

BASE = "http://localhost:8000"
API = "/api/v1"
PERF_EMAIL = "perf_baseline@test.local"
PERF_PASSWORD = "PerfBase123!"
SEARCH_QUERY = "剑"
BOARD_REPEATS = 3  # 榜单二次进入取多次中位数

results: dict = {}


def fmt(ms: float) -> str:
    return f"{ms:8.1f} ms"


def timeit(fn):
    """执行请求，返回 (elapsed_ms, response, bytes)"""
    t0 = time.perf_counter()
    r = fn()
    elapsed = (time.perf_counter() - t0) * 1000
    return elapsed, r, len(r.content)


def check(name: str, ms: float, budget: float, extra: str = ""):
    ok = "PASS" if ms < budget else "SLOW"
    print(f"  {name:<34} {fmt(ms)}  [< {budget:.0f}ms] {ok}  {extra}")
    results[name] = {"ms": round(ms, 1), "budget_ms": budget, "pass": ms < budget, "extra": extra}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--book-id", default=None)
    args = ap.parse_args()
    base = args.base.rstrip("/")
    client = httpx.Client(timeout=90.0)

    # ── 0. 冷启动首个请求：后端重启后立即运行本脚本时，/health 即进程首个被服务请求 ──
    ms, _, _ = timeit(lambda: client.get(f"{base}/health"))
    check("冷启动首个请求(/health)", ms, 1000, "仅重启后首次有意义")

    # ── 认证：注册(首次)或登录(复用)，保证测量不含注册开销 ──
    r = client.post(f"{base}{API}/auth/register",
                    json={"email": PERF_EMAIL, "password": PERF_PASSWORD, "name": "perf"})
    login = client.post(f"{base}{API}/auth/login",
                        json={"email": PERF_EMAIL, "password": PERF_PASSWORD})
    assert login.status_code == 200, f"登录失败: {login.status_code} {login.text[:200]}"
    token = login.json()["data"]["access_token"]
    H = {"Authorization": f"Bearer {token}"}
    print(f"认证 OK (register={'201' if r.status_code == 201 else '复用'})")

    # ── 1. 书架列表：cold + ETag 304 ──
    print("\n[书架 ShelfView]")
    ms, r, size = timeit(lambda: client.get(f"{base}{API}/books", headers=H))
    check("书架列表 cold", ms, 800, f"{size}B")
    etag = r.headers.get("etag")
    if etag:
        ms2, r2, _ = timeit(lambda: client.get(f"{base}{API}/books",
                                               headers={**H, "If-None-Match": etag}))
        check("书架列表 304 复用", ms2, 150, f"status={r2.status_code}")
    else:
        print("  !! 书架列表无 ETag 头")

    # ── 2. 阅读器路径：目录 + 正文（使用基线账号下经 /books/import 导入的 2000 章测试书）──
    shelf = client.get(f"{base}{API}/books", headers=H).json().get("data") or []
    book_id = args.book_id or next(
        (b["id"] for b in shelf if b["title"].startswith("PERF")), None)
    if not book_id:
        print("  !! 未找到基线导入书籍（PERF*），跳过阅读器测量。")
        print("     一次性准备: POST /api/v1/books/import 上传 scripts/perf_import.txt（见脚本 README 注释）")
        sys.exit(2)
    print(f"\n[阅读器 ReaderView] book={book_id}")
    ms, r, size = timeit(lambda: client.get(f"{base}{API}/books/{book_id}/chapters", headers=H))
    check("章节目录 cold", ms, 800, f"{size}B")
    toc_etag = r.headers.get("etag")
    if toc_etag:
        ms2, r2, _ = timeit(lambda: client.get(f"{base}{API}/books/{book_id}/chapters",
                                                headers={**H, "If-None-Match": toc_etag}))
        check("章节目录 304 复用", ms2, 150, f"status={r2.status_code}")
    ms, r, size = timeit(lambda: client.get(f"{base}{API}/books/{book_id}/chapters/1", headers=H))
    check("章节正文 cold", ms, 300, f"{size}B")
    ch_etag = r.headers.get("etag")
    if ch_etag:
        ms2, r2, _ = timeit(lambda: client.get(f"{base}{API}/books/{book_id}/chapters/1",
                                                headers={**H, "If-None-Match": ch_etag}))
        check("章节正文 304 复用", ms2, 100, f"status={r2.status_code}")

    # ── 3. 排行榜：源站列表 + 榜单二次进入 ──
    print("\n[排行榜 RankingView]")
    ms, r, size = timeit(lambda: client.get(f"{base}{API}/ranking/sources", headers=H))
    check("排行榜源站列表", ms, 300, f"{size}B")
    sources = r.json().get("data") or []
    if sources:
        s = sources[0]
        sid = s.get("id") or s.get("source_id")
        url = f"{base}{API}/ranking/{sid}/boards/0"
        ms_first, rf, _ = timeit(lambda: client.get(url, headers=H))  # 首次(冷/DB缓存)
        print(f"  {'榜单首次进入':<34} {fmt(ms_first)}  status={rf.status_code}")
        results["榜单首次进入"] = {"ms": round(ms_first, 1), "status": rf.status_code}
        times = [timeit(lambda: client.get(url, headers=H))[0] for _ in range(BOARD_REPEATS)]
        ms2, r2, board_size = timeit(lambda: client.get(url, headers=H))
        check(f"榜单二次进入(中位x{BOARD_REPEATS})", statistics.median(times), 300,
              f"{board_size}B status={r2.status_code} etag={'有' if r2.headers.get('etag') else '无'} "
              f"cache-control={r2.headers.get('cache-control', '无')}")

    # ── 4. 全网搜索：首次(冷) + 缓存命中 ──
    print("\n[搜索 SearchView]")
    ms1, r1, size1 = timeit(lambda: client.get(f"{base}{API}/search/external",
                                               params={"q": SEARCH_QUERY}, headers=H))
    n1 = len((r1.json().get("data") or {}).get("results", []) if isinstance(r1.json().get("data"), dict) else r1.json().get("data") or [])
    check("全网搜索 冷启动", ms1, 8000, f"{size1}B results={n1}")
    ms2, r2b, size2 = timeit(lambda: client.get(f"{base}{API}/search/external",
                                                 params={"q": SEARCH_QUERY}, headers=H))
    check("全网搜索 缓存命中", ms2, 300, f"{size2}B")
    # 不同关键词冷启动 x3（反映 gather 全等待的真实体感）
    colds = []
    for q in ["都市", "重生", "医妃"]:
        ms3, _, _ = timeit(lambda: client.get(f"{base}{API}/search/external",
                                               params={"q": q}, headers=H))
        colds.append(ms3)
    check("全网搜索 冷x3 中位", statistics.median(colds), 8000,
          f"max={max(colds):.0f}ms min={min(colds):.0f}ms")

    # ── 5. 冷启动首个请求（需重启后端后带 --cold-first 再跑才有意义，此处跳过）──

    out = Path(__file__).with_name("perf_baseline_result.json")
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    fails = [k for k, v in results.items() if not v.get("pass", True)]
    print(f"\n结果已写入 {out}")
    print(f"{'全部达标' if not fails else '未达标: ' + ', '.join(fails)}")
    client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
