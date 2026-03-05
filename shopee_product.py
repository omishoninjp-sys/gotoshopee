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


def get_attribute_tree(access_token: str, shop_id: int, category_id: int, language: str = "en"):
    """取得分類的屬性樹（使用 get_attribute_tree API）"""
    debug_info = {"step": "get_attribute_tree", "category_id": category_id}
    
    try:
        path = "/api/v2/product/get_attribute_tree"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        # 這個 API 需要 POST 請求
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        debug_info["url"] = url
        
        # POST body
        body = {
            "category_id_list": [category_id],
            "language": language
        }
        debug_info["body"] = body
        
        response = requests.post(url, json=body, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        debug_info["message"] = data.get("message", "")
        
        if data.get("error") == "":
            # 返回完整結構
            attribute_tree = data.get("response", {}).get("attribute_tree", [])
            debug_info["tree_count"] = len(attribute_tree)
            
            # 解析第一個分類的屬性
            attributes = []
            if attribute_tree:
                first_category = attribute_tree[0]
                attributes = first_category.get("attribute_list", [])
            
            return {
                "success": True,
                "category_id": category_id,
                "attribute_tree": attribute_tree,
                "attributes": attributes,
                "attributes_count": len(attributes),
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


def find_country_of_origin_attribute(attributes: list, target_country: str = "Japan"):
    """
    從屬性列表中找到產地屬性
    
    Args:
        attributes: 蝦皮分類屬性列表
        target_country: 目標產地名稱 (例如: "Japan", "China", "Taiwan" 等)
    
    Returns:
        產地屬性資訊 {"attribute_id": xxx, "value_id": xxx, "original_value_name": "Japan"}
    """
    country_keywords = ["country", "origin", "產地", "原產地", "region"]
    
    # 產地名稱對照表（用於匹配蝦皮屬性值）
    country_aliases = {
        "Japan": ["japan", "日本", "jp", "jpn"],
        "China": ["china", "中國", "中国", "cn", "chn", "大陸", "大陆"],
        "Taiwan": ["taiwan", "台灣", "台湾", "tw", "twn"],
        "Korea": ["korea", "韓國", "韩国", "kr", "kor", "south korea"],
        "United States": ["united states", "usa", "us", "美國", "美国", "america"],
        "Thailand": ["thailand", "泰國", "泰国", "th", "tha"],
        "Vietnam": ["vietnam", "越南", "vn", "vnm"],
        "Indonesia": ["indonesia", "印尼", "id", "idn"],
        "Malaysia": ["malaysia", "馬來西亞", "马来西亚", "my", "mys"],
        "Singapore": ["singapore", "新加坡", "sg", "sgp"],
        "Other": ["other", "其他", "others"]
    }
    
    # 取得目標產地的別名列表
    target_aliases = country_aliases.get(target_country, [target_country.lower()])
    
    for attr in attributes:
        attr_name = (attr.get("original_attribute_name", "") + " " + attr.get("display_attribute_name", "")).lower()
        if any(keyword in attr_name for keyword in country_keywords):
            # 找到產地屬性
            attr_id = attr.get("attribute_id")
            values = attr.get("attribute_value_list", [])
            
            # 嘗試找到目標產地的選項
            target_value_id = 0
            matched_name = target_country
            
            for val in values:
                val_name = (val.get("original_value_name", "") + " " + val.get("display_value_name", "")).lower()
                for alias in target_aliases:
                    if alias in val_name:
                        target_value_id = val.get("value_id", 0)
                        matched_name = val.get("original_value_name", target_country)
                        break
                if target_value_id:
                    break
            
            return {
                "attribute_id": attr_id,
                "value_id": target_value_id,
                "original_value_name": matched_name
            }
    
    return None


def find_mandatory_attributes(attributes: list, target_country: str = "Japan"):
    """
    找到所有必填屬性並設定預設值
    
    Args:
        attributes: 蝦皮分類屬性列表
        target_country: 目標產地名稱
    
    Returns:
        必填屬性列表 [{"attribute_id": xxx, "attribute_value_list": [...]}]
    """
    mandatory_attrs = []
    
    # 需要處理的重要屬性名稱（不管是否 mandatory 都要設定）
    important_attr_keywords = [
        "material", "材質", "วัสดุ",  # 材質
        "origin", "country", "region", "產地", "ประเทศ", "แหล่งกำเนิด",  # 產地
        "condition", "狀況", "สภาพ",  # 狀況
        "brand license", "license", "授權", "ใบอนุญาต",  # 品牌授權
    ]
    
    # 預設值對照表（根據屬性名稱）
    default_values = {
        # 材質相關
        "material": ["other", "others", "อื่นๆ", "其他", "mixed", "ผสม", "metal", "โลหะ"],
        "材質": ["other", "others", "อื่นๆ", "其他", "mixed"],
        "วัสดุ": ["other", "others", "อื่นๆ", "其他", "mixed", "โลหะ"],
        
        # 品牌授權
        "brand license": ["no brand", "no", "ไม่มี", "無", "none", "n/a"],
        "license": ["no brand", "no", "ไม่มี", "無", "none", "n/a", "ไม่มีแบรนด์"],
        "授權": ["no brand", "no", "ไม่มี", "無", "none"],
        "ใบอนุญาต": ["no brand", "no", "ไม่มี", "無", "none", "ไม่มีแบรนด์"],
        
        # 狀況/新舊
        "condition": ["new", "ใหม่", "新品", "brand new"],
        "狀況": ["new", "ใหม่", "新品", "brand new"],
        "สภาพ": ["new", "ใหม่", "新品", "brand new"],
        
        # 圖案
        "pattern": ["solid", "plain", "other", "อื่นๆ", "其他", "พิมพ์ลาย", "no pattern"],
        "圖案": ["solid", "plain", "other", "อื่นๆ", "其他"],
        "ลาย": ["solid", "plain", "other", "อื่นๆ", "其他"],
        
        # 加大尺碼
        "plus size": ["no", "ไม่", "否", "ไม่ใช่"],
        "加大": ["no", "ไม่", "否"],
        
        # 客製化
        "custom": ["no", "ไม่", "否", "ไม่ใช่"],
        "客製": ["no", "ไม่", "否"],
    }
    
    # 產地別名
    country_aliases = {
        "Japan": ["japan", "日本", "jp", "jpn", "ญี่ปุ่น"],
        "China": ["china", "中國", "中国", "cn", "จีน"],
        "Taiwan": ["taiwan", "台灣", "台湾", "tw", "ไต้หวัน"],
        "Korea": ["korea", "韓國", "韩国", "kr", "เกาหลี"],
        "United States": ["united states", "usa", "us", "美國", "อเมริกา"],
        "Thailand": ["thailand", "泰國", "泰国", "th", "ไทย"],
        "Other": ["other", "其他", "others", "อื่นๆ"]
    }
    
    for attr in attributes:
        attr_id = attr.get("attribute_id")
        attr_name = (attr.get("original_attribute_name", "") + " " + attr.get("display_attribute_name", "")).lower()
        values = attr.get("attribute_value_list", [])
        
        # 檢查是否為 mandatory（支援多種字段名稱）
        is_mandatory = attr.get("is_mandatory", False) or attr.get("mandatory", False) or attr.get("is_required", False)
        
        # 檢查是否為重要屬性（即使不是 mandatory 也處理）
        is_important = any(kw in attr_name for kw in important_attr_keywords)
        
        # 只處理 mandatory 或重要屬性
        if not is_mandatory and not is_important:
            continue
        
        # 跳過沒有選項的屬性
        if not values:
            continue
        
        # 嘗試找到合適的預設值
        selected_value_id = 0
        selected_value_name = ""
        
        # 檢查是否為產地屬性
        is_country_attr = any(kw in attr_name for kw in ["country", "origin", "region", "產地", "ประเทศ", "แหล่งกำเนิด"])
        
        if is_country_attr:
            # 產地屬性：使用指定的國家
            target_aliases = country_aliases.get(target_country, [target_country.lower()])
            for val in values:
                val_name = (val.get("original_value_name", "") + " " + val.get("display_value_name", "")).lower()
                for alias in target_aliases:
                    if alias in val_name:
                        selected_value_id = val.get("value_id", 0)
                        selected_value_name = val.get("original_value_name", target_country)
                        break
                if selected_value_id:
                    break
        else:
            # 其他屬性：嘗試匹配預設值
            for key, default_list in default_values.items():
                if key in attr_name and default_list:
                    for val in values:
                        val_name = (val.get("original_value_name", "") + " " + val.get("display_value_name", "")).lower()
                        for default in default_list:
                            if default.lower() in val_name:
                                selected_value_id = val.get("value_id", 0)
                                selected_value_name = val.get("original_value_name", default)
                                break
                        if selected_value_id:
                            break
                    if selected_value_id:
                        break
        
        # 如果找不到匹配的預設值，使用第一個可用的值
        if not selected_value_id and values:
            first_val = values[0]
            selected_value_id = first_val.get("value_id", 0)
            selected_value_name = first_val.get("original_value_name", "")
        
        # 加入必填屬性列表（避免重複）
        if selected_value_id or selected_value_name:
            # 檢查是否已經加入過
            existing_ids = [a.get("attribute_id") for a in mandatory_attrs]
            if attr_id not in existing_ids:
                mandatory_attrs.append({
                    "attribute_id": attr_id,
                    "attribute_value_list": [{
                        "value_id": selected_value_id,
                        "original_value_name": selected_value_name
                    }]
                })
    
    return mandatory_attrs


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


def support_size_chart(access_token: str, shop_id: int, category_id: int):
    """檢查分類是否支援尺碼表"""
    debug_info = {"step": "support_size_chart", "category_id": category_id}
    
    try:
        path = "/api/v2/product/support_size_chart"
        url = build_shop_api_url(path, access_token, shop_id, category_id=category_id)
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["response"] = data
        
        if data.get("error") == "":
            support = data.get("response", {}).get("support_size_chart", False)
            return {
                "success": True,
                "support": support,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "support": False,
                "error": data.get("message", data.get("error")),
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "support": False,
            "error": str(e),
            "debug": debug_info
        }


def upload_size_chart(access_token: str, shop_id: int, image_url: str):
    """上傳尺碼表圖片到蝦皮"""
    debug_info = {"step": "upload_size_chart", "image_url": image_url}
    
    try:
        # 1. 先下載圖片
        debug_info["sub_step"] = "downloading_image"
        img_response = requests.get(image_url, timeout=30)
        debug_info["download_status"] = img_response.status_code
        
        if img_response.status_code != 200:
            return {
                "success": False,
                "error": f"無法下載尺碼表圖片: HTTP {img_response.status_code}",
                "debug": debug_info
            }
        
        image_data = img_response.content
        debug_info["image_size"] = len(image_data)
        
        # 2. 上傳到蝦皮尺碼表專用 API
        debug_info["sub_step"] = "uploading_size_chart"
        path = "/api/v2/product/upload_size_chart"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        debug_info["upload_url"] = url
        
        files = {
            'image': ('size_chart.jpg', BytesIO(image_data), 'image/jpeg')
        }
        
        response = requests.post(url, files=files, timeout=60)
        debug_info["upload_status"] = response.status_code
        
        data = response.json()
        debug_info["response"] = data
        
        if data.get("error") == "":
            size_chart_id = data.get("response", {}).get("size_chart", "")
            return {
                "success": True,
                "size_chart_id": size_chart_id,
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

def shopify_to_shopee_product(shopify_product: dict, category_id: int, image_ids: list, collection_title: str = "", country_origin_attr: dict = None, exchange_rate: float = 0.21, markup_rate: float = 1.05, pre_order: bool = True, days_to_ship: int = 4, target_lang: str = "zh-TW", size_chart_id: str = "", mandatory_attrs: list = None, brand_name_override: str = None, region_of_origin: str = "Japan"):
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
        pre_order: 是否較長備貨，預設 True
        days_to_ship: 備貨天數，預設 4 天
        target_lang: 目標語言代碼，預設 "zh-TW"（繁體中文）
        size_chart_id: 尺碼表圖片 ID（從 upload_size_chart 取得）
        mandatory_attrs: 必填屬性列表（來自 find_mandatory_attributes）
        brand_name_override: 覆蓋的品牌名稱（優先於 Shopify vendor）
        region_of_origin: 產地名稱，預設 "Japan"
    """
    # 取得價格和選項資訊
    variants = shopify_product.get("variants", [])
    options = shopify_product.get("options", [])
    price = 0
    weight = 0.5  # 預設重量 0.5kg
    
    # 判斷是否為多規格商品
    # 如果只有一個 variant 且選項是 "Default Title"，則為單規格
    has_variants = len(variants) > 1 or (len(variants) == 1 and variants[0].get("option1") not in [None, "Default Title", "預設標題"])
    
    if variants:
        first_variant = variants[0]
        # 價格：Shopify 日圓 → 台幣（匯率 × 加成）
        shopify_price = float(first_variant.get("price", 0))
        price = round(shopify_price * exchange_rate * markup_rate)  # 四捨五入到整數
        
        # 重量：使用 Shopify 的重量（單位 kg）
        shopify_weight = float(first_variant.get("weight", 0) or 0)
        weight_unit = first_variant.get("weight_unit", "kg")
        
        # 轉換重量單位到 kg
        if weight_unit == "g" or weight_unit == "grams":
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
    
    # 庫存：使用 Shopify 實際庫存（單規格用第一個 variant 的庫存）
    # 如果沒追蹤庫存（inventory_quantity 為 900），則維持 900
    # 如果庫存為 0 或負數，設為 10（代購商品預設庫存）
    if variants:
        first_variant_stock = variants[0].get("inventory_quantity", 10)
        if first_variant_stock is None:
            stock = 10  # 沒追蹤庫存，設為預設值 10
        elif first_variant_stock <= 0:
            stock = 10  # 庫存為 0 或負數，設為 10
        else:
            stock = first_variant_stock
    else:
        stock = 10  # 沒有 variant，設為預設值 10
    
    # 引入翻譯模組
    from translator import translate_product, get_title_prefix, get_desc_prefix
    
    # 取得原始標題和描述
    original_title = shopify_product.get("title", "商品")
    
    # 處理描述（移除 HTML 標籤的簡單方法）
    description = shopify_product.get("body_html", "")
    if description:
        import re
        description = re.sub(r'<[^>]+>', '', description)
    
    if not description:
        description = original_title
    
    # 如果目標語言不是繁體中文，進行翻譯
    if target_lang != "zh-TW":
        translated_title, translated_desc = translate_product(original_title, description, target_lang)
        original_title = translated_title
        description = translated_desc
    
    # 取得對應語言的前綴
    title_prefix = get_title_prefix(target_lang)
    description_prefix = get_desc_prefix(target_lang)
    
    # 加上前綴
    item_name = title_prefix + original_title
    item_name = item_name[:120]  # 蝦皮標題上限 120 字
    
    description = description_prefix + description
    description = description[:3000]  # 蝦皮描述上限
    
    # 決定品牌名稱
    # 優先順序：override > Shopify vendor > No Brand
    if brand_name_override and brand_name_override != "No Brand" and brand_name_override != "use_shopify":
        brand_name = brand_name_override
    elif brand_name_override == "use_shopify":
        brand_name = shopify_product.get("vendor", "") or "No Brand"
    else:
        brand_name = "No Brand"
    
    # 建立蝦皮商品資料
    shopee_product = {
        "original_price": price if price >= 10 else 100,  # 最低價格 10 台幣，沒價格則設 100
        "description": description,
        "item_name": item_name,
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
        "item_status": "NORMAL",  # 直接上架
        # 品牌資訊（必填）
        "brand": {
            "brand_id": 0,  # 0 = 無品牌/自訂品牌
            "original_brand_name": brand_name if brand_name else "No Brand"
        }
    }
    
    # 加入尺碼表（如果有）
    if size_chart_id:
        shopee_product["size_chart"] = size_chart_id
    
    # 處理多規格商品
    if has_variants and options:
        # 蝦皮最多支援 2 層規格
        tier_variation = []
        
        # 處理第一層規格
        if len(options) >= 1:
            opt1 = options[0]
            opt1_name = opt1.get("name", "規格")
            opt1_values = opt1.get("values", [])
            if opt1_values:
                tier_variation.append({
                    "name": opt1_name[:20],  # 規格名稱最多 20 字
                    "option_list": [{"option": str(v)[:20]} for v in opt1_values]  # 選項最多 20 字
                })
        
        # 處理第二層規格（如果有）
        if len(options) >= 2:
            opt2 = options[1]
            opt2_name = opt2.get("name", "規格2")
            opt2_values = opt2.get("values", [])
            if opt2_values:
                tier_variation.append({
                    "name": opt2_name[:20],
                    "option_list": [{"option": str(v)[:20]} for v in opt2_values]
                })
        
        # 建立選項值到索引的對照表
        opt1_index_map = {}
        opt2_index_map = {}
        
        if len(tier_variation) >= 1:
            for idx, opt in enumerate(tier_variation[0].get("option_list", [])):
                opt1_index_map[opt.get("option")] = idx
        
        if len(tier_variation) >= 2:
            for idx, opt in enumerate(tier_variation[1].get("option_list", [])):
                opt2_index_map[opt.get("option")] = idx
        
        # 建立 model（每個變體的價格和庫存）
        model_list = []
        
        for v in variants:
            variant_price = round(float(v.get("price", 0)) * exchange_rate * markup_rate)
            if variant_price < 10:
                variant_price = price if price >= 10 else 100
            
            # 取得該 variant 的庫存數量
            # inventory_quantity 已經在 API 層處理過：null → 10, 0或負數 → 10
            variant_stock = v.get("inventory_quantity", 10)
            if variant_stock is None:
                variant_stock = 10  # 沒追蹤庫存，設為預設值 10
            elif variant_stock <= 0:
                variant_stock = 10  # 庫存為 0 或負數，設為 10
            
            # 取得選項值並找到對應索引
            opt1_val = str(v.get("option1", ""))[:20] if v.get("option1") else None
            opt2_val = str(v.get("option2", ""))[:20] if v.get("option2") else None
            
            tier_index = []
            if opt1_val and opt1_val in opt1_index_map:
                tier_index.append(opt1_index_map[opt1_val])
            if opt2_val and opt2_val in opt2_index_map:
                tier_index.append(opt2_index_map[opt2_val])
            
            if tier_index:  # 只有有對應索引才加入
                model_list.append({
                    "tier_index": tier_index,
                    "original_price": variant_price,
                    "stock": variant_stock
                })
        
        # 加入規格設定到商品資料
        if tier_variation and model_list:
            shopee_product["tier_variation"] = tier_variation
            shopee_product["model"] = model_list
            # 多規格商品：normal_stock 設為 0，seller_stock 保留但設為總庫存
            total_stock = sum(m.get("stock", 0) for m in model_list)
            shopee_product["normal_stock"] = 0
            shopee_product["seller_stock"] = [{"stock": total_stock}]
    
    # 備貨設定：根據參數決定是否較長備貨
    if pre_order:
        shopee_product["pre_order"] = {
            "is_pre_order": True,
            "days_to_ship": days_to_ship
        }
    else:
        # 一般出貨（非較長備貨）
        shopee_product["pre_order"] = {
            "is_pre_order": False
        }
        shopee_product["days_to_ship"] = 2  # 一般出貨預設 2 天
    
    # 商品屬性 - 根據分類 ID 動態設定
    # 食品類分類列表（需要完整食品屬性）
    FOOD_CATEGORY_IDS = [
        100629,  # Food & Beverages
        100656,  # Gift Set & Hampers
        100630,  # Snacks
        100631,  # Beverages
        100632,  # Dairy & Eggs
        100633,  # Breakfast Cereals & Spread
        100634,  # Baking Needs
        100635,  # Cooking Essentials
        100636,  # Food Staples
        100637,  # Convenience / Ready-to-eat
    ]
    
    if category_id in FOOD_CATEGORY_IDS:
        # 食品類分類：使用完整的食品屬性
        shopee_product["attribute_list"] = [
            {
                "attribute_id": 102384,  # Region of Origin (TW) 產地
                "attribute_value_list": [{"value_id": 17007}]  # Japan
            },
            {
                "attribute_id": 101021,  # Pork Origin Region 豬肉產地
                "attribute_value_list": [{"value_id": 5549}]  # No Pork
            },
            {
                "attribute_id": 100095,  # Weight 重量
                "attribute_value_list": [{"value_id": 613}]  # 500g
            },
            {
                "attribute_id": 100010,  # shelf lifes 保存期限
                "attribute_value_list": [{"value_id": 568}]  # 2 Months
            },
            {
                "attribute_id": 100975,  # Liable Company Name
                "attribute_value_list": [{"value_id": 0, "original_value_name": "Omishonin Co., Ltd."}]
            },
            {
                "attribute_id": 100976,  # Liable Company Address
                "attribute_value_list": [{"value_id": 0, "original_value_name": "New Ryogoku Heights 303, 1-28-4 Midori, Sumida-ku, Tokyo, 130-0021, Japan"}]
            },
            {
                "attribute_id": 100977,  # Liable Company Tel No.
                "attribute_value_list": [{"value_id": 0, "original_value_name": "+81 0366593195"}]
            },
            {
                "attribute_id": 100974,  # Ingredient 成分
                "attribute_value_list": [{"value_id": 0, "original_value_name": "詳見商品包裝"}]
            },
            {
                "attribute_id": 100999,  # Quantity 數量
                "attribute_value_list": [{"value_id": 0, "original_value_name": "1"}]
            },
            {
                "attribute_id": 102564,  # Food Additives 食品添加物
                "attribute_value_list": [{"value_id": 0, "original_value_name": "詳見商品包裝"}]
            },
            {
                "attribute_id": 102565,  # Nutrition Facts 營養標示
                "attribute_value_list": [{"value_id": 0, "original_value_name": "詳見商品包裝"}]
            },
            {
                "attribute_id": 102566,  # GMO Indication 基改標示
                "attribute_value_list": [{"value_id": 0, "original_value_name": "本產品不含基因改造成分"}]
            },
            {
                "attribute_id": 102567,  # Other Regulatory Requirements
                "attribute_value_list": [{"value_id": 0, "original_value_name": "詳見商品包裝"}]
            }
        ]
    else:
        # 非食品類分類：不傳送屬性（讓蝦皮用預設值或創建為草稿）
        # 注意：get_attributes API 被暫停，無法動態獲取屬性 ID
        shopee_product["attribute_list"] = []
    
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


def get_item_base_info(access_token: str, shop_id: int, item_id: int):
    """獲取已上架商品的詳細資訊"""
    debug_info = {"step": "get_item_base_info", "item_id": item_id}
    
    try:
        path = "/api/v2/product/get_item_base_info"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}&item_id_list={item_id}"
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        
        if data.get("error") == "":
            item_list = data.get("response", {}).get("item_list", [])
            if item_list:
                item = item_list[0]
                # 提取屬性資訊
                attributes = item.get("attribute_list", [])
                return {
                    "success": True,
                    "item_id": item_id,
                    "item_name": item.get("item_name"),
                    "category_id": item.get("category_id"),
                    "attributes": attributes,
                    "brand": item.get("brand", {}),
                    "debug": debug_info
                }
            else:
                return {
                    "success": False,
                    "error": "商品不存在",
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


def get_item_list(access_token: str, shop_id: int, offset: int = 0, page_size: int = 100, item_status: str = "NORMAL"):
    """
    取得蝦皮商品列表
    item_status: NORMAL, BANNED, DELETED, UNLIST
    """
    debug_info = {"step": "get_item_list", "offset": offset, "page_size": page_size}
    
    try:
        path = "/api/v2/product/get_item_list"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        url += f"&offset={offset}&page_size={page_size}&item_status={item_status}"
        
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        
        if data.get("error") == "":
            items = data.get("response", {}).get("item", [])
            has_next = data.get("response", {}).get("has_next_page", False)
            total = data.get("response", {}).get("total_count", 0)
            debug_info["items_count"] = len(items)
            return {
                "success": True,
                "items": items,
                "has_next": has_next,
                "total": total,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "items": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "items": [],
            "debug": debug_info
        }


def get_item_base_info(access_token: str, shop_id: int, item_id_list: list):
    """
    取得商品基本資訊（包含價格）
    item_id_list: 最多 50 個 item_id
    """
    debug_info = {"step": "get_item_base_info", "item_count": len(item_id_list)}
    
    try:
        path = "/api/v2/product/get_item_base_info"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        # item_id_list 要用逗號分隔
        item_ids_str = ",".join(str(i) for i in item_id_list)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        url += f"&item_id_list={item_ids_str}"
        
        debug_info["url"] = url
        
        response = requests.get(url, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["error"] = data.get("error", "")
        
        if data.get("error") == "":
            items = data.get("response", {}).get("item_list", [])
            debug_info["items_returned"] = len(items)
            return {
                "success": True,
                "items": items,
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": data.get("message", data.get("error")),
                "items": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "items": [],
            "debug": debug_info
        }


def update_price(access_token: str, shop_id: int, item_id: int, price: float):
    """
    更新商品價格
    """
    debug_info = {"step": "update_price", "item_id": item_id, "new_price": price}
    
    try:
        path = "/api/v2/product/update_price"
        timestamp = get_timestamp()
        sign = generate_shop_sign(path, timestamp, access_token, shop_id)
        
        url = f"{HOST}{path}?partner_id={PARTNER_ID}&timestamp={timestamp}&access_token={access_token}&shop_id={shop_id}&sign={sign}"
        debug_info["url"] = url
        
        # 請求 body
        body = {
            "item_id": item_id,
            "price_list": [
                {
                    "original_price": price
                }
            ]
        }
        debug_info["request_body"] = body
        
        response = requests.post(url, json=body, timeout=30)
        debug_info["status_code"] = response.status_code
        
        data = response.json()
        debug_info["response"] = data
        
        if data.get("error") == "":
            return {
                "success": True,
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


def search_item_by_name(access_token: str, shop_id: int, item_name: str, all_items: list = None):
    """
    用名稱搜尋蝦皮商品
    如果提供 all_items，從中搜尋；否則從 API 取得
    返回找到的 item_id 或 None
    """
    # 清理搜尋名稱（去掉前綴後比對）
    search_name = item_name.replace("日本代購 日本直送 GOYOUTATI ", "").strip().lower()
    
    if all_items is None:
        # 從 API 取得所有商品
        all_items = []
        offset = 0
        while True:
            result = get_item_list(access_token, shop_id, offset=offset, page_size=100)
            if not result.get("success"):
                break
            items = result.get("items", [])
            all_items.extend(items)
            if not result.get("has_next"):
                break
            offset += 100
    
    # 搜尋匹配的商品
    for item in all_items:
        item_id = item.get("item_id")
        # 需要再取得完整資訊才有名稱
    
    return None, all_items  # 暫時返回 None，需要用 get_item_base_info 取得名稱
