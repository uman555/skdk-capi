# SKDK CAPI 部署运行手册

> Railway 已部署完成 ✅
> **Web URL**: https://skdk-capi-production.up.railway.app

---

## 📊 当前部署状态

| 组件 | 状态 | URL / ID |
|------|------|---------|
| GitHub 仓库 | ✅ | https://github.com/uman555/skdk-capi |
| Railway 项目 | ✅ | skdk-capi (production) |
| Web 服务 | ✅ Online | https://skdk-capi-production.up.railway.app |
| Notion 集成 | ✅ | child_page 模型（页面已分享） |
| Meta CAPI | ⚠️ Token 过期 | 需要 System User Token |
| Scheduler 服务 | ⏸️ 未部署 | 在 Railway UI 添加 |
| Zapier 集成 | ⏳ 待配置 | 下面有步骤 |
| Notion Automation | ⏳ 待配置 | 下面有步骤 |

---

## 🔴 现在必须做的（5 分钟）

### 0. 修复 Meta Token 过期

**症状**：测试时 CAPI 返回 `400 Bad Request: Session has expired`

**原因**：用的是 Personal Token（1-2 小时过期）

**解决**：换成 System User Token（永不过期）

#### 操作步骤

1. 打开 https://business.facebook.com/settings/system-users
2. **Add** → 创建 System User
   - Name: `SKDK CAPI Service`
   - Role: **Admin**
3. **Add assets** → 勾选以下 6 项并分配：
   - [ ] Facebook 公共主页（SKDK Sport）
   - [ ] 广告账户（SKDK ad account）
   - [ ] Pixel 像素代码（关联 Dataset 1723656532148251）
   - [ ] Instagram 账户
   - [ ] WhatsApp 账户
   - [ ] **数据集**（最重要，Dataset ID = 1723656532148251）
4. **Generate new token**：
   - App：选择关联 App ID `1554011292941689` 的应用
   - Permission scopes：`ads_management` + `business_management`
   - Token expiry：**Never（永不过期）** ← 重要
5. 复制 token 发给 Claude → 自动更新 Railway env var + 重启服务 + 重试

---

## 🟡 然后做的（用户手动，10+10+5 分钟）

### 1. 在 Railway UI 添加 scheduler 服务

> Railway CLI 配置 scheduler 的启动命令比较复杂，建议在 UI 操作。

1. 打开 https://railway.com/project/e7ca6f46-da03-4647-8557-6f2cca6fa2cf
2. 点 **+ New** → **GitHub Repo** → 选择 `uman555/skdk-capi`
3. Service name 填 `scheduler`
4. 部署完成后 → **Variables** 标签 → 添加 7 个环境变量：
   ```
   NOTION_INTEGRATION_TOKEN=<你的-notion-token>
   NOTION_DATABASE_ID=389cae2a-241f-80a7-a772-eaedd8757b42
   META_DATASET_ID=1723656532148251
   META_APP_ID=1554011292941689
   META_ACCESS_TOKEN=<新 token>
   TIMEZONE=Asia/Shanghai
   LOG_LEVEL=INFO
   ```
5. **Settings** 标签 → **Deploy** → **Custom Start Command**：
   ```
   python scheduler.py
   ```
6. 等待部署完成 → 在 Logs 看 `🚀 SKDK CAPI 定时任务启动` 表示成功

---

### 2. 配置 Zapier（创建 1 个 Zap）

> Meta Lead Form 提交 → 自动调用 webhook 创建 Notion 记录 + 发 CAPI

#### Trigger
- App: **Facebook Lead Ads**
- Event: **New Lead**
- Page: 你的 SKDK Facebook 公共主页
- Form: 你的 Lead Form

#### Action
- App: **Webhooks by Zapier**
- Event: **POST**
- URL: `https://skdk-capi-production.up.railway.app/webhook/lead-submitted`
- Method: `POST`
- Content-Type: `application/json`
- Data (从 Lead Form 字段映射):

