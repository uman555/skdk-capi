"""
SKDK CAPI 集成 - Flask 主应用
=====================================
Webhooks:
1. /webhook/lead-submitted   - 创建新潜在客户（来自 Zapier / Meta Lead Form）
2. /webhook/status-update     - 状态变化（来自 Notion Automation）
3. /api/supplementary        - 手动触发每日补充上传
4. /health                    - 健康检查
"""

from flask import Flask, request, jsonify
import logging

from config import (
    NEW_LEAD_EVENT,
    STATUS_TO_EVENT,
    logger,
    PORT,
)
from capi_client import CAPIClient
from notion_client import NotionClient

# ====================================
# 初始化 Flask + 客户端
# ====================================
app = Flask(__name__)
capi = CAPIClient()
notion = NotionClient()


# ====================================
# Webhook 1: 创建新潜在客户
# ====================================
@app.route("/webhook/lead-submitted", methods=["POST"])
def lead_submitted():
    """
    接收来自 Zapier / Meta Lead Form 的新潜在客户数据
    流程：
    1. 在 Notion 创建记录（状态 = Contacted）
    2. 发送 CAPI SKDK_Lead_Submitted 事件
    """
    try:
        data = request.get_json(force=True)
        logger.info(f"📥 收到新 Lead Form 提交: {data.get('email', 'unknown')}")

        # 必填字段验证
        if not data.get("email"):
            return jsonify({"error": "email is required"}), 400

        # Step 1: 在 Notion 创建记录
        page_id = notion.create_lead(data)

        # Step 2: 发送 CAPI SKDK_Lead_Submitted 事件
        capi_result = capi.send_event(
            event_name=NEW_LEAD_EVENT,
            email=data["email"],
            lead_id=page_id,
        )

        return jsonify({
            "success": True,
            "notion_page_id": page_id,
            "capi_result": capi_result,
            "message": f"Lead {data['email']} 已创建并提交 CAPI 事件"
        }), 200

    except Exception as e:
        logger.error(f"❌ lead-submitted 处理失败: {e}")
        return jsonify({"error": str(e)}), 500


# ====================================
# Webhook 2: 状态变化
# ====================================
@app.route("/webhook/status-update", methods=["POST"])
def status_update():
    """
    接收 Notion Automation 的状态变化通知
    流程：
    1. 根据新状态 → 找到对应的 CAPI 事件
    2. 发送 CAPI 事件
    """
    try:
        data = request.get_json(force=True)
        page_id = data.get("page_id")
        new_status = data.get("new_status")
        email = data.get("email")

        logger.info(f"📥 收到状态更新: {page_id} → {new_status}")

        # 验证必填字段
        if not page_id or not new_status:
            return jsonify({"error": "page_id and new_status are required"}), 400

        # 查找对应的 CAPI 事件
        event_name = STATUS_TO_EVENT.get(new_status)
        if not event_name:
            logger.info(f"⏭️ 跳过状态 {new_status}（不发送 CAPI 事件）")
            return jsonify({
                "success": True,
                "skipped": True,
                "reason": f"No CAPI event for status {new_status}"
            }), 200

        # 如果没传 email，从 Notion 读取
        if not email:
            email = notion.get_email_by_page_id(page_id)
            if not email:
                return jsonify({"error": "email not provided and not found in Notion"}), 400

        # 发送 CAPI 事件
        capi_kwargs = {
            "event_name": event_name,
            "email": email,
            "lead_id": page_id,
        }

        # Purchase 事件需要 value
        if new_status == "Customer" and data.get("value"):
            capi_kwargs["value"] = float(data["value"])

        capi_result = capi.send_event(**capi_kwargs)

        return jsonify({
            "success": True,
            "page_id": page_id,
            "new_status": new_status,
            "event_sent": event_name,
            "capi_result": capi_result,
        }), 200

    except Exception as e:
        logger.error(f"❌ status-update 处理失败: {e}")
        return jsonify({"error": str(e)}), 500


# ====================================
# API: 手动触发每日补充上传
# ====================================
@app.route("/api/supplementary", methods=["POST"])
def supplementary_upload():
    """
    手动触发每日补充上传
    流程：
    1. 获取最近 1 天的所有潜在客户
    2. 根据状态发送对应的 CAPI 事件
    """
    try:
        data = request.get_json(silent=True) or {}
        days = data.get("days", 1)
        logger.info(f"🔄 手动触发补充上传（最近 {days} 天）")

        results = {"submitted": 0, "contacted": 0, "qualified": 0, "purchased": 0, "errors": []}

        for status, event_name in STATUS_TO_EVENT.items():
            if not event_name:
                continue

            # 获取该状态的最近记录
            leads = notion.get_leads_by_status(status, limit=100)

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
                        if status == "Contacted":
                            results["contacted"] += 1
                        elif status == "Qualified":
                            results["qualified"] += 1
                        elif status == "Customer":
                            results["purchased"] += 1
                except Exception as e:
                    results["errors"].append(f"{page_id}: {str(e)}")

        logger.info(f"✅ 补充上传完成: {results}")
        return jsonify(results), 200

    except Exception as e:
        logger.error(f"❌ 补充上传失败: {e}")
        return jsonify({"error": str(e)}), 500


# ====================================
# 健康检查
# ====================================
@app.route("/health", methods=["GET"])
def health():
    """
    健康检查
    """
    notion_health = notion.health_check()
    return jsonify({
        "status": "healthy" if notion_health else "degraded",
        "notion": "ok" if notion_health else "failed",
        "service": "skdk-capi-integration",
        "version": "1.0.0",
    }), 200 if notion_health else 503


# ====================================
# 根路径
# ====================================
@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "service": "SKDK CAPI Integration",
        "version": "1.0.0",
        "endpoints": {
            "POST /webhook/lead-submitted": "Create new lead from Meta Lead Form",
            "POST /webhook/status-update": "Update lead status and send CAPI event",
            "POST /api/supplementary": "Manually trigger daily supplementary upload",
            "GET /health": "Health check",
        }
    }), 200


# ====================================
# 错误处理
# ====================================
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"❌ Internal server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


# ====================================
# 启动
# ====================================
if __name__ == "__main__":
    logger.info("🚀 SKDK CAPI 集成服务启动")
    logger.info(f"   端口: {PORT}")
    logger.info(f"   端点: /webhook/lead-submitted, /webhook/status-update, /api/supplementary, /health")
    app.run(host="0.0.0.0", port=PORT, debug=False)
