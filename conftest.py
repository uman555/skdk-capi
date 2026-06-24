"""
测试配置文件 - 在所有测试运行前设置必需的环境变量
"""

import os

# 在导入任何模块前设置测试环境变量
os.environ.setdefault("NOTION_INTEGRATION_TOKEN", "test_notion_token_12345")
os.environ.setdefault("NOTION_DATABASE_ID", "test_database_id_12345")
os.environ.setdefault("META_DATASET_ID", "123456789")
os.environ.setdefault("META_APP_ID", "123456789")
os.environ.setdefault("META_ACCESS_TOKEN", "test_meta_token_12345")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("TIMEZONE", "UTC")
