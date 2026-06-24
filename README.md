# SKDK CAPI 集成系统

> **SKDK Sport** B2B 外贸 - 运动护具 OEM/ODM
> 将 Notion CRM 销售漏斗状态同步到 Meta 广告系统

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-orange.svg)]()

---

## 🎯 项目简介

SKDK CAPI 集成系统是一个 Python Flask 后端，用于将 **Notion CRM** 中的潜在客户销售漏斗状态实时同步到 **Meta 广告系统**，让 Meta 学习期找到更精准的"合格潜在客户"用户。

**核心价值**：
- ✅ 启用"合格潜在客户人数最大化"成效目标（CPL -21%）
- ✅ Meta 4 大销售漏斗事件自动同步
- ✅ 每日 23:00 补充上传（确保 50 转化数据完整性）
- ✅ 完整错误处理 + 健康检查

---

## 📊 系统架构

```
┌────────────────────────────────────────────────────────┐
│  Notion SKDK B2B Leads CRM                              │
│  状态变化 → Webhook                                     │
└────────────────┬───────────────────────────────────────┘
                 │ HTTP POST
                 ↓
┌────────────────────────────────────────────────────────┐
│  SKDK CAPI Backend (Flask) - Railway                    │
├────────────────────────────────────────────────────────┤
│  /webhook/lead-submitted   → 创建记录 + CAPI         │
│  /webhook/status-update     → 状态变化 + CAPI         │
│  /api/supplementary        → 手动补充上传            │
│  /health                   → 健康检查                │
│                                                         │
│  每日 23:00 cron         → 补传当天状态事件          │
└────────────────┬───────────────────────────────────────┘
                 │ HTTPS POST (CAPI)
                 ↓
┌────────────────────────────────────────────────────────┐
│  Meta Conversions API (v25.0)                           │
│  Endpoint: /1723656532148251/events                    │
└────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

- **Python 3.10+**
- **Flask 3.0** - Web 框架
- **APScheduler 3.10** - 定时任务
- **requests** - HTTP 客户端
- **Railway.app** - 部署平台
- **Gunicorn** - WSGI 服务器
- **pytest + responses** - 测试框架

---

## 🚀 快速开始

### 1. 克隆项目

```bash
cd e:\claude code项目文件
git clone <repo-url> skdk-capi
cd skdk-capi
```

### 2. 创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 到 `.env`，填入真实凭证：

```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

编辑 `.env`：

```env
NOTION_INTEGRATION_TOKEN=ntn_xxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=389cae2a241f800c9916c92b5e65e396
META_DATASET_ID=1723656532148251
META_APP_ID=1554011292941689
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
```

### 5. 本地运行

```bash
# 启动 Web 服务
python app.py

# 启动定时任务（另一个终端）
python scheduler.py
```

服务运行在 `http://localhost:5000`

### 6. 运行测试

```bash
pytest tests/ -v
```

---

## 🔑 凭证获取指南

### Notion 凭证

#### 1. Notion Integration Token

1. 访问 https://www.notion.so/my-integrations
2. 点击 "+ 新建集成"（New integration）
3. 名称：SKDK CAPI
4. Capabilities：全部勾选
5. 复制 **Internal Integration Token** → `NOTION_INTEGRATION_TOKEN`

#### 2. Notion Database ID

1. 打开 Notion SKDK B2B Leads CRM 数据库
2. 复制 URL 中的 32 位字符串
3. ⚠️ 必须把数据库**分享给 Integration**（右上角 "..." → "连接" → 添加）

#### 3. 测试 Notion 凭证

```bash
curl -X GET "https://api.notion.com/v1/databases/YOUR_DATABASE_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Notion-Version: 2022-06-28"
```

应返回数据库信息。

### Meta 凭证

#### 1. Meta Dataset ID（Pixel ID）

1. 访问 https://business.facebook.com/events_manager
2. 选择你的 SKDK Pixel / Dataset
3. 复制 Dataset ID

#### 2. Meta App ID

1. 访问 https://developers.facebook.com/apps/
2. 创建应用（用途：业务）
3. 复制 App ID

#### 3. Meta Access Token

**方法 A：System User Token（永不过期，推荐）**

1. 访问 https://business.facebook.com/settings/system-users
2. 创建 System User（Admin 角色）
3. 分配 6 项业务资产：
   - Facebook 公共主页
   - 广告账户
   - Pixel 像素代码
   - Instagram 账户
   - WhatsApp 账户
   - 数据集
