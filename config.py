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

# 蝦皮站點設定
SHOPEE_REGIONS = {
    "TW": {
        "name": "台灣",
        "domain": "shopee.tw",
        "currency": "TWD",
        "flag": "🇹🇼"
    },
    "TH": {
        "name": "泰國",
        "domain": "shopee.co.th",
        "currency": "THB",
        "flag": "🇹🇭"
    },
    "SG": {
        "name": "新加坡",
        "domain": "shopee.sg",
        "currency": "SGD",
        "flag": "🇸🇬"
    },
    "MY": {
        "name": "馬來西亞",
        "domain": "shopee.com.my",
        "currency": "MYR",
        "flag": "🇲🇾"
    },
    "ID": {
        "name": "印尼",
        "domain": "shopee.co.id",
        "currency": "IDR",
        "flag": "🇮🇩"
    },
    "VN": {
        "name": "越南",
        "domain": "shopee.vn",
        "currency": "VND",
        "flag": "🇻🇳"
    },
    "PH": {
        "name": "菲律賓",
        "domain": "shopee.ph",
        "currency": "PHP",
        "flag": "🇵🇭"
    },
    "BR": {
        "name": "巴西",
        "domain": "shopee.com.br",
        "currency": "BRL",
        "flag": "🇧🇷"
    }
}
