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
        <a class="btn" href="/sync">🔄 商品同步測試</a>
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


# ==================== 商品同步功能 ====================

@app.route("/sync")
def sync_page():
    """商品同步測試頁面"""
    if not token_storage.get("access_token"):
        return redirect("/auth")
    
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
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
            .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
            .progress-bar { width: 100%; height: 20px; background: #e0e0e0; border-radius: 10px; overflow: hidden; margin: 10px 0; }
            .progress-fill { height: 100%; background: linear-gradient(90deg, #ee4d2d, #ff6b35); transition: width 0.3s; }
            .collapse-btn { background: none; border: none; color: #ee4d2d; cursor: pointer; font-size: 12px; }
        </style>
    </head>
    <body>
        <h1>🔄 商品同步測試</h1>
        <p><a href="/" class="btn btn-secondary">← 返回首頁</a></p>
        
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
                    <input type="number" id="markup-rate" value="1.05" step="0.01" min="1" style="width: 100px;">
                </div>
                <div>
                    <label><strong>範例計算：</strong></label><br>
                    <span id="price-example">¥1,000 → NT$221</span>
                </div>
            </div>
            <script>
                function updatePriceExample() {
                    const rate = parseFloat(document.getElementById('exchange-rate').value) || 0.21;
                    const markup = parseFloat(document.getElementById('markup-rate').value) || 1.05;
                    const example = Math.round(1000 * rate * markup);
                    document.getElementById('price-example').textContent = '¥1,000 → NT$' + example;
                }
                document.getElementById('exchange-rate').addEventListener('input', updatePriceExample);
                document.getElementById('markup-rate').addEventListener('input', updatePriceExample);
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
                <div>
                    <label>每系列上限：</label>
                    <input type="number" id="sync-limit" value="250" min="1" max="250" style="width: 70px;">
                </div>
            </div>
            
            <p style="margin-top: 10px;">
                <small>🧪 測試同步：每個系列只同步 1 個商品（用於測試）</small><br>
                <small>🚀 全部上架：同步所有選中系列的全部商品（直接上架）</small>
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
                    const confirmMsg = '確定要同步 ' + collections.length + ' 個系列的所有商品？\\n\\n商品將直接上架到蝦皮商店！';
                    if (!confirm(confirmMsg)) {
                        return;
                    }
                }
                
                // 讀取價格設定
                const exchangeRate = parseFloat(document.getElementById('exchange-rate').value) || 0.21;
                const markupRate = parseFloat(document.getElementById('markup-rate').value) || 1.05;
                
                const testBtn = document.getElementById('test-btn');
                const syncBtn = document.getElementById('sync-btn');
                testBtn.disabled = true;
                syncBtn.disabled = true;
                syncBtn.textContent = '同步中...';
                
                document.getElementById('sync-progress').style.display = 'block';
                
                const modeText = isTestMode ? '測試同步' : '全部上架';
                log('========== 開始' + modeText + ' ==========', 'info');
                log('模式: ' + modeText + ' (每系列上限: ' + limit + ')', 'dim');
                log('分類 ID: ' + selectedCategoryId, 'dim');
                log('物流渠道: ' + logistics.join(', '), 'dim');
                log('匯率: ' + exchangeRate + ' | 加成: ' + markupRate + ' (價格乘數: ' + (exchangeRate * markupRate).toFixed(4) + ')', 'dim');
                log('系列數量: ' + collections.length, 'dim');
                log('', 'info');
                
                let totalSuccess = 0;
                let totalFail = 0;
                
                for (let i = 0; i < collections.length; i++) {
                    const col = collections[i];
                    updateProgress(i + 1, collections.length, '處理中: ' + col.title);
                    
                    log('[' + (i+1) + '/' + collections.length + '] 處理系列: ' + col.title, 'info');
                    
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
                                limit: limit
                            })
                        });
                        
                        const data = await res.json();
                        debug(data);
                        
                        if (data.success && data.results) {
                            const results = data.results;
                            const successItems = results.filter(r => r.success);
                            const failItems = results.filter(r => !r.success);
                            
                            totalSuccess += successItems.length;
                            totalFail += failItems.length;
                            
                            if (successItems.length > 0) {
                                log('  ✅ 成功同步 ' + successItems.length + ' 個商品', 'success');
                                successItems.forEach(function(r) {
                                    log('     • ' + r.title + ' (ID: ' + r.shopee_item_id + ')', 'dim');
                                });
                            }
                            
                            if (failItems.length > 0) {
                                log('  ❌ 失敗 ' + failItems.length + ' 個商品', 'error');
                                failItems.forEach(function(r) {
                                    log('     • ' + r.title + ': ' + r.error, 'dim');
                                });
                            }
                        } else {
                            totalFail++;
                            log('  ❌ 系列同步失敗: ' + (data.error || 'Unknown error'), 'error');
                            if (data.debug && data.debug.steps) {
                                data.debug.steps.forEach(function(step) {
                                    log('     ' + step, 'dim');
                                });
                            }
                        }
                        
                    } catch (e) {
                        totalFail++;
                        log('  ❌ 請求錯誤: ' + e.message, 'error');
                    }
                    
                    log('', 'info');
                    
                    // 稍微延遲避免 API 限制
                    await new Promise(function(r) { setTimeout(r, 1000); });
                }
                
                log('========== 同步完成 ==========', 'info');
                log('總計成功: ' + totalSuccess + ' 個商品 / 失敗: ' + totalFail, totalSuccess > 0 ? 'success' : 'error');
                
                testBtn.disabled = false;
                syncBtn.disabled = false;
                syncBtn.textContent = '🚀 全部上架';
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
    if not token_storage.get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopee_product import get_categories
    
    result = get_categories(
        token_storage["access_token"],
        token_storage["shop_id"]
    )
    
    return jsonify(result)


