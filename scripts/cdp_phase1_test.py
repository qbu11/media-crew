"""CDP verification for Phase 1 new pages."""
import asyncio
import json
import os
import base64
import urllib.request
import websockets

TAB_ID = "39794EF09813CCF0B7D911283C742C7D"
SCREENSHOT_DIR = os.path.expanduser("~/Desktop/crew_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
msg_id = 0


async def send(ws, method, params=None):
    global msg_id
    msg_id += 1
    msg = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data


async def screenshot(ws, name):
    r = await send(ws, "Page.captureScreenshot", {"format": "png"})
    if "result" in r:
        path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["result"]["data"]))
        print(f"  Screenshot: {name}.png")


async def evaluate(ws, expr):
    r = await send(ws, "Runtime.evaluate", {
        "expression": expr, "returnByValue": True, "awaitPromise": True,
    })
    return r.get("result", {}).get("result", {}).get("value")


async def navigate(ws, url):
    await send(ws, "Page.navigate", {"url": url})
    await asyncio.sleep(2.5)


async def main():
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    ws_url = None
    for t in tabs:
        if t.get("id") == TAB_ID:
            ws_url = t["webSocketDebuggerUrl"]
            break
    if not ws_url:
        print("Tab not found!")
        return

    async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
        await send(ws, "Page.enable")
        await send(ws, "Runtime.enable")

        pages = [
            ("p1_search", "http://127.0.0.1:5180/search"),
            ("p1_images", "http://127.0.0.1:5180/images"),
            ("p1_clients", "http://127.0.0.1:5180/clients"),
            ("p1_dashboard", "http://127.0.0.1:5180/"),
        ]

        for name, url in pages:
            print(f"\n=== {name} ({url}) ===")
            await navigate(ws, url)
            await screenshot(ws, name)

            content = await evaluate(ws, """
                (function() {
                    var main = document.querySelector('main');
                    if (!main) return 'NO MAIN';
                    return main.innerText.substring(0, 300);
                })()
            """)
            print(f"  Content: {(content or 'EMPTY')[:200]}")

            errors = await evaluate(ws, """
                (function() {
                    var err = document.querySelector('[class*="error"], [class*="Error"]');
                    return err ? 'ERROR: ' + err.textContent.substring(0, 100) : 'No errors';
                })()
            """)
            print(f"  Errors: {errors}")

            # Check sidebar has new sections
            nav = await evaluate(ws, """
                (function() {
                    var nav = document.querySelector('nav');
                    if (!nav) return 'NO NAV';
                    return nav.innerText;
                })()
            """)
            has_ops = 'false'
            if nav and ('热点搜索' in str(nav) or '\u70ed\u70b9' in str(nav)):
                has_ops = 'true'
            print(f"  Sidebar has ops section: {has_ops}")

        # Test API proxy for new endpoints
        print("\n=== API Proxy Tests ===")
        await navigate(ws, "http://127.0.0.1:5180/")

        clients_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/clients/');
                    var data = await res.json();
                    return 'Clients: ' + res.status + ', total=' + (data.data ? data.data.total : 'N/A');
                } catch(e) { return 'Error: ' + e.message; }
            })()
        """)
        print(f"  {clients_api}")

        search_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/search/status');
                    var data = await res.json();
                    var platforms = Object.keys(data.platforms || {});
                    return 'Search: ' + res.status + ', platforms=' + platforms.join(',');
                } catch(e) { return 'Error: ' + e.message; }
            })()
        """)
        print(f"  {search_api}")

        images_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/images/platforms');
                    var data = await res.json();
                    return 'Images: ' + res.status + ', success=' + data.success;
                } catch(e) { return 'Error: ' + e.message; }
            })()
        """)
        print(f"  {images_api}")

        content_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/content/platforms');
                    var data = await res.json();
                    return 'Content: ' + res.status + ', domestic=' + (data.domestic ? data.domestic.length : 'N/A');
                } catch(e) { return 'Error: ' + e.message; }
            })()
        """)
        print(f"  {content_api}")

        # Test sidebar navigation to new pages
        print("\n=== Sidebar Navigation ===")
        await navigate(ws, "http://127.0.0.1:5180/")
        for target, expected in [("热点搜索", "/search"), ("图片生成", "/images"), ("客户管理", "/clients")]:
            click = await evaluate(ws, f"""
                (function() {{
                    var links = document.querySelectorAll('nav a');
                    for (var i = 0; i < links.length; i++) {{
                        if (links[i].textContent.includes('{target}')) {{
                            links[i].click();
                            return 'Clicked: ' + links[i].textContent.trim();
                        }}
                    }}
                    return 'Not found: {target}';
                }})()
            """)
            await asyncio.sleep(0.5)
            url = await evaluate(ws, "window.location.pathname")
            status = "PASS" if url == expected else "FAIL"
            print(f"  [{status}] {click} -> {url} (expected: {expected})")

        print("\n=== DONE ===")


if __name__ == "__main__":
    asyncio.run(main())
