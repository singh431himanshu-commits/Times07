import os
import json
import time
import random
import argparse
from datetime import datetime
from openai import OpenAI
from ddgs import DDGS
import config
from PIL import Image
import requests
from io import BytesIO

# Groq Client Initialization
def get_next_client():
    key = random.choice(config.GROQ_KEYS)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

client = get_next_client()

def apply_watermark_to_image(img_url, output_filename):
    """डाउनलोड की गई HD इमेज पर आपके logo.png को ऑटोमैटिक वॉटरमार्क के रूप में लगाता है"""
    try:
        # 1. हेडर के साथ इमेज डाउनलोड करें ताकि वेबसाइट ब्लॉक न करे
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(img_url, headers=headers, timeout=10)
        
        # 2. चेक करें कि क्या यह वाकई एक इमेज फाइल है या नहीं
        content_type = response.headers.get('content-type', '')
        if 'image' not in content_type:
            return img_url # अगर इमेज नहीं है, तो चुपचाप ओरिजिनल यूआरएल लौटा दो
            
        base_image = Image.open(BytesIO(response.content)).convert("RGBA")
        
        # 3. आपका अपना logo.png लोड करें
        logo_path = "logo.png"
        if not os.path.exists(logo_path):
            return img_url 
            
        logo = Image.open(logo_path).convert("RGBA")
        
        # 4. लोगो का साइज़ सेट करें
        basewidth = int(base_image.width * 0.18)
        wpercent = (basewidth / float(logo.size[0]))
        hsize = int(float(logo.size[1]) * float(wpercent))
        logo = logo.resize((basewidth, hsize), Image.Resampling.LANCZOS)
        
        # 5. पोजीशन (Bottom Right Corner)
        margin = 20
        position = (base_image.width - logo.width - margin, base_image.height - logo.height - margin)
        
        # 6. वॉटरमार्क चिपकाएं
        base_image.paste(logo, position, logo)
        
        # 7. सेव करें
        os.makedirs("static/watermarked", exist_ok=True)
        save_path = f"static/watermarked/{output_filename}"
        
        rgb_image = base_image.convert("RGB")
        rgb_image.save(save_path, "JPEG", quality=95)
        
        return f"/{save_path}"
    except Exception as e:
        # अब एरर आने पर बोट रुकेगा नहीं, सीधे ओरिजिनल यूआरएल इस्तेमाल कर लेगा
        return img_url
def search_hd_images(query, count=5):
    """गूगल/DuckDuckGo से वर्ल्ड न्यूज़ की HD इमेजेस लाकर उनपर वॉटरमार्क लगाता है"""
    images = []
    try:
        time.sleep(2)
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} accident breaking news high resolution real photo", max_results=count))
            for i, res in enumerate(results):
                if 'image' in res:
                    raw_url = res['image']
                    # हर इमेज पर वॉटरमार्क प्रोसेस करें
                    unique_name = f"news_{int(time.time())}_{i}.jpg"
                    watermarked_url = apply_watermark_to_image(raw_url, unique_name)
                    images.append(watermarked_url)
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Using Fallback...")
    
    # Fallback imagesअगर कम मिलें
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
    """अंतरराष्ट्रीय ट्रेंडिंग न्यूज़ फेच करता है (USA, Russia, France आदि)"""
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            news_results = list(ddgs.news("international breaking news accident USA UK France Russia -India", max_results=3))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_worldnews_draft(topic_context=None):
    """बोट का मेन AI जनरेटर लॉजिक जो 429 एरर आने पर ऑटोमैटिक दूसरी API Key पर स्विच हो जाएगा"""
    
    prompt_instruction = f"""
    विषय: अंतरराष्ट्रीय ब्रेकिंग न्यूज़ (International News & Accidents) - '{topic_context}'.
    
    सख्त निर्देश (CRITICAL COMMAND - DO NOT IGNORE):
    1. यह खबर पूरी तरह से अंतरराष्ट्रीय होनी चाहिए (भारत से बाहर, जैसे USA, France, Russia आदि)।
    2. शब्द सीमा: पूरी खबर का सिर्फ एक सटीक और क्रिस्प सारांश (Summary) दें जो अधिकतम 150 से 200 शब्दों का हो।
    3. टोन: गंभीर, तथ्यात्मक (Factual) और अंतरराष्ट्रीय न्यूज़ चैनल जैसी हिंदी होनी चाहिए।
    4. हैशटैग नियम: समरी पैराग्राफ के बिल्कुल अंत में, ट्रेंडिंग हैशटैग्स और जिस देश की खबर है, उस देश का नाम हैशटैग के रूप में जरूर लिखें (जैसे: #Trending #WorldNews #USA #Accident)।
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

    # 🔑 स्मार्ट की-रोटेशन लूप: config.py की सारी कीज़ को बारी-बारी ट्राई करेगा
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
                max_tokens=1000,  # टोकन लिमिट बचाने के लिए 3000 से घटाकर 1000 किया गया
                response_format={"type": "json_object"}
            )
            response_content = response.choices[0].message.content.strip()
            break  # अगर सक्सेसफुल हो गया तो लूप से बाहर आ जाओ
        except Exception as e:
            print(f"⚠️ API Key limit hit or failed, switching to next key... Error: {e}")
            continue

    if not response_content:
        print("❌ All API Keys are rate-limited or exhausted!")
        return None

    try:
        data = json.loads(response_content)
        
        search_keyword = topic_context if topic_context else "World News Accident"
        data["image_options"] = search_hd_images(search_keyword, count=5)
        
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "world_news"
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
        
    print(f"✅ SUCCESS: Watermarked World News Draft saved to drafts.json!")

def run_world_bot_batch():
    print("\n🌍 World News Bot Running PRO Batch Execution with Watermarking...")
    
    live_news_list = fetch_live_trending_news()
    
    world_topics = [
        "Major highway accident in USA California", 
        "Train derailment emergency in France", 
        "Massive factory fire breaking news in Russia", 
        "Severe weather storm damage in USA Texas"
    ]
    random.shuffle(world_topics)
    
    generated_count = 0
    
    for news in live_news_list[:3]:
        print(f"📰 Generating News Draft for: {news[:40]}...")
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

    print(f"✨ BATCH COMPLETE: 3 Watermarked Short World News sent to Dashboard!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help='Manual command to generate a specific topic')
    args = parser.parse_args()

    if args.topic:
        print(f"⚡ Manual Command Received for: {args.topic}")
        draft = generate_worldnews_draft(topic_context=args.topic)
        if draft: 
            save_to_drafts(draft)
            print("✅ Manual Watermarked Topic Generated Successfully!")
    else:
        print("🚀 PRO World News Bot Service Started (Auto-runs every 1 hour)...")
        while True:
            run_world_bot_batch()
            print("⏰ Sleeping for 1 Hour (3600 Seconds)...")
            time.sleep(3600)