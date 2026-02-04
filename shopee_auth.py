import hashlib
import hmac
import time

from config import PARTNER_ID, PARTNER_KEY, HOST


def get_timestamp():
    """取得當前時間戳"""
    return int(time.time())


def generate_sign(path: str, timestamp: int, access_token: str = "", shop_id: int = 0) -> str:
    """
    產生 Shopee API 簽名 (HMAC-SHA256)
    
    簽名規則（Shopee V2 API）：
    - 授權相關: HMAC-SHA256(partner_key, partner_id + path + timestamp)
    - 商店相關: HMAC-SHA256(partner_key, partner_id + path + timestamp + access_token + shop_id)
    """
    if access_token and shop_id:
        base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    else:
        base_string = f"{PARTNER_ID}{path}{timestamp}"
    
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return sign


def build_auth_url(redirect_url: str) -> str:
    """
    產生商店授權 URL
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
    
    for key, value in params.items():
        url += f"&{key}={value}"
    
    return url
