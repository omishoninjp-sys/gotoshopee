import os
import hashlib
import hmac
import time
import requests
from flask import Flask, redirect, request, jsonify

from config import PARTNER_ID, PARTNER_KEY, HOST, REDIRECT_URL
from shopee_auth import build_auth_url, build_api_url, get_timestamp, generate_sign

app = Flask(__name__)

# 儲存 token（正式環境應該用資料庫）
token_storage = {}


@app.route("/")
def index():
    """首頁"""
    
    if token_storage.get("access_token"):
        status_class = "connected"
        status_text = f"已連接商店 (Shop ID: {token_storage.get('shop_id')})"
        action_html = """
        <a class="btn" href="/shop-info">查看商店資訊</a>
        <a class="btn" href="/auth">重新授權</a>
        """
    else:
        status_class = "disconnected"
        status_text = "尚未授權"
        action_html = '<a class="btn" href="/auth">連接蝦皮商店</a>'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Goyoutati Shopee Sync</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #ee4d2d; color: white; 
                   text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
            .btn:hover {{ background: #d73211; }}
            .status {{ padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .connected {{ background: #d4edda; color: #155724; }}
            .disconnected {{ background: #f8d7da; color: #721c24; }}
        </style>
    </head>
    <body>
        <h1>🛒 Goyoutati Shopee Sync</h1>
        <p>Shopify 商品同步到蝦皮</p>
        
        <div class="status {status_class}">
            <strong>狀態：</strong> {status_text}
        </div>
        
        {action_html}
        
        <hr>
        <p><a href="/debug">Debug 資訊</a> | <a href="/token-status">Token 狀態</a></p>
    </body>
    </html>
    """
    
    return html


@app.route("/debug")
def debug():
    """顯示 debug 資訊"""
    path = "/api/v2/shop/auth_partner"
    timestamp = get_timestamp()
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return jsonify({
        "partner_id": PARTNER_ID,
        "partner_id_type": str(type(PARTNER_ID)),
        "partner_key_length": len(PARTNER_KEY) if PARTNER_KEY else 0,
        "partner_key_first_4": PARTNER_KEY[:4] if PARTNER_KEY and len(PARTNER_KEY) > 4 else "N/A",
        "host": HOST,
        "redirect_url": REDIRECT_URL,
        "timestamp": timestamp,
        "path": path,
        "base_string": base_string,
        "sign": sign,
        "full_auth_url": build_auth_url(REDIRECT_URL)
    })


@app.route("/auth")
def auth():
    """開始 OAuth 授權流程"""
    auth_url = build_auth_url(REDIRECT_URL)
    return redirect(auth_url)


@app.route("/callback")
def callback():
    """處理授權回調"""
    import json
    
    code = request.args.get("code")
    shop_id = request.args.get("shop_id")
    
    if not code or not shop_id:
        return jsonify({
            "error": "Missing code or shop_id",
            "args": dict(request.args)
        }), 400
    
    shop_id = int(shop_id)
    
    path = "/api/v2/auth/token/get"
    timestamp = get_timestamp()
    
    # Public API 簽名格式：partner_id + path + timestamp（不需要 body）
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    body = {
        "code": code,
        "shop_id": shop_id,
        "partner_id": int(PARTNER_ID)
    }
    
    response = requests.post(url, json=body)
    data = response.json()
    
    if "access_token" in data:
        token_storage["access_token"] = data["access_token"]
        token_storage["refresh_token"] = data["refresh_token"]
        token_storage["shop_id"] = shop_id
        token_storage["expire_in"] = data.get("expire_in", 14400)
        return redirect("/?auth=success")
    
    # 顯示 debug 資訊
    return jsonify({
        "error": "Failed to get access token",
        "response": data,
        "debug": {
            "host": HOST,
            "partner_id": PARTNER_ID,
            "partner_key_length": len(PARTNER_KEY),
            "partner_key_first_8": PARTNER_KEY[:8] if len(PARTNER_KEY) > 8 else "N/A",
            "timestamp": timestamp,
            "path": path,
            "base_string": base_string,
            "sign": sign,
            "url": url,
            "body": body
        }
    }), 400


@app.route("/refresh-token")
def refresh_token():
    """刷新 access_token"""
    if not token_storage.get("refresh_token"):
        return jsonify({"error": "No refresh token available"}), 400
    
    path = "/api/v2/auth/access_token/get"
    timestamp = get_timestamp()
    base_string = f"{PARTNER_ID}{path}{timestamp}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&sign={sign}"
    
    body = {
        "refresh_token": token_storage["refresh_token"],
        "shop_id": token_storage["shop_id"],
        "partner_id": int(PARTNER_ID)
    }
    
    response = requests.post(url, json=body)
    data = response.json()
    
    if "access_token" in data:
        token_storage["access_token"] = data["access_token"]
        token_storage["refresh_token"] = data["refresh_token"]
        return jsonify({"message": "Token refreshed", "expire_in": data.get("expire_in")})
    else:
        return jsonify({"error": "Failed to refresh token", "response": data}), 400


@app.route("/token-status")
def token_status():
    """查看 token 狀態"""
    return jsonify({
        "has_access_token": bool(token_storage.get("access_token")),
        "has_refresh_token": bool(token_storage.get("refresh_token")),
        "shop_id": token_storage.get("shop_id"),
        "expire_in": token_storage.get("expire_in")
    })


@app.route("/shop-info")
def shop_info():
    """取得商店資訊"""
    if not token_storage.get("access_token"):
        return jsonify({"error": "Not authorized yet"}), 401
    
    path = "/api/v2/shop/get_shop_info"
    url = build_api_url(
        path,
        access_token=token_storage["access_token"],
        shop_id=token_storage["shop_id"]
    )
    
    response = requests.get(url)
    return jsonify(response.json())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
