"""
使用 OpenAI ChatGPT API 進行商品翻譯
針對各國電商平台優化 SEO 和當地語言習慣
"""
import requests
from config import OPENAI_API_KEY

# 語言代碼對應
LANGUAGE_NAMES = {
    "zh-TW": "繁體中文",
    "th": "泰文",
    "en": "英文",
    "id": "印尼文",
    "vi": "越南文",
    "pt": "葡萄牙文（巴西）",
    "ms": "馬來文",
}

# 標題前綴（根據目標語言）- 包含當地 SEO 關鍵字
TITLE_PREFIX = {
    "zh-TW": "日本代購 日本直送 GOYOUTATI ",
    "th": "พรีออเดอร์ญี่ปุ่น ส่งตรงจากญี่ปุ่น GOYOUTATI ",  # Pre-order日本 直送日本
    "en": "Japan Import Direct Ship GOYOUTATI ",
    "id": "PO Jepang Impor Langsung GOYOUTATI ",  # PO = Pre-order 印尼常用
    "vi": "Order Nhật Bản Ship Trực Tiếp GOYOUTATI ",
    "pt": "Importação Japão Envio Direto GOYOUTATI ",
    "ms": "PO Jepun Import Terus GOYOUTATI ",
}

# 描述前綴（根據目標語言）
DESC_PREFIX = {
    "zh-TW": "日本代購 日本直送 GOYOUTATI\n\n",
    "th": "🇯🇵 สินค้านำเข้าจากญี่ปุ่น ของแท้ 100%\n📦 ส่งตรงจากญี่ปุ่น\n🏷️ GOYOUTATI\n\n",
    "en": "🇯🇵 100% Authentic Japan Import\n📦 Direct Ship from Japan\n🏷️ GOYOUTATI\n\n",
    "id": "🇯🇵 Barang Asli Import Jepang 100%\n📦 Kirim Langsung dari Jepang\n🏷️ GOYOUTATI\n\n",
    "vi": "🇯🇵 Hàng Nhật chính hãng 100%\n📦 Ship trực tiếp từ Nhật\n🏷️ GOYOUTATI\n\n",
    "pt": "🇯🇵 Produto Original Japão 100%\n📦 Envio Direto do Japão\n🏷️ GOYOUTATI\n\n",
    "ms": "🇯🇵 Barang Asli Import Jepun 100%\n📦 Penghantaran Terus dari Jepun\n🏷️ GOYOUTATI\n\n",
}

# 各國 SEO 翻譯提示（針對電商平台優化）
SEO_PROMPTS = {
    "th": {
        "title": """你是專業的泰國電商 SEO 專家和翻譯。
請將以下日本商品標題翻譯成泰文，並優化 Shopee Thailand 的搜索排名。

**泰國 Shopee SEO 規則：**
1. 加入泰國人常搜索的關鍵字：
   - ของแท้ (正品)、แท้100% (100%正版)
   - พร้อมส่ง (現貨) 或 พรีออเดอร์ (預購)
   - นำเข้าจากญี่ปุ่น (日本進口)
   - ราคาถูก (便宜)、คุณภาพดี (高品質)
2. 商品類型要用泰文（如 กระเป๋า=包包, ตุ๊กตา=娃娃, เสื้อ=衣服）
3. 品牌名稱保持英文/日文原文
4. 標題簡潔有力，適合手機閱讀
5. 不要超過 100 字元

**格式範例：**
「SANRIO Hello Kitty 娃娃」→「ตุ๊กตา SANRIO Hello Kitty ของแท้ นำเข้าญี่ปุ่น」

只輸出翻譯結果：""",
        
        "description": """你是專業的泰國電商文案專家。
請將以下日本商品描述翻譯成泰文，並優化 Shopee Thailand 的轉換率。

**泰國消費者喜歡看到的內容：**
1. 強調「ของแท้」(正品)、「นำเข้าจากญี่ปุ่น」(日本進口)
2. 加入信任元素：✅ สินค้าพร้อมส่ง、📦 จัดส่งเร็ว
3. 使用 emoji 增加可讀性
4. 條列式說明商品特點
5. 加入尺寸、材質等實用資訊
6. 語氣友善親切，像朋友推薦

**泰國人在意的點：**
- 是不是正品？
- 多久會收到？
- 有什麼保障？

品牌名稱、型號、尺寸數字保持原文。
只輸出翻譯結果："""
    },
    
    "en": {
        "title": """You are an e-commerce SEO expert. Translate this Japanese product title to English, optimized for Shopee search.

Rules:
1. Include keywords: "Authentic", "Japan Import", "Original"
2. Keep brand names in original form
3. Product type in English
4. Concise and mobile-friendly
5. Max 100 characters

Output translation only:""",
        
        "description": """You are an e-commerce copywriter. Translate this Japanese product description to English, optimized for conversion.

Include:
1. Highlight "100% Authentic Japan Import"
2. Use bullet points for features
3. Include practical info (size, material)
4. Friendly, trustworthy tone
5. Use emojis sparingly

Keep brand names, model numbers, measurements in original form.
Output translation only:"""
    },
    
    "id": {
        "title": """Kamu adalah ahli SEO e-commerce Indonesia. Terjemahkan judul produk Jepang ini ke Bahasa Indonesia, dioptimalkan untuk Shopee.

Aturan:
1. Tambahkan kata kunci: "Original", "Import Jepang", "Asli 100%"
2. Pertahankan nama merek asli
3. Jenis produk dalam Bahasa Indonesia
4. Ringkas dan mobile-friendly
5. Maksimal 100 karakter

Output terjemahan saja:""",
        
        "description": """Kamu adalah copywriter e-commerce. Terjemahkan deskripsi produk Jepang ini ke Bahasa Indonesia.

Sertakan:
1. Tekankan "100% Original Import Jepang"
2. Gunakan bullet points
3. Info praktis (ukuran, bahan)
4. Nada ramah dan terpercaya
5. Gunakan emoji secukupnya

Pertahankan nama merek, nomor model, ukuran dalam bentuk asli.
Output terjemahan saja:"""
    },
    
    "vi": {
        "title": """Bạn là chuyên gia SEO thương mại điện tử Việt Nam. Dịch tiêu đề sản phẩm Nhật này sang tiếng Việt, tối ưu cho Shopee.

Quy tắc:
1. Thêm từ khóa: "Chính hãng", "Nhập khẩu Nhật", "Auth 100%"
2. Giữ nguyên tên thương hiệu
3. Loại sản phẩm bằng tiếng Việt
4. Ngắn gọn, dễ đọc trên điện thoại
5. Tối đa 100 ký tự

Chỉ xuất bản dịch:""",
        
        "description": """Bạn là copywriter thương mại điện tử. Dịch mô tả sản phẩm Nhật này sang tiếng Việt.

Bao gồm:
1. Nhấn mạnh "100% Chính hãng Nhật Bản"
2. Dùng bullet points
3. Thông tin thực tế (kích thước, chất liệu)
4. Giọng điệu thân thiện, đáng tin cậy
5. Dùng emoji vừa phải

Giữ nguyên tên thương hiệu, mã sản phẩm, số đo.
Chỉ xuất bản dịch:"""
    }
}