4. 生成令牌（永不过期）

**方法 B：Graph API Explorer（短期 1-2 小时，仅测试用）**

1. 访问 https://developers.facebook.com/tools/explorer/
2. 选择应用 + 权限
3. 生成 Token

---

## 🌐 Railway 部署

### 1. 准备 Git 仓库

```bash
cd skdk-capi
git init
git add .
git commit -m "Initial commit: SKDK CAPI integration"
```

推送到 GitHub：
```bash
git remote add origin https://github.com/your-repo/skdk-capi.git
git branch -M main
git push -u origin main
```

### 2. 在 Railway 创建项目

1. 访问 https://railway.app
2. 点击 "New Project" → "Deploy from GitHub"
3. 选择 `skdk-capi` 仓库
4. Railway 自动检测 Procfile

### 3. 配置环境变量

在 Railway 项目设置 → Variables：

```
NOTION_INTEGRATION_TOKEN=ntn_xxxxxxxxxxxxxxxxxx
NOTION_DATABASE_ID=389cae2a241f800c9916c92b5e65e396
META_DATASET_ID=1723656532148251
META_APP_ID=1554011292941689
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxx
LOG_LEVEL=INFO
TIMEZONE=Asia/Shanghai
```

### 4. 部署两个服务

Railway 默认只部署 `web` (app.py)。还需要部署 scheduler：

1. 在 Railway 项目 → "New Service" → "GitHub Repo"
2. 选择同一仓库
3. Settings → Deploy → Custom Start Command：
   ```
   python scheduler.py
   ```

### 5. 获取部署 URL

Railway 会分配 URL：
- Web 服务：`https://skdk-capi-production.up.railway.app`
- 健康检查：`https://skdk-capi-production.up.railway.app/health`

---

## 📡 Webhook 端点

### 1. POST /webhook/lead-submitted

**用途**：创建新潜在客户

**请求体**：
```json
{
  "email": "test@example.com",
  "name": "John Doe",
  "phone": "+1-555-0100",
  "company": "ABC Trading",
  "country": "United States",
  "business_type": "Distributor / Wholesaler",
  "monthly_volume": "500-3,000 units",
  "products": ["Knee Support", "Sports Gloves"]
}
```

**响应**：
```json
{
  "success": true,
  "notion_page_id": "abc123...",
  "capi_result": {"events_received": 1},
  "message": "Lead test@example.com 已创建并提交 CAPI 事件"
}
```

**配置**（Zapier）：
1. Trigger: "New Lead in Facebook Lead Ads"
2. Action: Webhook by Zapier
3. URL: `https://your-app.railway.app/webhook/lead-submitted`
4. Method: POST
5. Body: 上述 JSON 模板

### 2. POST /webhook/status-update

**用途**：状态变化触发 CAPI

**请求体**：
```json
{
  "page_id": "abc123...",
  "new_status": "Qualified",
  "email": "test@example.com",
  "value": null
}
```

**配置**（Notion Automation）：
1. Notion 数据库 → 设置 → Automations
2. 触发器："When Status changes to"（选择具体状态）
3. Action: "Send webhook"
4. URL: `https://your-app.railway.app/webhook/status-update`
5. Method: POST
6. Body: 上述 JSON 模板（用变量替换 page_id 和 new_status）

### 3. POST /api/supplementary

**用途**：手动触发每日补充上传

```bash
curl -X POST "https://your-app.railway.app/api/supplementary" \
  -H "Content-Type: application/json" \
  -d '{"days": 1}'
```

### 4. GET /health

**用途**：健康检查

```bash
curl "https://your-app.railway.app/health"
```

返回：
```json
{
  "status": "healthy",
  "notion": "ok",
  "service": "skdk-capi-integration",
  "version": "1.0.0"
}
```

---

## 📊 CAPI 事件说明

| Notion 状态 | CAPI 事件名 | 用途 | 优先级 |
|------------|-----------|------|--------|
| (新创建) | `SKDK_Lead_Submitted` | 提交线索 | P0 |
| Contacted | `SKDK_Lead_Contacted` | 销售联系 | P0 |
| **Qualified** ⭐ | `SKDK_Lead_Qualified` | 客户确认需求 | **P0（优化目标）** |
| Customer | `SKDK_Purchase` | 成交 | P0 |
| Lost | (不上报) | 流失 | - |

