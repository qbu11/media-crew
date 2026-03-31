"""CDP visual verification script for Crew Dashboard."""
import asyncio
import json
import os
import websockets

TAB_ID = "39794EF09813CCF0B7D911283C742C7D"
WS_URL = None
SCREENSHOT_DIR = os.path.expanduser("~/Desktop/crew_screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

msg_id = 0


async def send(ws, method, params=None):
    global msg_id
    msg_id += 1
    msg = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    # Wait for matching response
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        data = json.loads(raw)
        if data.get("id") == msg_id:
            return data
        # Skip events


async def screenshot(ws, name):
    """Take a screenshot and save it."""
    r = await send(ws, "Page.captureScreenshot", {"format": "png"})
    if "result" in r:
        import base64
        path = os.path.join(SCREENSHOT_DIR, f"{name}.png")
        with open(path, "wb") as f:
            f.write(base64.b64decode(r["result"]["data"]))
        print(f"  Screenshot saved: {path}")
        return path
    return None


async def evaluate(ws, expr):
    """Evaluate JS expression and return value."""
    r = await send(ws, "Runtime.evaluate", {
        "expression": expr,
        "returnByValue": True,
        "awaitPromise": True,
    })
    result = r.get("result", {}).get("result", {})
    return result.get("value")


async def navigate(ws, url):
    """Navigate to URL and wait for load."""
    await send(ws, "Page.navigate", {"url": url})
    await asyncio.sleep(2)


async def main():
    global WS_URL
    # Get WebSocket URL for tab
    import urllib.request
    tabs = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read())
    for t in tabs:
        if t.get("id") == TAB_ID:
            WS_URL = t["webSocketDebuggerUrl"]
            break

    if not WS_URL:
        print("Tab not found!")
        return

    print(f"Connecting to {WS_URL}")
    async with websockets.connect(WS_URL, max_size=50 * 1024 * 1024) as ws:
        await send(ws, "Page.enable")
        await send(ws, "Runtime.enable")

        pages = [
            ("dashboard", "http://127.0.0.1:5180/"),
            ("agents", "http://127.0.0.1:5180/agents"),
            ("crews", "http://127.0.0.1:5180/crews"),
            ("tasks", "http://127.0.0.1:5180/tasks"),
            ("analytics", "http://127.0.0.1:5180/analytics"),
        ]

        results = {}

        for name, url in pages:
            print(f"\n=== Testing page: {name} ({url}) ===")
            await navigate(ws, url)
            await screenshot(ws, f"final_{name}")

            # Check page title
            title = await evaluate(ws, "document.title")
            print(f"  Title: {title}")

            # Check for errors in console
            errors = await evaluate(ws, """
                (function() {
                    var errors = [];
                    var orig = console.error;
                    // Check if page has error boundary
                    var errEl = document.querySelector('[class*="error"]');
                    if (errEl) errors.push('Error element found: ' + errEl.textContent.substring(0, 100));
                    return errors.length > 0 ? errors.join('; ') : 'No errors';
                })()
            """)
            print(f"  Errors: {errors}")

            # Check main content area
            content = await evaluate(ws, """
                (function() {
                    var main = document.querySelector('main');
                    if (!main) return 'NO MAIN ELEMENT';
                    var text = main.innerText.substring(0, 300);
                    return text;
                })()
            """)
            print(f"  Content preview: {content[:200] if content else 'EMPTY'}")

            # Check sidebar links
            links = await evaluate(ws, """
                (function() {
                    var nav = document.querySelector('nav');
                    if (!nav) return 'NO NAV';
                    var anchors = nav.querySelectorAll('a');
                    return anchors.length + ' links: ' + Array.from(anchors).map(a => a.href).join(', ');
                })()
            """)
            print(f"  Nav links: {links}")

            # Check active nav item
            active = await evaluate(ws, """
                (function() {
                    var active = document.querySelector('nav a[class*="blue"]');
                    if (!active) return 'No active link found';
                    return 'Active: ' + active.textContent.trim();
                })()
            """)
            print(f"  Active nav: {active}")

            # Page-specific checks
            if name == "dashboard":
                stats = await evaluate(ws, """
                    (function() {
                        var cards = document.querySelectorAll('main h3, main [class*="stat"]');
                        return 'Found ' + cards.length + ' stat elements';
                    })()
                """)
                print(f"  Stats: {stats}")

            elif name == "agents":
                agents = await evaluate(ws, """
                    (function() {
                        var items = document.querySelectorAll('main [class*="rounded"]');
                        var headings = document.querySelectorAll('main h2, main h3');
                        var text = '';
                        headings.forEach(h => text += h.textContent + '; ');
                        return items.length + ' cards. Headings: ' + text;
                    })()
                """)
                print(f"  Agents: {agents}")

            elif name == "tasks":
                tasks = await evaluate(ws, """
                    (function() {
                        var rows = document.querySelectorAll('main tr, main [class*="cursor-pointer"]');
                        var buttons = document.querySelectorAll('main button');
                        return rows.length + ' rows, ' + buttons.length + ' buttons';
                    })()
                """)
                print(f"  Tasks: {tasks}")

            elif name == "crews":
                crews = await evaluate(ws, """
                    (function() {
                        var cards = document.querySelectorAll('main [class*="rounded-xl"], main [class*="rounded-lg"]');
                        return cards.length + ' crew cards';
                    })()
                """)
                print(f"  Crews: {crews}")

            elif name == "analytics":
                analytics = await evaluate(ws, """
                    (function() {
                        var tables = document.querySelectorAll('main table');
                        var cells = document.querySelectorAll('main td');
                        return tables.length + ' tables, ' + cells.length + ' cells';
                    })()
                """)
                print(f"  Analytics: {analytics}")

            results[name] = {
                "title": title,
                "errors": errors,
                "has_content": bool(content and len(content) > 10),
                "nav_links": links,
                "active_nav": active,
            }

        # Test API proxy from browser
        print("\n=== Testing API proxy from browser ===")
        await navigate(ws, "http://127.0.0.1:5180/")
        api_test = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/agents');
                    var data = await res.json();
                    return 'Agents API: ' + res.status + ', count=' + (data.data ? data.data.length : 'N/A');
                } catch(e) {
                    return 'API Error: ' + e.message;
                }
            })()
        """)
        print(f"  {api_test}")

        crews_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/crews');
                    var data = await res.json();
                    return 'Crews API: ' + res.status + ', count=' + (data.data ? data.data.length : 'N/A');
                } catch(e) {
                    return 'API Error: ' + e.message;
                }
            })()
        """)
        print(f"  {crews_api}")

        stats_api = await evaluate(ws, """
            (async function() {
                try {
                    var res = await fetch('/api/v1/system/stats');
                    var data = await res.json();
                    return 'Stats API: ' + res.status + ', data=' + JSON.stringify(data.data).substring(0, 100);
                } catch(e) {
                    return 'API Error: ' + e.message;
                }
            })()
        """)
        print(f"  {stats_api}")

        # Test sidebar navigation interaction
        print("\n=== Testing sidebar navigation clicks ===")
        await navigate(ws, "http://127.0.0.1:5180/")
        await asyncio.sleep(1)

        for target_text, expected_path in [
            ("Agent", "/agents"),
            ("Crew", "/crews"),
            ("任务", "/tasks"),
            ("数据", "/analytics"),
            ("概览", "/"),
        ]:
            click_result = await evaluate(ws, f"""
                (function() {{
                    var links = document.querySelectorAll('nav a');
                    for (var i = 0; i < links.length; i++) {{
                        if (links[i].textContent.includes('{target_text}')) {{
                            links[i].click();
                            return 'Clicked: ' + links[i].textContent.trim();
                        }}
                    }}
                    return 'Link not found for: {target_text}';
                }})()
            """)
            await asyncio.sleep(0.5)
            current_url = await evaluate(ws, "window.location.pathname")
            print(f"  {click_result} -> URL: {current_url} (expected: {expected_path})")

        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        all_ok = True
        for name, r in results.items():
            ok = r["has_content"] and "No errors" in str(r["errors"])
            status = "PASS" if ok else "FAIL"
            if not ok:
                all_ok = False
            print(f"  [{status}] {name}: content={'YES' if r['has_content'] else 'NO'}, errors={r['errors']}")

        print(f"\n  Overall: {'ALL PASSED' if all_ok else 'SOME FAILURES'}")
        print(f"  Screenshots saved to: {SCREENSHOT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
