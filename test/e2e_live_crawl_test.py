# -*- coding: utf-8 -*-
"""边爬边看（v1.4）端到端验证脚本

验证点：
1. SSE /crawl-stream 能收到 snapshot/plan/chapter_ready/done 事件
2. 抓取过程中章节已增量写库（/chapters 在 done 之前即有数据）
3. 抓取过程中可读取已就绪章节内容（边爬边看核心能力）
4. 抓取完成后状态与章节数正确
"""
import asyncio
import json
import sys
import time

import httpx

# Windows 控制台 GBK 无法输出 emoji/中文符号，统一切 UTF-8
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = "http://127.0.0.1:8000/api/v1"
SOURCE_URL = "http://www.xbiqugu.la/120/120345/"  # 真实源站目录页（香书小说，约152章）

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"{'✅' if cond else '❌'} {name}" + (f" — {detail}" if detail else ""))


async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        # ── 1. 注册/登录 ──
        email = f"livecrawl{int(time.time())}@test.com"
        r = await c.post(f"{BASE}/auth/register", json={
            "email": email, "password": "test123456", "nickname": "livecrawl"})
        if r.status_code not in (200, 201):
            print("注册失败:", r.status_code, r.text)
            sys.exit(1)
        r = await c.post(f"{BASE}/auth/login", json={
            "email": email, "password": "test123456"})
        token = r.json()["data"]["access_token"]
        H = {"Authorization": f"Bearer {token}"}
        print(f"登录成功: {email}")

        # ── 2. 添加书籍并触发抓取 ──
        r = await c.post(f"{BASE}/books", json={
            "title": "边爬边看测试", "author": "测试作者", "source_url": SOURCE_URL},
            headers=H)
        book_id = r.json()["data"]["id"]
        r = await c.post(f"{BASE}/books/{book_id}/crawl", headers=H)
        check("触发抓取", r.status_code == 200, f"status={r.json()['data']['status']}")

        # ── 3. 订阅 SSE 并观察增量写库 ──
        events = []
        saw_chapter_before_done = False
        read_during_crawl = None
        plan_received = asyncio.Event()
        done_received = asyncio.Event()

        async def consume_sse():
            async with httpx.AsyncClient(timeout=None) as sc:
                async with sc.stream(
                    "GET", f"{BASE}/books/{book_id}/crawl-stream", headers=H,
                ) as resp:
                    check("SSE 连接", resp.status_code == 200,
                          f"content-type={resp.headers.get('content-type')}")
                    buf = ""
                    async for chunk in resp.aiter_text():
                        buf += chunk
                        while "\n\n" in buf:
                            raw, buf = buf.split("\n\n", 1)
                            for line in raw.split("\n"):
                                line = line.strip()
                                if not line.startswith("data:"):
                                    continue
                                ev = json.loads(line[5:].strip())
                                events.append(ev)
                                if ev["type"] == "plan":
                                    plan_received.set()
                                elif ev["type"] == "chapter_ready":
                                    pass
                                elif ev["type"] in ("done", "failed"):
                                    done_received.set()
                                    return

        sse_task = asyncio.create_task(consume_sse())

        # 等待目录计划
        try:
            await asyncio.wait_for(plan_received.wait(), timeout=60)
            plan_ev = next(e for e in events if e["type"] == "plan")
            check("收到 plan 事件", True, f"total={plan_ev['total']}")
        except asyncio.TimeoutError:
            check("收到 plan 事件", False, "60s 超时")

        # 等待首批章节就绪（chapter_ready 事件）
        t0 = time.time()
        while time.time() - t0 < 90:
            if any(e["type"] == "chapter_ready" for e in events):
                break
            await asyncio.sleep(1)
        ready_ev = next((e for e in events if e["type"] == "chapter_ready"), None)
        check("收到 chapter_ready 事件", ready_ev is not None,
              f"index={ready_ev and ready_ev.get('index')}")

        # ── 4. 抓取中验证增量写库 + 边爬边看 ──
        r = await c.get(f"{BASE}/books/{book_id}/crawl-status", headers=H)
        st = r.json()["data"]
        check("抓取中进度实时", st["status"] == "crawling" and st["chapter_count"] > 0,
              f"{st['chapter_count']}/{st['total_chapters']}")

        r = await c.get(f"{BASE}/books/{book_id}/chapters", headers=H)
        chs = r.json()["data"]
        saw_chapter_before_done = len(chs) > 0 and not done_received.is_set()
        check("done 前章节已增量写库", saw_chapter_before_done, f"已写库 {len(chs)} 章")

        if chs:
            idx = chs[0]["index"]
            r = await c.get(f"{BASE}/books/{book_id}/chapters/{idx}", headers=H)
            ok = r.status_code == 200 and len(r.json()["data"]["content"]) > 0
            read_during_crawl = ok and not done_received.is_set()
            check("抓取中可读已就绪章节", read_during_crawl,
                  f"第{idx}章 {len(r.json()['data']['content']) if r.status_code == 200 else 0} 字")

        # ── 5. 等待 done ──
        try:
            await asyncio.wait_for(done_received.wait(), timeout=600)
        except asyncio.TimeoutError:
            check("收到 done 事件", False, "600s 超时")
        await asyncio.wait_for(sse_task, timeout=10)

        done_ev = next((e for e in events if e["type"] in ("done", "failed")), None)
        check("收到 done 事件", done_ev and done_ev["type"] == "done",
              f"total={done_ev and done_ev.get('total')}")

        r = await c.get(f"{BASE}/books/{book_id}", headers=H)
        book = r.json()["data"]
        check("完成后状态 done", book["status"] == "done",
              f"chapter_count={book['chapter_count']}")

        n_ready = sum(1 for e in events if e["type"] == "chapter_ready")
        check("chapter_ready 数 == 章节数", n_ready == book["chapter_count"],
              f"events={n_ready}, db={book['chapter_count']}")

        # 清理测试书籍
        await c.delete(f"{BASE}/books/{book_id}", headers=H)

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n═══ 边爬边看验证: {len(results) - len(failed)}/{len(results)} 通过 ═══")
    sys.exit(1 if failed else 0)


asyncio.run(main())
