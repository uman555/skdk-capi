"""
SKDK CAPI 集成 - Notion API 客户端
=====================================
负责：
1. 在 SKDK B2B Leads CRM 页面下创建潜在客户子页面
2. 更新子页面状态（Contacted → Qualified → Customer → Lost）
3. 查询子页面（按状态、按 ID）
4. 错误处理和重试

存储模型（child_page）：
- parent.page_id = SKDK B2B Leads CRM 页面 ID
- properties.title = 潜在客户姓名（或邮箱当姓名缺失）
- content blocks = bulleted_list_item，存储所有元数据
  - "Email: buyer@example.com"
  - "Status: Contacted"
  - "Company: ABC Trading"
  - "Country: United States"
  - "Phone: +1-555-0100"
  - "Business Type: Distributor"
  - "Monthly Volume: 500-3,000 units"
  - "Products: Knee Support | Sports Gloves"
  - "Lead Value: 2500"
  - "Created At: 2026-06-24 22:00"
  - "Status Updated At: 2026-06-24 22:00"
  - "Source: Meta Lead Form"
  - "Notes: ..."
"""

import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

from config import (
    NOTION_API_VERSION,
    NOTION_BASE_URL,
    NOTION_DATABASE_ID,
    NOTION_INTEGRATION_TOKEN,
    logger,
)


# ====================================
# 元数据字段定义（统一管理，避免拼写错误）
# ====================================
class Field:
    """Notion bulleted_list_item 中的元数据字段名"""
    EMAIL = "Email"
    STATUS = "Status"
    COMPANY = "Company"
    COUNTRY = "Country"
    PHONE = "Phone"
    BUSINESS_TYPE = "Business Type"
    MONTHLY_VOLUME = "Monthly Volume"
    PRODUCTS = "Products"
    LEAD_VALUE = "Lead Value"
    CREATED_AT = "Created At"
    STATUS_UPDATED_AT = "Status Updated At"
    SOURCE = "Source"
    NOTES = "Notes"


# 状态默认值
DEFAULT_STATUS = "Contacted"
VALID_STATUSES = {"Contacted", "Qualified", "Customer", "Lost"}


