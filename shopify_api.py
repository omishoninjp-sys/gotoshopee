"""
Shopify API 模組
用於從 Shopify 獲取商品資料
"""
import requests
from config import SHOPIFY_STORE, SHOPIFY_ACCESS_TOKEN


class ShopifyAPI:
    def __init__(self):
        self.store = SHOPIFY_STORE
        self.access_token = SHOPIFY_ACCESS_TOKEN
        self.api_version = "2024-01"
        self.base_url = f"https://{self.store}/admin/api/{self.api_version}"
        
    def _request(self, method, endpoint, params=None, json_data=None):
        """發送 API 請求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {
                "success": False, 
                "error": str(e),
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
            }
    
    def get_products(self, limit=50, collection_id=None, product_type=None):
        """
        獲取商品列表
        
        Args:
            limit: 每次獲取的數量
            collection_id: 系列 ID（可選）
            product_type: 商品類型（可選）
        """
        params = {"limit": limit}
        if collection_id:
            params["collection_id"] = collection_id
        if product_type:
            params["product_type"] = product_type
            
        return self._request("GET", "/products.json", params=params)
    
    def get_product(self, product_id):
        """獲取單一商品詳情"""
        return self._request("GET", f"/products/{product_id}.json")
    
    def get_collections(self, limit=50):
        """獲取所有系列（Custom Collections）"""
        result = self._request("GET", "/custom_collections.json", params={"limit": limit})
        return result
    
    def get_smart_collections(self, limit=50):
        """獲取智慧型系列（Smart Collections）"""
        result = self._request("GET", "/smart_collections.json", params={"limit": limit})
        return result
    
    def get_all_collections(self):
        """獲取所有系列（包含 Custom 和 Smart）"""
        collections = []
        
        # 獲取 Custom Collections
        custom = self.get_collections(limit=250)
        if custom.get("success") and custom.get("data", {}).get("custom_collections"):
            for c in custom["data"]["custom_collections"]:
                collections.append({
                    "id": c["id"],
                    "title": c["title"],
                    "type": "custom",
                    "handle": c.get("handle", "")
                })
        
        # 獲取 Smart Collections
        smart = self.get_smart_collections(limit=250)
        if smart.get("success") and smart.get("data", {}).get("smart_collections"):
            for c in smart["data"]["smart_collections"]:
                collections.append({
                    "id": c["id"],
                    "title": c["title"],
                    "type": "smart",
                    "handle": c.get("handle", "")
                })
        
        return collections
    
    def get_products_in_collection(self, collection_id, limit=1):
        """獲取某個系列中的商品（包含完整 variants 資料）"""
        # 使用 /products.json?collection_id= 來獲取完整商品資料（包含 variants）
        result = self._request(
            "GET", 
            f"/products.json",
            params={"collection_id": collection_id, "limit": limit}
        )
        return result
    
    def test_connection(self):
        """測試 API 連線"""
        if not self.access_token:
            return {
                "success": False,
                "error": "SHOPIFY_ACCESS_TOKEN 未設定"
            }
        
        result = self._request("GET", "/shop.json")
        if result.get("success"):
            shop = result["data"].get("shop", {})
            return {
                "success": True,
                "shop_name": shop.get("name"),
                "domain": shop.get("domain"),
                "email": shop.get("email")
            }
        return result