@app.route("/api/shopee/logistics")
def api_shopee_logistics():
    """獲取蝦皮物流"""
    if not token_storage.get("access_token"):
        return jsonify({"success": False, "error": "Not authorized"})
    
    from shopee_product import get_logistics
    
    result = get_logistics(
        token_storage["access_token"],
        token_storage["shop_id"]
    )
    
    return jsonify(result)


@app.route("/api/sync/collection", methods=["POST"])
def api_sync_collection():
    """同步一個系列的商品"""
    if not token_storage.get("access_token"):
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
    limit = data.get("limit", 1)
    
    debug_info = {
        "collection_id": collection_id,
        "collection_title": collection_title,
        "category_id": category_id,
        "logistic_ids": logistic_ids,
        "exchange_rate": exchange_rate,
        "markup_rate": markup_rate,
        "limit": limit,
        "steps": [],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    results = []
    
    try:
        # 0. 先查詢分類屬性，找到產地屬性
        debug_info["steps"].append("Step 0: 查詢分類屬性")
        attrs_result = get_attributes(
            token_storage["access_token"],
            token_storage["shop_id"],
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
        products_result = shopify.get_products_in_collection(collection_id, limit=limit)
        
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
        debug_info["products_count"] = len(products)
        debug_info["steps"].append(f"  ✅ 獲取到 {len(products)} 個商品")
        
        if not products:
            return jsonify({
                "success": False,
                "error": "系列中沒有商品",
                "debug": debug_info
            })
        
        # 2. 處理每個商品
        for idx, product in enumerate(products):
            product_debug = {
                "shopify_id": product.get("id"),
                "title": product.get("title"),
                "variants_count": len(product.get("variants", [])),
                "images_count": len(product.get("images", []))
            }
            
            product_result = {
                "shopify_id": product.get("id"),
                "title": product.get("title"),
                "success": False,
                "shopee_item_id": None,
                "error": None,
                "debug": product_debug
            }
            
            try:
                debug_info["steps"].append(f"Step 2.{idx+1}: 處理商品 - {product.get('title')}")
                
                # 2a. 檢查圖片
                images = product.get("images", [])
                image_urls = [img.get("src") for img in images if img.get("src")]
                product_debug["image_urls"] = image_urls[:3]  # 只記錄前3個
                
                if not image_urls:
                    product_result["error"] = "商品沒有圖片"
                    debug_info["steps"].append("  ❌ 商品沒有圖片")
                    results.append(product_result)
                    continue
                
                debug_info["steps"].append(f"  找到 {len(image_urls)} 張圖片")
                
                # 2b. 上傳圖片到蝦皮
                image_ids = []
                image_upload_results = []
                
                for i, img_url in enumerate(image_urls[:9]):  # 蝦皮最多 9 張
                    debug_info["steps"].append(f"  上傳圖片 {i+1}/{min(len(image_urls), 9)}...")
                    
                    upload_result = upload_image(
                        token_storage["access_token"],
                        token_storage["shop_id"],
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
                
                # 2c. 轉換商品格式
                debug_info["steps"].append("  轉換商品格式...")
                shopee_product_data = shopify_to_shopee_product(
                    product,
                    category_id,
                    image_ids,
                    collection_title,  # 傳遞系列名稱
                    country_origin_attr,  # 傳遞產地屬性
                    exchange_rate,  # 匯率
                    markup_rate  # 加成比例
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
                    token_storage["access_token"],
                    token_storage["shop_id"],
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
                    product_result["error"] = create_result.get("error")
                    debug_info["steps"].append(f"  ❌ 創建失敗: {create_result.get('error')}")
                    
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