**Meta 学习期要求**：
- ⚠️ 至少 50 次转化
- ⚠️ 每天至少上传一次数据
- ⚠️ 28 天内完成转化

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_capi_client.py -v
pytest tests/test_notion_client.py -v

# 查看覆盖率
pytest tests/ --cov=. --cov-report=html
```

---

## 🐛 故障排查

### 问题 1：Notion API 返回 401

**原因**：Token 无效或过期
**解决**：
1. 检查 `NOTION_INTEGRATION_TOKEN` 是否正确
2. 在 Notion 重新生成 Integration Token
3. 确认 Integration 已添加到数据库

### 问题 2：CAPI 返回 401

**原因**：Meta Access Token 无效或过期
**解决**：
1. Personal Token 1-2h 过期 → 使用 System User Token
2. 检查 System User 是否分配了所有 6 项业务资产
3. 重新生成 Token

### 问题 3：CAPI 返回 400

**原因**：Payload 错误
**解决**：
1. 检查 `action_source` 是否是 `"system_generated"`
2. 检查 `event_name` 是否符合规范（不能有空格）
3. 检查 `event_time` 是否是 UNIX 时间戳（10 位数字）
4. 检查 `user_data.em` 是否是 SHA-256 哈希（小写 64 字符）

### 问题 4：每日补充上传未执行

**原因**：scheduler 服务未运行
**解决**：
1. 检查 Railway scheduler 服务状态
2. 查看日志确认 cron 触发
3. 手动调用 `/api/supplementary` 测试

### 问题 5：健康检查返回 503

**原因**：Notion 集成断开
**解决**：
1. 检查 Notion 数据库是否分享给 Integration
2. 重新生成 Token
3. 重新部署服务

---

## 📋 维护 SOP

### 每周
- [ ] 检查 `/health` 端点状态
- [ ] 查看 Railway 日志中是否有错误
- [ ] 验证 CAPI 事件是否成功发送

### 每月
- [ ] 检查 Notion 集成是否需要更新
- [ ] 验证 Meta Token 有效期
- [ ] 分析 SKDK B2B Leads CRM 数据质量
- [ ] 检查拉黑率（< 5%）

### 每季度
- [ ] 更新 Python 依赖（`pip install --upgrade`）
- [ ] 审查 CAPI 性能数据
- [ ] 优化事件定义
- [ ] 评估是否启用"合格潜在客户"成效目标

---

## 🔒 安全建议

1. ⚠️ **永远不要**提交 `.env` 到 Git
2. ⚠️ **永远不要**在代码中硬编码 Token
3. ⚠️ 定期轮换 Meta Access Token
4. ✅ 使用 System User Token（不是 Personal Token）
5. ✅ 启用 Railway 的环境变量加密
6. ✅ 监控 Railway 日志中的异常请求

---

## 📚 相关文档

- [Meta 转化 API 官方文档](https://developers.facebook.com/docs/marketing-api/conversions-api)
- [Notion API 官方文档](https://developers.notion.com/)
- [SKDK 内部 Facebook 知识库](./META_HELP_KB.md)

---

## 🆘 常见问题

**Q: Token 过期了怎么办？**
A: Personal Token 1-2h 过期，需要定期重新生成。推荐使用 System User Token（永不过期）。

**Q: 为什么我的事件没被 Meta 收到？**
A: 检查 3 件事：
1. Dataset ID 是否正确
2. email 是否是 SHA-256 哈希（小写）
3. action_source 是否是 "system_generated"

**Q: Notion 字段名改了 API 报错怎么办？**
A: 字段名必须**完全匹配**配置中的字段（包括大小写）。修改后需更新代码。

**Q: 如何本地测试 CAPI？**
A: 在 Meta Events Manager → 测试事件 → 获取 test_event_code → 传入 send_event(test_event_code=...)

---

## 📞 联系方式

- **项目负责人**: SKDK Sport 技术团队
- **问题反馈**: support@skdksport.com
- **官方文档**: https://skdksport.com/docs

---

## 📝 许可证

MIT License - SKDK Sport 内部使用

---

**🎉 部署完成后，记得测试完整流程：Lead Form → Notion → CAPI → Meta**