class NotionClient:
    """
    Notion API 客户端（child_page 模型）
    封装 SKDK B2B Leads CRM 页面下的所有子页面操作
    """

    def __init__(self, token: str = None, page_id: str = None):
        """
        Args:
            token: Notion Integration Token（默认从 config 读取）
            page_id: SKDK B2B Leads CRM 页面 ID（默认从 config 读取）
        """
        self.token = token or NOTION_INTEGRATION_TOKEN
        self.page_id = page_id or NOTION_DATABASE_ID
        self.base_url = NOTION_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        })
        logger.info(f"Notion client initialized: page={self.page_id[:20]}...")

    # ==========================================
    # 底层 HTTP 请求
    # ==========================================
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        统一的 HTTP 请求方法（带错误处理）

        Args:
            method: HTTP 方法（GET/POST/PATCH/DELETE）
            endpoint: API 端点
            **kwargs: requests 参数

        Returns:
            API 响应 JSON

        Raises:
            requests.exceptions.RequestException: 请求错误
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            try:
                error_data = e.response.json()
                msg = error_data.get("message", "Unknown")
            except Exception:
                msg = e.response.text[:200]
            if status == 401:
                logger.error(f"❌ 401 Unauthorized: Notion Token 无效或过期 (msg={msg})")
            elif status == 404:
                logger.error(
                    f"❌ 404 Not Found: {endpoint}\n"
                    f"   请确认页面 ID 正确且已分享给 Integration"
                )
            else:
                logger.error(f"❌ HTTP {status}: {msg}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络错误: {e}")
            raise

    # ==========================================
    # 元数据解析：bulleted_list_item → dict
    # ==========================================
    @staticmethod
    def _parse_metadata_blocks(blocks: List[Dict]) -> Dict[str, str]:
        """
        解析子页面的 content blocks，提取 key:value 形式的元数据

        支持格式：
        - bulleted_list_item: "Email: buyer@example.com"
        - paragraph: "Email: buyer@example.com"
        - 任何 rich_text block: "Status: Qualified"

        Returns:
            {"Email": "buyer@example.com", "Status": "Qualified", ...}
        """
        metadata: Dict[str, str] = {}
        for block in blocks:
            btype = block.get("type")
            rich = block.get(btype, {}).get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich).strip()
            if not text:
                continue
            # 解析 "Key: Value" 或 "Key：Value"（中英文冒号都支持）
            match = re.match(r"^([^:：]+)\s*[:：]\s*(.*)$", text, re.DOTALL)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                metadata[key] = value
        return metadata

    @staticmethod
    def _build_bullet(field: str, value) -> Dict:
        """
        构造一个 bulleted_list_item block

        Args:
            field: 字段名（自动加冒号）
            value: 字段值

        Returns:
            Notion block dict
        """
        if value is None or value == "":
            text = f"{field}: "
        elif isinstance(value, list):
            text = f"{field}: " + " | ".join(str(v) for v in value)
        else:
            text = f"{field}: {value}"
        return {
            "object": "block",
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": text}}]
            },
        }

    # ==========================================
    # 子页面 CRUD
    # ==========================================
    def create_lead(self, lead_data: Dict) -> str:
        """
        在 SKDK B2B Leads CRM 页面下创建新潜在客户子页面

        Args:
            lead_data: 潜在客户数据字典
                - email (str, 必填): 邮箱
                - name (str, optional): 姓名（缺失则用 email 作为 title）
                - phone (str, optional): 电话
                - company (str, optional): 公司名
                - country (str, optional): 国家/地区
                - business_type (str, optional): 客户类型
                - monthly_volume (str, optional): 月采购量
                - products (list, optional): 产品兴趣列表
                - notes (str, optional): 备注
                - lead_value (float, optional): 预估订单价值
                - source (str, optional): 来源（默认 "Meta Lead Form"）

        Returns:
            Notion 页面 ID

        Raises:
            ValueError: 邮箱缺失
        """
        email = lead_data.get("email")
        if not email:
            raise ValueError("email is required")

        # title 用姓名，缺失则用邮箱
        title = lead_data.get("name") or email
        now_iso = datetime.now().isoformat()

        # 构造 content blocks（顺序固定，方便查阅）
        bullets = []
        bullets.append(self._build_bullet(Field.EMAIL, email))
        bullets.append(self._build_bullet(Field.STATUS, DEFAULT_STATUS))
        if lead_data.get("source"):
            bullets.append(self._build_bullet(Field.SOURCE, lead_data["source"]))
        if lead_data.get("phone"):
            bullets.append(self._build_bullet(Field.PHONE, lead_data["phone"]))
        if lead_data.get("company"):
            bullets.append(self._build_bullet(Field.COMPANY, lead_data["company"]))
        if lead_data.get("country"):
            bullets.append(self._build_bullet(Field.COUNTRY, lead_data["country"]))
        if lead_data.get("business_type"):
            bullets.append(self._build_bullet(Field.BUSINESS_TYPE, lead_data["business_type"]))
        if lead_data.get("monthly_volume"):
            bullets.append(self._build_bullet(Field.MONTHLY_VOLUME, lead_data["monthly_volume"]))
        if lead_data.get("products"):
            bullets.append(self._build_bullet(Field.PRODUCTS, lead_data["products"]))
        if lead_data.get("lead_value"):
            bullets.append(self._build_bullet(Field.LEAD_VALUE, lead_data["lead_value"]))
        if lead_data.get("notes"):
            bullets.append(self._build_bullet(Field.NOTES, lead_data["notes"]))
        bullets.append(self._build_bullet(Field.CREATED_AT, now_iso))
        bullets.append(self._build_bullet(Field.STATUS_UPDATED_AT, now_iso))

        payload = {
            "parent": {"page_id": self.page_id},
            "properties": {
                "title": {"title": [{"text": {"content": title}}]}
            },
            "children": bullets,
        }

        result = self._request("POST", "/pages", json=payload)
        page_id = result["id"]
        logger.info(f"✅ Notion 创建潜在客户成功: {email} (id={page_id[:20]}...)")
        return page_id

    def get_page(self, page_id: str) -> Dict:
        """
        获取子页面详情（含 content blocks 解析后的 metadata）

        Args:
            page_id: Notion 页面 ID

        Returns:
            {
                "id": "...",
                "title": "John Doe",
                "metadata": {"Email": "...", "Status": "...", ...},
                "raw": {...}  # 原始 page object
            }
        """
        page = self._request("GET", f"/pages/{page_id}")
        blocks = self._get_blocks(page_id)
        metadata = self._parse_metadata_blocks(blocks)
        # 提取 title
        title = ""
        title_prop = page.get("properties", {}).get("title", {})
        for t in title_prop.get("title", []):
            title += t.get("plain_text", "")
        return {
            "id": page_id,
            "title": title,
            "metadata": metadata,
            "raw": page,
        }

    def _get_blocks(self, block_id: str) -> List[Dict]:
        """
        获取 block 的所有子 blocks（自动翻页）

        Args:
            block_id: page 或 block 的 ID

        Returns:
            blocks 列表
        """
        all_blocks = []
        has_more = True
        start_cursor = None
        while has_more:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor
            try:
                result = self._request("GET", f"/blocks/{block_id}/children", params=params)
            except Exception as e:
                logger.error(f"❌ 获取 blocks 失败 {block_id}: {e}")
                break
            all_blocks.extend(result.get("results", []))
            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")
        return all_blocks

    def get_email_by_page_id(self, page_id: str) -> Optional[str]:
        """
        通过 page_id 提取 Email 字段

        Args:
            page_id: Notion 页面 ID

        Returns:
            邮箱地址（如果存在）
        """
        try:
            page = self.get_page(page_id)
            return page["metadata"].get(Field.EMAIL)
        except Exception as e:
            logger.error(f"❌ 获取邮箱失败 {page_id}: {e}")
            return None

    # ==========================================
    # 更新操作
    # ==========================================
    def update_status(self, page_id: str, new_status: str) -> Dict:
        """
        更新子页面的 Status 字段（同时更新 Status Updated At）

        实现方式：找到 Status block → 替换文本
        找不到时在末尾追加

        Args:
            page_id: Notion 页面 ID
            new_status: 新状态（Contacted/Qualified/Customer/Lost）

        Returns:
            API 响应
        """
        if new_status not in VALID_STATUSES:
            logger.warning(f"⚠️ 非标准状态: {new_status}（仍会更新）")

        now_iso = datetime.now().isoformat()
        return self._update_field(page_id, Field.STATUS, new_status, [
            (Field.STATUS, new_status),
            (Field.STATUS_UPDATED_AT, now_iso),
        ])

    def update_lead_value(self, page_id: str, value: float) -> Dict:
        """
        更新子页面的 Lead Value 字段

        Args:
            page_id: Notion 页面 ID
            value: 价值（数字）

        Returns:
            API 响应
        """
        return self._update_field(page_id, Field.LEAD_VALUE, value, [
            (Field.LEAD_VALUE, value),
        ])

    def add_note(self, page_id: str, note: str) -> Dict:
        """
        追加销售备注到子页面（在 Notes 块中追加新行）

        Args:
            page_id: Notion 页面 ID
            note: 备注内容

        Returns:
            API 响应
        """
        # 1. 找到现有的 Notes 块
        blocks = self._get_blocks(page_id)
        existing_notes_value = ""
        notes_block_id = None
        for b in blocks:
            if b.get("type") != "bulleted_list_item":
                continue
            rich = b["bulleted_list_item"].get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich)
            match = re.match(r"^Notes\s*[:：]\s*(.*)$", text, re.DOTALL)
            if match:
                notes_block_id = b["id"]
                existing_notes_value = match.group(1).strip()
                break

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_value = (
            f"{existing_notes_value}\n[{timestamp}] {note}".strip()
            if existing_notes_value
            else f"[{timestamp}] {note}"
        )

        if notes_block_id:
            # 2a. 更新现有 Notes 块
            payload = {
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": f"Notes: {new_value}"}}]
                }
            }
            result = self._request("PATCH", f"/blocks/{notes_block_id}", json=payload)
            logger.info(f"✅ Notion 更新 Notes: {page_id[:20]}...")
            return result
        else:
            # 2b. 追加新 Notes 块
            new_block = self._build_bullet(Field.NOTES, new_value)
            result = self._request("PATCH", f"/blocks/{page_id}/children", json={
                "children": [new_block]
            })
            logger.info(f"✅ Notion 添加 Notes: {page_id[:20]}...")
            return result

    def _update_field(
        self, page_id: str, primary_field: str, primary_value, all_updates: List[Tuple[str, str]]
    ) -> Dict:
        """
        通用字段更新方法

        Args:
            page_id: Notion 页面 ID
            primary_field: 必填字段（如果找不到则新建）
            primary_value: 必填值
            all_updates: [(field, value), ...] 全部要更新的字段

        Returns:
            最后一个 API 响应
        """
        blocks = self._get_blocks(page_id)
        existing_field_ids = {}  # field_name → block_id
        for b in blocks:
            if b.get("type") != "bulleted_list_item":
                continue
            rich = b["bulleted_list_item"].get("rich_text", [])
            text = "".join(rt.get("plain_text", "") for rt in rich)
            match = re.match(r"^([^:：]+)\s*[:：]", text)
            if match:
                existing_field_ids[match.group(1).strip()] = b["id"]

        last_result = None
        for field, value in all_updates:
            text = f"{field}: " + (
                " | ".join(str(v) for v in value) if isinstance(value, list)
                else str(value) if value is not None else ""
            )
            payload = {
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }
            if field in existing_field_ids:
                self._request("PATCH", f"/blocks/{existing_field_ids[field]}", json=payload)
            else:
                self._request("PATCH", f"/blocks/{page_id}/children", json={
                    "children": [self._build_bullet(field, value)]
                })
            last_result = {"field": field, "value": value}

        logger.info(f"✅ Notion 更新字段: {page_id[:20]}... ({primary_field}={primary_value})")
        return last_result or {}

    # ==========================================
    # 查询操作
    # ==========================================
    def get_leads_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """
        获取所有指定状态的潜在客户

        Args:
            status: 状态名
            limit: 最多返回数量

        Returns:
            潜在客户列表（每个元素是 get_page() 返回的 dict）

        Examples:
            >>> leads = notion.get_leads_by_status("Qualified")
            >>> for lead in leads:
            ...     print(lead["id"], lead["metadata"]["Email"])
        """
        return self._get_children_leads(
            filter_field=Field.STATUS,
            filter_value=status,
            limit=limit,
        )

    def get_recent_leads(self, days: int = 1, limit: int = 100) -> List[Dict]:
        """
        获取最近 N 天创建的潜在客户

        Args:
            days: 最近天数
            limit: 最多返回数量

        Returns:
            潜在客户列表
        """
        all_leads = self._get_children_leads(filter_field=None, filter_value=None, limit=limit)
        from datetime import timedelta
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        filtered = []
        for lead in all_leads:
            created = lead["metadata"].get(Field.CREATED_AT, "")
            if created and created >= cutoff:
                filtered.append(lead)
        return filtered

    def _get_children_leads(
        self, filter_field: Optional[str], filter_value: Optional[str], limit: int
    ) -> List[Dict]:
        """
        列出页面下所有子页面（child_page），可按元数据过滤

        Args:
            filter_field: 过滤字段名（None 不过滤）
            filter_value: 过滤值
            limit: 最多返回数量

        Returns:
            lead dict 列表
        """
        results = []
        has_more = True
        start_cursor = None

        while has_more and len(results) < limit:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor
            try:
                data = self._request("GET", f"/blocks/{self.page_id}/children", params=params)
            except Exception as e:
                logger.error(f"❌ 列子页面失败: {e}")
                break

            for block in data.get("results", []):
                if block.get("type") != "child_page":
                    continue
                try:
                    lead = self.get_page(block["id"])
                except Exception as e:
                    logger.warning(f"⚠️ 跳过无法读取的子页面 {block.get('id')}: {e}")
                    continue
                # 必须有 Email 才是有效 lead
                if not lead["metadata"].get(Field.EMAIL):
                    continue
                # 过滤
                if filter_field and lead["metadata"].get(filter_field) != filter_value:
                    continue
                results.append(lead)
                if len(results) >= limit:
                    break

            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        logger.info(
            f"✅ Notion 查询子页面: filter={filter_field}={filter_value} → {len(results)} 条"
        )
        return results[:limit]

    # ==========================================
    # 健康检查
    # ==========================================
    def health_check(self) -> bool:
        """
        检查 Notion 集成是否正常工作（能列出子页面）

        Returns:
            True 如果健康，False 如果失败
        """
        try:
            # 1. 验证页面可访问
            self._request("GET", f"/pages/{self.page_id}")
            # 2. 验证能列出 children
            params = {"page_size": 1}
            self._request("GET", f"/blocks/{self.page_id}/children", params=params)
            logger.info("✅ Notion health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Notion health check failed: {e}")
            return False
