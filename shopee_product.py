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


def find_country_of_origin_attribute(attributes: list):
    """從屬性列表中找到產地屬性"""
    country_keywords = ["country", "origin", "產地", "原產地"]
    
    for attr in attributes:
        attr_name = (attr.get("original_attribute_name", "") + " " + attr.get("display_attribute_name", "")).lower()
        if any(keyword in attr_name for keyword in country_keywords):
            # 找到產地屬性，嘗試找「日本」的選項
            attr_id = attr.get("attribute_id")
            values = attr.get("attribute_value_list", [])
            
            japan_value_id = 0
            for val in values:
                val_name = (val.get("original_value_name", "") + " " + val.get("display_value_name", "")).lower()
                if "japan" in val_name or "日本" in val_name:
                    japan_value_id = val.get("value_id", 0)
                    break
            
            return {
                "attribute_id": attr_id,
                "value_id": japan_value_id,
                "original_value_name": "日本"
            }
    
    return None

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

def shopify_to_shopee_product(shopify_product: dict, category_id: int, image_ids: list, collection_title: str = "", country_origin_attr: dict = None, exchange_rate: float = 0.21, markup_rate: float = 1.05):
    """
    將 Shopify 商品轉換為蝦皮商品格式
    
    Args:
        shopify_product: Shopify 商品資料
        category_id: 蝦皮分類 ID
        image_ids: 已上傳的圖片 ID 列表
        collection_title: Shopify 系列名稱（用於判斷預設庫存）
        country_origin_attr: 產地屬性資訊 {"attribute_id": xxx, "value_id": xxx, "original_value_name": "日本"}
        exchange_rate: 匯率 (JPY → TWD)，預設 0.21
        markup_rate: 加成比例，預設 1.05
    """
    # 取得價格（從第一個 variant）
    variants = shopify_product.get("variants", [])
    price = 0
    weight = 0.5  # 預設重量 0.5kg
    
    if variants:
        first_variant = variants[0]
        # 價格：Shopify 日圓 → 台幣（匯率 × 加成）
        shopify_price = float(first_variant.get("price", 0))
        price = round(shopify_price * exchange_rate * markup_rate)  # 四捨五入到整數
        
        # 重量：使用 Shopify 的重量（單位 kg）
        shopify_weight = float(first_variant.get("weight", 0) or 0)
        weight_unit = first_variant.get("weight_unit", "kg")
        
        # 轉換重量單位到 kg
        if weight_unit == "g":
            weight = shopify_weight / 1000
        elif weight_unit == "lb":
            weight = shopify_weight * 0.453592
        elif weight_unit == "oz":
            weight = shopify_weight * 0.0283495
        else:  # kg 或其他
            weight = shopify_weight
        
        # 確保重量至少 0.1kg（蝦皮最小值）
        if weight < 0.1:
            weight = 0.1
    
    # 庫存：統一設為 900
    stock = 900
    
    # 處理描述（移除 HTML 標籤的簡單方法）
    description = shopify_product.get("body_html", "")
    if description:
        import re
        description = re.sub(r'<[^>]+>', '', description)
        description = description[:3000]  # 蝦皮描述上限
    
    if not description:
        description = shopify_product.get("title", "商品描述")
    
    # 從 Shopify vendor 取得品牌名稱，沒有的話用「無品牌」
    brand_name = shopify_product.get("vendor", "")
    
    # 建立蝦皮商品資料
    shopee_product = {
        "original_price": price if price >= 10 else 100,  # 最低價格 10 台幣，沒價格則設 100
        "description": description,
        "item_name": shopify_product.get("title", "商品")[:120],  # 蝦皮標題上限 120 字
        "normal_stock": stock,
        "seller_stock": [{"stock": stock}],  # 賣家庫存（必填）
        "category_id": category_id,
        "image": {
            "image_id_list": image_ids
        },
        "weight": round(weight, 2),  # 重量保留兩位小數
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
        "item_status": "UNLIST",  # 先設為未上架，測試用
        # 品牌資訊（必填）
        "brand": {
            "brand_id": 0,  # 0 = 無品牌/自訂品牌
            "original_brand_name": brand_name if brand_name else "No Brand"
        }
    }
    
    # 商品屬性 - 正式環境 (分類 100656 禮盒)
    # 下拉選單屬性必須使用 value_id，文字輸入屬性使用 original_value_name
    shopee_product["attribute_list"] = [
        # ===== 下拉選單屬性（必須用 value_id）=====
        {
            "attribute_id": 102384,  # Region of Origin (TW) 產地
            "attribute_value_list": [
                {"value_id": 17007}  # Japan
            ]
        },
        {
            "attribute_id": 101021,  # Pork Origin Region 豬肉產地
            "attribute_value_list": [
                {"value_id": 5549}  # No Pork
            ]
        },
        {
            "attribute_id": 100095,  # Weight 重量
            "attribute_value_list": [
                {"value_id": 613}  # 500g
            ]
        },
        {
            "attribute_id": 100010,  # shelf lifes 保存期限
            "attribute_value_list": [
                {"value_id": 568}  # 2 Months
            ]
        },
        # ===== 文字輸入屬性（使用 original_value_name）=====
        {
            "attribute_id": 100975,  # Liable Company Name 負責廠商名稱
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "Omishonin Co., Ltd."}
            ]
        },
        {
            "attribute_id": 100976,  # Liable Company Address 負責廠商地址
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "New Ryogoku Heights 303, 1-28-4 Midori, Sumida-ku, Tokyo, 130-0021, Japan"}
            ]
        },
        {
            "attribute_id": 100977,  # Liable Company Tel No. 負責廠商電話
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "+81 0366593195"}
            ]
        },
        {
            "attribute_id": 100974,  # Ingredient 成分
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "詳見商品包裝"}
            ]
        },
        {
            "attribute_id": 100999,  # Quantity 數量
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "1"}
            ]
        },
        {
            "attribute_id": 102564,  # Food Additives 食品添加物
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "詳見商品包裝"}
            ]
        },
        {
            "attribute_id": 102565,  # Nutrition Facts 營養標示
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "詳見商品包裝"}
            ]
        },
        {
            "attribute_id": 102566,  # GMO Indication 基改標示
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "本產品不含基因改造成分"}
            ]
        },
        {
            "attribute_id": 102567,  # Other Regulatory Requirements 其他法規
            "attribute_value_list": [
                {"value_id": 0, "original_value_name": "詳見商品包裝"}
            ]
        }
    ]
    
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
