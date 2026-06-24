# 设计文档：SKDK CAPI 集成系统

## 概述
将 Notion CRM 中的潜在客户销售漏斗状态实时同步到 Meta 广告系统，让 Meta 学习期找到更精准的"合格潜在客户"用户。

## 功能范围

### P0（必须）
- ✅ 接收新潜在客户数据 → 创建 Notion 记录 + 发送 CAPI `SKDK_Lead_Submitted`
- ✅ 接收状态变化 → 发送对应 CAPI 事件
- ✅ 4 个 CAPI 事件映射：
  - Contacted → `SKDK_Lead_Contacted`
  - Qualified → `SKDK_Lead_Qualified` ⭐ 优化目标
  - Customer → `SKDK_Purchase`
  - Lost → (不上报)
- ✅ SHA-256 哈希邮箱
- ✅ 事件去重（event_id）
- ✅ 健康检查

### P1（重要）
- ✅ 每日 23:00 补充上传（Cron Job）
- ✅ 手动触发补充上传 API
- ✅ Notion 操作封装（CRUD）
- ✅ 完整错误处理 + 日志

### P2（可选，未来）
- ⏳ OAuth 2.0 授权流程
- ⏳ 批量发送优化
- ⏳ 实时仪表盘
- ⏳ 邮件/Slack 告警

## 架构概要

### 技术栈
- **后端框架**: Python 3.10+ Flask 3.0
- **HTTP 客户端**: requests
- **定时任务**: APScheduler (BlockingScheduler)
- **部署平台**: Railway.app
- **WSGI 服务器**: Gunicorn
- **测试**: pytest + responses

### 模块结构
```
app.py                  # Flask 主应用 + 4 个 Webhook
├── config.py           # 配置管理
├── capi_client.py      # Meta CAPI 封装
│   ├── hash_email()    # SHA-256 邮箱哈希
│   ├── build_event_id()# 事件去重 ID
│   └── CAPIClient      # 主客户端
│       ├── send_event() # 单事件
│       ├── send_batch() # 批量
│       └── test_event()# 测试
└── notion_client.py    # Notion API 封装
    └── NotionClient
        ├── create_lead()
        ├── update_status()
        ├── get_leads_by_status()
        └── health_check()
```

### 数据流
```
Notion Lead Form → Zapier → POST /webhook/lead-submitted
                              ↓
                          Notion.create_lead()
                              ↓
                          CAPI.send_event("SKDK_Lead_Submitted")

Notion Status Change → Notion Automation → POST /webhook/status-update
                              ↓
                          Notion.update_status()
                              ↓
                          CAPI.send_event("SKDK_Lead_<Status>")
```

## 数据模型

### Notion 数据库字段
| 字段 | 类型 | 必填 | 用途 |
|------|------|------|------|
| Name | title | ✅ | 客户姓名 |
| Email | email | ✅ | CAPI 哈希后发送 |
| Phone | phone | - | 销售联系 |
| Company | rich_text | - | 公司名 |
| Country | select | - | 国家/地区 |
| Business Type | select | - | 客户类型 |
| Monthly Volume | select | - | 月采购量 |
| Product Interest | multi_select | - | 产品兴趣 |
| Status | select | ✅ | 销售阶段 |
| Status Updated At | date | - | 状态更新时间 |
| Source | select | - | 来源 |
| Lead Value | number | - | 预估订单价值 |
| Notes | rich_text | - | 销售备注 |
| Created At | date | - | 创建时间 |

### CAPI Payload 模板
```json
{
  "data": [{
    "event_name": "SKDK_Lead_Qualified",
    "event_time": 1234567890,
    "action_source": "system_generated",
    "user_data": {
      "em": ["sha256_hashed_email"]
    },
    "custom_data": {
      "event_source": "crm",
      "lead_event_source": "Notion_CRM"
    },
    "event_id": "page_id_event_name_timestamp"
  }],
  "access_token": "..."
}
```

## 用户流程

### 流程 1：新潜在客户创建
```
1. 用户提交 Meta Lead Form
2. Zapier 触发 Webhook → POST /webhook/lead-submitted
3. 后端调用 Notion.create_lead() → 返回 page_id
4. 后端调用 CAPI.send_event("SKDK_Lead_Submitted")
5. Meta 接收事件
6. 返回 200 OK 给 Zapier
```

### 流程 2：状态变化
```
1. 销售在 Notion 修改状态：Contacted → Qualified
2. Notion Automation 触发 Webhook → POST /webhook/status-update
   (data: {page_id, new_status, email})
3. 后端调用 Notion.update_status()（确认状态）
4. 后端调用 CAPI.send_event("SKDK_Lead_Qualified") ⭐ 优化目标
5. Meta 接收事件
6. 返回 200 OK
```

### 流程 3：每日补充
```
1. 每天 23:00 cron 触发
2. 拉取所有非 Lost 状态的潜在客户
3. 对每个潜在客户发送对应 CAPI 事件
4. 记录日志
```

## 错误与边界

| 场景 | 处理 |
|------|------|
| Token 401 错误 | 记录警告 + 不重试（需要人工续期）|
| CAPI 400 错误 | 记录详细错误 + 标记 + 继续下一个 |
| Notion 404 错误 | 记录 + 返回 500 |
| Notion 401 错误 | 记录 + 立即通知管理员 |
| 网络错误 | 记录 + 返回 500 |
| 邮箱为空 | 跳过 + 记录警告 |
| event_id 重复 | Meta 自动去重 |

## 部署

### Railway 环境变量
- `NOTION_INTEGRATION_TOKEN`
- `NOTION_DATABASE_ID`
- `META_DATASET_ID`
- `META_APP_ID`
- `META_ACCESS_TOKEN`
- `LOG_LEVEL=INFO`
- `TIMEZONE=Asia/Shanghai`

### 启动命令
```bash
# Web 服务
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60

# 定时任务
python scheduler.py
```

## 方案对比

### 方案 A（已选）：Flask + APScheduler
- ✅ 简单：单一语言、单一框架
- ✅ 部署简单：Railway 一键部署
- ✅ 维护成本低
- ⚠️ 实时性一般（webhook + cron）

### 方案 B：FastAPI + Celery
- ⚠️ 复杂：需要 Redis 作为消息队列
- ❌ 部署成本高

### 方案 C：Node.js + Bull
- ⚠️ 需要学习 TypeScript
- ❌ 团队 Python 经验更丰富

**选 A** ✅

## 时间线

| 阶段 | 任务 | 时间 |
|------|------|------|
| Day 1 | 创建 Notion 数据库 + Meta 凭证 | 30 分钟 |
| Day 1 | 部署到 Railway | 30 分钟 |
| Day 2 | 配置 Zapier 接收 Lead Form | 30 分钟 |
| Day 2 | 配置 Notion Automation 状态变化 | 30 分钟 |
| Day 3 | 测试完整流程 | 1 小时 |
| Day 7+ | 50 转化数据后启用"合格潜在客户"成效目标 | 自动 |

## 监控指标

- ✅ CAPI 事件发送成功率（目标 >95%）
- ✅ Notion API 响应时间（目标 <2秒）
- ✅ Token 有效期（Token 即将过期时告警）
- ✅ 每日补充上传执行情况
- ✅ 拉黑率（<5%）