```json
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

#### 测试
1. 在 Zapier 面板点 **Test & Continue**
2. 应该看到 HTTP 200 响应
3. 检查 Notion SKDK B2B Leads CRM 页面 → 应该出现新的子页面

---

### 3. 配置 Notion Automation（创建 3 个）

> Notion 子页面状态变化 → 自动调用 webhook 发 CAPI 事件

⚠️ **重要**：Notion Automation 在 child_page 模型下，需要稍微不同的设置。

#### Automation 1: Status → Contacted

1. 打开 https://www.notion.so/389cae2a-241f-80a7-a772-eaedd8757b42
2. 右上角 **...** → **Connections** → 确认 **SKDK Notion Integration** 存在（已存在 ✅）
3. 顶部 **...** → **+ Add automation**
4. Trigger: **When page is added or updated**
   - 实际上对于 child_page 模型，最简单的方式是 **Manual trigger** 或 **按钮触发**
5. ⚠️ **Notion Automation 的限制**：Notion 的 Automation 不能直接监听 "Status 字段变化"（因为我们用的是 content block，不是 property）
6. **替代方案**：使用 Notion 的 Status column 作为 trigger（如果想用 property-based）：
   - 把 Status 也加为 child_page 的一个简单 property（用 emoji 在 title 中标记）
   - 但这会破坏现有数据

#### 💡 更简单的方案（推荐）：Manual Webhook

不要配置复杂的 Notion Automation。**直接在 SKDK CAPI Backend 暴露一个简单 API，让用户在 Notion 页面里点按钮触发**。

或者用 **Zapier 中转**：
- Trigger: Notion → New or Updated Page in Database
- Action: Webhook → POST to /webhook/status-update

---

## 🧪 完整测试流程（部署后）

```
□ 1. 提交测试 Lead Form（或 curl 模拟）
□ 2. 验证 Notion 页面有新子页面（标题 = Lead 姓名）
□ 3. 验证 Meta Events Manager 有 SKDK_Lead_Submitted 事件
□ 4. curl 触发 status-update → Qualified
□ 5. 验证 Meta Events Manager 有 SKDK_Lead_Qualified 事件
□ 6. curl 触发 status-update → Customer + value
□ 7. 验证 Meta Events Manager 有 SKDK_Purchase 事件
```

### 测试命令（可直接复制粘贴）

```bash
# 1. 测试 lead-submitted
curl -X POST https://skdk-capi-production.up.railway.app/webhook/lead-submitted \
  -H "Content-Type: application/json" \
  -d '{"email":"final-test@skdksport.com","name":"Final Test","country":"USA","products":["Knee Support"]}'

# 2. 测试 status-update → Qualified
curl -X POST https://skdk-capi-production.up.railway.app/webhook/status-update \
  -H "Content-Type: application/json" \
  -d '{"page_id":"<从 Notion 复制的 page_id>","new_status":"Qualified","email":"final-test@skdksport.com"}'

# 3. 测试 status-update → Customer
curl -X POST https://skdk-capi-production.up.railway.app/webhook/status-update \
  -H "Content-Type: application/json" \
  -d '{"page_id":"<page_id>","new_status":"Customer","email":"final-test@skdksport.com","value":3500}'

# 4. 健康检查
curl https://skdk-capi-production.up.railway.app/health

# 5. 手动补充上传
curl -X POST https://skdk-capi-production.up.railway.app/api/supplementary \
  -H "Content-Type: application/json" \
  -d '{"days":7}'
```

---

## ⚡ 快速参考

### Railway 项目信息
- Project ID: `e7ca6f46-da03-4647-8557-6f2cca6fa2cf`
- Project URL: https://railway.com/project/e7ca6f46-da03-4647-8557-6f2cca6fa2cf
- Web URL: https://skdk-capi-production.up.railway.app
- Webhook endpoints:
  - `POST /webhook/lead-submitted`
  - `POST /webhook/status-update`
  - `POST /api/supplementary`
  - `GET /health`

### Notion 信息
- Page ID: `389cae2a-241f-80a7-a772-eaedd8757b42`
- Page URL: https://www.notion.so/389cae2a-241f-80a7-a772-eaedd8757b42
- Integration: SKDK Notion Integration
- 模型: child_page（每个 lead = 一个子页面）

### Meta 信息
- Dataset ID: `1723656532148251`
- App ID: `1554011292941689`
- API Version: `v25.0`
- CAPI Endpoint: `https://graph.facebook.com/v25.0/1723656532148251/events`

---

## 🆘 故障排查

### Railway 服务 Crashed
1. 看 Railway Logs（实时）
2. 检查所有环境变量都设置了
3. 检查 Procfile 的 `web` 行：`web: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`

### Notion 401
- Token 过期或错误 → 在 Notion 重新生成 Integration Token
- 页面未分享 → 重新添加 SKDK Notion Integration 到页面

### Meta CAPI 400 / 401
- **400 "Session has expired"** → Token 过期，换 System User Token
- **400 "Invalid parameter"** → Payload 格式问题（检查 email hash、event_name）
- **401 "Invalid OAuth access token"** → Token 错误，重新生成
- **400 "permissions"** → System User 没分配所有 6 项资产

---

## 📞 联系

- 项目负责人: SKDK Sport 技术团队
- 问题反馈: support@skdksport.com
- GitHub: https://github.com/uman555/skdk-capi/issues