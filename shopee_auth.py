import hashlib
import time

from config import PARTNER_ID, PARTNER_KEY, HOST


def get_timestamp():
    """取得當前時間戳"""
    return int(time.time())


def generate_sign(path: str, timestamp: int, access_token: str = "", shop_id: int = 0) -> str:
    """
    產生 Shopee API 簽名
    
    簽名規則（Shopee V2 API）：
    - 授權相關: SHA256(partner_key + partner_id + path + timestamp)
    - 商店相關: SHA256(partner_key + partner_id + path + timestamp + access_token + shop_id)
    """
    if access_token and shop_id:
        base_string = f"{PARTNER_KEY}{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    else:
        base_string = f"{PARTNER_KEY}{PARTNER_ID}{path}{timestamp}"
    
    sign = hashlib.sha256(base_string.encode('utf-8')).hexdigest()
    
    return sign


def build_auth_url(redirect_url: str) -> str:
    """
    產生商店授權 URL
    
    用戶訪問這個 URL 後會被導向蝦皮登入頁面，
    授權成功後會回調到 redirect_url
    """
    path = "/api/v2/shop/auth_partner"
    timestamp = get_timestamp()
    sign = generate_sign(path, timestamp)
    
    auth_url = (
        f"{HOST}{path}"
        f"?partner_id={PARTNER_ID}"
        f"&timestamp={timestamp}"
        f"&sign={sign}"
        f"&redirect={redirect_url}"
    )
    
    return auth_url


def build_api_url(path: str, access_token: str = "", shop_id: int = 0, **params) -> str:
    """
    產生 API 請求 URL（含簽名）
    """
    timestamp = get_timestamp()
    sign = generate_sign(path, timestamp, access_token, shop_id)
    
    url = (
        f"{HOST}{path}"
        f"?partner_id={PARTNER_ID}"
        f"&timestamp={timestamp}"
        f"&sign={sign}"
    )
    
    if access_token:
        url += f"&access_token={access_token}"
    if shop_id:
        url += f"&shop_id={shop_id}"
    
    # 加入其他參數
    for key, value in params.items():
        url += f"&{key}={value}"
    
    return url
