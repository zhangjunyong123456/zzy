# -*- coding: utf-8 -*-
"""iCAN 参赛截图：自动走查产品核心页面，输出高清截图到 screenshots/。

用法（项目根目录）：
    .\\.venv\\Scripts\\python.exe scripts\\take_screenshots.py

前置：后端 127.0.0.1:8000 与前端 http://localhost:5173 已启动。
"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
OUT = Path(__file__).resolve().parent.parent / "screenshots"
OUT.mkdir(exist_ok=True)

VIEWPORT = {"width": 1440, "height": 900}
QUESTION = "我要参加 iCAN 比赛，帮我全面规划"


def launch(p):
    """优先系统 Edge，其次 Chrome，避免下载 chromium。"""
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel, headless=True)
        except Exception as e:
            print(f"[launch] {channel} 不可用: {e}")
    raise RuntimeError("未找到可用的 Edge/Chrome 浏览器")


def wait_stream_settled(page, selector=".chat-window", max_wait=300, interval=2.0, rounds=4):
    """等待 SSE 流式输出结束：消息区文本长度连续 rounds 轮不再增长。"""
    last, stable, deadline = -1, 0, time.time() + max_wait
    while time.time() < deadline:
        length = page.evaluate(
            "(s => document.querySelector(s)?.innerText.length ?? 0)", selector
        )
        if length == last and length > 0:
            stable += 1
            if stable >= rounds:
                return True
        else:
            stable = 0
        last = length
        page.wait_for_timeout(int(interval * 1000))
    return False


def main():
    with sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(viewport=VIEWPORT, device_scale_factor=2)
        page = ctx.new_page()

        # 1. 落地页（整页）
        print("[1/6] 落地页 ...")
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "01-landing.png"), full_page=True)

        # 2. 登录页
        print("[2/6] 登录页 ...")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "02-login.png"))

        # 3. 登录 → 对话首页（五大场景卡片）
        print("[3/6] 登录并进入对话首页 ...")
        page.fill('input[placeholder="用户名"]', "statdemo")
        page.fill('input[placeholder="密码"]', "pass123456")
        page.click(".submit-btn")
        page.wait_for_url("**/chat**", timeout=15000)
        page.wait_for_timeout(2200)
        page.screenshot(path=str(OUT / "03-chat-scenes.png"))

        # 4. 发送多 Agent 问题，等待流式输出完成后整页截图
        print(f"[4/6] 发送问题：{QUESTION}（等待 AI 输出，可能需要 1-3 分钟）...")
        page.fill("textarea", QUESTION)
        page.keyboard.press("Enter")
        try:
            page.wait_for_selector(".agent-card", timeout=30000)
            print("      Agent 卡片已出现，等待流式输出 ...")
        except Exception:
            print("      未检测到 agent-card，继续等待文本稳定 ...")
        page.wait_for_selector(".summary-card", timeout=240000)
        settled = wait_stream_settled(page)
        print(f"      流式输出{'已稳定' if settled else '超时（按当前状态截图）'}")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "04-ai-multi-agent.png"), full_page=True)

        # 5. 个人中心 · 模型配置中心
        print("[5/6] 个人中心模型配置 ...")
        page.goto(f"{BASE}/profile?tab=models", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "05-model-config.png"))

        # 6. 知识库（PDF 上传 / 管理）
        print("[6/6] 知识库页 ...")
        page.goto(f"{BASE}/docs", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(OUT / "06-docs.png"))

        browser.close()
    print(f"\n完成，截图已保存至：{OUT}")


if __name__ == "__main__":
    main()
