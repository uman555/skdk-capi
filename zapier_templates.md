# Zapier / Notion Automation 模板

> SKDK CAPI 集成 - Webhook 配置模板

## 📋 Zap 1: Meta Lead Form → Notion (创建新潜在客户)

### 触发器 (Trigger)
```
App: Facebook Lead Ads
Event: New Lead
Page: SKDK (你的 Facebook 公共主页)
Form: SKDK_B2B_Leads_Form (你的 Lead Form)
```

### 动作 (Action)
```
App: Webhooks by Zapier
Event: POST

URL: https://YOUR-APP.up.railway.app/webhook/lead-submitted
Method: POST
Content-Type: application/json

Data (从 Lead Form 字段映射):
{
  "email": "{{lead_email}}",
  "name": "{{lead_full_name}}",
  "phone": "{{lead_phone_number}}",
  "company": "{{lead_company_name}}",
  "country": "{{lead_country}}",
  "business_type": "{{lead_business_type}}",
  "monthly_volume": "{{lead_monthly_volume}}",
  "products": "{{lead_product_interest}}"
}
```

### 测试
1. 提交测试 Lead Form
2. 检查 Zap 任务历史 → 应显示 "Success"
3. 检查 Notion 数据库 → 应有新行
4. 检查 Meta Events Manager → 应有 CAPI 事件

---

## 📋 Automation 1: Notion 状态变化 → CAPI

### 触发器 (Trigger)
```
Database: SKDK B2B Leads CRM
Filter: Status is "Contacted" / "Qualified" / "Customer"
Action: Edit page
```

### 动作 (Action)
```
App: Webhooks by Zapier (或 Notion Automations 内置 Webhook)
Event: Send Webhook

URL: https://YOUR-APP.up.railway.app/webhook/status-update
Method: POST
Content-Type: application/json

Data (从 Notion 字段映射):
{
  "page_id": "{{notion_page_id}}",
  "new_status": "{{notion_status}}",
  "email": "{{notion_email}}",
  "value": "{{notion_lead_value}}"
}
```

### 多状态触发（需 3 个 Automation）

**Automation 1A: Contacted**
```
Trigger: Status changes to "Contacted"
Action: Send webhook with new_status="Contacted"
```

**Automation 1B: Qualified** ⭐
```
Trigger: Status changes to "Qualified"
Action: Send webhook with new_status="Qualified"
```

**Automation 1C: Customer**
```
Trigger: Status changes to "Customer"
Action: Send webhook with new_status="Customer", value={{notion_lead_value}}
```

---

## 📋 测试用例

### 测试 1: Lead Form 提交
```bash
curl -X POST "https://YOUR-APP.up.railway.app/webhook/lead-submitted" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@skdksport.com",
    "name": "Test Buyer",
    "phone": "+1-555-0199",
    "company": "Test B2B Co",
    "country": "United States",
    "business_type": "Distributor / Wholesaler",
    "monthly_volume": "500-3,000 units",
    "products": ["Knee Support", "Sports Gloves"]
  }'
```

**预期**：
- HTTP 200
- Notion 数据库有新行
- Meta Events Manager 有 SKDK_Lead_Submitted 事件

### 测试 2: 状态变化为 Qualified
```bash
curl -X POST "https://YOUR-APP.up.railway.app/webhook/status-update" \
  -H "Content-Type: application/json" \
  -d '{
    "page_id": "abc123...",
    "new_status": "Qualified",
    "email": "test@skdksport.com"
  }'
```

**预期**：
- HTTP 200
- Meta Events Manager 有 SKDK_Lead_Qualified 事件

### 测试 3: 健康检查
```bash
curl "https://YOUR-APP.up.railway.app/health"
```

**预期**：
```json
{
  "status": "healthy",
  "notion": "ok",
  "service": "skdk-capi-integration"
}
```

---

## 🚀 快速启动清单

```
□ 1. 在 Notion 中重新分享 Integration 到数据库
□ 2. 部署到 Railway（自动检测 Procfile）
□ 3. 配置 5 个环境变量
□ 4. 在 Zapier 中创建 Zap 1（Meta Lead → Webhook）
□ 5. 在 Notion 中创建 Automation 1A/1B/1C
□ 6. 测试完整流程
□ 7. 启用"合格潜在客户"优化目标（50 转化后）
```

---

## 🆘 故障排查

### 问题: Zap 任务显示 500 错误
**原因**: Notion Integration 没有分享到数据库
**解决**: 在 Notion UI 中重新添加连接

### 问题: Meta 没有收到事件
**原因**: 
1. CAPI endpoint 错误
2. Token 无效或过期
3. Dataset ID 错误

**解决**:
1. 检查 .env 中 META_DATASET_ID
2. 检查 Token 是否过期（Personal Token 1-2h 过期）
3. 查看 Railway 日志

### 问题: Notion 创建成功但 CAPI 失败
**原因**: Meta API 错误
**解决**:
1. 查看 Railway 日志中 CAPI 错误
2. 检查权限
3. 使用 Graph API Explorer 测试

---

## 📚 相关文档

- [SKDK CAPI 完整 README](./README.md)
- [设计文档](./docs/specs/2026-06-24-skdk-capi-design.md)
- [Notion 分享指南](./setup_notion_sharing.md)
