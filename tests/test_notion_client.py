"""
SKDK Notion 客户端单元测试
"""

import pytest
import responses

from notion_client import NotionClient


class TestNotionClient:
    """Notion 客户端测试"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.client = NotionClient(
            token="test_token_123",
            database_id="db_test_456",
        )

    @responses.activate
    def test_create_lead_success(self):
        """成功创建潜在客户"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={
                "id": "page_new_123",
                "object": "page",
                "url": "https://notion.so/page_new_123",
            },
            status=200,
        )

        lead_data = {
            "email": "test@example.com",
            "name": "John Doe",
            "phone": "+1-555-0100",
            "company": "ABC Trading",
            "country": "United States",
            "business_type": "Distributor / Wholesaler",
            "monthly_volume": "500-3,000 units",
            "products": ["Knee Support", "Sports Gloves"],
        }

        page_id = self.client.create_lead(lead_data)
        assert page_id == "page_new_123"
        assert len(responses.calls) == 1

        # 验证请求体
        import json
        body = json.loads(responses.calls[0].request.body)
        assert body["parent"]["database_id"] == "db_test_456"
        assert body["properties"]["Email"]["email"] == "test@example.com"
        assert body["properties"]["Name"]["title"][0]["text"]["content"] == "John Doe"
        assert body["properties"]["Status"]["select"]["name"] == "Contacted"
        assert body["properties"]["Country"]["select"]["name"] == "United States"
        assert body["properties"]["Business Type"]["select"]["name"] == "Distributor / Wholesaler"
        assert body["properties"]["Monthly Volume"]["select"]["name"] == "500-3,000 units"
        assert len(body["properties"]["Product Interest"]["multi_select"]) == 2

    @responses.activate
    def test_create_lead_minimal(self):
        """最小必填字段（仅 email）"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"id": "page_minimal"},
            status=200,
        )

        page_id = self.client.create_lead({"email": "minimal@test.com"})
        assert page_id == "page_minimal"

    @responses.activate
    def test_create_lead_401(self):
        """401 错误"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"message": "API token invalid"},
            status=401,
        )

        with pytest.raises(Exception):
            self.client.create_lead({"email": "test@test.com"})

    @responses.activate
    def test_create_lead_404_database_not_found(self):
        """404 错误：数据库未找到"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"message": "Could not find database"},
            status=404,
        )

        with pytest.raises(Exception):
            self.client.create_lead({"email": "test@test.com"})

    @responses.activate
    def test_update_status_success(self):
        """成功更新状态"""
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "object": "page"},
            status=200,
        )

        result = self.client.update_status("page123", "Qualified")
        assert result["id"] == "page123"

        import json
        body = json.loads(responses.calls[0].request.body)
        assert body["properties"]["Status"]["select"]["name"] == "Qualified"
        assert "Status Updated At" in body["properties"]

    @responses.activate
    def test_update_lead_value_success(self):
        """更新 Lead Value"""
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123"},
            status=200,
        )

        result = self.client.update_lead_value("page123", 2500.0)
        assert result["id"] == "page123"

        import json
        body = json.loads(responses.calls[0].request.body)
        assert body["properties"]["Lead Value"]["number"] == 2500.0

    @responses.activate
    def test_get_page_success(self):
        """获取页面详情"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={
                "id": "page123",
                "properties": {
                    "Email": {"email": "test@test.com"},
                    "Name": {"title": [{"plain_text": "Test"}]}
                }
            },
            status=200,
        )

        page = self.client.get_page("page123")
        assert page["id"] == "page123"
        assert page["properties"]["Email"]["email"] == "test@test.com"

    @responses.activate
    def test_get_leads_by_status(self):
        """按状态查询"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/databases/db_test_456/query",
            json={
                "results": [
                    {"id": "page1", "properties": {"Email": {"email": "a@test.com"}}},
                    {"id": "page2", "properties": {"Email": {"email": "b@test.com"}}},
                ]
            },
            status=200,
        )

        leads = self.client.get_leads_by_status("Qualified")
        assert len(leads) == 2
        assert leads[0]["id"] == "page1"

    @responses.activate
    def test_get_email_by_page_id(self):
        """通过页面 ID 获取邮箱"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={
                "id": "page123",
                "properties": {"Email": {"email": "user@example.com"}}
            },
            status=200,
        )

        email = self.client.get_email_by_page_id("page123")
        assert email == "user@example.com"

    @responses.activate
    def test_get_email_by_page_id_not_found(self):
        """页面没有 email 字段"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={
                "id": "page123",
                "properties": {}
            },
            status=200,
        )

        email = self.client.get_email_by_page_id("page123")
        assert email is None

    @responses.activate
    def test_health_check_success(self):
        """健康检查成功"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/db_test_456",
            json={"id": "db_test_456"},
            status=200,
        )

        result = self.client.health_check()
        assert result is True

    @responses.activate
    def test_health_check_failure(self):
        """健康检查失败"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/databases/db_test_456",
            json={"message": "Unauthorized"},
            status=401,
        )

        result = self.client.health_check()
        assert result is False
