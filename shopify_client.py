"""
Shopify API 客戶端
"""
import os
import requests

SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE", "goyoutati.myshopify.com")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN", "")

def get_headers():
    """取得 Shopify API headers"""
    return {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

def get_base_url():
    """取得 Shopify API base URL"""
    return f"https://{SHOPIFY_STORE}/admin/api/2024-01"

def test_connection():
    """測試 Shopify 連線"""
    debug_info = {
        "store": SHOPIFY_STORE,
        "has_token": bool(SHOPIFY_ACCESS_TOKEN),
        "token_length": len(SHOPIFY_ACCESS_TOKEN) if SHOPIFY_ACCESS_TOKEN else 0
    }
    
    if not SHOPIFY_ACCESS_TOKEN:
        return {
            "success": False,
            "error": "SHOPIFY_ACCESS_TOKEN 環境變數未設定",
            "debug": debug_info
        }
    
    try:
        url = f"{get_base_url()}/shop.json"
        response = requests.get(url, headers=get_headers(), timeout=10)
        debug_info["status_code"] = response.status_code
        debug_info["response"] = response.json() if response.status_code == 200 else response.text[:500]
        
        if response.status_code == 200:
            return {
                "success": True,
                "shop": response.json().get("shop", {}),
                "debug": debug_info
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "debug": debug_info
        }

def get_collections():
    """取得所有 Collections"""
    debug_info = {"step": "get_collections"}
    
    try:
        # 取得 Custom Collections
        url = f"{get_base_url()}/custom_collections.json?limit=250"
        response = requests.get(url, headers=get_headers(), timeout=30)
        debug_info["custom_collections_status"] = response.status_code
        
        custom_collections = []
        if response.status_code == 200:
            custom_collections = response.json().get("custom_collections", [])
        
        # 取得 Smart Collections
        url = f"{get_base_url()}/smart_collections.json?limit=250"
        response = requests.get(url, headers=get_headers(), timeout=30)
        debug_info["smart_collections_status"] = response.status_code
        
        smart_collections = []
        if response.status_code == 200:
            smart_collections = response.json().get("smart_collections", [])
        
        all_collections = custom_collections + smart_collections
        debug_info["total_collections"] = len(all_collections)
        
        return {
            "success": True,
            "collections": all_collections,
            "debug": debug_info
        }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "collections": [],
            "debug": debug_info
        }

def get_products_in_collection(collection_id, limit=1):
    """取得 Collection 中的商品"""
    debug_info = {"step": "get_products_in_collection", "collection_id": collection_id, "limit": limit}
    
    try:
        url = f"{get_base_url()}/collections/{collection_id}/products.json?limit={limit}"
        response = requests.get(url, headers=get_headers(), timeout=30)
        debug_info["status_code"] = response.status_code
        
        if response.status_code == 200:
            products = response.json().get("products", [])
            debug_info["products_count"] = len(products)
            return {
                "success": True,
                "products": products,
                "debug": debug_info
            }
        else:
            debug_info["response"] = response.text[:500]
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "products": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "products": [],
            "debug": debug_info
        }

def get_all_products(limit=50):
    """取得所有商品（不分 collection）"""
    debug_info = {"step": "get_all_products", "limit": limit}
    
    try:
        url = f"{get_base_url()}/products.json?limit={limit}"
        response = requests.get(url, headers=get_headers(), timeout=30)
        debug_info["status_code"] = response.status_code
        
        if response.status_code == 200:
            products = response.json().get("products", [])
            debug_info["products_count"] = len(products)
            return {
                "success": True,
                "products": products,
                "debug": debug_info
            }
        else:
            debug_info["response"] = response.text[:500]
            return {
                "success": False,
                "error": f"HTTP {response.status_code}",
                "products": [],
                "debug": debug_info
            }
    except Exception as e:
        debug_info["exception"] = str(e)
        return {
            "success": False,
            "error": str(e),
            "products": [],
            "debug": debug_info
        }
