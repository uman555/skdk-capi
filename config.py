"""
SKDK CAPI 集成 - 配置管理
=====================================
从环境变量读取所有凭证，支持 .env 文件（开发）和 Railway 环境变量（生产）。
"""

import os
import logging
from dotenv import load_dotenv

# 加载 .env 文件（如果存在，override=True 确保 .env 优先于系统环境变量）
load_dotenv(override=True)


def get_env(key: str, required: bool = True, default: str = None) -> str:
    """
    从环境变量获取值，可选必填

    Args:
        key: 环境变量名
        required: 是否必填
        default: 默认值

    Returns:
        环境变量值

    Raises:
        ValueError: 必填字段缺失时
    """
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(
            f"❌ 环境变量 {key} 未设置！\n"
            f"   请检查 .env 文件或 Railway 环境变量配置。\n"
            f"   参考 .env.example 文件。"
        )
    return value


# ====================================
# Notion 凭证
# ====================================
NOTION_INTEGRATION_TOKEN = get_env("NOTION_INTEGRATION_TOKEN")
NOTION_DATABASE_ID = get_env("NOTION_DATABASE_ID")
NOTION_API_VERSION = "2022-06-28"
NOTION_BASE_URL = "https://api.notion.com/v1"

# ====================================
# Meta 凭证
# ====================================
META_DATASET_ID = get_env("META_DATASET_ID")
META_APP_ID = get_env("META_APP_ID")
META_ACCESS_TOKEN = get_env("META_ACCESS_TOKEN")
META_API_VERSION = "v25.0"
META_CAPI_BASE_URL = f"https://graph.facebook.com/{META_API_VERSION}/{META_DATASET_ID}/events"

# ====================================
# 应用配置
# ====================================
LOG_LEVEL = get_env("LOG_LEVEL", required=False, default="INFO")
TIMEZONE = get_env("TIMEZONE", required=False, default="Asia/Shanghai")
PORT = int(os.getenv("PORT", 5000))

# ====================================
# 日志配置
# ====================================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("skdk-capi")

# ====================================
# CAPI 事件配置
# ====================================
# Notion 状态 → CAPI 事件映射
STATUS_TO_EVENT = {
    "Contacted": "SKDK_Lead_Contacted",
    "Qualified": "SKDK_Lead_Qualified",  # ⭐ 优化目标
    "Customer": "SKDK_Purchase",
    "Lost": None,  # 流失不发送
}

# 新建记录（首次创建）发送的事件
NEW_LEAD_EVENT = "SKDK_Lead_Submitted"

# CRM 标识（CAPI 必填）
LEAD_EVENT_SOURCE = "Notion_CRM"
EVENT_SOURCE = "crm"
ACTION_SOURCE = "system_generated"
