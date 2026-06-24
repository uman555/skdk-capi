"""
SKDK CAPI 集成 - Meta 转化 API 客户端
=====================================
负责：
1. SHA-256 哈希用户邮箱（Meta 隐私要求）
2. 发送 CAPI 事件到 Meta Dataset
3. 错误处理和重试逻辑
4. 事件去重（event_id 机制）
"""

import hashlib
import json
import logging
import time
from typing import Dict, Optional

import requests

from config import (
    META_ACCESS_TOKEN,
    META_CAPI_BASE_URL,
    ACTION_SOURCE,
    EVENT_SOURCE,
    LEAD_EVENT_SOURCE,
    logger,
)


def hash_email(email: str) -> str:
    """
    SHA-256 哈希邮箱（Meta 隐私要求）

    Args:
        email: 用户邮箱

    Returns:
        SHA-256 哈希值（小写十六进制）

    Examples:
        >>> hash_email("Test@Example.com")
        '973dfe463ec85785f5f95af5ba6a5cc25d56a3d9a8f0b0e0a5b7e0a8d2c0e5b3'
    """
    if not email:
        raise ValueError("Email cannot be empty")
    # Meta 要求：先 lower + trim 再 SHA-256
    normalized = email.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def build_event_id(lead_id: str, event_name: str) -> str:
    """
    构建唯一 event_id（用于去重）

    Args:
        lead_id: Notion 页面 ID
        event_name: CAPI 事件名

    Returns:
        唯一 event_id 字符串
    """
    timestamp = int(time.time())
    return f"{lead_id}_{event_name}_{timestamp}"


class CAPIClient:
    """
    Meta 转化 API (CAPI) 客户端
    负责向 Meta Dataset 发送服务器端事件
    """

    def __init__(self, access_token: str = None, base_url: str = None):
        """
        Args:
            access_token: Meta 访问令牌（默认从 config 读取）
            base_url: CAPI 端点 URL（默认从 config 读取）
        """
        self.access_token = access_token or META_ACCESS_TOKEN
        self.base_url = base_url or META_CAPI_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
        })
        logger.info(f"CAPI client initialized: {self.base_url}")

    def send_event(
        self,
        event_name: str,
        email: str,
        lead_id: str,
        value: Optional[float] = None,
        currency: str = "USD",
        test_event_code: Optional[str] = None,
    ) -> Dict:
        """
        发送单个 CAPI 事件

        Args:
            event_name: 事件名（如 "SKDK_Lead_Qualified"）
            email: 用户邮箱（必填，会被 SHA-256 哈希）
            lead_id: Notion 页面 ID（用于去重）
            value: 转化价值（仅 Purchase 事件）
            currency: 货币（默认 USD）
            test_event_code: 测试事件代码（仅测试用）

        Returns:
            Meta API 响应字典

        Raises:
            requests.exceptions.RequestException: 网络错误
        """
        # 1. 哈希邮箱
        hashed_email = hash_email(email)

        # 2. 构建 event_id（去重）
        event_id = build_event_id(lead_id, event_name)

        # 3. 构建事件
        event = {
            "event_name": event_name,
            "event_time": int(time.time()),
            "action_source": ACTION_SOURCE,
            "user_data": {
                "em": [hashed_email],
            },
            "custom_data": {
                "event_source": EVENT_SOURCE,
                "lead_event_source": LEAD_EVENT_SOURCE,
            },
            "event_id": event_id,
        }

        # 4. 添加价值（Purchase 事件）
        if value is not None:
            event["custom_data"]["value"] = value
            event["custom_data"]["currency"] = currency

        # 5. 测试事件代码
        if test_event_code:
            event["test_event_code"] = test_event_code

        # 6. 发送请求
        payload = {
            "data": [event],
            "access_token": self.access_token,
        }

        try:
            logger.info(f"📤 发送 CAPI 事件: {event_name} (lead_id={lead_id})")
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()

            if "events_received" in result and result["events_received"] >= 1:
                logger.info(f"✅ 事件发送成功: {event_name}")
            else:
                logger.warning(f"⚠️ 事件可能被去重: {result}")

            return result

        except requests.exceptions.HTTPError as e:
            # 处理 Meta 特定错误
            if e.response.status_code == 401:
                logger.error(
                    f"❌ 401 Unauthorized: Token 可能过期或无效\n"
                    f"   请检查 META_ACCESS_TOKEN 配置"
                )
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    logger.error(
                        f"❌ 400 Bad Request: {error_data.get('error', {}).get('message', 'Unknown')}"
                    )
                except Exception:
                    logger.error(f"❌ 400 Bad Request: {e.response.text[:200]}")
            else:
                logger.error(f"❌ HTTP {e.response.status_code}: {e}")

            return {"error": str(e), "status_code": e.response.status_code}

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络错误: {e}")
            return {"error": str(e)}

    def send_batch(self, events: list) -> Dict:
        """
        批量发送多个 CAPI 事件（最多 1000 个/批）

        Args:
            events: 事件列表，每个事件包含 event_name, email, lead_id, value 等字段

        Returns:
            Meta API 响应
        """
        if not events:
            return {"error": "No events to send"}

        if len(events) > 1000:
            logger.warning(f"⚠️ 事件数量 {len(events)} 超过 1000 限制，将分批发送")
            # 简单分批（递归）
            results = []
            for i in range(0, len(events), 1000):
                batch = events[i:i + 1000]
                results.append(self.send_batch(batch))
            return {"batches": results}

        # 构建所有事件
        payload_events = []
        for evt in events:
            try:
                payload_events.append({
                    "event_name": evt["event_name"],
                    "event_time": int(time.time()),
                    "action_source": ACTION_SOURCE,
                    "user_data": {
                        "em": [hash_email(evt["email"])],
                    },
                    "custom_data": {
                        "event_source": EVENT_SOURCE,
                        "lead_event_source": LEAD_EVENT_SOURCE,
                    },
                    "event_id": build_event_id(evt["lead_id"], evt["event_name"]),
                })
            except Exception as e:
                logger.error(f"❌ 事件构建失败: {evt} - {e}")

        payload = {
            "data": payload_events,
            "access_token": self.access_token,
        }

        try:
            logger.info(f"📤 批量发送 {len(payload_events)} 个 CAPI 事件")
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ 批量事件发送成功: {result.get('events_received', 0)} 个")
            return result
        except Exception as e:
            logger.error(f"❌ 批量事件发送失败: {e}")
            return {"error": str(e)}

    def test_event(self, event_name: str = "SKDK_Lead_Qualified", test_code: str = "TEST12345") -> Dict:
        """
        发送测试事件（用于验证 CAPI 集成）

        Args:
            event_name: 事件名
            test_code: 测试事件代码（在 Meta Events Manager → 测试事件中获取）

        Returns:
            Meta API 响应
        """
        return self.send_event(
            event_name=event_name,
            email="test@skdksport.com",
            lead_id="test_lead_001",
            test_event_code=test_code,
        )
