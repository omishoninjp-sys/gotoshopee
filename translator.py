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

# 標題後綴（根據目標語言）- 放在標題最後面以優化 SEO
# 品牌/商品名稱應該放在最前面
TITLE_SUFFIX = {
    "zh-TW": " | 日本代購 日本直送 GOYOUTATI",
    "th": " | นำเข้าญี่ปุ่น GOYOUTATI",  # 日本進口 GOYOUTATI
    "en": " | Japan Import GOYOUTATI",
    "id": " | Import Jepang GOYOUTATI",
    "vi": " | Nhập Nhật Bản GOYOUTATI",
    "pt": " | Importação Japão GOYOUTATI",
    "ms": " | Import Jepun GOYOUTATI",
}

# 描述前綴（根據目標語言）
DESC_PREFIX = {
    "zh-TW": "🇯🇵 日本代購 日本直送 GOYOUTATI\n📦 7日內出貨\n\n",
    "th": "🇯🇵 นำเข้าจากญี่ปุ่นแท้ ของแท้ 100% การันตี\n💯 ไม่แท้ยินดีคืนเงิน\n📦 จัดส่งภายใน 7 วัน\n🏷️ GOYOUTATI\n\n",
    "en": "🇯🇵 100% Authentic Japan Import - Guaranteed\n💯 Not authentic? Full refund!\n📦 Ships within 7 days\n🏷️ GOYOUTATI\n\n",
    "id": "🇯🇵 100% Asli Import Jepang - Garansi\n💯 Tidak asli? Uang kembali!\n📦 Dikirim dalam 7 hari\n🏷️ GOYOUTATI\n\n",
    "vi": "🇯🇵 100% Chính hãng Nhật - Cam kết\n💯 Không chính hãng? Hoàn tiền!\n📦 Giao hàng trong 7 ngày\n🏷️ GOYOUTATI\n\n",
    "pt": "🇯🇵 100% Original Japão - Garantido\n💯 Não é original? Reembolso!\n📦 Envio em até 7 dias\n🏷️ GOYOUTATI\n\n",
    "ms": "🇯🇵 100% Asli Import Jepun - Jaminan\n💯 Bukan asli? Wang dikembalikan!\n📦 Dihantar dalam 7 hari\n🏷️ GOYOUTATI\n\n",
}

