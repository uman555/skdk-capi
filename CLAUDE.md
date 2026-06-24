# SKDK CAPI 集成系统

> Meta 开发者文档 + Notion 集成的销售漏斗自动化

## 项目概述
SKDK Sport（skdksport.com）B2B 外贸 - 运动护具 OEM/ODM
将 Notion CRM 中的销售漏斗状态实时同步到 Meta 广告系统，让 Meta 学习期找到更精准的"合格潜在客户"用户。

## 技术栈
- Python 3.10+
- Flask 3.0（Web 框架）
- APScheduler 3.10（定时任务）
- requests（HTTP 客户端）
- pytest + responses（测试）
- Railway.app（部署）
- Gunicorn（WSGI 服务器）

## 项目结构
```
skdk-capi/
├── app.py                  # Flask 主应用（4 个 Webhook + 健康检查）
├── config.py               # 配置（从环境变量读取）
├── capi_client.py          # Meta CAPI 封装
├── notion_client.py        # Notion API 封装
├── scheduler.py            # 每日 23:00 cron
├── requirements.txt        # Python 依赖
├── Procfile               # Railway 部署
├── .env.example           # 环境变量示例
├── .gitignore             # 忽略 .env 等敏感文件
├── README.md              # 完整部署文档
├── CLAUDE.md              # AI 上下文（本文件）
├── docs/
│   └── specs/
│       └── 2026-06-24-skdk-capi-design.md
└── tests/
    ├── test_capi_client.py
    └── test_notion_client.py
```

## 运行方式

### 本地开发
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入真实凭证

# 启动 Web 服务
python app.py
# 启动定时任务（另一个终端）
python scheduler.py

# 运行测试
pytest tests/ -v
```

### Railway 部署
```bash
# 1. 推送到 GitHub
git init
git add .
git commit -m "Initial commit"
git push origin main

# 2. 在 Railway 创建项目（Deploy from GitHub）
# 3. 配置环境变量
# 4. Railway 自动部署（Procfile 决定启动命令）

# 部署 2 个服务：
# - web: gunicorn app:app
# - scheduler: python scheduler.py
```

## 4 个 Webhook 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/webhook/lead-submitted` | POST | 创建新潜在客户（来自 Zapier / Meta Lead Form）|
| `/webhook/status-update` | POST | 状态变化触发 CAPI（来自 Notion Automation）|
| `/api/supplementary` | POST | 手动触发每日补充上传 |
| `/health` | GET | 健康检查 |

## 4 个 CAPI 事件

| Notion 状态 | CAPI 事件名 | 优先级 |
|------------|-----------|--------|
| (新) | `SKDK_Lead_Submitted` | P0 |
| Contacted | `SKDK_Lead_Contacted` | P0 |
| **Qualified** ⭐ | `SKDK_Lead_Qualified` | P0（优化目标）|
| Customer | `SKDK_Purchase` | P0 |
| Lost | (不上报) | - |

## 核心配置

### Notion
- Integration Token（32 字符）
- Database ID（32 字符）
- 必须把数据库分享给 Integration

### Meta
- Dataset ID = Pixel ID
- App ID
- Access Token（推荐 System User Token 永不过期）

### CAPI 规范
- API Version: v25.0
- Endpoint: `https://graph.facebook.com/v25.0/{dataset_id}/events`
- action_source: "system_generated"（不是 "website"）
- email: SHA-256 哈希（小写 64 字符）
- event_id: 唯一（用于去重）

## 关键技术决策

1. **Flask over FastAPI**：更简单，团队 Python 经验
2. **APScheduler over Celery**：不需要 Redis 队列
3. **Personal Token 临时方案 + System User Token 长期方案**
4. **Railway over AWS/GCP**：一键部署，免费
5. **每日 cron 补充上传**：确保 Meta 50 转化数据完整性

## 测试规范
- 单元测试：每个核心函数 ≥2 个用例
- 集成测试：模块间 API 调用
- 测试覆盖率目标：>80%

## 开发规范
- **命名**：Python snake_case
- **类型标注**：必须（type hints）
- **注释**：中英双语
- **错误处理**：try-catch + logging
- **DRY**：重复 3 次提取函数

## 维护 SOP

### 每周
- 检查 `/health` 状态
- 查看 Railway 日志
- 验证 CAPI 事件

### 每月
- 检查 Notion 集成
- 验证 Meta Token
- 分析 CRM 数据质量
- 监控拉黑率

## 相关项目
- **META_HELP_KB.md**: 父级 Meta 知识库（113 节，~6,800 行）
- **facebook-ad-man skill**: Meta 广告管理父 skill

## 更新历史
- **2026-06-24**: v1.0.0 初始版本
  - 4 个 CAPI 事件支持
  - 4 个 Webhook 端点
  - Notion 完整集成
  - 每日 cron 补充上传
  - 完整测试 + 部署文档
