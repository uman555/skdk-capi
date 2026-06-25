"""
SKDK Meta Token 自动续期服务
=====================================
功能：每 50 天自动用 long-lived token 续期
依赖：GitHub Actions cron 或 Railway cron
"""

import os
import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("token-refresher")


def refresh_long_lived_token(app_id: str, app_secret: str, current_token: str) -> dict:
    """
    用 long-lived token 续期
    返回新 token + 过期时间
    """
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": current_token,
    }
    response = requests.get(url, params=params, timeout=10)
    result = response.json()

    if "access_token" in result:
        new_token = result["access_token"]
        expires_in = result.get("expires_in", 0)
        expires_at = datetime.now() + timedelta(seconds=expires_in)
        logger.info(f"✅ 续期成功，新 token 有效期至 {expires_at}")
        return {
            "success": True,
            "token": new_token,
            "expires_at": expires_at.isoformat(),
            "expires_in_days": expires_in / 86400,
        }
    else:
        logger.error(f"❌ 续期失败: {result}")
        return {"success": False, "error": result}


def update_github_secret(token: str) -> bool:
    """
    更新 GitHub Secret（通过 GitHub API）
    依赖：GH_TOKEN 环境变量（GitHub PAT with repo 权限）
    """
    repo = os.getenv("GITHUB_REPO", "uman555/skdk-capi")
    secret_name = "META_ACCESS_TOKEN"
    gh_token = os.getenv("GH_TOKEN")

    if not gh_token:
        logger.warning("⚠️ GH_TOKEN 未设置，无法自动更新 GitHub Secret")
        return False

    # 使用 GitHub API 更新 secret
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github+json",
    }

    # 获取 public key
    pubkey_url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    pubkey_resp = requests.get(pubkey_url, headers=headers, timeout=10)
    if pubkey_resp.status_code != 200:
        logger.error(f"❌ 无法获取 public key: {pubkey_resp.status_code}")
        return False

    public_key = pubkey_resp.json()
    key_id = public_key["key_id"]
    key = public_key["key"]

    # 使用 PyNaCl 加密（如果没有 PyNaCl，使用 base64 作为占位）
    try:
        from nacl import encoding, public
        sealed_box = public.SealedBox(public.PublicKey(key.encode("utf-8")))
        encrypted = sealed_box.encrypt(token.encode("utf-8"))
        encrypted_b64 = encoding.Base64Encoder.encode(encrypted).decode("utf-8")
    except ImportError:
        logger.warning("⚠️ PyNaCl 未安装，使用未加密方式（GitHub 不接受）")
        return False

    # 更新 secret
    secret_url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    data = {
        "encrypted_value": encrypted_b64,
        "key_id": key_id,
    }
    secret_resp = requests.put(secret_url, headers=headers, json=data, timeout=10)
    if secret_resp.status_code in (201, 204):
        logger.info("✅ GitHub Secret 更新成功")
        return True
    else:
        logger.error(f"❌ GitHub Secret 更新失败: {secret_resp.status_code} {secret_resp.text}")
        return False


def update_railway_var(token: str) -> bool:
    """
    更新 Railway 环境变量（通过 Railway GraphQL API）
    """
    railway_token = os.getenv("RAILWAY_TOKEN")
    project_id = os.getenv("RAILWAY_PROJECT_ID")
    service_id = os.getenv("RAILWAY_SERVICE_ID")
    env_name = "META_ACCESS_TOKEN"

    if not all([railway_token, project_id, service_id]):
        logger.warning("⚠️ Railway 凭证未设置")
        return False

    # Railway GraphQL mutation
    url = "https://backboard.railway.app/graphql/v2"
    headers = {
        "Authorization": f"Bearer {railway_token}",
        "Content-Type": "application/json",
    }

    # 简化：调用 Railway API
    mutation = """
    mutation variableUpdate($projectId: String!, $environmentId: String!, $serviceId: String!, $name: String!, $value: String!) {
      variableUpdate(projectId: $projectId, environmentId: $environmentId, serviceId: $serviceId, name: $name, value: $value)
    }
    """

    # ... Railway API 调用（需要先获取 environmentId）
    logger.info("⚠️ Railway 集成需要 environmentId，需手动更新")
    return False


def main():
    """
    主函数：检查 token 状态，必要时续期
    建议通过 GitHub Actions 每周 cron 运行
    """
    app_id = os.getenv("META_APP_ID", "1554011292941689")
    app_secret = os.getenv("META_APP_SECRET")
    current_token = os.getenv("META_ACCESS_TOKEN")

    if not app_secret or not current_token:
        logger.error("❌ 缺少 META_APP_SECRET 或 META_ACCESS_TOKEN 环境变量")
        return

    # 1. 检查当前 token 状态
    me_resp = requests.get(
        "https://graph.facebook.com/v18.0/me",
        params={"access_token": current_token},
        timeout=10,
    )
    me_data = me_resp.json()

    if "error" in me_data:
        logger.info("当前 token 无效，需要续期")
    else:
        # Token 有效
        # 检查过期时间（如果有 debug 信息）
        debug_resp = requests.get(
            "https://graph.facebook.com/v18.0/debug_token",
            params={
                "input_token": current_token,
                "access_token": current_token,
            },
            timeout=10,
        )
        debug = debug_resp.json().get("data", {})
        if debug.get("expires_at"):
            from datetime import datetime
            expires = datetime.fromtimestamp(debug["expires_at"])
            days_left = (expires - datetime.now()).days
            logger.info(f"当前 token 有效期: {expires} ({days_left} 天)")

            if days_left > 7:
                logger.info("Token 还有 > 7 天，无需续期")
                return
            logger.info(f"Token 即将过期（{days_left} 天），开始续期")

    # 2. 续期
    result = refresh_long_lived_token(app_id, app_secret, current_token)

    if result["success"]:
        new_token = result["token"]
        # 3. 更新 GitHub Secret
        if update_github_secret(new_token):
            logger.info("✅ Token 已更新到 GitHub Secret")
        # 4. 更新 Railway
        if update_railway_var(new_token):
            logger.info("✅ Token 已更新到 Railway")
        # 5. 输出新 token（用于本地 .env）
        print(f"\n新 Token: {new_token}")
        print(f"过期时间: {result['expires_at']}")
    else:
        logger.error(f"❌ 续期失败: {result}")


if __name__ == "__main__":
    main()
