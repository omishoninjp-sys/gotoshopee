import os
import hashlib
import hmac
import time
import requests
from flask import Flask, redirect, request, jsonify

from config import PARTNER_ID, PARTNER_KEY, HOST, REDIRECT_URL, SHOPEE_REGIONS, SIZE_CHART_URL, is_clothing_product
from shopee_auth import build_auth_url, build_api_url, get_timestamp, generate_sign

app = Flask(__name__)

# 儲存 token（正式環境應該用資料庫）
# 結構：{ "TW": { "access_token": ..., "shop_id": ... }, "TH": { ... } }
token_storage = {}

# 當前選擇的站點
current_region = "TW"

def get_current_token():
    """取得當前站點的 token"""
    return token_storage.get(current_region, {})

def set_current_token(data):
    """設定當前站點的 token"""
    token_storage[current_region] = data


@app.route("/")
def index():
    """首頁"""
    global current_region
    
    # 如果有 region 參數，切換站點
    if request.args.get("region"):
        current_region = request.args.get("region")
    
    current_token = get_current_token()
    region_info = SHOPEE_REGIONS.get(current_region, {})
    
    if current_token.get("access_token"):
        status_class = "connected"
        status_text = f"已連接商店 (Shop ID: {current_token.get('shop_id')})"
        action_html = """
        <a class="btn" href="/sync">🔄 商品同步測試</a>
        <a class="btn" href="/shop-info">查看商店資訊</a>
        <a class="btn" href="/auth">重新授權</a>
        """
    else:
        status_class = "disconnected"
        status_text = "尚未授權"
        action_html = '<a class="btn" href="/auth">連接蝦皮商店</a>'
    
    # 建立站點選擇按鈕
    region_buttons = ""
    for code, info in SHOPEE_REGIONS.items():
        token = token_storage.get(code, {})
        is_current = code == current_region
        has_token = bool(token.get("access_token"))
        
        btn_class = "region-btn"
        if is_current:
            btn_class += " active"
        if has_token:
            btn_class += " connected"
        
        # 使用中文名稱
        display_name = info.get("name_zh", info.get("name", ""))
        region_buttons += f'<a href="/?region={code}" class="{btn_class}">{info["flag"]} {display_name}</a>'
    
    # 顯示已授權的商店列表
    shop_list = ""
    for code, token in token_storage.items():
        if token.get("access_token"):
            info = SHOPEE_REGIONS.get(code, {})
            display_name = info.get("name_zh", info.get("name", ""))
            shop_list += f'<div class="shop-item">{info.get("flag", "")} {display_name}: Shop ID {token.get("shop_id")}</div>'
    
    if not shop_list:
        shop_list = '<div class="shop-item">尚無已授權商店</div>'
    
    # 當前站點顯示名稱
    current_display_name = region_info.get("name_zh", region_info.get("name", ""))
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Goyoutati Shopee Sync</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 50px auto; padding: 20px; }}
            .btn {{ display: inline-block; padding: 10px 20px; background: #ee4d2d; color: white; 
                   text-decoration: none; border-radius: 5px; margin: 10px 5px; }}
            .btn:hover {{ background: #d73211; }}
            .status {{ padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .connected {{ background: #d4edda; color: #155724; }}
            .disconnected {{ background: #f8d7da; color: #721c24; }}
            
            .region-selector {{ margin: 20px 0; padding: 15px; background: #f8f9fa; border-radius: 8px; }}
            .region-selector h3 {{ margin-top: 0; }}
            .region-btn {{ display: inline-block; padding: 8px 15px; margin: 5px; background: #e9ecef; 
                          color: #333; text-decoration: none; border-radius: 5px; border: 2px solid transparent; }}
            .region-btn:hover {{ background: #dee2e6; }}
            .region-btn.active {{ border-color: #ee4d2d; background: #fff; }}
            .region-btn.connected {{ position: relative; }}
            .region-btn.connected::after {{ content: "✓"; position: absolute; top: -5px; right: -5px; 
                                           background: #28a745; color: white; border-radius: 50%; 
                                           width: 18px; height: 18px; font-size: 12px; line-height: 18px; text-align: center; }}
            
            .shop-list {{ margin: 20px 0; padding: 15px; background: #fff; border: 1px solid #ddd; border-radius: 8px; }}
            .shop-item {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
            .shop-item:last-child {{ border-bottom: none; }}
        </style>
    </head>
    <body>
        <h1>🛒 Goyoutati Shopee Sync</h1>
        <p>Shopify 商品同步到蝦皮（多站點支援）</p>
        
        <div class="region-selector">
            <h3>🌏 選擇站點</h3>
            {region_buttons}
        </div>
        
        <div class="status {status_class}">
            <strong>狀態：</strong> {region_info.get('flag', '')} {current_display_name} - {status_text}
        </div>
        
        {action_html}
        
        <div class="shop-list">
            <h3>📋 已授權商店</h3>
            {shop_list}
        </div>
        
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
        # 儲存到當前選擇的站點
        token_storage[current_region] = {
            "access_token": data["access_token"],
            "refresh_token": data["refresh_token"],
            "shop_id": shop_id,
            "expire_in": data.get("expire_in", 14400)
        }
        return redirect("/?auth=success")
    
    # 顯示 debug 資訊
    return jsonify({
        "error": "Failed to get access token",
        "response": data,
        "current_region": current_region,
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
    current_token = get_current_token()
    if not current_token.get("refresh_token"):
        return jsonify({"error": "No refresh token available", "region": current_region}), 400
    
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
        "refresh_token": current_token["refresh_token"],
        "shop_id": current_token["shop_id"],
        "partner_id": int(PARTNER_ID)
    }
    
    response = requests.post(url, json=body)
    data = response.json()
    
    if "access_token" in data:
        token_storage[current_region]["access_token"] = data["access_token"]
        token_storage[current_region]["refresh_token"] = data["refresh_token"]
        return jsonify({"message": "Token refreshed", "region": current_region, "expire_in": data.get("expire_in")})
    else:
        return jsonify({"error": "Failed to refresh token", "response": data}), 400


@app.route("/token-status")
def token_status():
    """查看 token 狀態"""
    current_token = get_current_token()
    all_regions = {}
    for code, token in token_storage.items():
        all_regions[code] = {
            "has_token": bool(token.get("access_token")),
            "shop_id": token.get("shop_id")
        }
    
    return jsonify({
        "current_region": current_region,
        "has_access_token": bool(current_token.get("access_token")),
        "has_refresh_token": bool(current_token.get("refresh_token")),
        "shop_id": current_token.get("shop_id"),
        "all_regions": all_regions,
        "expire_in": current_token.get("expire_in")
    })


@app.route("/shop-info")
def shop_info():
    """取得商店資訊"""
    current_token = get_current_token()
    if not current_token.get("access_token"):
        return jsonify({"error": "Not authorized yet", "region": current_region}), 401
    
    path = "/api/v2/shop/get_shop_info"
    url = build_api_url(
        path,
        access_token=current_token["access_token"],
        shop_id=current_token["shop_id"]
    )
    
    response = requests.get(url)
    return jsonify(response.json())


# ==================== 商品同步功能 ====================

@app.route("/sync")
def sync_page():
    """商品同步測試頁面"""
    current_token = get_current_token()
    if not current_token.get("access_token"):
        return redirect("/auth")
    
    region_info = SHOPEE_REGIONS.get(current_region, {})
    region_flag = region_info.get('flag', '')
    region_name = region_info.get('name_zh', region_info.get('name', ''))  # 優先使用中文名稱
    shop_id = current_token.get('shop_id', '')
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>商品同步測試 - Goyoutati</title>
        <meta charset="utf-8">
        <style>
            * { box-sizing: border-box; }
            body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }
            h1 { color: #ee4d2d; }
            .btn { display: inline-block; padding: 10px 20px; background: #ee4d2d; color: white; 
                   text-decoration: none; border-radius: 5px; margin: 5px; cursor: pointer; border: none; font-size: 14px; }
            .btn:hover { background: #d73211; }
            .btn:disabled { background: #ccc; cursor: not-allowed; }
            .btn-secondary { background: #6c757d; }
            .btn-success { background: #28a745; }
            .btn-warning { background: #ffc107; color: #000; }
            .section { background: white; border: 1px solid #ddd; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .section h3 { margin-top: 0; border-bottom: 2px solid #ee4d2d; padding-bottom: 10px; color: #333; }
            .log-box { background: #1e1e1e; color: #fff; border: none; padding: 15px; border-radius: 5px;
                       max-height: 500px; overflow-y: auto; font-family: 'Consolas', monospace; font-size: 13px; 
                       white-space: pre-wrap; line-height: 1.5; }
            .success { color: #4ade80; }
            .error { color: #f87171; }
            .warning { color: #fbbf24; }
            .info { color: #60a5fa; }
            .dim { color: #888; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { border: 1px solid #ddd; padding: 10px; text-align: left; }
            th { background: #f8f9fa; }
            select, input { padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
            select { min-width: 200px; }
            .status-box { padding: 12px; margin: 10px 0; border-radius: 5px; }
            .status-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
            .status-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
            .status-info { background: #cce5ff; color: #004085; border: 1px solid #b8daff; }
            .status-warning { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
            .checkbox-group { max-height: 300px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; border-radius: 5px; }
            .checkbox-item { padding: 8px; border-bottom: 1px solid #eee; display: flex; align-items: center; }
            .checkbox-item:last-child { border-bottom: none; }
            .checkbox-item input { margin-right: 10px; transform: scale(1.2); }
            .checkbox-item label { flex: 1; cursor: pointer; }
            .badge { display: inline-block; padding: 2px 8px; border-radius: 3px; font-size: 12px; margin-left: 5px; }
            .badge-custom { background: #17a2b8; color: white; }
            .badge-smart { background: #6f42c1; color: white; }
            .step-indicator { display: inline-block; width: 28px; height: 28px; background: #ee4d2d; color: white; 
                             border-radius: 50%; text-align: center; line-height: 28px; margin-right: 10px; font-weight: bold; }
            .loading-spinner { display: inline-block; width: 20px; height: 20px; border: 3px solid #f3f3f3;
                              border-top: 3px solid #ee4d2d; border-radius: 50%; animation: spin 1s linear infinite; margin-left: 10px; }
            @keyframes spin { 0%% { transform: rotate(0deg); } 100%% { transform: rotate(360deg); } }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
            .progress-bar { width: 100%%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
            .progress-fill { height: 100%%; background: linear-gradient(90deg, #ee4d2d, #ff6b35); transition: width 0.3s; }
            .collapse-btn { background: none; border: none; color: #ee4d2d; cursor: pointer; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>🔄 商品同步測試 """ + region_flag + " " + region_name + """</h1>
        <p><a href="/" class="btn btn-secondary">← 返回首頁</a> <span style="margin-left: 15px; color: #666;">Shop ID: """ + str(shop_id) + """</span></p>
        
        <!-- Step 1: 連線測試 -->
        <div class="section">
            <h3><span class="step-indicator">1</span>連線測試</h3>
            <div class="grid-2">
                <div>
                    <button class="btn" onclick="testShopify()">🛍️ 測試 Shopify</button>
                    <div id="shopify-status"></div>
                </div>
                <div>
                    <button class="btn" onclick="testShopee()">🦐 測試蝦皮</button>
                    <div id="shopee-status"></div>
                </div>
            </div>
        </div>
        
        <!-- Step 2: 蝦皮分類 -->
        <div class="section">
            <h3><span class="step-indicator">2</span>選擇蝦皮分類</h3>
            <button class="btn" onclick="loadCategories()">載入分類</button>
            <div id="category-status"></div>
            <div id="category-select" style="display:none; margin-top: 15px;">
                <label><strong>主分類：</strong></label>
                <select id="shopee-category" onchange="onCategoryChange()">
                    <option value="">-- 請選擇 --</option>
                </select>
                <br><br>
                <label><strong>子分類：</strong></label>
                <select id="shopee-subcategory" style="display:none;">
                    <option value="">-- 請選擇子分類 --</option>
                </select>
                <div id="selected-category-info" class="status-box status-info" style="display:none;"></div>
            </div>
        </div>
        
        <!-- Step 3: 物流渠道 -->
        <div class="section">
            <h3><span class="step-indicator">3</span>物流設定</h3>
            <button class="btn" onclick="loadLogistics()">載入物流渠道</button>
            <div id="logistics-status"></div>
            <div id="logistics-list" style="display:none; margin-top: 15px;">
                <p>選擇要啟用的物流渠道：</p>
                <div id="logistics-checkboxes" class="checkbox-group"></div>
            </div>
        </div>
        
        <!-- Step 4: Shopify 系列 -->
        <div class="section">
            <h3><span class="step-indicator">4</span>選擇 Shopify 系列</h3>
            <button class="btn" onclick="loadCollections()">載入系列列表</button>
            <div id="collections-status"></div>
            <div id="collections-list" style="display:none; margin-top: 15px;">
                <p>⚠️ 每個系列只會同步 <strong>1 個商品</strong>（測試用）</p>
                <div id="collections-checkboxes" class="checkbox-group"></div>
                <div style="margin-top: 10px;">
                    <button class="btn btn-secondary" onclick="selectAllCollections()">全選</button>
                    <button class="btn btn-secondary" onclick="deselectAllCollections()">取消全選</button>
                </div>
            </div>
        </div>
        
        <!-- Step 4.5: 價格設定 -->
        <div class="section">
            <h3><span class="step-indicator">💰</span>價格設定</h3>
            <p>計算公式：<strong>Shopify 價格 × 匯率 × 加成比例 = 台幣售價</strong></p>
            <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
                <div>
                    <label><strong>匯率 (JPY → TWD)：</strong></label><br>
                    <input type="number" id="exchange-rate" value="0.21" step="0.01" min="0.01" style="width: 100px;">
                </div>
                <div>
                    <label><strong>加成比例：</strong></label><br>
                    <input type="number" id="markup-rate" value="1.3" step="0.01" min="1" style="width: 100px;">
                </div>
                <div>
                    <label><strong>最低價格 (NT$)：</strong></label><br>
                    <input type="number" id="min-price" value="1500" step="100" min="0" style="width: 100px;">
                </div>
                <div>
                    <label><strong>範例計算：</strong></label><br>
                    <span id="price-example">¥1,000 → NT$273</span>
                </div>
            </div>
            <p style="margin-top: 10px; color: #666;">
                <small>⚠️ 低於最低價格的商品將自動跳過不上架</small>
            </p>
            <script>
                function updatePriceExample() {
                    const rate = parseFloat(document.getElementById('exchange-rate').value) || 0.21;
                    const markup = parseFloat(document.getElementById('markup-rate').value) || 1.3;
                    const example = Math.round(1000 * rate * markup);
                    document.getElementById('price-example').textContent = '¥1,000 → NT$' + example;
                }
                document.getElementById('exchange-rate').addEventListener('input', updatePriceExample);
                document.getElementById('markup-rate').addEventListener('input', updatePriceExample);
            </script>
        </div>
        
        <!-- Step 4.6: 備貨設定 -->
        <div class="section">
            <h3><span class="step-indicator">📦</span>備貨設定</h3>
            <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
                <div>
                    <label style="cursor: pointer;">
                        <input type="checkbox" id="pre-order" checked onchange="toggleDaysToShip()">
                        <strong>較長備貨</strong>
                    </label>
                </div>
                <div id="days-to-ship-container">
                    <label><strong>備貨天數：</strong></label>
                    <input type="number" id="days-to-ship" value="4" min="1" max="15" style="width: 60px;">
                    <span>天</span>
                </div>
            </div>
            <p style="margin-top: 10px; color: #666;">
                <small>✅ 較長備貨：代購商品建議開啟，備貨時間可設 1-15 天</small><br>
                <small>❌ 不勾選：一般商品，需在 1-3 個工作日內出貨</small>
            </p>
            <script>
                function toggleDaysToShip() {
                    const preOrder = document.getElementById('pre-order').checked;
                    const container = document.getElementById('days-to-ship-container');
                    container.style.opacity = preOrder ? '1' : '0.5';
                    document.getElementById('days-to-ship').disabled = !preOrder;
                }
            </script>
        </div>
        
        <!-- Step 5: 執行同步 -->
        <div class="section">
            <h3><span class="step-indicator">5</span>執行同步</h3>
            <div id="sync-summary" class="status-box status-warning" style="display:none;"></div>
            
            <div style="display: flex; gap: 15px; flex-wrap: wrap; align-items: center;">
                <button class="btn" onclick="startSync(1)" id="test-btn" style="font-size: 14px; padding: 12px 20px; background: #6c757d;">
                    🧪 測試同步 (每系列1個)
                </button>
                <button class="btn btn-success" onclick="startSync(250)" id="sync-btn" style="font-size: 16px; padding: 15px 30px;">
                    🚀 全部上架
                </button>
                <button class="btn btn-warning" onclick="updatePrices()" id="price-btn" style="font-size: 14px; padding: 12px 20px;">
                    💰 更新價格
                </button>
                <div>
                    <label>每系列上限：</label>
                    <input type="number" id="sync-limit" value="250" min="1" max="250" style="width: 70px;">
                </div>
            </div>
            
            <p style="margin-top: 10px;">
                <small>🧪 測試同步：每個系列只同步 1 個商品（用於測試）</small><br>
                <small>🚀 全部上架：同步所有選中系列的全部商品（新商品上架，已存在商品自動更新價格）</small><br>
                <small>💰 更新價格：只更新選中系列已存在商品的價格（不會新增商品）</small>
            </p>
            
            <div id="sync-progress" style="display:none;">
                <div class="progress-bar"><div class="progress-fill" id="progress-fill" style="width: 0%;"></div></div>
                <div id="progress-text">準備中...</div>
            </div>
        </div>
        
        <!-- 同步日誌 -->
        <div class="section">
            <h3>📋 同步日誌</h3>
            <button class="btn btn-secondary" onclick="clearLog()">清除</button>
            <button class="btn btn-secondary" onclick="copyLog()">複製</button>
            <div id="sync-log" class="log-box">等待開始...
</div>
        </div>
        
        <!-- Debug 資訊 -->
        <div class="section">
            <h3>🔧 Debug 資訊 <button class="collapse-btn" onclick="toggleDebug()">[顯示/隱藏]</button></h3>
            <div id="debug-info" class="log-box" style="display:none; background: #f8f9fa; color: #333;"></div>
        </div>

        <script>
            // 全域變數
            let allCategories = [];
            let allLogistics = [];
            let selectedCategoryId = null;
            
            // ====== 日誌函數 ======
            function log(message, type = 'info') {
                const logBox = document.getElementById('sync-log');
                const time = new Date().toLocaleTimeString();
                logBox.innerHTML += '<span class="' + type + '">[' + time + '] ' + message + '</span>\\n';
                logBox.scrollTop = logBox.scrollHeight;
            }
            
            function clearLog() {
                document.getElementById('sync-log').innerHTML = '';
            }
            
            function copyLog() {
                const logText = document.getElementById('sync-log').innerText;
                navigator.clipboard.writeText(logText);
                alert('已複製到剪貼簿');
            }
            
            function debug(data) {
                document.getElementById('debug-info').textContent = JSON.stringify(data, null, 2);
            }
            
            function toggleDebug() {
                const el = document.getElementById('debug-info');
                el.style.display = el.style.display === 'none' ? 'block' : 'none';
            }
            
            function updateProgress(current, total, text) {
                const percent = Math.round((current / total) * 100);
                document.getElementById('progress-fill').style.width = percent + '%';
                document.getElementById('progress-text').textContent = text || (current + '/' + total + ' (' + percent + '%)');
            }
            
            // ====== Step 1: 連線測試 ======
            async function testShopify() {
                log('測試 Shopify 連線...', 'info');
                const statusEl = document.getElementById('shopify-status');
                statusEl.innerHTML = '<div class="status-box status-info">連線中...<span class="loading-spinner"></span></div>';
                
                try {
                    const res = await fetch('/api/shopify/test');
                    const data = await res.json();
                    debug(data);
                    
                    if (data.success) {
                        log('✅ Shopify 連線成功: ' + data.shop_name, 'success');
                        statusEl.innerHTML = '<div class="status-box status-success">✅ ' + data.shop_name + '<br><small>' + data.domain + '</small></div>';
                    } else {
                        log('❌ Shopify 連線失敗: ' + data.error, 'error');
                        statusEl.innerHTML = '<div class="status-box status-error">❌ ' + data.error + '</div>';
                    }
                } catch (e) {
                    log('❌ 請求失敗: ' + e.message, 'error');
                    statusEl.innerHTML = '<div class="status-box status-error">❌ 網路錯誤: ' + e.message + '</div>';
                }
            }
            
            async function testShopee() {
                log('測試蝦皮連線...', 'info');
                const statusEl = document.getElementById('shopee-status');
                statusEl.innerHTML = '<div class="status-box status-info">連線中...<span class="loading-spinner"></span></div>';
                
                try {
                    const res = await fetch('/shop-info');
                    const data = await res.json();
                    debug(data);
                    
                    // 檢查兩種可能的回應格式
                    const shopInfo = data.response || data;
                    
                    if (shopInfo.shop_name && shopInfo.error === '') {
                        log('✅ 蝦皮連線成功: ' + shopInfo.shop_name, 'success');
                        statusEl.innerHTML = '<div class="status-box status-success">✅ ' + shopInfo.shop_name + '<br><small>地區: ' + shopInfo.region + ' | 狀態: ' + shopInfo.status + '</small></div>';
                    } else if (data.error && data.error !== '') {
                        log('❌ 蝦皮連線失敗: ' + (data.message || data.error), 'error');
                        statusEl.innerHTML = '<div class="status-box status-error">❌ ' + (data.message || data.error) + '</div>';
                    } else {
                        log('⚠️ 蝦皮回應異常', 'warning');
                        statusEl.innerHTML = '<div class="status-box status-warning">⚠️ 回應異常，請查看 Debug</div>';
                    }
                } catch (e) {
                    log('❌ 請求失敗: ' + e.message, 'error');
                    statusEl.innerHTML = '<div class="status-box status-error">❌ 網路錯誤: ' + e.message + '</div>';
                }
            }
            
            // ====== Step 2: 分類 ======
            async function loadCategories() {
                log('載入蝦皮分類...', 'info');
                const statusEl = document.getElementById('category-status');
                statusEl.innerHTML = '<div class="status-box status-info">載入中...<span class="loading-spinner"></span></div>';
                
                try {
                    const res = await fetch('/api/shopee/categories');
                    const data = await res.json();
                    debug(data);
                    
                    if (data.success) {
                        allCategories = data.categories;
                        log('✅ 載入 ' + allCategories.length + ' 個分類', 'success');
                        
                        const select = document.getElementById('shopee-category');
                        select.innerHTML = '<option value="">-- 請選擇 --</option>';
                        
                        // 只顯示頂層分類（沒有 parent 或 parent 為 0）
                        const topCategories = allCategories.filter(function(c) { return !c.parent_category_id || c.parent_category_id === 0; });
                        topCategories.forEach(function(cat) {
                            const name = cat.display_category_name || cat.original_category_name;
                            select.innerHTML += '<option value="' + cat.category_id + '">' + name + '</option>';
                        });
                        
                        document.getElementById('category-select').style.display = 'block';
                        statusEl.innerHTML = '<div class="status-box status-success">✅ 載入 ' + topCategories.length + ' 個主分類</div>';
                    } else {
                        log('❌ 載入分類失敗: ' + data.error, 'error');
                        statusEl.innerHTML = '<div class="status-box status-error">❌ ' + data.error + '</div>';
                    }
                } catch (e) {
                    log('❌ 請求失敗: ' + e.message, 'error');
                    statusEl.innerHTML = '<div class="status-box status-error">❌ 網路錯誤: ' + e.message + '</div>';
                }
            }
            
            function onCategoryChange() {
                const mainSelect = document.getElementById('shopee-category');
                const subSelect = document.getElementById('shopee-subcategory');
                const infoBox = document.getElementById('selected-category-info');
                const mainCatId = parseInt(mainSelect.value);
                
                if (!mainCatId) {
                    subSelect.style.display = 'none';
                    infoBox.style.display = 'none';
                    selectedCategoryId = null;
                    return;
                }
                
                // 找子分類
                const subCategories = allCategories.filter(function(c) { return c.parent_category_id === mainCatId; });
                
                if (subCategories.length > 0) {
                    subSelect.innerHTML = '<option value="">-- 請選擇子分類 --</option>';
                    subCategories.forEach(function(cat) {
                        const name = cat.display_category_name || cat.original_category_name;
                        subSelect.innerHTML += '<option value="' + cat.category_id + '">' + name + '</option>';
                    });
                    subSelect.style.display = 'inline-block';
                    subSelect.onchange = function() {
                        selectedCategoryId = parseInt(this.value) || mainCatId;
                        updateCategoryInfo();
                    };
                    selectedCategoryId = mainCatId;
                } else {
                    subSelect.style.display = 'none';
                    selectedCategoryId = mainCatId;
                }
                
                updateCategoryInfo();
            }
            
            function updateCategoryInfo() {
                const infoBox = document.getElementById('selected-category-info');
                if (selectedCategoryId) {
                    const cat = allCategories.find(function(c) { return c.category_id === selectedCategoryId; });
                    const name = cat ? (cat.display_category_name || cat.original_category_name) : selectedCategoryId;
                    infoBox.innerHTML = '✅ 已選擇分類：<strong>' + name + '</strong> (ID: ' + selectedCategoryId + ')';
                    infoBox.style.display = 'block';
                    log('選擇分類: ' + name + ' (ID: ' + selectedCategoryId + ')', 'info');
                } else {
                    infoBox.style.display = 'none';
                }
                updateSyncSummary();
            }
            
            // ====== Step 3: 物流 ======
            async function loadLogistics() {
                log('載入物流渠道...', 'info');
                const statusEl = document.getElementById('logistics-status');
                statusEl.innerHTML = '<div class="status-box status-info">載入中...<span class="loading-spinner"></span></div>';
                
                try {
                    const res = await fetch('/api/shopee/logistics');
                    const data = await res.json();
                    debug(data);
                    
                    if (data.success) {
                        allLogistics = data.logistics;
                        log('✅ 載入 ' + allLogistics.length + ' 個物流渠道', 'success');
                        
                        const container = document.getElementById('logistics-checkboxes');
                        container.innerHTML = '';
                        
                        allLogistics.forEach(function(lg) {
                            const enabled = lg.enabled ? '可用' : '不可用';
                            const checked = lg.enabled ? 'checked' : '';
                            const disabled = lg.enabled ? '' : 'disabled';
                            container.innerHTML += '<div class="checkbox-item"><input type="checkbox" id="lg-' + lg.logistics_channel_id + '" value="' + lg.logistics_channel_id + '" ' + checked + ' ' + disabled + '><label for="lg-' + lg.logistics_channel_id + '">' + lg.logistics_channel_name + ' <small style="color: ' + (lg.enabled ? 'green' : 'red') + '">(' + enabled + ')</small></label></div>';
                        });
                        
                        document.getElementById('logistics-list').style.display = 'block';
                        statusEl.innerHTML = '<div class="status-box status-success">✅ 載入 ' + allLogistics.length + ' 個物流渠道</div>';
                    } else {
                        log('❌ 載入物流失敗: ' + data.error, 'error');
                        statusEl.innerHTML = '<div class="status-box status-error">❌ ' + data.error + '</div>';
                    }
                } catch (e) {
                    log('❌ 請求失敗: ' + e.message, 'error');
                    statusEl.innerHTML = '<div class="status-box status-error">❌ 網路錯誤: ' + e.message + '</div>';
                }
            }
            
            function getSelectedLogistics() {
                const checked = document.querySelectorAll('#logistics-checkboxes input:checked');
                return Array.from(checked).map(function(el) { return parseInt(el.value); });
            }
            
            // ====== Step 4: 系列 ======
            async function loadCollections() {
                log('載入 Shopify 系列...', 'info');
                const statusEl = document.getElementById('collections-status');
                statusEl.innerHTML = '<div class="status-box status-info">載入中...<span class="loading-spinner"></span></div>';
                
                try {
                    const res = await fetch('/api/shopify/collections');
                    const data = await res.json();
                    debug(data);
                    
                    if (data.success) {
                        const collections = data.collections;
                        log('✅ 載入 ' + collections.length + ' 個系列', 'success');
                        
                        const container = document.getElementById('collections-checkboxes');
                        container.innerHTML = '';
                        
                        collections.forEach(function(col) {
                            const badgeClass = col.type === 'smart' ? 'badge-smart' : 'badge-custom';
                            const badgeText = col.type === 'smart' ? '智慧' : '手動';
                            container.innerHTML += '<div class="checkbox-item"><input type="checkbox" id="col-' + col.id + '" value="' + col.id + '" data-title="' + col.title + '"><label for="col-' + col.id + '">' + col.title + ' <span class="badge ' + badgeClass + '">' + badgeText + '</span></label></div>';
                        });
                        
                        // 添加 change 事件監聽
                        container.querySelectorAll('input').forEach(function(input) {
                            input.addEventListener('change', updateSyncSummary);
                        });
                        
                        document.getElementById('collections-list').style.display = 'block';
                        statusEl.innerHTML = '<div class="status-box status-success">✅ 載入 ' + collections.length + ' 個系列</div>';
                    } else {
                        log('❌ 載入系列失敗: ' + data.error, 'error');
                        statusEl.innerHTML = '<div class="status-box status-error">❌ ' + data.error + '</div>';
                    }
                } catch (e) {
                    log('❌ 請求失敗: ' + e.message, 'error');
                    statusEl.innerHTML = '<div class="status-box status-error">❌ 網路錯誤: ' + e.message + '</div>';
                }
            }
            
            function selectAllCollections() {
                document.querySelectorAll('#collections-checkboxes input').forEach(function(el) { el.checked = true; });
                updateSyncSummary();
            }
            
            function deselectAllCollections() {
                document.querySelectorAll('#collections-checkboxes input').forEach(function(el) { el.checked = false; });
                updateSyncSummary();
            }
            
            function getSelectedCollections() {
                const checked = document.querySelectorAll('#collections-checkboxes input:checked');
                return Array.from(checked).map(function(el) {
                    return { id: el.value, title: el.dataset.title };
                });
            }
            
            function updateSyncSummary() {
                const summaryEl = document.getElementById('sync-summary');
                const collections = getSelectedCollections();
                const logistics = getSelectedLogistics();
                
                if (collections.length === 0) {
                    summaryEl.style.display = 'none';
                    return;
                }
                
                let html = '<strong>同步摘要：</strong><br>';
                html += '• 分類：' + (selectedCategoryId ? '已選擇 (ID: ' + selectedCategoryId + ')' : '⚠️ 未選擇') + '<br>';
                html += '• 物流：' + logistics.length + ' 個渠道<br>';
                html += '• 系列：' + collections.length + ' 個（將同步 ' + collections.length + ' 個商品）';
                
                summaryEl.innerHTML = html;
                summaryEl.style.display = 'block';
            }
            
            // ====== Step 5: 執行同步 ======
            async function startSync(defaultLimit) {
                const collections = getSelectedCollections();
                const logistics = getSelectedLogistics();
                
                // 使用傳入的 limit 或從輸入框讀取
                const limit = defaultLimit || parseInt(document.getElementById('sync-limit').value) || 250;
                const isTestMode = (limit === 1);
                
                // 每批處理的商品數量（避免超時，每個商品需上傳多張圖片）
                const batchSize = 1;
                
                // 驗證
                if (!selectedCategoryId) {
                    alert('請先選擇蝦皮分類！');
                    return;
                }
                
                if (logistics.length === 0) {
                    alert('請先選擇至少一個物流渠道！');
                    return;
                }
                
                if (collections.length === 0) {
                    alert('請先選擇要同步的系列！');
                    return;
                }
                
                // 全部上架前確認
                if (!isTestMode) {
                    const confirmMsg = '確定要同步 ' + collections.length + ' 個系列的所有商品？\\n\\n商品將直接上架到蝦皮商店！\\n（每批處理 ' + batchSize + ' 個商品，避免超時）';
                    if (!confirm(confirmMsg)) {
                        return;
                    }
                }
                
                // 讀取價格設定
                const exchangeRate = parseFloat(document.getElementById('exchange-rate').value) || 0.21;
                const markupRate = parseFloat(document.getElementById('markup-rate').value) || 1.05;
                const minPrice = parseInt(document.getElementById('min-price').value) || 1000;
                
                // 讀取備貨設定
                const preOrder = document.getElementById('pre-order').checked;
                const daysToShip = parseInt(document.getElementById('days-to-ship').value) || 4;
                
                const testBtn = document.getElementById('test-btn');
                const syncBtn = document.getElementById('sync-btn');
                testBtn.disabled = true;
                syncBtn.disabled = true;
                syncBtn.textContent = '同步中...';
                
                document.getElementById('sync-progress').style.display = 'block';
                
                const modeText = isTestMode ? '測試同步' : '全部上架';
                log('========== 開始' + modeText + ' ==========', 'info');
                log('模式: ' + modeText + ' (每系列上限: ' + limit + ', 每批: ' + batchSize + ')', 'dim');
                log('分類 ID: ' + selectedCategoryId, 'dim');
                log('物流渠道: ' + logistics.join(', '), 'dim');
                log('匯率: ' + exchangeRate + ' | 加成: ' + markupRate + ' | 最低價格: NT$' + minPrice, 'dim');
                log('較長備貨: ' + (preOrder ? '是 (' + daysToShip + '天)' : '否'), 'dim');
                log('系列數量: ' + collections.length, 'dim');
                log('', 'info');
                
                let totalSuccess = 0;
                let totalFail = 0;
                
                for (let i = 0; i < collections.length; i++) {
                    const col = collections[i];
                    updateProgress(i + 1, collections.length, '處理中: ' + col.title);
                    
                    log('[' + (i+1) + '/' + collections.length + '] 處理系列: ' + col.title, 'info');
                    
                    // 系列級別的計數器
                    let seriesSuccess = 0;
                    let seriesFail = 0;
                    
                    // 分批處理（每批 1 個商品）
                    let offset = 0;
                    let hasMore = true;
                    
                    while (hasMore && offset < limit) {
                        const currentBatchSize = Math.min(batchSize, limit - offset);
                        
                        try {
                            const res = await fetch('/api/sync/collection', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    collection_id: col.id,
                                    collection_title: col.title,
                                    category_id: selectedCategoryId,
                                    logistic_ids: logistics,
                                    exchange_rate: exchangeRate,
                                    markup_rate: markupRate,
                                    min_price: minPrice,
                                    pre_order: preOrder,
                                    days_to_ship: daysToShip,
                                    limit: currentBatchSize,
                                    offset: offset
                                })
                            });
                            
                            const data = await res.json();
                            debug(data);
                            
                            if (data.results && data.results.length > 0) {
                                const results = data.results;
                                const successItems = results.filter(r => r.success && !r.skipped && !r.price_updated);
                                const priceUpdatedItems = results.filter(r => r.success && r.price_updated);
                                const skippedItems = results.filter(r => r.success && r.skipped && !r.low_price);
                                const lowPriceItems = results.filter(r => r.low_price);
                                const japaneseItems = results.filter(r => r.has_japanese);
                                const failItems = results.filter(r => !r.success && !r.low_price && !r.has_japanese);
                                
                                totalSuccess += successItems.length + priceUpdatedItems.length;
                                totalFail += failItems.length;
                                seriesSuccess += successItems.length + priceUpdatedItems.length + skippedItems.length;
                                seriesFail += failItems.length;
                                
                                successItems.forEach(function(r) {
                                    log('  ✅ ' + r.title + ' NT$' + r.price + ' (ID: ' + r.shopee_item_id + ')', 'success');
                                });
                                
                                priceUpdatedItems.forEach(function(r) {
                                    log('  💰 ' + r.title + ' (ID: ' + r.shopee_item_id + ') 價格已更新', 'info');
                                });
                                
                                skippedItems.forEach(function(r) {
                                    log('  ⏭️ ' + r.title + ' (已存在，跳過)', 'warning');
                                });
                                
                                lowPriceItems.forEach(function(r) {
                                    log('  💸 ' + r.title + ' NT$' + r.price + ' (低於最低價格，跳過)', 'dim');
                                });
                                
                                japaneseItems.forEach(function(r) {
                                    log('  🈂️ ' + r.title + ' (商品名為日文，請重新同步商品或翻譯)', 'warning');
                                });
                                
                                failItems.forEach(function(r) {
                                    log('  ❌ ' + r.title + ': ' + r.error, 'error');
                                });
                                
                                // 如果返回的商品數量少於請求的，表示沒有更多了
                                if (results.length < currentBatchSize) {
                                    hasMore = false;
                                }
                            } else if (data.results && data.results.length === 0) {
                                // 沒有更多商品
                                hasMore = false;
                            } else {
                                log('  ❌ 失敗: ' + (data.error || 'Unknown error'), 'error');
                                hasMore = false;
                            }
                            
                        } catch (e) {
                            log('  ❌ 請求錯誤: ' + e.message, 'error');
                            hasMore = false;
                        }
                        
                        offset += currentBatchSize;
                        
                        // 批次間延遲
                        if (hasMore) {
                            await new Promise(function(r) { setTimeout(r, 500); });
                        }
                    }
                    
                    log('  📊 系列小計: 成功 ' + seriesSuccess + ' / 失敗 ' + seriesFail, 'dim');
                    
                    log('', 'info');
                    
                    // 系列間延遲
                    await new Promise(function(r) { setTimeout(r, 1000); });
                }
                
                log('========== 同步完成 ==========', 'info');
                log('總計成功: ' + totalSuccess + ' 個商品 / 失敗: ' + totalFail, totalSuccess > 0 ? 'success' : 'error');
                
                testBtn.disabled = false;
                syncBtn.disabled = false;
                document.getElementById('price-btn').disabled = false;
                syncBtn.textContent = '🚀 全部上架';
                updateProgress(collections.length, collections.length, '完成！');
            }
            
            // ====== 更新價格功能 ======
            async function updatePrices() {
                const collections = getSelectedCollections();
                const logistics = getSelectedLogistics();
                
                // 驗證
                if (!selectedCategoryId) {
                    alert('請先選擇蝦皮分類！');
                    return;
                }
                
                if (collections.length === 0) {
                    alert('請先選擇要更新價格的系列！');
                    return;
                }
                
                const confirmMsg = '確定要更新 ' + collections.length + ' 個系列的商品價格？\\n\\n這會比對 Shopify 和蝦皮的商品，更新已存在商品的價格。';
                if (!confirm(confirmMsg)) {
                    return;
                }
                
                // 讀取價格設定
                const exchangeRate = parseFloat(document.getElementById('exchange-rate').value) || 0.21;
                const markupRate = parseFloat(document.getElementById('markup-rate').value) || 1.05;
                
                const testBtn = document.getElementById('test-btn');
                const syncBtn = document.getElementById('sync-btn');
                const priceBtn = document.getElementById('price-btn');
                testBtn.disabled = true;
                syncBtn.disabled = true;
                priceBtn.disabled = true;
                priceBtn.textContent = '更新中...';
                
                document.getElementById('sync-progress').style.display = 'block';
                
                log('========== 開始更新價格 ==========', 'info');
                log('匯率: ' + exchangeRate + ' | 加成: ' + markupRate + ' (價格乘數: ' + (exchangeRate * markupRate).toFixed(4) + ')', 'dim');
                log('系列數量: ' + collections.length, 'dim');
                log('', 'info');
                
                let totalUpdated = 0;
                let totalSkipped = 0;
                let totalFail = 0;
                
                for (let i = 0; i < collections.length; i++) {
                    const col = collections[i];
                    updateProgress(i + 1, collections.length, '處理中: ' + col.title);
                    
                    log('[' + (i+1) + '/' + collections.length + '] 處理系列: ' + col.title, 'info');
                    
                    try {
                        const res = await fetch('/api/sync/update-prices', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                collection_id: col.id,
                                collection_title: col.title,
                                exchange_rate: exchangeRate,
                                markup_rate: markupRate
                            })
                        });
                        
                        const data = await res.json();
                        debug(data);
                        
                        if (data.success && data.results) {
                            const results = data.results;
                            
                            results.forEach(function(r) {
                                if (r.updated) {
                                    totalUpdated++;
                                    log('  💰 ' + r.title + ' (ID: ' + r.shopee_item_id + ') ' + r.old_price + ' → ' + r.new_price, 'success');
                                } else if (r.skipped) {
                                    totalSkipped++;
                                    log('  ⏭️ ' + r.title + ' (價格相同，跳過)', 'dim');
                                } else if (r.not_found) {
                                    totalSkipped++;
                                    log('  ⚠️ ' + r.title + ' (蝦皮找不到此商品)', 'warning');
                                } else if (r.error) {
                                    totalFail++;
                                    log('  ❌ ' + r.title + ': ' + r.error, 'error');
                                }
                            });
                            
                            log('  📊 系列小計: 更新 ' + results.filter(r => r.updated).length + ' / 跳過 ' + results.filter(r => r.skipped || r.not_found).length, 'dim');
                        } else {
                            log('  ❌ 失敗: ' + (data.error || 'Unknown error'), 'error');
                        }
                        
                    } catch (e) {
                        log('  ❌ 請求錯誤: ' + e.message, 'error');
                    }
                    
                    log('', 'info');
                    
                    // 系列間延遲
                    await new Promise(function(r) { setTimeout(r, 1000); });
                }
                
                log('========== 價格更新完成 ==========', 'info');
                log('總計更新: ' + totalUpdated + ' / 跳過: ' + totalSkipped + ' / 失敗: ' + totalFail, totalUpdated > 0 ? 'success' : 'warning');
                
                testBtn.disabled = false;
                syncBtn.disabled = false;
                priceBtn.disabled = false;
                priceBtn.textContent = '💰 更新價格';
                updateProgress(collections.length, collections.length, '完成！');
            }
        </script>
    </body>
    </html>
    """
    return html


# ==================== API 路由 ====================

@app.route("/api/shopify/test")
def api_shopify_test():
    """測試 Shopify 連線"""
    from shopify_api import ShopifyAPI
    
    shopify = ShopifyAPI()
    result = shopify.test_connection()
    return jsonify(result)


@app.route("/api/shopify/collections")
def api_shopify_collections():
    """獲取 Shopify 系列"""
    from shopify_api import ShopifyAPI
    
    shopify = ShopifyAPI()
    collections = shopify.get_all_collections()
    
    return jsonify({
        "success": True,
        "collections": collections,
        "count": len(collections)
    })


@app.route("/api/shopify/products/<collection_id>")
def api_shopify_products(collection_id):
    """獲取系列中的商品"""
    from shopify_api import ShopifyAPI
    
    limit = request.args.get("limit", 1, type=int)
    
    shopify = ShopifyAPI()
    result = shopify.get_products_in_collection(collection_id, limit=limit)
    
    if result.get("success"):
        return jsonify({
            "success": True,
            "products": result.get("data", {}).get("products", [])
        })
    else:
        return jsonify(result)


@app.route("/api/shopee/categories")
def api_shopee_categories():
    """獲取蝦皮分類"""
    if not get_current_token().get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopee_product import get_categories
    
    result = get_categories(
        get_current_token()["access_token"],
        get_current_token()["shop_id"]
    )
    
    return jsonify(result)


@app.route("/api/shopee/logistics")
def api_shopee_logistics():
    """獲取蝦皮物流"""
    if not get_current_token().get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopee_product import get_logistics
    
    result = get_logistics(
        get_current_token()["access_token"],
        get_current_token()["shop_id"]
    )
    
    return jsonify(result)


@app.route("/api/sync/collection", methods=["POST"])
def api_sync_collection():
    """同步一個系列的商品"""
    if not get_current_token().get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopify_api import ShopifyAPI
    from shopee_product import upload_image, create_product, shopify_to_shopee_product, get_attributes, find_country_of_origin_attribute
    
    data = request.json
    collection_id = data.get("collection_id")
    collection_title = data.get("collection_title", "")  # 系列名稱
    category_id = data.get("category_id")
    logistic_ids = data.get("logistic_ids", [])
    exchange_rate = data.get("exchange_rate", 0.21)  # 匯率
    markup_rate = data.get("markup_rate", 1.05)  # 加成比例
    min_price = data.get("min_price", 0)  # 最低價格限制
    pre_order = data.get("pre_order", True)  # 是否較長備貨
    days_to_ship = data.get("days_to_ship", 4)  # 備貨天數
    limit = data.get("limit", 1)
    offset = data.get("offset", 0)  # 分頁偏移量
    
    # 取得當前站點的語言
    region_info = SHOPEE_REGIONS.get(current_region, {})
    target_lang = region_info.get("lang", "zh-TW")
    
    debug_info = {
        "collection_id": collection_id,
        "collection_title": collection_title,
        "category_id": category_id,
        "logistic_ids": logistic_ids,
        "exchange_rate": exchange_rate,
        "markup_rate": markup_rate,
        "min_price": min_price,
        "pre_order": pre_order,
        "days_to_ship": days_to_ship,
        "target_lang": target_lang,
        "limit": limit,
        "offset": offset,
        "steps": [],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    results = []
    
    try:
        # 0. 先查詢分類屬性，找到產地屬性
        debug_info["steps"].append("Step 0: 查詢分類屬性")
        attrs_result = get_attributes(
            get_current_token()["access_token"],
            get_current_token()["shop_id"],
            category_id
        )
        
        country_origin_attr = None
        if attrs_result.get("success"):
            attributes = attrs_result.get("attributes", [])
            debug_info["attributes_count"] = len(attributes)
            country_origin_attr = find_country_of_origin_attribute(attributes)
            
            if country_origin_attr:
                debug_info["steps"].append(f"  ✅ 找到產地屬性 (ID: {country_origin_attr.get('attribute_id')})")
                debug_info["country_origin_attr"] = country_origin_attr
            else:
                debug_info["steps"].append("  ⚠️ 未找到產地屬性，將嘗試不帶屬性創建")
        else:
            debug_info["steps"].append(f"  ⚠️ 查詢屬性失敗: {attrs_result.get('error')}")
        
        # 1. 獲取 Shopify 商品
        debug_info["steps"].append("Step 1: 獲取 Shopify 商品")
        shopify = ShopifyAPI()
        # 獲取足夠多的商品（offset + limit），然後切片
        fetch_limit = offset + limit
        products_result = shopify.get_products_in_collection(collection_id, limit=fetch_limit)
        
        debug_info["shopify_api_response"] = {
            "success": products_result.get("success"),
            "error": products_result.get("error"),
            "status_code": products_result.get("status_code")
        }
        
        if not products_result.get("success"):
            debug_info["steps"].append(f"  ❌ 失敗: {products_result.get('error')}")
            return jsonify({
                "success": False,
                "error": "無法獲取 Shopify 商品: " + str(products_result.get("error")),
                "debug": debug_info
            })
        
        products = products_result.get("data", {}).get("products", [])
        total_products = len(products)
        debug_info["total_products_fetched"] = total_products
        
        # 應用 offset 切片
        products = products[offset:offset + limit]
        debug_info["products_count"] = len(products)
        debug_info["steps"].append(f"  ✅ 獲取到 {total_products} 個商品，處理 offset {offset} 起的 {len(products)} 個")
        
        if not products:
            return jsonify({
                "success": True,
                "results": [],
                "message": "沒有更多商品",
                "debug": debug_info
            })
        
        # 2. 處理每個商品
        for idx, product in enumerate(products):
            product_debug = {
                "shopify_id": product.get("id"),
                "title": product.get("title"),
                "handle": product.get("handle"),  # 加入 handle 以便 debug
                "variants_count": len(product.get("variants", [])),
                "images_count": len(product.get("images", []))
            }
            
            product_result = {
                "shopify_id": product.get("id"),
                "title": product.get("title"),
                "handle": product.get("handle"),  # 加入 handle
                "success": False,
                "shopee_item_id": None,
                "error": None,
                "debug": product_debug
            }
            
            try:
                debug_info["steps"].append(f"Step 2.{idx+1}: 處理商品 - {product.get('title')} (handle: {product.get('handle')})")
                
                # 2a. 檢查商品名稱是否包含日文（平假名或片假名）
                import re
                title = product.get("title", "")
                # 平假名: \u3040-\u309F, 片假名: \u30A0-\u30FF
                if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', title):
                    product_result["has_japanese"] = True
                    product_result["success"] = False
                    debug_info["steps"].append(f"  🈂️ 商品名稱含有日文，請重新同步商品或翻譯")
                    results.append(product_result)
                    continue
                
                # 2b. 計算價格，檢查是否低於最低價格
                variants = product.get("variants", [])
                calculated_price = 100
                if variants:
                    shopify_price = float(variants[0].get("price", 0))
                    calculated_price = round(shopify_price * exchange_rate * markup_rate)
                
                product_result["price"] = calculated_price
                
                if min_price > 0 and calculated_price < min_price:
                    product_result["low_price"] = True
                    product_result["success"] = False
                    debug_info["steps"].append(f"  💸 價格 NT${calculated_price} 低於最低價格 NT${min_price}，跳過")
                    results.append(product_result)
                    continue
                
                # 2c. 檢查圖片
                images = product.get("images", [])
                image_urls = [img.get("src") for img in images if img.get("src")]
                product_debug["image_urls"] = image_urls[:3]  # 只記錄前3個
                
                if not image_urls:
                    product_result["error"] = "商品沒有圖片"
                    debug_info["steps"].append("  ❌ 商品沒有圖片")
                    results.append(product_result)
                    continue
                
                debug_info["steps"].append(f"  找到 {len(image_urls)} 張圖片")
                
                # 2d. 上傳圖片到蝦皮
                image_ids = []
                image_upload_results = []
                
                for i, img_url in enumerate(image_urls[:9]):  # 蝦皮最多 9 張
                    debug_info["steps"].append(f"  上傳圖片 {i+1}/{min(len(image_urls), 9)}...")
                    
                    upload_result = upload_image(
                        get_current_token()["access_token"],
                        get_current_token()["shop_id"],
                        img_url
                    )
                    
                    image_upload_results.append({
                        "index": i,
                        "success": upload_result.get("success"),
                        "image_id": upload_result.get("image_id"),
                        "error": upload_result.get("error")
                    })
                    
                    if upload_result.get("success"):
                        image_id = upload_result.get("image_id")
                        if image_id:
                            image_ids.append(image_id)
                            debug_info["steps"].append(f"    ✅ 成功 (ID: {image_id})")
                    else:
                        debug_info["steps"].append(f"    ❌ 失敗: {upload_result.get('error')}")
                
                product_debug["image_uploads"] = image_upload_results
                
                if not image_ids:
                    product_result["error"] = "沒有成功上傳任何圖片"
                    debug_info["steps"].append("  ❌ 所有圖片上傳都失敗了")
                    results.append(product_result)
                    continue
                
                debug_info["steps"].append(f"  成功上傳 {len(image_ids)} 張圖片")
                
                # 2d-2. 檢測是否為衣服類商品，自動加上尺碼表
                product_tags = product.get("tags", "").split(",") if product.get("tags") else []
                product_tags = [t.strip() for t in product_tags]
                
                if SIZE_CHART_URL and is_clothing_product(product.get("title", ""), collection_title, product_tags):
                    debug_info["steps"].append("  📏 檢測到衣服類商品，上傳尺碼表...")
                    
                    # 檢查是否還有圖片空間（蝦皮最多 9 張）
                    if len(image_ids) < 9:
                        size_chart_result = upload_image(
                            get_current_token()["access_token"],
                            get_current_token()["shop_id"],
                            SIZE_CHART_URL
                        )
                        
                        if size_chart_result.get("success"):
                            size_chart_id = size_chart_result.get("image_id")
                            if size_chart_id:
                                image_ids.append(size_chart_id)
                                debug_info["steps"].append(f"    ✅ 尺碼表上傳成功 (ID: {size_chart_id})")
                        else:
                            debug_info["steps"].append(f"    ⚠️ 尺碼表上傳失敗: {size_chart_result.get('error')}")
                    else:
                        debug_info["steps"].append("    ⚠️ 圖片已達上限(9張)，跳過尺碼表")
                
                # 2c. 轉換商品格式
                debug_info["steps"].append("  轉換商品格式...")
                if target_lang != "zh-TW":
                    debug_info["steps"].append(f"  翻譯成 {target_lang}...")
                
                shopee_product_data = shopify_to_shopee_product(
                    product,
                    category_id,
                    image_ids,
                    collection_title,  # 傳遞系列名稱
                    country_origin_attr,  # 傳遞產地屬性
                    exchange_rate,  # 匯率
                    markup_rate,  # 加成比例
                    pre_order,  # 是否較長備貨
                    days_to_ship,  # 備貨天數
                    target_lang  # 目標語言
                )
                
                # 更新物流設定
                if logistic_ids:
                    shopee_product_data["logistic_info"] = [
                        {"logistic_id": lid, "enabled": True}
                        for lid in logistic_ids
                    ]
                
                product_debug["shopee_product_data"] = {
                    "item_name": shopee_product_data.get("item_name"),
                    "original_price": shopee_product_data.get("original_price"),
                    "normal_stock": shopee_product_data.get("normal_stock"),
                    "seller_stock": shopee_product_data.get("seller_stock"),
                    "category_id": shopee_product_data.get("category_id"),
                    "brand": shopee_product_data.get("brand"),
                    "attribute_list": shopee_product_data.get("attribute_list"),
                    "image_count": len(image_ids),
                    "logistic_count": len(logistic_ids)
                }
                
                # 2d. 創建蝦皮商品
                debug_info["steps"].append("  創建蝦皮商品...")
                
                create_result = create_product(
                    get_current_token()["access_token"],
                    get_current_token()["shop_id"],
                    shopee_product_data
                )
                
                product_debug["create_result"] = {
                    "success": create_result.get("success"),
                    "item_id": create_result.get("item_id"),
                    "error": create_result.get("error")
                }
                
                if create_result.get("success"):
                    product_result["success"] = True
                    product_result["shopee_item_id"] = create_result.get("item_id")
                    debug_info["steps"].append(f"  ✅ 創建成功！Item ID: {create_result.get('item_id')}")
                else:
                    error_msg = create_result.get("error", "")
                    
                    # 檢查是否為重複商品
                    if "duplicate" in error_msg.lower() or "duplicated" in error_msg.lower():
                        # 嘗試更新價格
                        from shopee_product import update_price, get_item_list, get_item_base_info
                        
                        new_price = shopee_product_data.get("original_price", 0)
                        item_name = shopee_product_data.get("item_name", "")
                        
                        debug_info["steps"].append(f"  🔄 商品已存在，嘗試更新價格...")
                        
                        # 嘗試找到現有商品的 item_id
                        found_item_id = None
                        
                        # 搜尋現有商品（用快取或重新取得）
                        if 'shopee_items_cache' not in debug_info:
                            # 取得所有蝦皮商品
                            items_result = get_item_list(
                                get_current_token()["access_token"],
                                get_current_token()["shop_id"],
                                offset=0,
                                page_size=100
                            )
                            if items_result.get("success"):
                                item_ids = [i.get("item_id") for i in items_result.get("items", [])]
                                if item_ids:
                                    # 取得商品詳細資訊
                                    info_result = get_item_base_info(
                                        get_current_token()["access_token"],
                                        get_current_token()["shop_id"],
                                        item_ids[:50]  # API 限制 50 個
                                    )
                                    if info_result.get("success"):
                                        debug_info['shopee_items_cache'] = info_result.get("items", [])
                        
                        # 在快取中搜尋匹配的商品
                        cached_items = debug_info.get('shopee_items_cache', [])
                        for cached_item in cached_items:
                            cached_name = cached_item.get("item_name", "")
                            # 比對名稱（可能有細微差異，用包含關係）
                            original_title = product.get("title", "")
                            if original_title in cached_name or cached_name in item_name:
                                found_item_id = cached_item.get("item_id")
                                old_price = cached_item.get("price_info", [{}])[0].get("original_price", 0)
                                product_debug["found_existing_item"] = {
                                    "item_id": found_item_id,
                                    "old_price": old_price,
                                    "new_price": new_price
                                }
                                break
                        
                        if found_item_id:
                            # 更新價格
                            update_result = update_price(
                                get_current_token()["access_token"],
                                get_current_token()["shop_id"],
                                found_item_id,
                                new_price
                            )
                            
                            if update_result.get("success"):
                                product_result["success"] = True
                                product_result["shopee_item_id"] = found_item_id
                                product_result["price_updated"] = True
                                debug_info["steps"].append(f"  💰 價格更新成功！Item ID: {found_item_id}, 新價格: {new_price}")
                            else:
                                product_result["success"] = True  # 商品存在，只是價格更新失敗
                                product_result["shopee_item_id"] = found_item_id
                                product_result["skipped"] = True
                                debug_info["steps"].append(f"  ⚠️ 價格更新失敗: {update_result.get('error')}")
                        else:
                            # 找不到現有商品，標記為跳過
                            product_result["success"] = True
                            product_result["shopee_item_id"] = "已存在"
                            product_result["skipped"] = True
                            debug_info["steps"].append(f"  ⏭️ 商品已存在但無法匹配，跳過")
                    else:
                        product_result["error"] = error_msg
                        debug_info["steps"].append(f"  ❌ 創建失敗: {error_msg}")
                    
                    # 記錄完整的 API 回應以便 debug
                    if create_result.get("debug", {}).get("response"):
                        product_debug["shopee_error_detail"] = create_result["debug"]["response"]
                
            except Exception as e:
                product_result["error"] = str(e)
                debug_info["steps"].append(f"  ❌ 處理時發生例外: {str(e)}")
                import traceback
                product_debug["exception_traceback"] = traceback.format_exc()
            
            results.append(product_result)
        
        # 統計結果
        success_count = sum(1 for r in results if r["success"])
        
        return jsonify({
            "success": success_count > 0,
            "results": results,
            "summary": {
                "total": len(results),
                "success": success_count,
                "failed": len(results) - success_count
            },
            "debug": debug_info
        })
        
    except Exception as e:
        import traceback
        debug_info["exception"] = str(e)
        debug_info["traceback"] = traceback.format_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "debug": debug_info
        })


@app.route("/api/sync/update-prices", methods=["POST"])
def api_update_prices():
    """只更新價格（不新增商品）"""
    if not get_current_token().get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopify_api import ShopifyAPI
    from shopee_product import get_item_list, get_item_base_info, update_price
    
    data = request.json
    collection_id = data.get("collection_id")
    collection_title = data.get("collection_title", "")
    exchange_rate = data.get("exchange_rate", 0.21)
    markup_rate = data.get("markup_rate", 1.05)
    
    debug_info = {
        "collection_id": collection_id,
        "collection_title": collection_title,
        "exchange_rate": exchange_rate,
        "markup_rate": markup_rate,
        "steps": [],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    results = []
    
    try:
        # 1. 取得蝦皮所有商品
        debug_info["steps"].append("Step 1: 取得蝦皮商品列表")
        
        shopee_items = []
        offset = 0
        while True:
            items_result = get_item_list(
                get_current_token()["access_token"],
                get_current_token()["shop_id"],
                offset=offset,
                page_size=100
            )
            if not items_result.get("success"):
                debug_info["steps"].append(f"  ⚠️ 取得商品列表失敗: {items_result.get('error')}")
                break
            
            item_ids = [i.get("item_id") for i in items_result.get("items", [])]
            if item_ids:
                # 取得商品詳細資訊（包含名稱和價格）
                info_result = get_item_base_info(
                    get_current_token()["access_token"],
                    get_current_token()["shop_id"],
                    item_ids[:50]
                )
                if info_result.get("success"):
                    shopee_items.extend(info_result.get("items", []))
            
            if not items_result.get("has_next"):
                break
            offset += 100
            
            # 安全限制
            if offset > 1000:
                break
        
        debug_info["shopee_items_count"] = len(shopee_items)
        debug_info["steps"].append(f"  ✅ 取得 {len(shopee_items)} 個蝦皮商品")
        
        # 建立名稱 → 商品的對照表
        shopee_name_map = {}
        for item in shopee_items:
            item_name = item.get("item_name", "")
            # 去掉前綴後比對
            clean_name = item_name.replace("日本代購 日本直送 GOYOUTATI ", "").strip()
            shopee_name_map[clean_name] = item
            shopee_name_map[item_name] = item  # 也保留完整名稱
        
        # 2. 取得 Shopify 商品
        debug_info["steps"].append("Step 2: 取得 Shopify 商品")
        shopify = ShopifyAPI()
        products_result = shopify.get_products_in_collection(collection_id, limit=250)
        
        if not products_result.get("success"):
            return jsonify({
                "success": False,
                "error": f"無法取得 Shopify 商品: {products_result.get('error')}",
                "debug": debug_info
            })
        
        products = products_result.get("data", {}).get("products", [])
        debug_info["shopify_products_count"] = len(products)
        debug_info["steps"].append(f"  ✅ 取得 {len(products)} 個 Shopify 商品")
        
        # 3. 比對並更新價格
        debug_info["steps"].append("Step 3: 比對並更新價格")
        
        for product in products:
            shopify_title = product.get("title", "")
            variants = product.get("variants", [])
            
            # 計算新價格
            new_price = 100
            if variants:
                shopify_price = float(variants[0].get("price", 0))
                new_price = round(shopify_price * exchange_rate * markup_rate)
            
            result = {
                "shopify_id": product.get("id"),
                "title": shopify_title,
                "new_price": new_price
            }
            
            # 在蝦皮商品中搜尋
            shopee_item = shopee_name_map.get(shopify_title)
            
            if not shopee_item:
                # 嘗試模糊比對
                for name, item in shopee_name_map.items():
                    if shopify_title in name or name in shopify_title:
                        shopee_item = item
                        break
            
            if shopee_item:
                item_id = shopee_item.get("item_id")
                price_info = shopee_item.get("price_info", [{}])
                old_price = price_info[0].get("original_price", 0) if price_info else 0
                
                result["shopee_item_id"] = item_id
                result["old_price"] = old_price
                
                # 檢查價格是否需要更新
                if abs(float(old_price) - float(new_price)) < 1:
                    result["skipped"] = True
                    result["reason"] = "價格相同"
                else:
                    # 更新價格
                    update_result = update_price(
                        get_current_token()["access_token"],
                        get_current_token()["shop_id"],
                        item_id,
                        new_price
                    )
                    
                    if update_result.get("success"):
                        result["updated"] = True
                    else:
                        result["error"] = update_result.get("error")
            else:
                result["not_found"] = True
            
            results.append(result)
        
        return jsonify({
            "success": True,
            "results": results,
            "summary": {
                "total": len(results),
                "updated": len([r for r in results if r.get("updated")]),
                "skipped": len([r for r in results if r.get("skipped")]),
                "not_found": len([r for r in results if r.get("not_found")]),
                "failed": len([r for r in results if r.get("error")])
            },
            "debug": debug_info
        })
        
    except Exception as e:
        import traceback
        debug_info["traceback"] = traceback.format_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "debug": debug_info
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
