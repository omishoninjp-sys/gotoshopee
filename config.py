import os

# Shopee API 設定
PARTNER_ID = os.environ.get("SHOPEE_PARTNER_ID", "1215936")
PARTNER_KEY = os.environ.get("SHOPEE_PARTNER_KEY", "")

# 測試環境 (2025-11-21 官方文件更新的新 URL)
HOST = "https://openplatform.sandbox.test-stable.shopee.sg"
# 舊的測試環境 URL（可能已棄用）
# HOST = "https://partner.test-stable.shopeemobile.com"
# 正式環境（之後再換）
# HOST = "https://partner.shopeemobile.com"

# 授權回調網址
REDIRECT_URL = os.environ.get("REDIRECT_URL", "https://gotoshopee.zeabur.app/callback")

# Shopify 設定（之後會用到）
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "goyoutati.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")
