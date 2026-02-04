"""
商品同步邏輯
"""
import shopify_client
import shopee_product

def run_test_sync(access_token: str, shop_id: int, test_category_id: int = None):
    """
    執行測試同步
    - 每個 Collection 只同步 1 個商品
    - 詳細記錄每個步驟的 debug 資訊
    """
    results = {
        "success": False,
        "steps": [],
        "synced_products": [],
        "errors": [],
        "debug": {}
    }
    
    # ============ Step 1: 測試 Shopify 連線 ============
    step1 = {"step": "1. 測試 Shopify 連線", "status": "pending"}
    shopify_test = shopify_client.test_connection()
    step1["result"] = shopify_test
    
    if not shopify_test["success"]:
        step1["status"] = "failed"
        results["steps"].append(step1)
        results["errors"].append(f"Shopify 連線失敗: {shopify_test.get('error')}")
        return results
    
    step1["status"] = "success"
    step1["shop_name"] = shopify_test.get("shop", {}).get("name", "N/A")
    results["steps"].append(step1)
    
    # ============ Step 2: 取得蝦皮分類 ============
    step2 = {"step": "2. 取得蝦皮分類", "status": "pending"}
    categories_result = shopee_product.get_categories(access_token, shop_id)
    step2["result"] = categories_result
    
    if not categories_result["success"]:
        step2["status"] = "failed"
        results["steps"].append(step2)
        results["errors"].append(f"取得蝦皮分類失敗: {categories_result.get('error')}")
        # 繼續執行，使用預設分類
    else:
        step2["status"] = "success"
        step2["categories_count"] = len(categories_result.get("categories", []))
    
    results["steps"].append(step2)
    
    # 選擇一個測試分類（如果沒有指定）
    if test_category_id is None:
        categories = categories_result.get("categories", [])
        # 找一個有子分類的分類
        for cat in categories:
            if cat.get("has_children") == False:  # 找沒有子分類的（葉子分類）
                test_category_id = cat.get("category_id")
                break
        if test_category_id is None and categories:
            test_category_id = categories[0].get("category_id")
    
    results["debug"]["selected_category_id"] = test_category_id
    
    # ============ Step 3: 取得蝦皮物流 ============
    step3 = {"step": "3. 取得蝦皮物流", "status": "pending"}
    logistics_result = shopee_product.get_logistics(access_token, shop_id)
    step3["result"] = logistics_result
    
    if not logistics_result["success"]:
        step3["status"] = "failed"
        results["steps"].append(step3)
        results["errors"].append(f"取得物流失敗: {logistics_result.get('error')}")
    else:
        step3["status"] = "success"
        step3["logistics_count"] = len(logistics_result.get("logistics", []))
        # 取得可用的物流 ID
        enabled_logistics = [
            l for l in logistics_result.get("logistics", [])
            if l.get("enabled", False)
        ]
        step3["enabled_logistics"] = [l.get("logistics_channel_id") for l in enabled_logistics[:3]]
    
    results["steps"].append(step3)
    results["debug"]["logistics"] = logistics_result.get("logistics", [])[:5]
    
    # ============ Step 4: 取得 Shopify Collections ============
    step4 = {"step": "4. 取得 Shopify Collections", "status": "pending"}
    collections_result = shopify_client.get_collections()
    step4["result"] = collections_result
    
    if not collections_result["success"]:
        step4["status"] = "failed"
        results["steps"].append(step4)
        results["errors"].append(f"取得 Collections 失敗: {collections_result.get('error')}")
        return results
    
    collections = collections_result.get("collections", [])
    step4["status"] = "success"
    step4["collections_count"] = len(collections)
    step4["collection_names"] = [c.get("title", "N/A") for c in collections[:10]]
    results["steps"].append(step4)
    
    if not collections:
        # 如果沒有 collections，直接取所有商品
        results["errors"].append("沒有找到 Collections，改為取得所有商品")
        all_products_result = shopify_client.get_all_products(limit=5)
        if all_products_result["success"]:
            collections = [{"id": "all", "title": "所有商品", "_products": all_products_result["products"][:1]}]
    
    # ============ Step 5: 同步每個 Collection 的 1 個商品 ============
    step5 = {"step": "5. 同步商品", "status": "pending", "details": []}
    
    synced_count = 0
    max_sync = 5  # 最多同步 5 個商品（測試用）
    
    for collection in collections:
        if synced_count >= max_sync:
            break
        
        collection_id = collection.get("id")
        collection_title = collection.get("title", "N/A")
        
        sync_detail = {
            "collection": collection_title,
            "collection_id": collection_id,
            "status": "pending"
        }
        
        # 取得該 Collection 的第 1 個商品
        if "_products" in collection:
            # 已經有商品（從 all products 來的）
            products = collection["_products"]
        else:
            products_result = shopify_client.get_products_in_collection(collection_id, limit=1)
            sync_detail["products_fetch"] = products_result.get("debug", {})
            
            if not products_result["success"]:
                sync_detail["status"] = "failed"
                sync_detail["error"] = f"取得商品失敗: {products_result.get('error')}"
                step5["details"].append(sync_detail)
                continue
            
            products = products_result.get("products", [])
        
        if not products:
            sync_detail["status"] = "skipped"
            sync_detail["reason"] = "Collection 內沒有商品"
            step5["details"].append(sync_detail)
            continue
        
        product = products[0]
        sync_detail["shopify_product_id"] = product.get("id")
        sync_detail["shopify_product_title"] = product.get("title", "N/A")
        
        # 上傳圖片
        images = product.get("images", [])
        uploaded_image_ids = []
        sync_detail["images_count"] = len(images)
        sync_detail["image_uploads"] = []
        
        for img in images[:3]:  # 最多上傳 3 張圖
            img_url = img.get("src", "")
            if not img_url:
                continue
            
            upload_result = shopee_product.upload_image(access_token, shop_id, img_url)
            sync_detail["image_uploads"].append({
                "url": img_url[:100],
                "success": upload_result["success"],
                "error": upload_result.get("error"),
                "image_id": upload_result.get("image_id")
            })
            
            if upload_result["success"]:
                uploaded_image_ids.append(upload_result["image_id"])
        
        if not uploaded_image_ids:
            sync_detail["status"] = "failed"
            sync_detail["error"] = "沒有成功上傳任何圖片"
            step5["details"].append(sync_detail)
            continue
        
        sync_detail["uploaded_image_ids"] = uploaded_image_ids
        
        # 建立蝦皮商品資料
        shopee_data = shopee_product.shopify_to_shopee_product(
            product,
            test_category_id,
            uploaded_image_ids
        )
        
        # 設定物流
        if step3.get("enabled_logistics"):
            shopee_data["logistic_info"] = [
                {"logistic_id": lid, "enabled": True}
                for lid in step3.get("enabled_logistics", [])[:1]
            ]
        
        sync_detail["shopee_data"] = shopee_data
        
        # 建立商品
        create_result = shopee_product.create_product(access_token, shop_id, shopee_data)
        sync_detail["create_result"] = create_result
        
        if create_result["success"]:
            sync_detail["status"] = "success"
            sync_detail["shopee_item_id"] = create_result.get("item_id")
            results["synced_products"].append({
                "shopify_id": product.get("id"),
                "shopify_title": product.get("title"),
                "shopee_item_id": create_result.get("item_id"),
                "collection": collection_title
            })
            synced_count += 1
        else:
            sync_detail["status"] = "failed"
            sync_detail["error"] = create_result.get("error")
        
        step5["details"].append(sync_detail)
    
    step5["status"] = "completed"
    step5["synced_count"] = synced_count
    results["steps"].append(step5)
    
    # 最終結果
    results["success"] = synced_count > 0
    results["debug"]["total_collections"] = len(collections)
    results["debug"]["synced_count"] = synced_count
    
    return results


