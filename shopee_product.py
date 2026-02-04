"""
Shopee Product API 模組
"""
import os
import hashlib
import hmac
import time
import requests
from io import BytesIO

from config import PARTNER_ID, PARTNER_KEY, HOST

def get_timestamp():
    """取得當前時間戳"""
    return int(time.time())

def generate_shop_sign(path: str, timestamp: int, access_token: str, shop_id: int) -> str:
    """
    產生 Shop API 簽名
    格式：partner_id + path + timestamp + access_token + shop_id
    """
    base_string = f"{PARTNER_ID}{path}{timestamp}{access_token}{shop_id}"
    sign = hmac.new(
        PARTNER_KEY.encode('utf-8'),
        base_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return sign

def build_shop_api_url(path: str, access_token: str, shop_id: int, **extra_params) -> str:
    """建立 Shop API URL"""
    timestamp = get_timestamp()
    sign = generate_shop_sign(path, timestamp, access_token, shop_id)
    
    url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
    
    for key, value in extra_params.items():
        url += f"&{key}={value}"
    
    return url

def get_categories(access_token: str, shop_id: int, language: str = "zh-Hant"):
    """取得蝦皮分類列表"""
    debug_info = {"step": "get_categories", "language": language}
    
    try:
        path = "/api/v2/product/get_category"
        url = build_shop_api_url(path, access_token, shop_id, language=language)
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        debug_info["message"] = data.get("message", "")
        
        if data.get("error") == "":
            categories = data.get("response", {}).get("category_list", [])
            debug_info["categories_count"] = len(categories)
            return {
                "success": True,
                "categories": categories,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "categories": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "categories": [],
            "debug": debug_info
        }

def get_attributes(access_token: str, shop_id: int, category_id: int, language: str = "zh-Hant"):
    """取得分類的屬性要求"""
    debug_info = {"step": "get_attributes", "category_id": category_id}
    
    try:
        path = "/api/v2/product/get_attributes"
        url = build_shop_api_url(path, access_token, shop_id, category_id=category_id, language=language)
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        
        if data.get("error") == "":
            attributes = data.get("response", {}).get("attribute_list", [])
            debug_info["attributes_count"] = len(attributes)
            return {
                "success": True,
                "attributes": attributes,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "attributes": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "attributes": [],
            "debug": debug_info
        }

def upload_image(access_token: str, shop_id: int, image_url: str):
    """上傳圖片到蝦皮 MediaSpace"""
    debug_info = {"step": "upload_image", "image_url": image_url}
    
    try:
        # 1. 先下載圖片
        debug_info["sub_step"] = "downloading_image"
        img_response = requests.get(image_url, timeout=30)
        debug_info["download_status"] = img_response.status_code
        
        if img_response.status_code != 200:
            return {
                "success": False,
                "error": f"無法下載圖片: HTTP {img_response.status_code}",
                "debug": debug_info
            }
        
        image_data = img_response.content
        debug_info["image_size"] = len(image_data)
        
        # 2. 上傳到蝦皮
        debug_info["sub_step"] = "uploading_to_shopee"
        path = "/api/v2/media_space/upload_image"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        debug_info["upload_url"] = url
        
        files = {
            'image': ('image.jpg', BytesIO(image_data), 'image/jpeg')
        }
        
        response = requests.post(url, files=files, timeout=60)
        debug_info["upload_status"] = response.status_code
        
        data = response.json()
        debug_info["response"] = data
        
        if data.get("error") == "":
            image_info = data.get("response", {}).get("image_info", {})
            return {
                "success": True,
                "image_id": image_info.get("image_id"),
                "image_url": image_info.get("image_url_list", [{}])[0].get("image_url"),
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "debug": debug_info
        }

def create_product(access_token: str, shop_id: int, product_data: dict):
    """
    建立蝦皮商品
    
    product_data 應包含：
    - original_price: 原價
    - description: 描述
    - item_name: 商品名稱
    - normal_stock: 庫存
    - category_id: 分類ID
    - image: {"image_id_list": ["xxx"]}
    - weight: 重量(kg)
    - dimension: {"package_length": 10, "package_width": 10, "package_height": 10}
    """
    debug_info = {"step": "create_product", "product_name": product_data.get("item_name", "N/A")}
    
    try:
        path = "/api/v2/product/add_item"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        debug_info["url"] = url
        debug_info["request_body"] = product_data
        
        response = requests.post(url, json=product_data, timeout=60)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["response"] = data
        
        if data.get("error") == "":
            item_id = data.get("response", {}).get("item_id")
            return {
                "success": True,
                "item_id": item_id,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "debug": debug_info
        }

def shopify_to_shopee_product(shopify_product: dict, category_id: int, image_ids: list):
    """
    將 Shopify 商品轉換為蝦皮商品格式
    """
    # 取得價格（從第一個 variant）
    variants = shopify_product.get("variants", [])
    price = 0
    stock = 0
    weight = 0.5  # 預設重量 0.5kg
    
    if variants:
        first_variant = variants[0]
        price = float(first_variant.get("price", 0))
        stock = first_variant.get("inventory_quantity", 0)
        if stock < 0:
            stock = 10  # 如果庫存為負，設為預設值
        weight = float(first_variant.get("weight", 0.5)) or 0.5
    
    # 處理描述（移除 HTML 標籤的簡單方法）
    description = shopify_product.get("body_html", "")
    if description:
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = description[:3000]  # 蝦皮描述上限
    
    if not description:
        description = shopify_product.get("title", "商品描述")
    
    # 建立蝦皮商品資料
    shopee_product = {
        "original_price": price if price > 0 else 100,  # 最低價格
        "description": description,
        "item_name": shopify_product.get("title", "商品")[:120],  # 蝦皮標題上限 120 字
        "normal_stock": stock if stock > 0 else 10,
        "category_id": category_id,
        "image": {
            "image_id_list": image_ids
        },
        "weight": weight,
        "dimension": {
            "package_length": 10,
            "package_width": 10,
            "package_height": 10
        },
        "logistic_info": [
            {
                "logistic_id": 70022,  # 需要根據實際物流設定
                "enabled": True
            }
        ],
        "condition": "NEW",
        "item_status": "UNLIST"  # 先設為未上架，測試用
    }
    
    return shopee_product

def get_logistics(access_token: str, shop_id: int):
    """取得可用的物流渠道"""
    debug_info = {"step": "get_logistics"}
    
    try:
        path = "/api/v2/logistics/get_channel_list"
        url = build_shop_api_url(path, access_token, shop_id)
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        
        if data.get("error") == "":
            logistics = data.get("response", {}).get("logistics_channel_list", [])
            debug_info["logistics_count"] = len(logistics)
            return {
                "success": True,
                "logistics": logistics,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "logistics": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "logistics": [],
            "debug": debug_info
        }
