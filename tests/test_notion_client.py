"""
SKDK Notion 客户端单元测试（child_page 模型）
"""

import json
import pytest
import responses

from notion_client import NotionClient, Field


# ====================================
# Mock 辅助：构造 child_page 内容块
# ====================================
def make_bullet(field: str, value) -> dict:
    """构造一个 bulleted_list_item block"""
    text = f"{field}: {value}" if value is not None else f"{field}: "
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "id": f"block_{field.replace(' ', '_')}",
        "bulleted_list_item": {
            "rich_text": [{"type": "text", "text": {"content": text}, "plain_text": text}]
        },
    }


def make_child_page_response(page_id: str, title: str, metadata: dict) -> dict:
    """构造 child_page 的标准响应"""
    children = [make_bullet(k, v) for k, v in metadata.items()]
    return {
        "id": page_id,
        "object": "page",
        "properties": {
            "title": {
                "id": "title",
                "type": "title",
                "title": [{"plain_text": title, "text": {"content": title}}],
            }
        },
        "children": children,
    }


# ====================================
# Test class
# ====================================
class TestNotionClient:
    """Notion 客户端测试（child_page 模型）"""

    def setup_method(self):
        """每个测试前的初始化"""
        self.client = NotionClient(
            token="test_token_123",
            page_id="page_test_456",
        )

    # ==========================================
    # create_lead
    # ==========================================
    @responses.activate
    def test_create_lead_success(self):
        """成功创建潜在客户"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"id": "page_new_123", "object": "page", "url": "https://notion.so/page_new_123"},
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
        body = json.loads(responses.calls[0].request.body)
        assert body["parent"]["page_id"] == "page_test_456"
        # 关键：title 是唯一 property
        assert "title" in body["properties"]
        assert "Email" not in body["properties"]  # 不再是 property
        # children 包含 bulleted_list_item
        assert len(body["children"]) > 0
        # 验证 Email 在 children 第一个 bullet
        first_bullet = body["children"][0]
        assert first_bullet["type"] == "bulleted_list_item"
        first_text = first_bullet["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        assert first_text == "Email: test@example.com"
        # 验证 Status
        status_bullets = [c for c in body["children"] if "Status: " in c["bulleted_list_item"]["rich_text"][0]["text"]["content"]]
        assert any("Status: Contacted" in c["bulleted_list_item"]["rich_text"][0]["text"]["content"] for c in status_bullets)
        # 验证 products 用 | 分隔
        product_bullets = [c for c in body["children"] if "Products: " in c["bulleted_list_item"]["rich_text"][0]["text"]["content"]]
        assert any("Knee Support | Sports Gloves" in c["bulleted_list_item"]["rich_text"][0]["text"]["content"] for c in product_bullets)

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

        body = json.loads(responses.calls[0].request.body)
        # 没有 name 时，title 用 email
        assert body["properties"]["title"]["title"][0]["text"]["content"] == "minimal@test.com"

    def test_create_lead_missing_email(self):
        """缺 email 必填字段"""
        import pytest
        with pytest.raises(ValueError, match="email is required"):
            self.client.create_lead({"name": "No Email"})

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
    def test_create_lead_404(self):
        """404 错误：页面未分享"""
        responses.add(
            responses.POST,
            "https://api.notion.com/v1/pages",
            json={"message": "Could not find page"},
            status=404,
        )
        with pytest.raises(Exception):
            self.client.create_lead({"email": "test@test.com"})

    # ==========================================
    # _parse_metadata_blocks
    # ==========================================
    def test_parse_metadata_blocks_basic(self):
        """解析基本元数据"""
        blocks = [
            make_bullet("Email", "buyer@example.com"),
            make_bullet("Status", "Contacted"),
            make_bullet("Country", "United States"),
        ]
        result = NotionClient._parse_metadata_blocks(blocks)
        assert result == {
            "Email": "buyer@example.com",
            "Status": "Contacted",
            "Country": "United States",
        }

    def test_parse_metadata_blocks_chinese_colon(self):
        """支持中文冒号"""
        blocks = [
            make_bullet("Email", "test@test.com"),
        ]
        # 修改 block 使用中文冒号
        blocks[0]["bulleted_list_item"]["rich_text"][0]["text"]["content"] = "Email：test@test.com"
        blocks[0]["bulleted_list_item"]["rich_text"][0]["plain_text"] = "Email：test@test.com"
        result = NotionClient._parse_metadata_blocks(blocks)
        assert result == {"Email": "test@test.com"}

    def test_parse_metadata_blocks_skip_empty(self):
        """跳过空 block"""
        blocks = [
            make_bullet("Email", "test@test.com"),
            {"type": "bulleted_list_item", "bulleted_list_item": {"rich_text": []}},
            make_bullet("Status", "Contacted"),
        ]
        result = NotionClient._parse_metadata_blocks(blocks)
        assert result == {"Email": "test@test.com", "Status": "Contacted"}

    # ==========================================
    # update_status
    # ==========================================
    @responses.activate
    def test_update_status_success(self):
        """成功更新状态"""
        # 1. mock GET blocks
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={
                "results": [
                    make_bullet("Email", "test@test.com"),
                    make_bullet("Status", "Contacted"),
                ],
                "has_more": False,
            },
            status=200,
        )
        # 2. mock PATCH status block
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/blocks/block_Status",
            json={"id": "block_Status"},
            status=200,
        )
        # 3. mock PATCH status_updated_at (找不到，追加新 block)
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/blocks/page123/children",
            json={"results": []},
            status=200,
        )

        result = self.client.update_status("page123", "Qualified")
        assert result["field"] == "Status Updated At"
        # 至少 3 个 API 调用：GET children + 2 PATCH
        assert len(responses.calls) == 3

    # ==========================================
    # get_page
    # ==========================================
    @responses.activate
    def test_get_page_success(self):
        """获取页面详情"""
        # 1. mock GET page
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={
                "id": "page123",
                "properties": {
                    "title": {
                        "title": [{"plain_text": "Test Lead"}]
                    }
                }
            },
            status=200,
        )
        # 2. mock GET children
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={
                "results": [
                    make_bullet("Email", "test@test.com"),
                    make_bullet("Status", "Qualified"),
                ],
                "has_more": False,
            },
            status=200,
        )

        lead = self.client.get_page("page123")
        assert lead["id"] == "page123"
        assert lead["title"] == "Test Lead"
        assert lead["metadata"]["Email"] == "test@test.com"
        assert lead["metadata"]["Status"] == "Qualified"

    # ==========================================
    # get_email_by_page_id
    # ==========================================
    @responses.activate
    def test_get_email_by_page_id(self):
        """通过 page_id 获取 email"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "properties": {"title": {"title": [{"plain_text": "X"}]}}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={"results": [make_bullet("Email", "user@example.com")], "has_more": False},
            status=200,
        )

        email = self.client.get_email_by_page_id("page123")
        assert email == "user@example.com"

    @responses.activate
    def test_get_email_by_page_id_no_email(self):
        """页面没有 email 字段"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page123",
            json={"id": "page123", "properties": {"title": {"title": [{"plain_text": "X"}]}}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={"results": [], "has_more": False},
            status=200,
        )

        email = self.client.get_email_by_page_id("page123")
        assert email is None

    # ==========================================
    # get_leads_by_status
    # ==========================================
    @responses.activate
    def test_get_leads_by_status(self):
        """按状态查询"""
        # 1. mock 列子页面
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page_test_456/children",
            json={
                "results": [
                    {"id": "page1", "type": "child_page", "child_page": {"title": "Lead 1"}},
                    {"id": "page2", "type": "child_page", "child_page": {"title": "Lead 2"}},
                ],
                "has_more": False,
            },
            status=200,
        )
        # 2-3. mock 每个 page 的 details
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page1",
            json={"id": "page1", "properties": {"title": {"title": [{"plain_text": "Lead 1"}]}}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page1/children",
            json={
                "results": [
                    make_bullet("Email", "a@test.com"),
                    make_bullet("Status", "Qualified"),
                ],
                "has_more": False,
            },
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page2",
            json={"id": "page2", "properties": {"title": {"title": [{"plain_text": "Lead 2"}]}}},
            status=200,
        )
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page2/children",
            json={
                "results": [
                    make_bullet("Email", "b@test.com"),
                    make_bullet("Status", "Contacted"),  # 不是 Qualified
                ],
                "has_more": False,
            },
            status=200,
        )

        leads = self.client.get_leads_by_status("Qualified")
        assert len(leads) == 1
        assert leads[0]["id"] == "page1"
        assert leads[0]["metadata"]["Email"] == "a@test.com"

    # ==========================================
    # add_note
    # ==========================================
    @responses.activate
    def test_add_note_existing(self):
        """追加到现有 Notes 块"""
        # 1. mock GET blocks 找到 Notes 块
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={
                "results": [
                    make_bullet("Email", "test@test.com"),
                    {
                        "id": "block_notes",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": "Notes: 旧备注"}, "plain_text": "Notes: 旧备注"}]
                        },
                    },
                ],
                "has_more": False,
            },
            status=200,
        )
        # 2. mock PATCH 现有 Notes 块
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/blocks/block_notes",
            json={"id": "block_notes"},
            status=200,
        )

        result = self.client.add_note("page123", "新备注")
        assert result["id"] == "block_notes"
        # 验证 PATCH 的 body 包含新旧备注
        body = json.loads(responses.calls[1].request.body)
        new_text = body["bulleted_list_item"]["rich_text"][0]["text"]["content"]
        assert "新备注" in new_text
        assert "旧备注" in new_text

    @responses.activate
    def test_add_note_new(self):
        """无 Notes 块时追加新块"""
        # 1. mock GET blocks（无 Notes 块）
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page123/children",
            json={
                "results": [make_bullet("Email", "test@test.com")],
                "has_more": False,
            },
            status=200,
        )
        # 2. mock PATCH 追加 children
        responses.add(
            responses.PATCH,
            "https://api.notion.com/v1/blocks/page123/children",
            json={"results": []},
            status=200,
        )

        result = self.client.add_note("page123", "全新备注")
        assert "results" in result

    # ==========================================
    # health_check
    # ==========================================
    @responses.activate
    def test_health_check_success(self):
        """健康检查成功"""
        # 1. mock GET page
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page_test_456",
            json={"id": "page_test_456"},
            status=200,
        )
        # 2. mock GET children
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/blocks/page_test_456/children",
            json={"results": [], "has_more": False},
            status=200,
        )

        result = self.client.health_check()
        assert result is True

    @responses.activate
    def test_health_check_failure(self):
        """健康检查失败"""
        responses.add(
            responses.GET,
            "https://api.notion.com/v1/pages/page_test_456",
            json={"message": "Unauthorized"},
            status=401,
        )

        result = self.client.health_check()
        assert result is False
