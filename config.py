import os

# Shopee API 設定
PARTNER_ID = os.environ.get("SHOPEE_PARTNER_ID", "2015134")
PARTNER_KEY = os.environ.get("SHOPEE_PARTNER_KEY", "")

# 正式環境
HOST = "https://partner.shopeemobile.com"
# 測試環境（備用）
# HOST = "https://openplatform.sandbox.test-stable.shopee.sg"

# 授權回調網址
REDIRECT_URL = os.environ.get("REDIRECT_URL", "https://gotoshopee.zeabur.app/callback")

# Shopify 設定（之後會用到）
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "goyoutati.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

# OpenAI API 設定（用於翻譯）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# 蝦皮站點設定
SHOPEE_REGIONS = {
    "TW": {
        "name": "台灣",
        "domain": "shopee.tw",
        "currency": "TWD",
        "flag": "🇹🇼",
        "lang": "zh-TW"
    },
    "TH": {
        "name": "ไทย",
        "name_zh": "泰國",
        "domain": "shopee.co.th",
        "currency": "THB",
        "flag": "🇹🇭",
        "lang": "th"
    },
    "SG": {
        "name": "Singapore",
        "name_zh": "新加坡",
        "domain": "shopee.sg",
        "currency": "SGD",
        "flag": "🇸🇬",
        "lang": "en"
    },
    "MY": {
        "name": "Malaysia",
        "name_zh": "馬來西亞",
        "domain": "shopee.com.my",
        "currency": "MYR",
        "flag": "🇲🇾",
        "lang": "en"
    },
    "ID": {
        "name": "Indonesia",
        "name_zh": "印尼",
        "domain": "shopee.co.id",
        "currency": "IDR",
        "flag": "🇮🇩",
        "lang": "id"
    },
    "VN": {
        "name": "Việt Nam",
        "name_zh": "越南",
        "domain": "shopee.vn",
        "currency": "VND",
        "flag": "🇻🇳",
        "lang": "vi"
    },
    "PH": {
        "name": "Philippines",
        "name_zh": "菲律賓",
        "domain": "shopee.ph",
        "currency": "PHP",
        "flag": "🇵🇭",
        "lang": "en"
    },
    "BR": {
        "name": "Brasil",
        "name_zh": "巴西",
        "domain": "shopee.com.br",
        "currency": "BRL",
        "flag": "🇧🇷",
        "lang": "pt"
    }
}

