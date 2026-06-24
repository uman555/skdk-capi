"""
SKDK CAPI 客户端单元测试
"""

import pytest
import responses
import hashlib

from capi_client import CAPIClient, hash_email, build_event_id


class TestHashEmail:
    """测试邮箱 SHA-256 哈希"""

    def test_hash_email_basic(self):
        """基本邮箱哈希"""
        email = "test@example.com"
        result = hash_email(email)
        expected = hashlib.sha256(b"test@example.com").hexdigest()
        assert result == expected
        assert len(result) == 64  # SHA-256 输出 64 个十六进制字符

    def test_hash_email_lowercase_normalization(self):
        """大写转小写"""
        email1 = "Test@Example.com"
        email2 = "test@example.com"
        assert hash_email(email1) == hash_email(email2)

    def test_hash_email_trim_whitespace(self):
        """去除前后空格"""
        email1 = "  test@example.com  "
        email2 = "test@example.com"
        assert hash_email(email1) == hash_email(email2)

    def test_hash_email_empty_raises(self):
        """空邮箱抛错"""
        with pytest.raises(ValueError):
            hash_email("")

    def test_hash_email_none_raises(self):
        """None 抛错"""
        with pytest.raises((ValueError, AttributeError)):
            hash_email(None)


class TestBuildEventId:
    """测试 event_id 构建"""

    def test_event_id_format(self):
        """event_id 格式: lead_id_eventname_timestamp"""
        event_id = build_event_id("page123", "SKDK_Lead_Qualified")
        parts = event_id.split("_")
        # page123 + SKDK + Lead + Qualified + timestamp = 5 parts
        assert len(parts) == 5
        assert parts[0] == "page123"
        assert parts[-1].isdigit()  # 最后一部分是时间戳
        # 事件名部分（去掉 lead_id 和 timestamp）
        event_part = "_".join(parts[1:-1])
        assert event_part == "SKDK_Lead_Qualified"

    def test_event_id_unique(self):
        """不同时刻调用产生不同 ID"""
        id1 = build_event_id("page123", "SKDK_Lead_Qualified")
        import time
        time.sleep(2)  # 等待 2 秒确保时间戳不同
        id2 = build_event_id("page123", "SKDK_Lead_Qualified")
        assert id1 != id2


class TestCAPIClientSendEvent:
    """测试 CAPI 事件发送"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.client = CAPIClient(
            access_token="test_token",
            base_url="https://graph.facebook.com/v25.0/123456789/events",
        )

    @responses.activate
    def test_send_event_success(self):
        """成功发送事件"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"events_received": 1, "messages": []},
            status=200,
        )

        result = self.client.send_event(
            event_name="SKDK_Lead_Qualified",
            email="test@example.com",
            lead_id="page123",
        )

        assert "events_received" in result
        assert result["events_received"] == 1
        assert len(responses.calls) == 1

        # 验证请求体
        call = responses.calls[0]
        import json
        body = json.loads(call.request.body)
        assert body["data"][0]["event_name"] == "SKDK_Lead_Qualified"
        assert body["data"][0]["action_source"] == "system_generated"
        assert body["data"][0]["user_data"]["em"][0] == hash_email("test@example.com")
        assert body["data"][0]["custom_data"]["event_source"] == "crm"
        assert body["data"][0]["custom_data"]["lead_event_source"] == "Notion_CRM"

    @responses.activate
    def test_send_event_with_value(self):
        """带转化价值（Purchase 事件）"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"events_received": 1},
            status=200,
        )

        result = self.client.send_event(
            event_name="SKDK_Purchase",
            email="test@example.com",
            lead_id="page123",
            value=1500.50,
        )

        import json
        call_body = json.loads(responses.calls[0].request.body)
        assert call_body["data"][0]["custom_data"]["value"] == 1500.50
        assert call_body["data"][0]["custom_data"]["currency"] == "USD"

    @responses.activate
    def test_send_event_401_unauthorized(self):
        """401 错误：Token 无效"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"error": {"message": "Invalid OAuth access token"}},
            status=401,
        )

        result = self.client.send_event(
            event_name="SKDK_Lead_Qualified",
            email="test@example.com",
            lead_id="page123",
        )

        assert "error" in result
        assert result["status_code"] == 401

    @responses.activate
    def test_send_event_400_bad_request(self):
        """400 错误：请求参数错误"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"error": {"message": "Invalid event_name"}},
            status=400,
        )

        result = self.client.send_event(
            event_name="Invalid",
            email="test@example.com",
            lead_id="page123",
        )

        assert "error" in result
        assert result["status_code"] == 400

    @responses.activate
    def test_send_event_network_error(self):
        """网络错误"""
        import requests
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            body=requests.exceptions.ConnectionError("Connection failed"),
        )

        result = self.client.send_event(
            event_name="SKDK_Lead_Qualified",
            email="test@example.com",
            lead_id="page123",
        )

        assert "error" in result


class TestCAPIClientBatch:
    """测试批量发送"""

    def setup_method(self):
        self.client = CAPIClient(
            access_token="test_token",
            base_url="https://graph.facebook.com/v25.0/123456789/events",
        )

    @responses.activate
    def test_batch_empty(self):
        """空批次"""
        result = self.client.send_batch([])
        assert "error" in result

    @responses.activate
    def test_batch_success(self):
        """批量成功"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"events_received": 3},
            status=200,
        )

        events = [
            {"event_name": "SKDK_Lead_Contacted", "email": f"user{i}@test.com", "lead_id": f"page{i}"}
            for i in range(3)
        ]

        result = self.client.send_batch(events)
        assert result["events_received"] == 3

    @responses.activate
    def test_batch_split(self):
        """超过 1000 个分批"""
        responses.add(
            responses.POST,
            "https://graph.facebook.com/v25.0/123456789/events",
            json={"events_received": 100},
            status=200,
        )

        events = [
            {"event_name": "SKDK_Lead_Contacted", "email": f"user{i}@test.com", "lead_id": f"page{i}"}
            for i in range(1500)  # 超过 1000
        ]

        result = self.client.send_batch(events)
        # 应该分 2 批
        assert "batches" in result
