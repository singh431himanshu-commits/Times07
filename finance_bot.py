import os
import json
import time
import random
import argparse
from datetime import datetime
from openai import OpenAI
from ddgs import DDGS
import config
from PIL import Image, ImageEnhance
import requests
from io import BytesIO

# Groq Client Initialization
def get_next_client():
    key = random.choice(config.GROQ_KEYS)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

client = get_next_client()

def make_pro_image(base_image):
    """फोटो को 16:9 में क्रॉप करता है और HD लुक के लिए कलर्स को एन्हांस करता है[cite: 6]"""
    target_ratio = 16 / 9
    img_ratio = base_image.width / base_image.height
    
    if img_ratio > target_ratio:
        new_width = int(target_ratio * base_image.height)
        offset = (base_image.width - new_width) // 2
        base_image = base_image.crop((offset, 0, offset + new_width, base_image.height))
    elif img_ratio < target_ratio:
        new_height = int(base_image.width / target_ratio)
        offset = (base_image.height - new_height) // 2
        base_image = base_image.crop((0, offset, base_image.width, offset + new_height))
        
    enhancer = ImageEnhance.Color(base_image)
    base_image = enhancer.enhance(1.15)
    return base_image

def apply_watermark_to_image(img_url, output_filename):
    """इमेज को प्रो-लेवल बनाकर फिक्स टॉप-राइट वॉटरमार्क लगाता है[cite: 6]"""
    fallback_list = [
        img_url,
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1000",
        "https://images.unsplash.com/photo-1590283603385-18ff38593524?w=1000"
    ]
    
    for current_url in fallback_list:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(current_url, headers=headers, timeout=8)
            
            if 'image' not in response.headers.get('content-type', ''):
                continue
                
            raw_image = Image.open(BytesIO(response.content)).convert("RGBA")
            base_image = make_pro_image(raw_image)
            
            logo_path = "logo.png"
            if not os.path.exists(logo_path):
                break
                
            logo = Image.open(logo_path).convert("RGBA")
            basewidth = int(base_image.width * 0.16)
            wpercent = (basewidth / float(logo.size[0]))
            hsize = int(float(logo.size[1]) * float(wpercent))
            logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
            
            margin_x = int(base_image.width * 0.02)
            margin_y = int(base_image.height * 0.03)
            position = (base_image.width - logo.width - margin_x, margin_y)
            
            base_image.paste(logo, position, logo)
            
            os.makedirs("static/watermarked", exist_ok=True)
            save_path = f"static/watermarked/{output_filename}"
            
            rgb_image = base_image.convert("RGB")
            rgb_image.save(save_path, "JPEG", quality=95)
            
            return f"/{save_path}"
        except Exception as e:
            print(f"⚠️ Watermark Process Error: {e}")
            continue
            
    return "/logo.png"

def search_hd_finance_images(query, count=5):
    """फाइनेंस के लिए स्मार्ट HD इमेज सर्च और वॉटरमार्क प्रोसेसिंग"""
    images = []
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} stock market finance high resolution", max_results=count))
            for i, res in enumerate(results):
                if 'image' in res:
                    raw_url = res['image']
                    unique_name = f"fin_{int(time.time())}_{i}.jpg"
                    watermarked_url = apply_watermark_to_image(raw_url, unique_name)
                    images.append(watermarked_url)
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Switching to Fallback...")
    
    fallback_hd = [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1000",
        "https://images.unsplash.com/photo-1590283603385-18ff38593524?w=1000",
        "https://images.unsplash.com/photo-1642543492481-44e81e39148c?w=1000"
    ]
    
    if len(images) < count:
        for i, fallback_url in enumerate(random.sample(fallback_hd, min(count - len(images), len(fallback_hd)))):
            unique_name = f"fin_fallback_{int(time.time())}_{i}.jpg"
            watermarked_url = apply_watermark_to_image(fallback_url, unique_name)
            images.append(watermarked_url)
        
    return images[:count]

def fetch_live_finance_news():
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            news_results = list(ddgs.news("share market cryptocurrency finance breaking news", max_results=5))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_finance_draft(topic_context):
    prompt = f"""
    आप भारत के नंबर 1 फाइनेंशियल एनालिस्ट और Times07 News के एक्सपर्ट रिपोर्टर हैं।
    विषय: '{topic_context}'.
    सख्त निर्देश:
    1. भाषा: शुद्ध और प्रोफेशनल हिंदी (PURE HINDI).
    2. गहराई: कम से कम 500 से 700 शब्दों में विस्तार से समझाएं।
    3. संरचना: 4-5 हेडिंग्स (<h3>) शामिल करें।
    4. 5 कैंची टाइटल्स जनरेट करें और अंत में ' | Times07 News' लगाएं।

    Return strictly a VALID JSON object (NO markdown formatting, just raw JSON):
    {{
      "title_options": [
        "पहला टाइटल | Times07 News", 
        "दूसरा टाइटल | Times07 News", 
        "तीसरा टाइटल | Times07 News", 
        "चौथा टाइटल | Times07 News", 
        "पांचवा टाइटल | Times07 News"
      ],
      "meta_description": "SEO मेटा डिस्क्रिप्शन",
      "hashtags": ["#Times07News", "#ShareMarket", "#Crypto", "#FinanceIndia"],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "बिजनेस",
      "default_tags": ["शेयर बाजार", "क्रिप्टोकरेंसी", "फाइनेंस"]
    }}
    """

    available_keys = config.GROQ_KEYS.copy()
    random.shuffle(available_keys)
    
    response_content = None
    for key in available_keys:
        try:
            temp_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            response = temp_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=6000, 
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content.strip()
            break
        except Exception as e:
            continue

    if not response_content:
        return None

    try:
        data = json.loads(response_content)
        data["image_options"] = search_hd_finance_images(topic_context, count=5)
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "finance_crypto"
        data["id"] = int(datetime.now().timestamp() * 1000)
        return data
    except Exception as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None

def save_to_drafts(draft_data):
    drafts_file = "drafts_finance.json"
    drafts = []
    if os.path.exists(drafts_file):
        try:
            with open(drafts_file, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except Exception:
            drafts = []
    drafts.insert(0, draft_data)
    with open(drafts_file, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=4)
    print(f"✅ SUCCESS: Pro Watermarked Finance Draft saved to drafts_finance.json!")

def run_finance_bot_batch():
    print("\n📈 Finance Bot Running PRO Batch Execution...")
    live_news_list = fetch_live_finance_news()
    evergreen_finance_topics = [
        "Nifty 50 and Sensex Market Prediction", 
        "Bitcoin Price Analysis Today", 
        "Best Penny Stocks to Buy"
    ]
    random.shuffle(evergreen_finance_topics)
    
    generated_count = 0
    for news in live_news_list:
        if generated_count >= 5: 
            break
        draft = generate_finance_draft(topic_context=news)
        if draft:
            save_to_drafts(draft)
            generated_count += 1

    topic_index = 0
    while generated_count < 5 and topic_index < len(evergreen_finance_topics):
        draft = generate_finance_draft(topic_context=evergreen_finance_topics[topic_index])
        if draft:
            save_to_drafts(draft)
            generated_count += 1
        topic_index += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str)
    args = parser.parse_args()
    if args.topic:
        draft = generate_finance_draft(topic_context=args.topic)
        if draft: save_to_drafts(draft)
    else:
        while True:
            run_finance_bot_batch()
            os.system('git add -A ; git commit -m "Auto Post Update" ; git push origin main')
            time.sleep(3600)