# 多語言翻譯
TRANSLATIONS = {
    "zh-TW": {
        # 首頁
        "title": "Goyoutati Shopee Sync",
        "subtitle": "Shopify 商品同步到蝦皮（多站點支援）",
        "select_region": "選擇站點",
        "status": "狀態",
        "connected": "已連接商店",
        "not_authorized": "尚未授權",
        "connect_shop": "連接蝦皮商店",
        "sync_test": "商品同步測試",
        "shop_info": "查看商店資訊",
        "reauthorize": "重新授權",
        "authorized_shops": "已授權商店",
        "no_shops": "尚無已授權商店",
        
        # 同步頁面
        "sync_title": "商品同步測試",
        "back_home": "返回首頁",
        "connection_test": "連線測試",
        "test_shopify": "測試 Shopify",
        "test_shopee": "測試蝦皮",
        "select_category": "選擇蝦皮分類",
        "load_categories": "載入分類",
        "main_category": "主分類",
        "sub_category": "子分類",
        "please_select": "請選擇",
        "select_sub": "請選擇子分類",
        "logistics": "物流渠道",
        "load_logistics": "載入物流",
        "select_collections": "選擇 Shopify 系列",
        "load_collections": "載入系列",
        "select_all": "全選",
        "deselect_all": "取消全選",
        "price_settings": "價格設定",
        "price_formula": "計算公式：Shopify 價格 × 匯率 × 加成比例 = 售價",
        "exchange_rate": "匯率",
        "markup_rate": "加成比例",
        "min_price": "最低價格",
        "example_calc": "範例計算",
        "low_price_skip": "低於最低價格的商品將自動跳過不上架",
        "shipping_settings": "備貨設定",
        "pre_order": "較長備貨",
        "days_to_ship": "備貨天數",
        "days": "天",
        "pre_order_tip": "較長備貨：代購商品建議開啟，備貨時間可設 1-15 天",
        "normal_ship_tip": "不勾選：一般商品，需在 1-3 個工作日內出貨",
        "execute_sync": "執行同步",
        "test_sync": "測試同步 (每系列1個)",
        "full_sync": "全部上架",
        "update_price": "更新價格",
        "per_series_limit": "每系列上限",
        "sync_log": "同步日誌",
        "debug_info": "Debug 資訊",
        "show_hide": "顯示/隱藏",
        
        # 狀態訊息
        "loading": "載入中...",
        "success": "成功",
        "failed": "失敗",
        "skipped": "跳過",
        "price_updated": "價格已更新",
        "exists_skipped": "已存在，跳過",
        "low_price_skipped": "低於最低價格，跳過",
        "japanese_skipped": "商品名為日文，請重新同步商品或翻譯",
        "sync_complete": "同步完成",
        "total_success": "總計成功",
        "total_failed": "失敗",
        "products": "個商品",
    },
    "th": {
        # หน้าแรก
        "title": "Goyoutati Shopee Sync",
        "subtitle": "ซิงค์สินค้าจาก Shopify ไปยัง Shopee (รองรับหลายประเทศ)",
        "select_region": "เลือกประเทศ",
        "status": "สถานะ",
        "connected": "เชื่อมต่อร้านค้าแล้ว",
        "not_authorized": "ยังไม่ได้อนุญาต",
        "connect_shop": "เชื่อมต่อร้านค้า Shopee",
        "sync_test": "ทดสอบซิงค์สินค้า",
        "shop_info": "ดูข้อมูลร้านค้า",
        "reauthorize": "อนุญาตใหม่",
        "authorized_shops": "ร้านค้าที่อนุญาตแล้ว",
        "no_shops": "ยังไม่มีร้านค้าที่อนุญาต",
        
        # หน้าซิงค์
        "sync_title": "ทดสอบซิงค์สินค้า",
        "back_home": "กลับหน้าแรก",
        "connection_test": "ทดสอบการเชื่อมต่อ",
        "test_shopify": "ทดสอบ Shopify",
        "test_shopee": "ทดสอบ Shopee",
        "select_category": "เลือกหมวดหมู่ Shopee",
        "load_categories": "โหลดหมวดหมู่",
        "main_category": "หมวดหมู่หลัก",
        "sub_category": "หมวดหมู่ย่อย",
        "please_select": "กรุณาเลือก",
        "select_sub": "กรุณาเลือกหมวดหมู่ย่อย",
        "logistics": "ช่องทางขนส่ง",
        "load_logistics": "โหลดช่องทางขนส่ง",
        "select_collections": "เลือกคอลเลกชัน Shopify",
        "load_collections": "โหลดคอลเลกชัน",
        "select_all": "เลือกทั้งหมด",
        "deselect_all": "ยกเลิกการเลือกทั้งหมด",
        "price_settings": "ตั้งค่าราคา",
        "price_formula": "สูตรคำนวณ: ราคา Shopify × อัตราแลกเปลี่ยน × อัตราเพิ่ม = ราคาขาย",
        "exchange_rate": "อัตราแลกเปลี่ยน",
        "markup_rate": "อัตราเพิ่ม",
        "min_price": "ราคาขั้นต่ำ",
        "example_calc": "ตัวอย่างการคำนวณ",
        "low_price_skip": "สินค้าที่ราคาต่ำกว่าขั้นต่ำจะถูกข้ามโดยอัตโนมัติ",
        "shipping_settings": "ตั้งค่าการจัดส่ง",
        "pre_order": "สั่งจองล่วงหน้า",
        "days_to_ship": "วันในการจัดเตรียม",
        "days": "วัน",
        "pre_order_tip": "สั่งจองล่วงหน้า: แนะนำสำหรับสินค้านำเข้า ตั้งเวลาได้ 1-15 วัน",
        "normal_ship_tip": "ไม่เลือก: สินค้าทั่วไป ต้องจัดส่งภายใน 1-3 วันทำการ",
        "execute_sync": "ดำเนินการซิงค์",
        "test_sync": "ทดสอบซิงค์ (1 ต่อคอลเลกชัน)",
        "full_sync": "อัปโหลดทั้งหมด",
        "update_price": "อัปเดตราคา",
        "per_series_limit": "จำกัดต่อคอลเลกชัน",
        "sync_log": "บันทึกการซิงค์",
        "debug_info": "ข้อมูล Debug",
        "show_hide": "แสดง/ซ่อน",
        
        # ข้อความสถานะ
        "loading": "กำลังโหลด...",
        "success": "สำเร็จ",
        "failed": "ล้มเหลว",
        "skipped": "ข้าม",
        "price_updated": "อัปเดตราคาแล้ว",
        "exists_skipped": "มีอยู่แล้ว ข้าม",
        "low_price_skipped": "ราคาต่ำกว่าขั้นต่ำ ข้าม",
        "japanese_skipped": "ชื่อสินค้าเป็นภาษาญี่ปุ่น กรุณาซิงค์ใหม่หรือแปล",
        "sync_complete": "ซิงค์เสร็จสิ้น",
        "total_success": "สำเร็จทั้งหมด",
        "total_failed": "ล้มเหลว",
        "products": "สินค้า",
    },
    "en": {
        # Home
        "title": "Goyoutati Shopee Sync",
        "subtitle": "Sync products from Shopify to Shopee (Multi-region support)",
        "select_region": "Select Region",
        "status": "Status",
        "connected": "Connected to shop",
        "not_authorized": "Not authorized",
        "connect_shop": "Connect Shopee Shop",
        "sync_test": "Product Sync Test",
        "shop_info": "View Shop Info",
        "reauthorize": "Re-authorize",
        "authorized_shops": "Authorized Shops",
        "no_shops": "No authorized shops yet",
        
        # Sync page
        "sync_title": "Product Sync Test",
        "back_home": "Back to Home",
        "connection_test": "Connection Test",
        "test_shopify": "Test Shopify",
        "test_shopee": "Test Shopee",
        "select_category": "Select Shopee Category",
        "load_categories": "Load Categories",
        "main_category": "Main Category",
        "sub_category": "Sub Category",
        "please_select": "Please Select",
        "select_sub": "Please select sub-category",
        "logistics": "Logistics",
        "load_logistics": "Load Logistics",
        "select_collections": "Select Shopify Collections",
        "load_collections": "Load Collections",
        "select_all": "Select All",
        "deselect_all": "Deselect All",
        "price_settings": "Price Settings",
        "price_formula": "Formula: Shopify Price × Exchange Rate × Markup = Selling Price",
        "exchange_rate": "Exchange Rate",
        "markup_rate": "Markup Rate",
        "min_price": "Minimum Price",
        "example_calc": "Example Calculation",
        "low_price_skip": "Products below minimum price will be skipped automatically",
        "shipping_settings": "Shipping Settings",
        "pre_order": "Pre-order",
        "days_to_ship": "Days to Ship",
        "days": "days",
        "pre_order_tip": "Pre-order: Recommended for import products, can set 1-15 days",
        "normal_ship_tip": "Unchecked: Normal products, must ship within 1-3 business days",
        "execute_sync": "Execute Sync",
        "test_sync": "Test Sync (1 per collection)",
        "full_sync": "Upload All",
        "update_price": "Update Price",
        "per_series_limit": "Limit per collection",
        "sync_log": "Sync Log",
        "debug_info": "Debug Info",
        "show_hide": "Show/Hide",
        
        # Status messages
        "loading": "Loading...",
        "success": "Success",
        "failed": "Failed",
        "skipped": "Skipped",
        "price_updated": "Price updated",
        "exists_skipped": "Already exists, skipped",
        "low_price_skipped": "Below minimum price, skipped",
        "japanese_skipped": "Product name in Japanese, please re-sync or translate",
        "sync_complete": "Sync Complete",
        "total_success": "Total Success",
        "total_failed": "Failed",
        "products": "products",
    }
}