# 各國 SEO 翻譯提示（針對電商平台優化）
SEO_PROMPTS = {
    "th": {
        "title": """你是專業的泰國電商 SEO 專家和翻譯。
請將以下日本商品標題翻譯成泰文，並優化 Shopee Thailand 的搜索排名。

**🚨 最重要規則：所有中文/日文必須翻譯成泰文！**
輸出中絕對不可以出現任何中文或日文字元！

**Shopee 泰國 SEO 最佳標題格式（務必遵守）：**
品牌名 + 商品名 + 商品類型(泰文) + ของแท้

**常見商品類型翻譯：**
- 帆布袋/トートバッグ → กระเป๋าผ้า
- 零錢包 → กระเป๋าใส่เหรียญ
- 卡片夾 → กระเป๋าใส่บัตร
- 鐵盒/缶 → กล่องเหล็ก
- 娃娃/ぬいぐるみ → ตุ๊กตา
- 鞋子 → รองเท้า
- 衣服/Tシャツ → เสื้อ
- 項鍊/ネックレス → สร้อยคอ
- 刺繡 → ปัก
- 限定版 → รุ่นพิเศษ

**範例：**
- 「Human Made 帆布袋」→「Human Made กระเป๋าผ้า Canvas Bag ของแท้」
- 「Onitsuka Tiger MEXICO 66」→「Onitsuka Tiger MEXICO 66 รองเท้า ของแท้」
- 「SANRIO Hello Kitty 娃娃」→「SANRIO Hello Kitty ตุ๊กตา ของแท้」
- 「Human Made 零錢包」→「Human Made กระเป๋าใส่เหรียญ Coin Pouch ของแท้」
- 「刺繡 T-shirt」→「เสื้อยืดปัก T-shirt ของแท้」

**重要規則：**
1. 品牌名稱放在最前面（英文/日文原文）
2. 商品名稱/型號緊跟在品牌後面
3. 商品類型用泰文（กระเป๋า=包包, ตุ๊กตา=娃娃, เสื้อ=衣服, รองเท้า=鞋子）
4. 結尾加 ของแท้ (正品)
5. 標題控制在 60 字元以內（因為還會加上後綴）
6. 不要加 GOYOUTATI（系統會自動加在後面）

**禁止使用的詞彙：**
- พร้อมส่ง (現貨)
- พรีออเดอร์ (預購)
- นำเข้าจากญี่ปุ่น (系統會自動加)

只輸出翻譯結果：""",
        
        "description": """你是專業的泰國電商文案專家。
請將以下日本商品描述翻譯成泰文，並優化 Shopee Thailand 的轉換率。

**🚨 最重要規則：所有中文/日文必須翻譯成泰文！**
絕對不可以在輸出中出現任何中文或日文字元！

**常見詞彙對照表（務必翻譯）：**
- 型號 / 型番 → รุ่น
- 品番 / 商品番号 → หมายเลขสินค้า
- 顏色 / カラー → สี
- 尺寸 / サイズ → ขนาด
- 素材 / 材質 → วัสดุ
- 刺繡 / 刺しゅう → ปัก
- 限定 → รุ่นพิเศษ / Limited Edition
- 新品 → สินค้าใหม่
- 預約 / 予約 → จองล่วงหน้า
- 發售日 / 発売日 → วันวางจำหน่าย
- 日本製 → ผลิตในญี่ปุ่น
- 正品 / 本物 → ของแท้
- 附贈 / 付属 → แถม / รวม
- 數量限定 → จำนวนจำกัด

**泰國熱賣店家常用的信任關鍵詞（務必加入）：**
1. ✅ ของแท้ 100% การันตี (100%正品保證)
2. 💯 ไม่แท้ยินดีคืนเงิน (不是正品願意退款)
3. 🇯🇵 นำเข้าจากญี่ปุ่นแท้ (正宗日本進口)
4. 📦 จัดส่งภายใน 7 วัน (7日內出貨)
5. 🏆 สินค้าคุณภาพสูง (高品質商品)

**泰國消費者喜歡看到的內容：**
- 使用 emoji 增加可讀性 ✅ 💯 🇯🇵 📦 🎁
- 條列式說明商品特點
- 加入尺寸、材質等實用資訊
- 語氣友善親切，像朋友推薦

**重要：不要使用以下詞彙：**
- พร้อมส่ง (現貨)
- พรีออเดอร์ (預購)

**泰國人在意的點：**
- 是不是正品？→ 強調 ของแท้ 100% การันตี
- 假貨怎麼辦？→ 加入 ไม่แท้ยินดีคืนเงิน
- 多久會收到？→ 說明 7 日內出貨
- 有什麼保障？→ 強調日本直送、品質保證

**品牌名稱、型號代碼（如 1181A119）、尺寸數字保持原文，但標籤文字必須用泰文。**
例如：「型號: 1181A119」→「รุ่น: 1181A119」

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
6. DO NOT use "In Stock", "Ready to Ship", "Pre-order"

Output translation only:""",
        
        "description": """You are an e-commerce copywriter. Translate this Japanese product description to English, optimized for conversion.

Include:
1. Highlight "100% Authentic Japan Import"
2. Mention "Ships within 7 days"
3. Use bullet points for features
4. Include practical info (size, material)
5. Friendly, trustworthy tone
6. Use emojis sparingly

DO NOT use "In Stock", "Ready to Ship", "Pre-order" - just say "Ships within 7 days".

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
6. JANGAN gunakan "Ready Stock", "Siap Kirim", "PO", "Pre-order"

Output terjemahan saja:""",
        
        "description": """Kamu adalah copywriter e-commerce. Terjemahkan deskripsi produk Jepang ini ke Bahasa Indonesia.

Sertakan:
1. Tekankan "100% Original Import Jepang"
2. Jelaskan "Dikirim dalam 7 hari"
3. Gunakan bullet points
4. Info praktis (ukuran, bahan)
5. Nada ramah dan terpercaya
6. Gunakan emoji secukupnya

JANGAN gunakan "Ready Stock", "Siap Kirim", "PO", "Pre-order".

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
6. KHÔNG dùng "Có sẵn", "Giao ngay", "Pre-order"

Chỉ xuất bản dịch:""",
        
        "description": """Bạn là copywriter thương mại điện tử. Dịch mô tả sản phẩm Nhật này sang tiếng Việt.

Bao gồm:
1. Nhấn mạnh "100% Chính hãng Nhật Bản"
2. Giải thích "Giao hàng trong 7 ngày"
3. Dùng bullet points
4. Thông tin thực tế (kích thước, chất liệu)
5. Giọng điệu thân thiện, đáng tin cậy
6. Dùng emoji vừa phải

KHÔNG dùng "Có sẵn", "Giao ngay", "Pre-order".

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
6. DO NOT use "In Stock", "Ready to Ship", "Pre-order"

Output translation only:""",
    
    "description": """You are an e-commerce copywriter. Translate this Japanese product description to {lang_name}.

Include:
1. Highlight authenticity and Japan import
2. Mention "Ships within 7 days"
3. Use bullet points for features
4. Practical info (size, material)
5. Friendly, trustworthy tone

DO NOT use "In Stock", "Ready to Ship", "Pre-order".

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


def get_title_suffix(target_lang: str) -> str:
    """取得標題後綴（SEO 優化：品牌在前，GOYOUTATI 在後）"""
    return TITLE_SUFFIX.get(target_lang, TITLE_SUFFIX["en"])


def get_title_prefix(target_lang: str) -> str:
    """取得標題前綴（已棄用，改用 get_title_suffix）"""
    # 為了向後兼容，返回空字串
    return ""


def get_desc_prefix(target_lang: str) -> str:
    """取得描述前綴"""
    return DESC_PREFIX.get(target_lang, DESC_PREFIX["en"])
