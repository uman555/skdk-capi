# Notion 集成配置（v2 - child_page 模型）

> ✅ 2026-06-24 已修复：原"内嵌数据库"方案失败（数据库 404），现改为 child_page 模型。

## 🔍 问题诊断与最终方案

### 原方案（已废弃）
- 假设 SKDK B2B Leads CRM 是**内嵌数据库**（child_database）
- `NOTION_DATABASE_ID` 实际是 page_id
- 真实 database_id = `389cae2a-241f-800c-9916-c92b5e65e396`，但该数据库**未分享给 Integration**（API 返回 404）
- 即使分享，数据库 schema 也是空的（title/properties 都是空数组）

### 当前方案（✅ 已工作）
- **child_page 模型**：直接在 SKDK B2B Leads CRM 页面下创建**子页面**作为 lead
- 页面 ID = `389cae2a-241f-80a7-a772-eaedd8757b42`（已分享给 Integration，可读写）
- 子页面用 `title` 存姓名 + `bulleted_list_item` 内容块存元数据

## 📊 存储结构

每个 lead 是一个 child_page：

```
📄 Sarah Johnson (title)
├── 📧 Email: buyer-002@skdksport.com
├── 🎯 Status: Qualified
├── 🏢 Company: Pacific Coast Sports
├── 🌍 Country: United States
├── 📞 Phone: +1-555-0199
├── 💼 Business Type: Distributor / Wholesaler
├── 📊 Monthly Volume: 1,000-5,000 units
├── 🎁 Products: Knee Support | Wrist Support
├── 💰 Lead Value: 2500
├── 🕐 Created At: 2026-06-24T22:34:58
├── 🕐 Status Updated At: 2026-06-24T22:35:53
├── 📡 Source: Meta Lead Form
└── 📝 Notes: ...
```

## ✅ 验证结果（2026-06-24 22:36）

| 测试项 | 状态 |
|--------|------|
| `pytest tests/test_notion_client.py -v` | ✅ 17 passed |
| `GET /health` | ✅ `{"notion":"ok","status":"healthy"}` |
| `POST /webhook/lead-submitted` | ✅ Notion + CAPI 全部成功 |
| `POST /webhook/status-update` | ✅ CAPI `SKDK_Lead_Qualified` 已发送 |
| `notion.update_status()` | ✅ Notion 字段已更新（Status + Updated At）|
| `notion.get_leads_by_status()` | ✅ 正确过滤 + 1 个 Qualified |
| `POST /api/supplementary` | ✅ 1 事件发送，0 错误 |

## 🔧 当前 .env 配置

```env
# Notion
NOTION_INTEGRATION_TOKEN=<your-notion-integration-token>
# 这是**页面 ID**（虽然变量名是 DATABASE_ID，保持向后兼容）
NOTION_DATABASE_ID=389cae2a-241f-80a7-a772-eaedd8757b42

# Meta
META_DATASET_ID=<your-meta-dataset-id>
META_APP_ID=<your-meta-app-id>
META_ACCESS_TOKEN=<your-meta-access-token>
```

> **注意**：`NOTION_DATABASE_ID` 这个变量名虽然保留，但实际存的是**页面 ID**。代码内部已统一使用 `page_id` 语义。

## 🛠️ 未来可优化（可选）

### 选项 1：保持 child_page 模型（推荐，简单可靠）
- ✅ 优点：不需要用户额外操作，Notion UI 中可读性高
- ❌ 缺点：无法在 Notion 表格视图查看全部 lead（需要切到页面视图）

### 选项 2：让用户把页面升级为数据库
- 用户在 Notion 中：把 "SKDK B2B Leads CRM" 页面转换为数据库
- 然后分享该数据库给 Integration
- 代码需要小改：property 名要重新映射

### 选项 3：手动分享原数据库给 Integration
- 用户在 Notion 中：找到真实 database（`389cae2a-241f-800c-9916-c92b5e65e396`）
- 右上角 "..." → "连接" → 添加 "SKDK Notion Integration"
- 但该数据库 schema 是空的（title/properties 都为空），需要先添加 property 字段
- 不推荐：成本高，收益小

## 📝 维护 SOP

### 每周
- 检查 `/health` 状态 → 确认 Notion 子页面可读
- 查看 Railway 日志 → 确认 CAPI 事件正常发送
- 抽查 1-2 个 lead 的 Notion 字段完整性

### 每月
- 检查 Notion Integration 权限（页面仍需在分享列表中）
- 验证 Meta Token 未过期
- 分析 lead 数据质量（Email/Status 字段是否完整）