def get_translation(lang, key):
    """取得翻譯文字"""
    if lang not in TRANSLATIONS:
        lang = "en"  # 預設英文
    return TRANSLATIONS.get(lang, {}).get(key, TRANSLATIONS["en"].get(key, key))

# ==================== 尺碼表設定 ====================

# 尺碼表圖片 URL（請上傳到圖床後設定）
# 可以使用 Imgur、GitHub 或其他圖床
SIZE_CHART_URL = os.environ.get("SIZE_CHART_URL", "")

# 衣服相關關鍵字（用於判斷是否為衣服類商品）
# 標題或系列名稱包含這些關鍵字時，會自動加上尺碼表
CLOTHING_KEYWORDS = [
    # 英文
    "shirt", "t-shirt", "tee", "top", "blouse", "hoodie", "sweater", "jacket", 
    "coat", "pants", "trousers", "jeans", "shorts", "skirt", "dress", "vest",
    "cardigan", "pullover", "sweatshirt", "polo", "tank", "cap", "hat", "beanie",
    "shoes", "sneakers", "boots", "sandals", "slippers",
    # 日文
    "シャツ", "Tシャツ", "パーカー", "ジャケット", "コート", "パンツ", "ズボン",
    "スカート", "ワンピース", "セーター", "カーディガン", "ベスト", "帽子", "キャップ",
    "靴", "スニーカー", "ブーツ",
    # 中文
    "上衣", "T恤", "襯衫", "外套", "夾克", "褲子", "長褲", "短褲", "裙子", "洋裝",
    "毛衣", "針織", "帽子", "鞋", "運動鞋", "靴子", "衛衣", "連帽",
    # 品牌關鍵字（通常是服飾品牌）
    "BAPE", "Human Made", "NEIGHBORHOOD", "Supreme", "Stussy", "UNIQLO",
    "adidas", "Nike", "Onitsuka Tiger", "New Balance"
]

def is_clothing_product(title: str, collection_title: str = "", tags: list = None) -> bool:
    """
    判斷商品是否為衣服相關
    
    Args:
        title: 商品標題
        collection_title: 系列名稱
        tags: 商品標籤列表
    
    Returns:
        True 如果是衣服相關商品
    """
    # 合併檢查的文字
    check_text = (title + " " + collection_title).lower()
    
    # 加入標籤
    if tags:
        check_text += " " + " ".join(tags).lower()
    
    # 檢查是否包含衣服關鍵字
    for keyword in CLOTHING_KEYWORDS:
        if keyword.lower() in check_text:
            return True
    
    return False
