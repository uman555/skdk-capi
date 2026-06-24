"""
SKDK CAPI 集成 - Notion API 客户端
=====================================
负责：
1. 在 SKDK B2B Leads CRM 数据库创建潜在客户记录
2. 更新记录状态（Contacted → Qualified → Customer）
3. 查询记录（按状态、按 ID）
4. 错误处理和重试
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

from config import (
    NOTION_API_VERSION,
    NOTION_BASE_URL,
    NOTION_DATABASE_ID,
    NOTION_INTEGRATION_TOKEN,
    logger,
)


class NotionClient:
    """
    Notion API 客户端
    封装 SKDK B2B Leads CRM 数据库的所有操作
    """

    def __init__(self, token: str = None, database_id: str = None):
        """
        Args:
            token: Notion Integration Token（默认从 config 读取）
            database_id: 数据库 ID 或 Page ID（默认从 config 读取）
                        ⚠️ 如果是内嵌数据库，传入的是 page_id
                        构造函数会自动解析真实的 database_id
        """
        self.token = token or NOTION_INTEGRATION_TOKEN
        self.input_id = database_id or NOTION_DATABASE_ID
        self.base_url = NOTION_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_API_VERSION,
            "Content-Type": "application/json",
        })
        # 自动解析真实的 database_id
        self.database_id = self._resolve_database_id()
        logger.info(f"Notion client initialized: database={self.database_id[:20]}...")

    def _resolve_database_id(self) -> str:
        """
        解析真实的 database_id
        如果传入的是 page_id（内嵌数据库），自动获取真实的 database_id

        Returns:
            真实的 database_id
        """
        # 先尝试直接作为 database 访问
        try:
            self._request("GET", f"/databases/{self.input_id}")
            logger.info(f"✅ Input ID 是真实 database_id")
            return self.input_id
        except Exception:
            # 失败说明是 page_id
            try:
                logger.info(f"⚙️ Input ID 不是 database_id，尝试作为 page_id 解析...")
                page = self._request("GET", f"/pages/{self.input_id}")
                parent = page.get("parent", {})
                if parent.get("type") == "database_id":
                    real_db_id = parent.get("database_id")
                    logger.info(f"✅ 解析到真实 database_id: {real_db_id[:20]}...")
                    return real_db_id
                else:
                    logger.warning(
                        f"⚠️ Page parent type is {parent.get('type')}, not database_id. "
                        f"Using original ID: {self.input_id}"
                    )
                    return self.input_id
            except Exception as e:
                logger.error(f"❌ 无法解析 database_id: {e}")
                # 降级使用原 ID
                return self.input_id

    def _is_inline_database(self) -> bool:
        """
        判断当前配置的是 page_id（内嵌数据库）还是真正的 database_id
        通过是否能直接访问 /databases/{id} 来判断

        Returns:
            True: 是内嵌数据库（用 page_id 操作）
            False: 是独立数据库（用 database_id 操作）
        """
        try:
            self._request("GET", f"/databases/{self.input_id}")
            return False  # 可以直接访问 → 独立数据库
        except Exception:
            return True  # 不能直接访问 → 内嵌数据库（用 page_id）

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        统一的 HTTP 请求方法（带错误处理）

        Args:
            method: HTTP 方法（GET/POST/PATCH）
            endpoint: API 端点（如 /pages 或 /databases/{id}/query）
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
            if e.response.status_code == 401:
                logger.error(
                    "❌ 401 Unauthorized: Notion Token 无效或过期\n"
                    "   请检查 NOTION_INTEGRATION_TOKEN"
                )
            elif e.response.status_code == 404:
                logger.error(
                    f"❌ 404 Not Found: {endpoint}\n"
                    f"   请确认数据库 ID 正确且已分享给 Integration"
                )
            else:
                try:
                    error_data = e.response.json()
                    logger.error(
                        f"❌ HTTP {e.response.status_code}: {error_data.get('message', 'Unknown')}"
                    )
                except Exception:
                    logger.error(f"❌ HTTP {e.response.status_code}: {e.response.text[:200]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ 网络错误: {e}")
            raise

    # ==========================================
    # 创建新潜在客户
    # ==========================================
    def create_lead(self, lead_data: Dict) -> str:
        """
        在 SKDK B2B Leads CRM 数据库创建新潜在客户

        Args:
            lead_data: 潜在客户数据字典，必填字段：
                - email (str): 邮箱
                - name (str, optional): 姓名
                - phone (str, optional): 电话
                - company (str, optional): 公司名
                - country (str, optional): 国家/地区
                - business_type (str, optional): 客户类型
                - monthly_volume (str, optional): 月采购量
                - products (list, optional): 产品兴趣列表

        Returns:
            Notion 页面 ID

        Examples:
            >>> lead_id = notion.create_lead({
            ...     "email": "test@example.com",
            ...     "name": "John Doe",
            ...     "company": "ABC Trading",
            ...     "country": "United States",
            ...     "business_type": "Distributor / Wholesaler",
            ...     "monthly_volume": "500-3,000 units",
            ...     "products": ["Knee Support", "Sports Gloves"]
            ... })
        """
        properties = {
            # ⚠️ 关键：Notion API 中 title 字段必须用 "title" 作为 key
            # （display name 可以是 "Name"，但 API 字段名是 "title"）
            "title": {
                "title": [{"text": {"content": lead_data.get("name", "Unknown")}}]
            },
            "Email": {
                "email": lead_data["email"]
            },
            "Source": {
                "select": {"name": lead_data.get("source", "Meta Lead Form")}
            },
            "Status": {
                "select": {"name": "Contacted"}  # 默认状态
            },
            "Status Updated At": {
                "date": {"start": datetime.now().isoformat()}
            },
            "Created At": {
                "date": {"start": datetime.now().isoformat()}
            },
        }

        # 可选字段
        if lead_data.get("phone"):
            properties["Phone"] = {"phone_number": lead_data["phone"]}
        if lead_data.get("company"):
            properties["Company"] = {
                "rich_text": [{"text": {"content": lead_data["company"]}}]
            }
        if lead_data.get("country"):
            properties["Country"] = {"select": {"name": lead_data["country"]}}
        if lead_data.get("business_type"):
            properties["Business Type"] = {
                "select": {"name": lead_data["business_type"]}
            }
        if lead_data.get("monthly_volume"):
            properties["Monthly Volume"] = {
                "select": {"name": lead_data["monthly_volume"]}
            }
        if lead_data.get("products"):
            properties["Product Interest"] = {
                "multi_select": [
                    {"name": p} for p in lead_data["products"]
                ]
            }
        if lead_data.get("notes"):
            properties["Notes"] = {
                "rich_text": [{"text": {"content": lead_data["notes"]}}]
            }
        if lead_data.get("lead_value"):
            properties["Lead Value"] = {"number": lead_data["lead_value"]}

        payload = {
            "parent": {"page_id": self.input_id},
            "properties": properties,
        }

        result = self._request("POST", "/pages", json=payload)
        page_id = result["id"]
        logger.info(
            f"✅ Notion 创建潜在客户成功: {lead_data['email']} (id={page_id})"
        )
        return page_id

    # ==========================================
    # 更新记录状态
    # ==========================================
    def update_status(self, page_id: str, new_status: str) -> Dict:
        """
        更新 Notion 记录的状态字段

        Args:
            page_id: Notion 页面 ID
            new_status: 新状态（Contacted / Qualified / Customer / Lost）

        Returns:
            API 响应
        """
        payload = {
            "properties": {
                "Status": {"select": {"name": new_status}},
                "Status Updated At": {
                    "date": {"start": datetime.now().isoformat()}
                },
            }
        }

        result = self._request("PATCH", f"/pages/{page_id}", json=payload)
        logger.info(f"✅ Notion 更新状态: {page_id} → {new_status}")
        return result

    def update_lead_value(self, page_id: str, value: float) -> Dict:
        """
        更新 Notion 记录的预估订单价值

        Args:
            page_id: Notion 页面 ID
            value: 价值（数字）

        Returns:
            API 响应
        """
        payload = {
            "properties": {
                "Lead Value": {"number": value}
            }
        }
        result = self._request("PATCH", f"/pages/{page_id}", json=payload)
        logger.info(f"✅ Notion 更新 Lead Value: {page_id} → {value}")
        return result

    def add_note(self, page_id: str, note: str) -> Dict:
        """
        追加销售备注到 Notion 记录

        Args:
            page_id: Notion 页面 ID
            note: 备注内容

        Returns:
            API 响应
        """
        # 获取当前备注
        page = self.get_page(page_id)
        current_notes = ""
        notes_prop = page.get("properties", {}).get("Notes", {})
        if notes_prop.get("rich_text"):
            current_notes = "".join(
                [rt.get("plain_text", "") for rt in notes_prop["rich_text"]]
            )

        # 追加新备注
        new_notes = f"{current_notes}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}".strip()

        payload = {
            "properties": {
                "Notes": {
                    "rich_text": [{"text": {"content": new_notes}}]
                }
            }
        }
        result = self._request("PATCH", f"/pages/{page_id}", json=payload)
        logger.info(f"✅ Notion 添加备注: {page_id}")
        return result

    # ==========================================
    # 查询记录
    # ==========================================
    def get_page(self, page_id: str) -> Dict:
        """
        通过 Notion 页面 ID 获取记录详情

        Args:
            page_id: Notion 页面 ID

        Returns:
            页面详情字典
        """
        return self._request("GET", f"/pages/{page_id}")

    def get_leads_by_status(self, status: str, limit: int = 100) -> List[Dict]:
        """
        获取所有指定状态的潜在客户

        Args:
            status: 状态名（Contacted / Qualified / Customer / Lost）
            limit: 最多返回数量

        Returns:
            潜在客户列表

        Examples:
            >>> leads = notion.get_leads_by_status("Qualified")
            >>> for lead in leads:
            ...     print(lead["id"], lead["properties"]["Email"]["email"])
        """
        if self._is_inline_database():
            # 内嵌数据库：用 page_id 作为 parent 查询
            return self._get_children_by_status(self.input_id, status, limit)
        else:
            payload = {
                "filter": {
                    "property": "Status",
                    "select": {"equals": status}
                },
                "page_size": min(limit, 100)
            }
            result = self._request("POST", f"/databases/{self.database_id}/query", json=payload)
            leads = result.get("results", [])
            logger.info(f"✅ Notion 查询 '{status}' 状态: {len(leads)} 条")
            return leads

    def _get_children_by_status(self, page_id: str, status: str, limit: int = 100) -> List[Dict]:
        """
        内嵌数据库的备用查询方法 - 通过 page 的 children API
        ⚠️ 此方法只能获取所有子页面，无法在 API 层过滤
        需要在客户端代码中过滤 status
        """
        all_children = []
        has_more = True
        start_cursor = None

        while has_more and len(all_children) < limit:
            params = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            url = f"{self.base_url}/blocks/{page_id}/children"
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                result = response.json()
            except Exception as e:
                logger.error(f"❌ children API failed: {e}")
                break

            for child in result.get("results", []):
                if child.get("type") == "child_page":
                    # 获取子页面详情
                    try:
                        page_detail = self.get_page(child["id"])
                        all_children.append(page_detail)
                    except Exception:
                        pass

            has_more = result.get("has_more", False)
            start_cursor = result.get("next_cursor")

        # 在客户端过滤 status
        filtered = []
        for lead in all_children:
            status_prop = lead.get("properties", {}).get("Status", {})
            if status_prop.get("select"):
                if status_prop["select"].get("name") == status:
                    filtered.append(lead)

        logger.info(f"✅ Notion 查询 '{status}' 状态（内嵌数据库）: {len(filtered)} 条")
        return filtered[:limit]

    def get_recent_leads(self, days: int = 1, limit: int = 100) -> List[Dict]:
        """
        获取最近 N 天创建的潜在客户

        Args:
            days: 最近天数
            limit: 最多返回数量

        Returns:
            潜在客户列表
        """
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).isoformat()

        if self._is_inline_database():
            # 内嵌数据库：获取所有 children 然后客户端过滤
            all_children = self._get_children_by_status(self.input_id, status="", limit=limit)
            filtered = []
            for lead in all_children:
                created_prop = lead.get("properties", {}).get("Created At", {})
                if created_prop.get("date"):
                    if created_prop["date"].get("start", "") >= start_date:
                        filtered.append(lead)
            return filtered
        else:
            payload = {
                "filter": {
                    "property": "Created At",
                    "date": {"on_or_after": start_date}
                },
                "sort": [{"property": "Created At", "direction": "descending"}],
                "page_size": min(limit, 100)
            }
            result = self._request("POST", f"/databases/{self.database_id}/query", json=payload)
            leads = result.get("results", [])
            logger.info(f"✅ Notion 查询最近 {days} 天: {len(leads)} 条")
            return leads

    def get_email_by_page_id(self, page_id: str) -> Optional[str]:
        """
        通过 Notion 页面 ID 获取邮箱

        Args:
            page_id: Notion 页面 ID

        Returns:
            邮箱地址（如果存在）
        """
        try:
            page = self.get_page(page_id)
            email_prop = page.get("properties", {}).get("Email", {})
            if email_prop.get("email"):
                return email_prop["email"]
        except Exception as e:
            logger.error(f"❌ 获取邮箱失败 {page_id}: {e}")
        return None

    # ==========================================
    # 健康检查
    # ==========================================
    def health_check(self) -> bool:
        """
        检查 Notion 集成是否正常工作

        Returns:
            True 如果健康，False 如果失败
        """
        try:
            # 内嵌数据库用 page endpoint，独立数据库用 database endpoint
            if self._is_inline_database():
                self._request("GET", f"/pages/{self.input_id}")
            else:
                self._request("GET", f"/databases/{self.database_id}")
            logger.info("✅ Notion health check passed")
            return True
        except Exception as e:
            logger.error(f"❌ Notion health check failed: {e}")
            return False
