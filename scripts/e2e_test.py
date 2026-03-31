"""End-to-end interaction test: content creation flow via browser."""
import asyncio
import os
from playwright.async_api import async_playwright

outdir = os.path.expanduser("~/AppData/Local/Temp/metabot-outputs/oc_5193c9cdd3c64037d00eae0df8274b3e")
os.makedirs(outdir, exist_ok=True)

async def test_content_create():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 720})

        errors = []
        page.on("pageerror", lambda err: errors.append(str(err)))

        # 1. Navigate to content create page
        await page.goto("http://localhost:5177/content/create", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(outdir, "e2e-1-create-empty.png"))
        print("1. Content create page loaded")

        # 2. Fill in the form
        await page.fill('input[placeholder*="输入创作主题"]', "2026年AI创业趋势分析")
        await page.click('button:has-text("微博")')  # select weibo platform
        await page.fill('input[placeholder*="职场"]', "科技")
        await page.screenshot(path=os.path.join(outdir, "e2e-2-form-filled.png"))
        print("2. Form filled")

        # 3. Click start button
        await page.click('button:has-text("开始创作")')
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(outdir, "e2e-3-progress.png"))
        print("3. Creation started, progress visible")

        # 4. Wait for completion (poll every 2s, max 30s)
        for i in range(15):
            await page.wait_for_timeout(2000)
            # Check if result appeared
            has_result = await page.evaluate(
                "Boolean(document.querySelector('pre') || document.querySelector('[class*=prose]'))"
            )
            if has_result:
                print(f"4. Result appeared after {(i+1)*2}s")
                break

        await page.screenshot(path=os.path.join(outdir, "e2e-4-result.png"))
        print("5. Final screenshot taken")

        # 5. Navigate to content center to verify
        await page.goto("http://localhost:5177/content", wait_until="networkidle")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(outdir, "e2e-5-content-center.png"))
        print("6. Content center with execution history")

        if errors:
            print(f"Page errors: {len(errors)}")
            for e in errors[:3]:
                print(f"  {e[:150]}")
        else:
            print("No page errors!")

        await browser.close()

asyncio.run(test_content_create())
