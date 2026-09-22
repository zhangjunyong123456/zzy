# -*- coding: utf-8 -*-
"""补充截图：落地页分段（滚动动画区块）+ 对话首页（无提示条）+ 知识库上传示例。"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:5173"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "screenshots"
PDF = ROOT / "backend" / "data" / "test_upload.pdf"


def launch(p):
    for channel in ("msedge", "chrome"):
        try:
            return p.chromium.launch(channel=channel, headless=True)
        except Exception as e:
            print(f"[launch] {channel} 不可用: {e}")
    raise RuntimeError("未找到可用的 Edge/Chrome 浏览器")


def main():
    with sync_playwright() as p:
        browser = launch(p)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900}, device_scale_factor=2
        )
        page = ctx.new_page()

        # 1. 落地页：首屏（视口）
        print("[1] 落地页首屏 ...")
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "01-landing.png"))

        # 2. 落地页：滚动到「路由/并行/汇总」功能区
        print("[2] 落地页功能区 ...")
        marks = ["路由", "并行", "汇总", "五大", "场景"]
        target_y = 0
        for m in marks:
            target_y = page.evaluate(
                """(word) => {
                    const els = Array.from(document.querySelectorAll('h2,h3,p,span,div'))
                        .filter(e => e.children.length === 0 && e.textContent.trim() === word);
                    for (const e of els) {
                        const r = e.getBoundingClientRect();
                        if (r.top > window.innerHeight * 0.5) return Math.max(0, r.top + window.scrollY - 200);
                    }
                    return 0;
                }""",
                m,
            )
            if target_y:
                break
        if target_y:
            page.evaluate(f"window.scrollTo({{top: {target_y}}})")
            page.wait_for_timeout(1800)
        else:
            page.evaluate("window.scrollBy(0, window.innerHeight)")
            page.wait_for_timeout(1800)
        page.screenshot(path=str(OUT / "01b-landing-features.png"))

        # 3. 登录 → 对话首页（等「登录成功」提示消失）
        print("[3] 对话首页（无提示条）...")
        page.goto(f"{BASE}/login", wait_until="networkidle")
        page.fill('input[placeholder="用户名"]', "statdemo")
        page.fill('input[placeholder="密码"]', "pass123456")
        page.click(".submit-btn")
        page.wait_for_url("**/chat**", timeout=15000)
        page.wait_for_timeout(4200)
        page.screenshot(path=str(OUT / "03-chat-scenes.png"))

        # 4. 知识库：上传示例 PDF，等待解析完成
        print("[4] 知识库上传示例 PDF ...")
        page.goto(f"{BASE}/docs", wait_until="networkidle")
        page.wait_for_timeout(1200)
        page.set_input_files('input[type="file"]', str(PDF))
        try:
            page.wait_for_selector("text=就绪", timeout=90000)
            print("      解析完成（就绪）")
        except Exception:
            print("      等待就绪超时，按当前状态截图")
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "06-docs.png"))

        browser.close()
    print(f"\n完成，截图已更新至：{OUT}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"耗时 {time.time() - t0:.0f}s")
