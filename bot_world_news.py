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
    """फोटो को 16:9 में क्रॉप करता है और HD लुक के लिए कलर्स को एन्हांस करता है"""
    # 1. 16:9 Aspect Ratio Cropping
    target_ratio = 16 / 9
    img_ratio = base_image.width / base_image.height
    
    if img_ratio > target_ratio:
        # इमेज बहुत चौड़ी है, किनारों से काटें
        new_width = int(target_ratio * base_image.height)
        offset = (base_image.width - new_width) // 2
        base_image = base_image.crop((offset, 0, offset + new_width, base_image.height))
    elif img_ratio < target_ratio:
        # इमेज बहुत लंबी है, ऊपर-नीचे से काटें
        new_height = int(base_image.width / target_ratio)
        offset = (base_image.height - new_height) // 2
        base_image = base_image.crop((0, offset, base_image.width, offset + new_height))
        
    # 2. HD Color Enhancement (कलर्स को 15% बढ़ाएं)
    enhancer = ImageEnhance.Color(base_image)
    base_image = enhancer.enhance(1.15)
    
    return base_image

def apply_watermark_to_image(img_url, output_filename):
    """इमेज को प्रो-लेवल बनाकर फिक्स टॉप-राइट वॉटरमार्क लगाता है"""
    fallback_list = [
        img_url,
        "https://images.unsplash.com/photo-1524850011238-e3d235c7d4c9?w=1000",
        "https://images.unsplash.com/photo-1567113463300-102a7eb3cb26?w=1000",
        "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=1000"
    ]
    
    for current_url in fallback_list:
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            response = requests.get(current_url, headers=headers, timeout=8)
            
            if 'image' not in response.headers.get('content-type', ''):
                continue
                
            raw_image = Image.open(BytesIO(response.content)).convert("RGBA")
            
            # 🌟 प्रो फीचर: इमेज को 16:9 में काटो और कलर्स निखारो
            base_image = make_pro_image(raw_image)
            
            logo_path = "logo.png"
            if not os.path.exists(logo_path):
                break
                
            logo = Image.open(logo_path).convert("RGBA")
            
            # 🌟 प्रो फीचर: लोगो का फिक्स साइज़ (इमेज का 16%)
            basewidth = int(base_image.width * 0.16)
            wpercent = (basewidth / float(logo.size[0]))
            hsize = int(float(logo.size[1]) * float(wpercent))
            logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
            
            # 🌟 प्रो फीचर: फिक्स मैथमेटिकल पोज़िशन (Top-Right)
            margin_x = int(base_image.width * 0.02) # चौड़ाई का 2% मार्जिन
            margin_y = int(base_image.height * 0.03) # ऊंचाई का 3% मार्जिन
            position = (base_image.width - logo.width - margin_x, margin_y)
            
            # चिपकाएं
            base_image.paste(logo, position, logo)
            
            # सेव करें
            os.makedirs("static/watermarked", exist_ok=True)
            save_path = f"static/watermarked/{output_filename}"
            
            rgb_image = base_image.convert("RGB")
            rgb_image.save(save_path, "JPEG", quality=95)
            
            return f"/{save_path}"
        except Exception as e:
            print(f"⚠️ Watermark Process Error: {e}")
            continue
            
    return "/logo.png"

def search_hd_images(query, count=5):
    """स्मार्ट HD न्यूज़ इमेज सर्च (बिना फालतू कीवर्ड के)"""
    images = []
    try:
        time.sleep(2)
        # सिर्फ ज़रूरी कीवर्ड्स रखे गए हैं ताकि हर तरह की खबर की सही फोटो आए
        search_query = f"{query} high resolution real news photography"
        with DDGS() as ddgs:
            results = list(ddgs.images(search_query, max_results=count))
            for i, res in enumerate(results):
                if 'image' in res:
                    raw_url = res['image']
                    unique_name = f"news_{int(time.time())}_{i}.jpg"
                    watermarked_url = apply_watermark_to_image(raw_url, unique_name)
                    images.append(watermarked_url)
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Using Fallback...")
    
    fallback_hd = [
        "https://images.unsplash.com/photo-1524850011238-e3d235c7d4c9?w=1000",
        "https://images.unsplash.com/photo-1567113463300-102a7eb3cb26?w=1000",
        "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=1000"
    ]
    
    if len(images) < count:
        for i, fallback_url in enumerate(random.sample(fallback_hd, min(count - len(images), len(fallback_hd)))):
            unique_name = f"fallback_{int(time.time())}_{i}.jpg"
            watermarked_url = apply_watermark_to_image(fallback_url, unique_name)
            images.append(watermarked_url)
        
    return images[:count]

