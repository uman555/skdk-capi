"""
SKDK Long-Lived Token 获取工具
=====================================
目的：获取 60 天有效的 long-lived user token
绕过 App Review 限制
"""

import requests
import sys

# ====================================
# SKDK 凭证
# ====================================
APP_ID = "1554011292941689"  # SKDK CAPI App ID
# 你需要先获取 App Secret（在 developers.facebook.com/apps/ -> SKDK CAPI App -> Settings -> Basic)

# ====================================
# 使用方法
# ====================================
"""
1. 打开 https://developers.facebook.com/tools/explorer/
2. 选择应用：SKDK CAPI App
3. 权限：ads_management + business_management
4. 生成 Short-Lived Access Token (约 1-2 小时)
5. 复制 Token，粘贴到下面
6. 运行此脚本获取 Long-Lived Token (60 天)
"""

SHORT_LIVED_TOKEN = input("请粘贴 Short-Lived Token: ").strip()
APP_SECRET = input("请输入 App Secret: ").strip()

# ====================================
# 交换为 Long-Lived Token
# ====================================
url = "https://graph.facebook.com/v18.0/oauth/access_token"
params = {
    "grant_type": "fb_exchange_token",
    "client_id": APP_ID,
    "client_secret": APP_SECRET,
    "fb_exchange_token": SHORT_LIVED_TOKEN,
}

print("\n正在交换 Long-Lived Token...")
response = requests.get(url, params=params, timeout=10)
result = response.json()

if "access_token" in result:
    long_lived_token = result["access_token"]
    expires_in = result.get("expires_in", 0)
    days = expires_in / 86400
    print(f"\n✅ 成功！Long-Lived Token 已生成")
    print(f"   有效期: {days:.0f} 天 ({expires_in} 秒)")
    print(f"\n📋 Token（复制到 .env 的 META_ACCESS_TOKEN）:")
    print(f"\n{long_lived_token}\n")

    # 同时验证 token
    print("验证 token 有效性...")
    me_resp = requests.get(
        "https://graph.facebook.com/v18.0/me",
        params={"access_token": long_lived_token},
        timeout=10,
    )
    me_data = me_resp.json()
    if "name" in me_data:
        print(f"✅ Token 有效！用户: {me_data.get('name')} (ID: {me_data.get('id')})")
    else:
        print(f"⚠️ 验证失败: {me_data}")
else:
    print(f"\n❌ 失败: {result}")
    print("\n可能原因：")
    print("1. App Secret 不正确")
    print("2. Short-lived token 已过期")
    print("3. App 处于 Development 模式（需要先 Live）")
    print("4. Token 权限不足")
