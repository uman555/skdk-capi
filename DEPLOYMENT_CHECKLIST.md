# 🚀 SKDK CAPI 部署清单

> 你需要做的所有事情 - 按顺序执行

## ✅ 已完成（我可以做的）

```
✅ 1. 完整代码（8 个核心文件 + 2 个测试）
✅ 2. 27 个单元测试全部通过
✅ 3. .env 文件已配置（Notion + Meta 凭证）
✅ 4. Git 仓库初始化 + 首次提交
✅ 5. 部署配置（Procfile + railway.json）
✅ 6. 完整文档（README + 设计文档 + Zapier 模板）
```

## ⏳ 需要你介入（5 件事）

### 🔴 优先级 1: 修复 Notion 集成（5 分钟）

**问题**：你的 Notion Integration 没有分享到数据库

**解决**：
1. 打开 Notion SKDK B2B Leads CRM 数据库
2. 右上角 "..." → "连接" → 添加 "SKDK Notion Integration"
3. ⚠️ 重要：必须是**数据库**，不是页面
4. 把新的 32 位 Database ID 发给我

详细步骤：[setup_notion_sharing.md](./setup_notion_sharing.md)

### 🟡 优先级 2: 推送到 GitHub（5 分钟）

**步骤**：
1. 在 GitHub 创建新仓库 `skdk-capi`
2. 在本地运行：
   ```bash
   cd "e:\claude code项目文件\skdk-capi"
   git remote add origin https://github.com/YOUR-USERNAME/skdk-capi.git
   git branch -M main
   git push -u origin main
   ```
3. 把 GitHub 仓库地址发给我

### 🟢 优先级 3: 部署到 Railway（10 分钟）

**步骤**：
1. 访问 https://railway.app
2. New Project → Deploy from GitHub → 选择 `skdk-capi`
3. 在 Variables 中设置 5 个环境变量（凭证）
4. 添加第二个 service 运行 scheduler
5. 等待部署完成（2-5 分钟）
6. 拿到 Railway 分配的 URL

**Railway 环境变量**（从 .env.example 复制）：
```
NOTION_INTEGRATION_TOKEN=ntn_...
NOTION_DATABASE_ID=...
META_DATASET_ID=1723656532148251
META_APP_ID=1554011292941689
META_ACCESS_TOKEN=...
```

### 🟢 优先级 4: 配置 Zapier（10 分钟）

**Webhook 1: Meta Lead Form → 后端**
1. 登录 https://zapier.com
2. New Zap
3. Trigger: Facebook Lead Ads → New Lead
4. Action: Webhooks by Zapier → POST
5. URL: `https://YOUR-APP.up.railway.app/webhook/lead-submitted`
6. Body: 见 [zapier_templates.md](./zapier_templates.md)

详细模板：[zapier_templates.md](./zapier_templates.md)

### 🟢 优先级 5: 配置 Notion Automation（5 分钟）

**创建 3 个 Automation**（针对 3 个状态）：
1. Status → Contacted → Webhook
2. Status → Qualified → Webhook ⭐
3. Status → Customer → Webhook

**Webhook URL**: `https://YOUR-APP.up.railway.app/webhook/status-update`

## 🧪 完整测试流程（部署后）

```
□ 1. 提交测试 Lead Form
□ 2. 验证 Notion 数据库有新行
□ 3. 验证 Meta Events Manager 有 SKDK_Lead_Submitted
□ 4. 在 Notion 改状态为 Qualified
□ 5. 验证 Meta Events Manager 有 SKDK_Lead_Qualified
□ 6. 在 Notion 改状态为 Customer
□ 7. 验证 Meta Events Manager 有 SKDK_Purchase
```

## ⏰ 时间线

```
你做 优先级 1（Notion 重新分享）     5 分钟
我更新 .env + 重启服务 + 测试       2 分钟
────────── 总计                          7 分钟 ──────────

你做 优先级 2-3（GitHub + Railway）   15 分钟
我等部署完成                          5 分钟
────────── 总计                          20 分钟 ──────────

你做 优先级 4-5（Zapier + Automation） 15 分钟
我等配置完成                          5 分钟
────────── 总计                          20 分钟 ──────────
```

## 📞 随时可以让我帮你

- 更新 .env 凭证
- 调试任何问题
- 优化代码
- 添加新功能
- 生成测试数据

## 🎯 关键提醒

⚠️ **Meta Personal Token 1-2 小时过期**！
   部署到 Railway 后立即换成 System User Token（永不过期）。
   详细步骤见 README.md。

## 🚦 当前状态

| 任务 | 状态 |
|------|------|
| 代码开发 | ✅ 完成 |
| 单元测试 | ✅ 27/27 通过 |
| Git 仓库 | ✅ 已初始化 |
| 部署配置 | ✅ 已就绪 |
| 本地服务测试 | ⚠️ 需要 Notion 重新分享 |
| Railway 部署 | ⏳ 等待你 |
| Webhook 配置 | ⏳ 等待你 |
| 完整流程测试 | ⏳ 等待你 |

## 💬 当前状态

我已经完成所有能自动完成的部分。现在等你：
1. 重新分享 Notion Integration 到数据库（拿到新的 Database ID 发我）
2. 推送到 GitHub
3. 部署到 Railway

按顺序完成这些后，整个 SKDK CAPI 集成系统就能完全上线！
