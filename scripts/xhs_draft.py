import time, random, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.sync_api import sync_playwright

WS_URL = "ws://localhost:9222/devtools/browser/cf9fcac6-89c9-439d-b404-842f0df6f3cf"

def rd(lo=0.3, hi=0.8):
    time.sleep(random.uniform(lo, hi))

xhs_title = "AI编程工具大爆发！这3个GitHub项目一夜涨粉数千"
xhs_body = ("最近 GitHub Trending 被 AI Agent 工具霸榜了，分享 3 个值得关注的项目\n\n"
    "1. superpowers - 给 AI 编程助手装技能包的框架，自然语言定义技能\n"
    "2. oh-my-claudecode - Claude Code 多 Agent 编排，一人指挥多个 AI 同时干活\n"
    "3. dexter - 自主金融研究 Agent，自动搜索分析写报告\n\n"
    "趋势：AI 编程正在从一个助手变成一支团队。Multi-Agent 不再是论文概念，而是真正可用的开发工具。\n\n"
    "如果你在用 Claude Code 或 Cursor，强烈建议试试 superpowers。")

# Find a cover image
cover_dir = "C:/11Projects/Crew/generated_images"
cover_img = None
for root, dirs, files in os.walk(cover_dir):
    for f in files:
        if f.endswith('.png'):
            cover_img = os.path.join(root, f).replace("\\", "/")
            break
    if cover_img:
        break

print(f"Cover: {cover_img}")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(WS_URL)

    # Find existing XHS page
    xhs_page = None
    for ctx in browser.contexts:
        for pg in ctx.pages:
            if "creator.xiaohongshu.com" in pg.url:
                xhs_page = pg
                break
        if xhs_page:
            break

    if not xhs_page:
        xhs_page = browser.contexts[0].new_page()
        xhs_page.goto("https://creator.xiaohongshu.com/publish/publish",
                       wait_until="domcontentloaded", timeout=20000)
        time.sleep(4)

    xhs_page.bring_to_front()
    time.sleep(2)
    print(f"XHS page: {xhs_page.url}")

    # Upload image
    if cover_img:
        try:
            file_input = xhs_page.locator('input[type="file"]').first
            file_input.set_input_files(cover_img)
            print("Image uploaded via file input")
            time.sleep(6)
        except Exception as e:
            print(f"Upload error: {e}")
            try:
                with xhs_page.expect_file_chooser(timeout=5000) as fc_info:
                    xhs_page.locator('[class*="upload"]').first.click()
                fc = fc_info.value
                fc.set_files(cover_img)
                print("Image uploaded via file chooser")
                time.sleep(6)
            except Exception as e2:
                print(f"File chooser error: {e2}")

    xhs_page.screenshot(path="screenshots/xhs_after_upload.png")

    # Fill title
    for sel in ['[placeholder*="title"]', '#title', 'input[type="text"]']:
        try:
            el = xhs_page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                rd(0.3, 0.5)
                el.fill(xhs_title)
                print(f"Title filled via {sel}")
                break
        except:
            continue

    # Fill body
    for sel in ['[contenteditable="true"]', '.ql-editor', '[data-placeholder]']:
        try:
            el = xhs_page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click()
                rd(0.3, 0.5)
                xhs_page.keyboard.type(xhs_body, delay=8)
                print(f"Body filled via {sel}")
                break
        except:
            continue

    rd(1, 2)
    xhs_page.screenshot(path="screenshots/xhs_filled_final.png")

    # Save draft
    for sel in ['button:has-text("Save draft")', 'text=Save draft', 'button:has-text("save")']:
        try:
            el = xhs_page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                rd(2, 3)
                print(f"Draft saved via {sel}")
                break
        except:
            continue

    xhs_page.screenshot(path="screenshots/xhs_done_final.png")
    print("=== XHS DONE ===")
    browser.close()