def get_sync_preview(access_token: str, shop_id: int):
    """
    取得同步預覽（不實際同步，只顯示會同步什麼）
    """
    preview = {
        "shopify_status": None,
        "shopee_status": None,
        "collections": [],
        "errors": []
    }
    
    # 測試 Shopify
    shopify_test = shopify_client.test_connection()
    preview["shopify_status"] = {
        "connected": shopify_test["success"],
        "shop_name": shopify_test.get("shop", {}).get("name") if shopify_test["success"] else None,
        "error": shopify_test.get("error") if not shopify_test["success"] else None
    }
    
    # 測試蝦皮分類
    categories_result = shopee_product.get_categories(access_token, shop_id)
    preview["shopee_status"] = {
        "connected": categories_result["success"],
        "categories_count": len(categories_result.get("categories", [])),
        "error": categories_result.get("error") if not categories_result["success"] else None
    }
    
    # 取得 Collections 預覽
    if shopify_test["success"]:
        collections_result = shopify_client.get_collections()
        if collections_result["success"]:
            for col in collections_result.get("collections", [])[:10]:
                products_result = shopify_client.get_products_in_collection(col.get("id"), limit=1)
                products = products_result.get("products", [])
                preview["collections"].append({
                    "id": col.get("id"),
                    "title": col.get("title"),
                    "products_count": col.get("products_count", "?"),
                    "first_product": products[0].get("title") if products else None
                })
    
    return preview
