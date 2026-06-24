# Notion 集成重新分享指南

> 修复 SKDK CAPI 集成的 Notion 访问问题

## 🔍 问题诊断

```
当前 NOTION_DATABASE_ID（无效）：
389cae2a-241f-80a7-a772-eaedd8757b42 (这是 page_id)

正确的 database_id（需获取）：
未知 - 你的数据库是内嵌的，Integration 还没分享到
```

## 📋 你需要做的（3 步，5 分钟）

### Step 1: 在 Notion 中打开 SKDK B2B Leads CRM

直接在 Notion 中打开你的数据库页面。

### Step 2: 把 Integration 添加到数据库（不是页面）

```
1. 在数据库页面，右上角 "..."（三个点/更多）
2. 菜单中找 "连接" / "Connections" / "Add connections"
3. 搜索 "SKDK Notion Integration"
4. 点击 → 确认添加
5. ✅ 应该看到 "SKDK Notion Integration" 显示在连接列表中
```

**重要**：必须添加到**数据库**，不是页面。如果你之前只添加到了页面，请重新添加。

### Step 3: 获取真正的 Database ID

```
方法 A: 复制数据库链接
1. 在数据库页面，右上角 "..." → "复制链接" / "Copy link"
2. 粘贴到文本编辑器
3. URL 格式：https://www.notion.so/workspace/[DATABASE_ID]?v=...
4. [DATABASE_ID] 就是 32 位字符串
5. ⚠️ 去掉所有连字符 (-)

方法 B: 通过父级关系
1. 在 Notion 中，数据库在 "页面" 内部
2. 找到真正的数据库（不是页面）
3. URL 中的 32 位 ID

如果方法 A 和 B 都失败：
- 联系 Notion 客服询问内嵌数据库的 ID 获取方式
- 或考虑将数据库移到独立页面（推荐）
```

## 📝 获得 Database ID 后告诉我

把 32 位字符串（去掉连字符）发给我，我会：
1. 更新 .env 文件
2. 重新启动服务
3. 重新测试完整 CAPI 流程
4. 发送测试事件到 Meta

## 💡 临时变通方案

如果你现在没时间重新分享，可以：
- ✅ 继续测试 CAPI 发送（这不依赖 Notion）
- ✅ 在 Meta 端验证事件是否接收
- ✅ 准备 Railway 部署
- ⏸️ 暂停 Notion 集成的完整测试

## 🔄 已有的临时方案

我已经让代码支持两种 Notion ID 模式：
- **Database ID 模式**（推荐）：直接访问数据库
- **Page ID 模式**（临时）：创建子页面（但只能设置 title）

如果 Database ID 暂时无法获取，我们可以先用 Page ID 模式跑通 CAPI 发送，但需要在 Notion UI 中手动完善其他字段。

## 🎯 最佳路径

1. **你**重新分享 Notion Integration 到数据库 + 给我 Database ID（5 分钟）
2. **我**立即更新 .env + 重新测试 + 部署 Railway
3. **完成**整个 CAPI 集成系统上线

需要我帮你做其他的吗？
