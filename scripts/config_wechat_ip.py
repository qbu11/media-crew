"""
配置微信 IP 白名单的辅助脚本

使用方式:
1. 在 Chrome 中登录微信公众平台 https://mp.weixin.qq.com
2. 启动 Chrome 远程调试: chrome.exe --remote-debugging-port=9222
3. 运行此脚本: python scripts/config_wechat_ip.py

IP 白名单地址:
- IPv4: 111.197.251.153
- IPv6: 2408:8207:2461:6a00:dbb:4712:c1c0:27a0
"""

IP_WHITELIST = """111.197.251.153
2408:8207:2461:6a00:dbb:4712:c1c0:27a0"""

# 微信公众平台 IP 白名单配置页面
IP_WHITELIST_URL = "https://mp.weixin.qq.com/cgi-bin/settingpage?t=setting/index&action=setip&lang=zh_CN"

# 手动配置步骤
MANUAL_STEPS = """
=== 手动配置微信 IP 白名单 ===

1. 访问: https://mp.weixin.qq.com
2. 登录后，点击左侧菜单: 设置与开发 -> 基本配置
3. 向下滚动找到 "IP白名单" 部分
4. 点击 "修改" 或直接输入
5. 输入以下 IP 地址 (每行一个):

   111.197.251.153
   2408:8207:2461:6a00:dbb:4712:c1c0:27a0

6. 点击 "确认" 保存

配置完成后，你的系统就可以通过 API 方式调用微信接口了。
"""

if __name__ == "__main__":
    print(MANUAL_STEPS)
    print(f"\n你的 IP 地址:")
    print(f"  IPv4: 111.197.251.153")
    print(f"  IPv6: 2408:8207:2461:6a00:dbb:4712:c1c0:27a0")
