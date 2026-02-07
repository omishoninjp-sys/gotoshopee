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
