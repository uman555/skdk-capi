"""
SKDK CAPI 集成 - 定时任务
=====================================
每天 23:00 自动运行补充上传
（确保 Meta 学习期 50 转化数据完整性）
"""

import logging
import sys
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    STATUS_TO_EVENT,
    TIMEZONE,
    logger,
)
from capi_client import CAPIClient
from notion_client import NotionClient

# ====================================
# 初始化客户端
# ====================================
capi = CAPIClient()
notion = NotionClient()


def daily_supplementary_upload():
    """
    每日 23:00 自动运行
    流程：
    1. 拉取 Notion 中所有"非 Lost"状态的潜在客户
    2. 根据状态发送对应的 CAPI 事件
    3. 记录日志
    """
    logger.info("🔄 每日 23:00 补充上传任务启动")

    results = {
        "date": None,
        "total": 0,
        "submitted": 0,
        "errors": [],
    }

    try:
        from datetime import datetime
        results["date"] = datetime.now().strftime("%Y-%m-%d")

        for status, event_name in STATUS_TO_EVENT.items():
            if not event_name:
                continue

            # 获取该状态的所有潜在客户
            leads = notion.get_leads_by_status(status, limit=100)
            results["total"] += len(leads)

            for lead in leads:
                try:
                    page_id = lead["id"]
                    email_prop = lead.get("properties", {}).get("Email", {})
                    email = email_prop.get("email")
                    if not email:
                        continue

                    capi_kwargs = {
                        "event_name": event_name,
                        "email": email,
                        "lead_id": page_id,
                    }

                    if status == "Customer":
                        value_prop = lead.get("properties", {}).get("Lead Value", {})
                        value = value_prop.get("number", 0)
                        if value:
                            capi_kwargs["value"] = value

                    result = capi.send_event(**capi_kwargs)

                    if "error" not in result:
                        results["submitted"] += 1
                except Exception as e:
                    error_msg = f"{page_id}: {str(e)}"
                    results["errors"].append(error_msg)
                    logger.error(f"❌ 补充上传失败 {error_msg}")

        logger.info(f"✅ 每日补充上传完成: {results}")

    except Exception as e:
        logger.error(f"❌ 每日补充上传任务异常: {e}")
        results["errors"].append(str(e))

    return results


def main():
    """
    启动定时任务调度器
    """
    scheduler = BlockingScheduler(timezone=TIMEZONE)

    # 每天 23:00 触发
    scheduler.add_job(
        daily_supplementary_upload,
        CronTrigger(hour=23, minute=0),
        id="daily_capi_upload",
        name="Daily CAPI Supplementary Upload",
        replace_existing=True,
    )

    logger.info(f"🚀 SKDK CAPI 定时任务启动（时区: {TIMEZONE}）")
    logger.info("📅 每日 23:00 触发补充上传")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 定时任务停止")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
