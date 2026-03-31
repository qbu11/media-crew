# -*- coding: utf-8 -*-
import sys
import os
import time

os.environ['PYTHONIOENCODING'] = 'utf-8'
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from playwright.sync_api import sync_playwright

IP_ADDRESS = '111.197.251.153'

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp('http://127.0.0.1:9222')
    context = browser.contexts[0]

    wechat_page = None
    for page in context.pages:
        if 'mp.weixin.qq.com' in page.url:
            wechat_page = page
            break

    if not wechat_page:
        print('WeChat page not found')
        sys.exit(1)

    time.sleep(1)

    # Find IP whitelist input using JavaScript
    result = wechat_page.evaluate('''
        () => {
            function findAndFillIP() {
                const inputs = document.querySelectorAll('input[type="text"], textarea');
                for (const input of inputs) {
                    const label = input.closest('label, .form-group, .weui-cell');
                    const labelText = label ? label.innerText : '';
                    if (labelText.includes('IP') || labelText.includes('ip') || labelText.includes('白名单')) {
                        input.value = "111.197.251.153";
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        return { type: 'main', label: labelText };
                    }
                }
                return null;
            }
            return findAndFillIP();
        }
    ''')

    print(f'Fill result: {result}')
    wechat_page.screenshot(path='C:/Users/puzzl/AppData/Local/Temp/wechat-after-fill.png')
    print('Done')
