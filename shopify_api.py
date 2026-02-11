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
        self.graphql_url = f"https://{self.store}/admin/api/{self.api_version}/graphql.json"
        
    def _request(self, method, endpoint, params=None, json_data=None):
        """發送 REST API 請求"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
            "Accept-Language": "zh-TW"
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
    
    def _graphql_request(self, query, variables=None):
        """發送 GraphQL API 請求"""
        headers = {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(
                self.graphql_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": str(e)
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
        """獲取某個系列中的商品（使用 GraphQL 獲取繁體中文翻譯）"""
        
        # 使用 GraphQL API 獲取商品及翻譯
        # 加入 status:ACTIVE 只獲取已發布的商品（排除草稿和已封存）
        query = """
        query getProducts($first: Int!) {
            products(first: $first, query: "collection_id:%s AND status:ACTIVE") {
                nodes {
                    id
                    title
                    handle
                    status
                    descriptionHtml
                    vendor
                    productType
                    translations(locale: "zh-TW") {
                        key
                        value
                    }
                    variants(first: 10) {
                        nodes {
                            id
                            title
                            price
                            sku
                            inventoryItem {
                                measurement {
                                    weight {
                                        value
                                        unit
                                    }
                                }
                            }
                        }
                    }
                    images(first: 10) {
                        nodes {
                            url
                            altText
                        }
                    }
                }
            }
        }
        """ % collection_id
        
        result = self._graphql_request(query, {"first": limit})
        
        if not result.get("success"):
            return result
        
        data = result.get("data", {})
        
        # 檢查 GraphQL 錯誤
        if "errors" in data:
            return {
                "success": False,
                "error": str(data["errors"])
            }
        
        # 轉換 GraphQL 格式為 REST API 格式（保持相容性）
        products_data = data.get("data", {}).get("products", {}).get("nodes", [])
        
        products = []
        for p in products_data:
            # 將 GraphQL ID 轉換為數字 ID
            gid = p.get("id", "")
            numeric_id = gid.split("/")[-1] if "/" in gid else gid
            
            # 從 translations 中獲取翻譯後的標題
            title = p.get("title", "")
            body_html = p.get("descriptionHtml", "")
            
            translations = p.get("translations", [])
            for t in translations:
                if t.get("key") == "title" and t.get("value"):
                    title = t.get("value")
                elif t.get("key") == "body_html" and t.get("value"):
                    body_html = t.get("value")
            
            # 轉換 variants
            variants = []
            for v in p.get("variants", {}).get("nodes", []):
                v_gid = v.get("id", "")
                v_numeric_id = v_gid.split("/")[-1] if "/" in v_gid else v_gid
                
                # 獲取重量
                weight = 0
                weight_unit = "g"
                inv_item = v.get("inventoryItem", {})
                if inv_item:
                    measurement = inv_item.get("measurement", {})
                    if measurement:
                        weight_info = measurement.get("weight", {})
                        if weight_info:
                            weight = weight_info.get("value", 0)
                            weight_unit = weight_info.get("unit", "GRAMS").lower()
                
                variants.append({
                    "id": v_numeric_id,
                    "title": v.get("title"),
                    "price": v.get("price"),
                    "sku": v.get("sku"),
                    "weight": weight,
                    "weight_unit": weight_unit
                })
            
            # 轉換 images
            images = []
            for img in p.get("images", {}).get("nodes", []):
                images.append({
                    "src": img.get("url"),
                    "alt": img.get("altText")
                })
            
            products.append({
                "id": numeric_id,
                "title": title,
                "handle": p.get("handle"),
                "body_html": body_html,
                "vendor": p.get("vendor"),
                "product_type": p.get("productType"),
                "variants": variants,
                "images": images
            })
        
        return {
            "success": True,
            "data": {
                "products": products
            }
        }
    
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
