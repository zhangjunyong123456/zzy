"""产品核心页面截图脚本（Playwright 无头 Chromium）。

用法：backend/frontend 服务已启动的前提下执行
    .venv/Scripts/python scripts/take_product_screens.py
输出：screenshots/*.png
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
os.makedirs(OUT, exist_ok=True)

INPUT_SEL = 'textarea[placeholder^="输入问题"]'
CLEAN_PREFIXES = ("我是大二", "我想参加")


def shot(page, name, full=False):
    page.screenshot(path=os.path.join(OUT, name), full_page=full)
    print("saved", name)


def shot_section(page, sel, name):
    """滚动到指定区块（触发渐显动画）后截视口。"""
    page.eval_on_selector(sel, "el => el.scrollIntoView({ block: 'start' })")
    page.wait_for_timeout(1400)
    shot(page, name)


def cleanup_sessions(page):
    """删除之前运行残留的测试会话。"""
    items = page.locator(".session-item")
    n = items.count()
    for i in range(n - 1, -1, -1):
        it = items.nth(i)
        title = it.locator(".title").inner_text()
        if any(title.startswith(p) for p in CLEAN_PREFIXES):
            it.hover()
            it.locator(".del").click()
            page.wait_for_timeout(800)


def wait_stream_done(page, timeout_s=300):
    """等流式结束：发送按钮回归（streaming 时是停止按钮）+ 内容长度连续两轮不变。"""
    page.wait_for_selector(".agent-card", timeout=60000)
    page.wait_for_selector('button:has-text("发送")', timeout=timeout_s * 1000, state="visible")
    last, stable = -1, 0
    while stable < 2:
        ln = page.evaluate("() => (document.querySelector('.chat-window')?.innerText || '').length")
        stable = stable + 1 if (ln == last and ln > 0) else 0
        last = ln
        page.wait_for_timeout(2000)
    page.evaluate(
        "() => { const w = document.querySelector('.chat-window'); if (w) w.scrollTop = w.scrollHeight }"
    )
    page.wait_for_timeout(600)


def ask(page, question):
    page.fill(INPUT_SEL, question)
    page.keyboard.press("Enter")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
        page = ctx.new_page()

        # ---- 落地页：首屏 + 五大场景 + 多智能体流程（分区滚动触发渐显动画）----
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(1500)
        shot(page, "01-landing-hero.png")
        shot_section(page, ".scenes", "02-landing-scenes.png")
        shot_section(page, ".flow", "03-landing-flow.png")

        # ---- 登录页 + 登录（测试账号，偶发时序问题自动重试）----
        page.goto(BASE + "/login", wait_until="networkidle")
        page.wait_for_timeout(800)
        shot(page, "04-login.png")
        pane = page.locator(".el-tab-pane").first
        pane.locator("input").nth(0).fill("statdemo")
        pane.locator("input").nth(1).fill("pass123456")
        for _ in range(3):
            pane.locator("button").first.click()
            try:
                page.wait_for_url("**/chat", timeout=15000)
                break
            except Exception:
                if "/chat" in page.url:
                    break
                page.wait_for_timeout(1000)
        page.wait_for_timeout(1500)

        # 清理上次残留会话 + 开新会话
        cleanup_sessions(page)
        page.locator(".new-btn").click()
        page.wait_for_timeout(800)

        # ---- 对话主界面初始状态 ----
        shot(page, "05-chat-home.png")

        # ---- 第一问：学习 Agent 实际输出 ----
        ask(page, "我是大二计算机专业学生，请帮我制定本学期的学习计划")
        wait_stream_done(page)
        shot(page, "06-ai-reply-study.png", full=True)

        # ---- 第二问：竞赛 Agent 实际输出 ----
        page.locator(".new-btn").click()
        page.wait_for_timeout(600)
        ask(page, "我想参加蓝桥杯比赛，帮我做一份备赛规划")
        wait_stream_done(page)
        shot(page, "07-ai-reply-contest.png", full=True)

        # ---- 知识库 ----
        page.goto(BASE + "/docs", wait_until="networkidle")
        page.wait_for_timeout(1200)
        shot(page, "08-docs.png")

        # ---- 个人中心：我的资料 / 数据统计 / 模型服务 ----
        page.goto(BASE + "/profile", wait_until="networkidle")
        page.wait_for_timeout(1500)
        shot(page, "09-profile-me.png")
        page.get_by_text("数据统计", exact=True).click()
        page.wait_for_timeout(1800)
        shot(page, "10-profile-stats.png", full=True)
        page.get_by_text("模型服务", exact=True).click()
        page.wait_for_timeout(1200)
        shot(page, "11-profile-model.png")

        browser.close()
        print("ALL DONE ->", OUT)


if __name__ == "__main__":
    sys.exit(main())