def fetch_live_trending_news():
    """पूरी दुनिया की रियल-टाइम ट्रेंडिंग न्यूज़ फेच करता है"""
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            news_results = list(ddgs.news("international breaking news today global world -India", max_results=5))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_worldnews_draft(topic_context=None):
    """बोट का मेन AI जनरेटर लॉजिक"""
    
    prompt_instruction = f"""
    विषय: अंतरराष्ट्रीय न्यूज़ (International News) - '{topic_context}'.
    
    सख्त निर्देश (CRITICAL COMMAND - DO NOT IGNORE):
    1. यह खबर पूरी तरह से अंतरराष्ट्रीय होनी चाहिए (भारत से बाहर)।
    2. शब्द सीमा: पूरी खबर का सिर्फ एक सटीक और क्रिस्प सारांश (Summary) दें जो अधिकतम 150 से 200 शब्दों का हो।
    3. टोन: गंभीर, तथ्यात्मक (Factual) और अंतरराष्ट्रीय न्यूज़ चैनल जैसी हिंदी होनी चाहिए।
    4. हैशटैग नियम: समरी पैराग्राफ के बिल्कुल अंत में, ट्रेंडिंग हैशटैग्स और जिस देश की खबर है, उस देश का नाम हैशटैग के रूप में जरूर लिखें।
    """

    prompt = f"""
    आप Times07 News के सबसे बड़े अंतरराष्ट्रीय संवाददाता हैं।
    {prompt_instruction}

    CRITICAL REQUIREMENTS:
    1. WRITE EVERYTHING STRICTLY IN PURE HINDI (हिंदी भाषा में).
    2. 5 SEO फ्रेंडली टाइटल्स जनरेट करें (title_options में 5 ऑप्शंस दें).
    3. हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं.

    Return strictly a VALID JSON object (NO markdown formatting, just raw JSON):
    {{
      "title_options": [
        "पहला टाइटल | Times07 News",
        "दूसरा टाइटल | Times07 News",
        "तीसरा टाइटल | Times07 News",
        "चौथा टाइटल | Times07 News",
        "पांचवा टाइटल | Times07 News"
      ],
      "one_line_teaser": "हिंदी में 1-लाइन का ब्रेकिंग न्यूज़ टीज़र",
      "visual_summary_points": [
        "मुख्य बिंदु 1", "मुख्य बिंदु 2", "मुख्य बिंदु 3"
      ],
      "content_html": "<p>200 शब्दों की पूरी न्यूज़ समरी यहाँ होगी...</p><p><strong>#TrendingNews #WorldNews #CountryName #Breaking</strong></p>",
      "category": "अंतरराष्ट्रीय",
      "default_tags": ["#WorldNews", "#GlobalUpdate", "#Times07Exclusive"]
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
                temperature=0.4,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content.strip()
            break
        except Exception as e:
            print(f"⚠️ API Key limit hit, switching... Error: {e}")
            continue

    if not response_content:
        print("❌ All API Keys are rate-limited!")
        return None

    try:
        data = json.loads(response_content)
        
        # टॉपिक में से कुछ कीवर्ड निकालकर सटीक सर्च करेगा
        search_keyword = topic_context.split()[:4] 
        search_keyword = " ".join(search_keyword) if topic_context else "World News Breaking"
        
        data["image_options"] = search_hd_images(search_keyword, count=5)
        
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "world_news"
        data["id"] = int(datetime.now().timestamp() * 1000)
        
        return data
    except Exception as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None

def save_to_drafts(draft_data):
    drafts_file = "drafts_world.json"
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
        
    print(f"✅ SUCCESS: HD Pro-Watermarked Draft saved to drafts_world.json!")

def run_world_bot_batch():
    print("\n🌍 Running PRO World News Bot (With HD Auto-Crop & Fixed Watermark)...")
    
    live_news_list = fetch_live_trending_news()
    
    world_topics = [
        "Technology AI latest global updates",
        "Massive protests in Europe today",
        "Huge business merger international",
        "Climate change severe weather alerts",
        "Space mission successful launch"
    ]
    random.shuffle(world_topics)
    
    generated_count = 0
    
    for news in live_news_list[:3]:
        print(f"📰 Generating News Draft for: {news[:50]}...")
        draft = generate_worldnews_draft(topic_context=news)
        if draft:
            save_to_drafts(draft)
            generated_count += 1

    topic_index = 0
    while generated_count < 3 and topic_index < len(world_topics):
        topic = world_topics[topic_index]
        print(f"🚨 Generating News Draft for Topic: {topic}...")
        draft = generate_worldnews_draft(topic_context=topic)
        if draft:
            save_to_drafts(draft)
            generated_count += 1
        topic_index += 1

    print(f"✨ BATCH COMPLETE: 3 HD PRO World News sent to Dashboard!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help='Manual command to generate a specific topic')
    args = parser.parse_args()

    if args.topic:
        print(f"⚡ Manual Command Received for: {args.topic}")
        draft = generate_worldnews_draft(topic_context=args.topic)
        if draft: 
            save_to_drafts(draft)
            print("✅ Manual Topic Generated Successfully!")
    else:
      print("🚀 ULTRA-PRO World News Bot Started...")
        while True:
            run_world_bot_batch()
            os.system('git add -A ; git commit -m "Auto Post Update" ; git push origin main')
            time.sleep(3600)