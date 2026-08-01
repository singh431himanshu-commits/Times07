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
        "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=1000",
        "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=1000"
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

def search_hd_images(query, count=5):
    """गूगल/DuckDuckGo से HD इमेजेस फेच करके वॉटरमार्क लगाता है"""
    images = []
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} high resolution recent photo", max_results=count))
            for i, res in enumerate(results):
                if 'image' in res:
                    raw_url = res['image']
                    unique_name = f"bolly_{int(time.time())}_{i}.jpg"
                    watermarked_url = apply_watermark_to_image(raw_url, unique_name)
                    images.append(watermarked_url)
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Switching to Fallback...")
    
    fallback_hd = [
        "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=1000",
        "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=1000",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=1000"
    ]
    
    if len(images) < count:
        for i, fallback_url in enumerate(random.sample(fallback_hd, min(count - len(images), len(fallback_hd)))):
            unique_name = f"bolly_fallback_{int(time.time())}_{i}.jpg"
            watermarked_url = apply_watermark_to_image(fallback_url, unique_name)
            images.append(watermarked_url)
        
    return images[:count]

def fetch_live_trending_news():
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            news_results = list(ddgs.news("Bollywood viral gossip breaking news india", max_results=3))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_bollywood_draft(topic_context=None, is_biography=False):
    if is_biography:
        prompt_instruction = f"""
        विषय: बॉलीवुड सुपरस्टार बायोग्राफी (Biography Special) - '{topic_context}'.
        सख्त निर्देश:
        1. यह एक बेहद विस्तृत और प्रो-लेवल बायोग्राफी होनी चाहिए (Wikipedia स्टाइल में)। 
        2. शब्द सीमा: कम से कम 1200 से 1500 शब्दों का प्रयोग करें।
        3. कम से कम 6-7 अलग-अलग हेडिंग्स (<h3>) शामिल करें: प्रारंभिक जीवन, फिल्मी करियर, टर्निंग पॉइंट, लव लाइफ, नेट वर्थ, आने वाले प्रोजेक्ट्स।
        4. टोन: मसालेदार और रोचक।
        """
    else:
        prompt_instruction = f"""
        विषय: बॉलीवुड ताज़ा ब्रेकिंग / गॉसिप खबर - '{topic_context}'.
        सख्त निर्देश:
        1. टोन एकदम चटपटा और मसाला स्टाइल।
        2. कम से कम 4 सब-हेडिंग्स (<h3>) जरूर होनी चाहिए।
        3. 500-800 शब्दों में <p> टैग्स के साथ लिखें।
        """

    prompt = f"""
    आप Times07 News के सबसे बड़े एंटरटेनमेंट जर्नलिस्ट हैं।
    {prompt_instruction}

    CRITICAL REQUIREMENTS:
    1. WRITE EVERYTHING STRICTLY IN PURE HINDI (हिंदी भाषा में).
    2. 5 चटपटे और SEO फ्रेंडली टाइटल्स जनरेट करें।
    3. हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं।

    Return strictly a VALID JSON object (NO markdown formatting, just raw JSON):
    {{
      "title_options": [
        "पहला चटपटा टाइटल | Times07 News",
        "दूसरा वायरल टाइटल | Times07 News",
        "तीसरा सस्पेंस टाइटल | Times07 News",
        "चौथा बड़ा खुलासा टाइटल | Times07 News",
        "पांचवा ट्रेंडिंग टाइटल | Times07 News"
      ],
      "one_line_teaser": "हिंदी में 1-लाइन का मसालेदार टीज़र",
      "visual_summary_points": ["मुख्य बिंदु 1", "मुख्य बिंदु 2", "मुख्य बिंदु 3", "मुख्य बिंदु 4"],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "मनोरंजन",
      "default_tags": ["#BollywoodGossip", "#Times07Exclusive", "#CelebUpdate"]
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
                temperature=0.6,
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
        search_keyword = topic_context if topic_context else "Bollywood Stars"
        data["image_options"] = search_hd_images(search_keyword, count=5)
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "bollywood"
        data["id"] = int(datetime.now().timestamp() * 1000)
        return data
    except Exception as e:
        print(f"❌ JSON Parsing Error: {e}")
        return None

def save_to_drafts(draft_data):
    drafts_file = "drafts.json"
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
    print(f"✅ SUCCESS: Pro Watermarked Bollywood Draft saved to drafts.json!")

def run_bollywood_bot_batch():
    print("\n🎬 Bollywood Bot Running PRO Batch Execution...")
    live_news_list = fetch_live_trending_news()
    famous_actors = [
        "Shah Rukh Khan", "Salman Khan", "Deepika Padukone", "Ranbir Kapoor", 
        "Amitabh Bachchan", "Alia Bhatt", "Hrithik Roshan", "Kareena Kapoor"
    ]
    random.shuffle(famous_actors)
    
    generated_count = 0
    for news in live_news_list[:3]:
        draft = generate_bollywood_draft(topic_context=news, is_biography=False)
        if draft:
            save_to_drafts(draft)
            generated_count += 1

    actor_index = 0
    while generated_count < 3 and actor_index < len(famous_actors):
        draft = generate_bollywood_draft(topic_context=famous_actors[actor_index], is_biography=True)
        if draft:
            save_to_drafts(draft)
            generated_count += 1
        actor_index += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str)
    args = parser.parse_args()
    if args.topic:
        draft = generate_bollywood_draft(topic_context=args.topic, is_biography=True)
        if draft: save_to_drafts(draft)
   else:
        while True:
            run_bollywood_bot_batch()
            os.system('git add -A ; git commit -m "Auto Post Update" ; git push origin main')
            time.sleep(3600)