# 預設 prompt（其他語言使用）
DEFAULT_SEO_PROMPT = {
    "title": """You are an e-commerce SEO expert. Translate this Japanese product title to {lang_name}, optimized for Shopee search.

Rules:
1. Include keywords indicating authenticity and Japan import
2. Keep brand names in original form
3. Product type in target language
4. Concise and mobile-friendly
5. Max 100 characters

Output translation only:""",
    
    "description": """You are an e-commerce copywriter. Translate this Japanese product description to {lang_name}.

Include:
1. Highlight authenticity and Japan import
2. Use bullet points for features
3. Practical info (size, material)
4. Friendly, trustworthy tone

Keep brand names, model numbers in original form.
Output translation only:"""
}


def translate_text(text: str, target_lang: str, text_type: str = "product") -> str:
    """
    使用 ChatGPT API 翻譯文字（針對電商 SEO 優化）
    
    Args:
        text: 要翻譯的文字
        target_lang: 目標語言代碼 (th, en, id, vi, pt, ms)
        text_type: 文字類型 (title/description)
    
    Returns:
        翻譯後的文字，如果失敗則返回原文
    """
    if not OPENAI_API_KEY:
        print("警告：未設定 OPENAI_API_KEY，跳過翻譯")
        return text
    
    if not text or not text.strip():
        return text
    
    # 如果目標語言是繁體中文，不需要翻譯
    if target_lang == "zh-TW":
        return text
    
    target_lang_name = LANGUAGE_NAMES.get(target_lang, "English")
    
    # 取得對應語言的 SEO 優化 prompt
    if target_lang in SEO_PROMPTS:
        if text_type == "title":
            system_prompt = SEO_PROMPTS[target_lang]["title"]
        else:
            system_prompt = SEO_PROMPTS[target_lang]["description"]
    else:
        # 使用預設 prompt
        if text_type == "title":
            system_prompt = DEFAULT_SEO_PROMPT["title"].format(lang_name=target_lang_name)
        else:
            system_prompt = DEFAULT_SEO_PROMPT["description"].format(lang_name=target_lang_name)
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                "max_tokens": 1500,
                "temperature": 0.3
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            translated = data["choices"][0]["message"]["content"].strip()
            return translated
        else:
            print(f"翻譯 API 錯誤: {response.status_code} - {response.text}")
            return text
            
    except Exception as e:
        print(f"翻譯失敗: {str(e)}")
        return text


def translate_product(title: str, description: str, target_lang: str) -> tuple:
    """
    翻譯商品標題和描述
    
    Args:
        title: 商品標題
        description: 商品描述
        target_lang: 目標語言代碼
    
    Returns:
        (翻譯後的標題, 翻譯後的描述)
    """
    # 如果是繁體中文，不需要翻譯
    if target_lang == "zh-TW":
        return title, description
    
    # 翻譯標題（使用 title 類型的 SEO prompt）
    translated_title = translate_text(title, target_lang, "title")
    
    # 翻譯描述（使用 description 類型的 SEO prompt）
    translated_desc = translate_text(description, target_lang, "description")
    
    return translated_title, translated_desc


def get_title_prefix(target_lang: str) -> str:
    """取得標題前綴"""
    return TITLE_PREFIX.get(target_lang, TITLE_PREFIX["en"])


def get_desc_prefix(target_lang: str) -> str:
    """取得描述前綴"""
    return DESC_PREFIX.get(target_lang, DESC_PREFIX["en"])
