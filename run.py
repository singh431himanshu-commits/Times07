import os
import json
import requests
import feedparser
import logging
from bs4 import BeautifulSoup
from newspaper import Article
from ddgs import DDGS
import time
import re
import random
import urllib.parse
from PIL import Image, ImageEnhance
import io
from io import BytesIO
import base64
from datetime import datetime
from openai import OpenAI

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"
STATS_URL = "https://times07news-default-rtdb.firebaseio.com/bot_stats.json"

# 🔑 GROQ API Keys
import config
GROQ_KEYS = config.GROQ_KEYS

CHECK_INTERVAL_MINUTES = 30

# 📝 Logging System
logging.basicConfig(
    filename='bot.log', level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
error_logger = logging.getLogger('ErrorLogger')
error_handler = logging.FileHandler('error.log')
error_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
error_logger.addHandler(error_handler)

TRUSTED_RSS_SOURCES = [
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC News", "trust_score": 100},
    {"url": "https://pib.gov.in/RssMain.aspx?ModId=6&LangId=1", "source": "PIB India", "trust_score": 95},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "trust_score": 90},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "NY Times", "trust_score": 88},
    {"url": "https://www.aajtak.in/rss/feed/index.xml", "source": "Aaj Tak", "trust_score": 85},
    {"url": "https://ndtv.in/rss/top-stories", "source": "NDTV India", "trust_score": 85},
    {"url": "https://www.amarujala.com/rss/breaking-news.xml", "source": "Amar Ujala", "trust_score": 80}
]

def get_next_client():
    key = random.choice(GROQ_KEYS)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

def update_bot_stats(stat_type):
    stats = {"published": 0, "skipped": 0, "duplicate": 0, "failed": 0, "ai_errors": 0}
    try:
        res = requests.get(STATS_URL, timeout=5)
        if res.status_code == 200 and res.json():
            stats.update(res.json())
    except: pass
    stats[stat_type] = stats.get(stat_type, 0) + 1
    try:
        requests.put(STATS_URL, json=stats, timeout=5)
    except: pass

def normalize_text(text):
    return re.sub(r'\W+', '', text.lower())

def get_db_data():
    """डुप्लीकेट चेक करने के लिए Firebase से पुरानी खबरें लाना"""
    pub_links, pub_titles = set(), set()
    try:
        res = requests.get(FIREBASE_URL, timeout=10)
        if res.status_code == 200 and isinstance(res.json(), dict):
            for val in res.json().values():
                if isinstance(val, dict):
                    if "link" in val: pub_links.add(val["link"])
                    if "title" in val: pub_titles.add(normalize_text(val["title"].replace(" | Times07News", "")))
    except: pass
    return pub_links, pub_titles
def generate_sitemap():
    try:
        res = requests.get(FIREBASE_URL, timeout=10)

        urls = [{
            "loc": "https://times07news.in/",
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d")
        }]

        if res.status_code == 200 and isinstance(res.json(), dict):
            for item in res.json().values():
                if not isinstance(item, dict):
                    continue

                link = item.get("link")
                if link:
                    urls.append({
                        "loc": link,
                        "lastmod": datetime.utcnow().strftime("%Y-%m-%d")
                    })

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

        for u in urls:
            xml += f"""  <url>
    <loc>{u['loc']}</loc>
    <lastmod>{u['lastmod']}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
"""

        xml += "</urlset>"

        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(xml)

        print("✅ sitemap.xml updated")

    except Exception as e:
        print("Sitemap Error:", e)

def ping_google():
    try:
        sitemap_url = "https://times07news.in/sitemap.xml"

        requests.get(
            f"https://www.google.com/ping?sitemap={sitemap_url}",
            timeout=10
        )

        print("✅ Google Ping Sent")

    except Exception as e:
        print("Google Ping Error:", e)

def fetch_google_trends():
    trends = []
    try:
        feed = feedparser.parse("https://trends.google.com/trending/rss?geo=IN")
        for entry in feed.entries[:5]: trends.append(entry.title)
    except: pass
    return trends

# ==========================================
# 🌟 PRO IMAGE LOGIC (With Watermark)
# ==========================================
def make_pro_image(base_image):
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
    return enhancer.enhance(1.15)

def apply_watermark_to_image(img_url, output_filename):
    fallback_list = [
        img_url
]

    for current_url in fallback_list:
                
        try:
            headers = {"User-Agent": "Mozilla/5.0"}

            response = requests.get(
                current_url,
                headers=headers,
                timeout=8
            )
            if len(response.content) < 150000:
                continue


            print("Downloading:", current_url)
            print("Status:", response.status_code)
            print("Type:", response.headers.get("content-type"))

            if "image" not in response.headers.get("content-type", ""):
                continue

            raw_image = Image.open(BytesIO(response.content)).convert("RGBA")
            base_image = make_pro_image(raw_image)

            # Logo
            logo_path = "logo.png"
            if os.path.exists(logo_path):
                logo = Image.open(logo_path).convert("RGBA")

                basewidth = int(base_image.width * 0.16)
                wpercent = basewidth / float(logo.width)
                hsize = int(float(logo.height) * wpercent)

                logo = logo.resize(
                    (basewidth, hsize),
                    Image.Resampling.LANCZOS
                )

                margin_x = int(base_image.width * 0.02)
                margin_y = int(base_image.height * 0.03)

                position = (
                    base_image.width - logo.width - margin_x,
                    margin_y
                )

                base_image.paste(logo, position, logo)

            # Resize Image
            base_image = base_image.resize(
                (1280, 720),
                Image.Resampling.LANCZOS
            )

            # Save Folder
            os.makedirs("static/watermarked", exist_ok=True)

            save_path = f"static/watermarked/{output_filename}"

            rgb_image = base_image.convert("RGB")

            rgb_image.save(
                save_path,
                "JPEG",
                quality=75,
                optimize=True,
                progressive=True
)

            return f"https://times07news.in/{save_path}"

        except Exception as e:
            print(f"Image Error: {e}")
            continue

    return "/logo.png"
def search_hd_images(query, count=5):
    images = []

    try:
        time.sleep(2)

        search_queries = [
            f'"{query}" official news photo',
            f'"{query}" India news',
            f'"{query}" latest event',
            query
        ]

        with DDGS() as ddgs:

            results = []

            for q in search_queries:

                print("🔍 Trying:", q)

                try:
                    temp = list(ddgs.images(
                        query=q,
                        region="in-en",
                        safesearch="on",
                        size="Large",
                        type_image="photo",
                        layout="Wide",
                        max_results=25
                    ))

                    results.extend(temp)
                    results = list({
                        item.get("image"): item
                        for item in results
                        if item.get("image")
                    }.values())

                    if len(results) >= 80:
                        break

                except:
                    pass

            
            print("🔎 Total Images Found:", len(results))

            for i, res in enumerate(results):

                if "image" not in res:
                    continue

                raw_url = res["image"]

                title = str(res.get("title", "")).lower()
                source = str(res.get("source", "")).lower()
                query_words = query.lower().split()

                matched = 0

                for word in query_words:
                    if len(word) >= 4 and word in title:
                        matched += 1

                if matched == 0 and len(query_words) > 1:
                    continue                             

                if any(x in source for x in [
                    "pinterest",
                    "shutterstock",
                    "freepik",
                    "istock",
                    "alamy"
                ]):
                    continue

                if any(x in title for x in [
                    "youtube",
                    "thumbnail",
                    "logo",
                    "poster",
                    "wallpaper",
                    "stock",
                    "vector",
                    "illustration",
                    "clipart",
                    "template",
                    "mockup",
                    "3d render"
                ]):
                    continue

                if "ytimg.com" in raw_url:
                    continue

                if "ytimg.com" in raw_url:
                    continue

                if raw_url.lower().endswith(".gif"):
                    continue

                if raw_url.lower().endswith(".svg"):
                    continue
                width = int(res.get("width") or 0)
                height = int(res.get("height") or 0)

                if width < 1000:
                     continue

                if height < 600:
                     continue     
               
                print("IMG:", raw_url)


                unique_name = f"trend_{int(time.time())}_{i}.jpg"

                watermarked_url = apply_watermark_to_image(
                    raw_url,
                    unique_name
                )

                if watermarked_url != "/logo.png":
                    images.append(watermarked_url)

                if len(images) >= count:
                    break

    except Exception as e:
        print("Search Error:", e)


    return images[:count]

# ==========================================
# 🔄 AI DRAFT GENERATOR (For Admin Panel)
# ==========================================
def generate_trending_draft(raw_title, raw_text=""):
    prompt = f"""
    आप Times07 News के सबसे बड़े जर्नलिस्ट हैं।
    विषय: {raw_title}
    संदर्भ/Context: {raw_text[:1200]}

    सख्त निर्देश:
    1. यह पूरी तरह से तथ्यात्मक (Factual) और न्यूज़ चैनल जैसी हिंदी होनी चाहिए।
    2. 500-800 शब्दों में विस्तृत खबर लिखें (H3 हेडिंग्स और <p> टैग्स के साथ)।
    3. 5 SEO फ्रेंडली टाइटल्स जनरेट करें। हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं।
    4. खबर में जिस व्यक्ति, जगह, घटना या विषय की फोटो सबसे सही होगी, उसके लिए 2-5 शब्दों का image_keyword भी दो। उदाहरण: "Narendra Modi", "Virat Kohli", "ISRO Chandrayaan", "Delhi Rain".

    Return strictly a VALID JSON object (NO markdown):
    {{
      "title_options": [
        "पहला टाइटल | Times07 News",
        "दूसरा टाइटल | Times07 News",
        "तीसरा टाइटल | Times07 News",
        "चौथा टाइटल | Times07 News",
        "पांचवा टाइटल | Times07 News"
      ],
      "one_line_teaser": "1-लाइन का ब्रेकिंग न्यूज़ टीज़र",
      "visual_summary_points": ["पॉइंट 1", "पॉइंट 2", "पॉइंट 3"],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "मुख्य समाचार",
      "default_tags": ["#TrendingNews", "#LatestUpdate", "#Times07"]
      "image_keyword": "2-5 words related to the main person, place or event"
    }}
    """

    available_keys = GROQ_KEYS.copy()
    random.shuffle(available_keys)
    
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]
    
    for key in available_keys:
        for model in models:
            try:
                temp_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
                response = temp_client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4,
                    max_tokens=2000,
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content.strip())

                # Smart Image Search
                search_keyword = raw_title

                # Remove extra words
                search_keyword = re.sub(r"\|.*", "", search_keyword)
                search_keyword = re.sub(r"\b20\d{2}\b", "", search_keyword)

                remove_words = [
                    "जानें", "देखें", "Live", "Breaking",
                    "ब्रेकिंग", "Today", "Latest",
                    "News", "न्यूज", "अपडेट",
                    "क्या", "कैसे", "कब",
                    "क्यों", "और", "का", "की", "के"
                ]

                for word in remove_words:
                    search_keyword = search_keyword.replace(word, "")

                search_keyword = " ".join(search_keyword.split())

                print("🔍 Image Search:", search_keyword)

                image_query = data.get("image_keyword", search_keyword)

                print("🖼️ AI Image Keyword:", image_query)

                data["image_options"] = search_hd_images(
                    image_query,
                    count=5
                )
                
                
                
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["bot_type"] = "trending"
                data["id"] = int(datetime.now().timestamp() * 1000)
                return data
            except Exception as e:
                error_logger.error(f"Groq API Error on model {model}: {e}")
                continue
    return None

def save_to_drafts(draft_data):
    drafts_file = "drafts_trending.json"
    drafts = []
    if os.path.exists(drafts_file):
        try:
            with open(drafts_file, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except: pass
        
    drafts.insert(0, draft_data)
    with open(drafts_file, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=4)
        
    print(f"✅ SUCCESS: Trending Draft saved to drafts_trending.json! Check your Dashboard.")

def run_bot():
    print("\n🔍 Engine Active: Scanning Google Trends & RSS Feeds...")
    pub_links, pub_titles = get_db_data()
    candidates = []

    # Google Trends & News
    gt_topics = fetch_google_trends()
    for topic in gt_topics:
        encoded_q = urllib.parse.quote(topic)
        trend_rss = f"https://news.google.com/rss/search?q={encoded_q}&hl=hi&gl=IN&ceid=IN:hi"
        feed = feedparser.parse(trend_rss)
        for entry in feed.entries[:2]:
            candidates.append({"entry": entry, "source_name": "Google Trends"})

    for src in TRUSTED_RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:2]:
                candidates.append({"entry": entry, "source_name": src["source"]})
        except: pass

    generated_count = 0
    for item in candidates:
        if generated_count >= 4: # एक बार में सिर्फ 4 ड्राफ्ट्स बनाएगा
            break
            
        entry = item["entry"]
        source_name = item["source_name"]
        news_title = getattr(entry, 'title', '')
        news_url = getattr(entry, 'link', '')

        norm_t = normalize_text(news_title)
        if news_url in pub_links or norm_t in pub_titles: 
            update_bot_stats("duplicate")
            continue

        print(f"\n📰 [Processing & Reading Article]: {news_title[:55]}...")
        raw_text = ""
        try:
            # 🚀 Newspaper3k restored: पूरी खबर अंदर जाकर पढ़ेगा
            art = Article(news_url)
            art.download()
            art.parse()
            raw_text = art.text
        except: pass

        draft = generate_trending_draft(news_title, raw_text)
        
        if draft and "title_options" in draft:
            save_to_drafts(draft)
            generated_count += 1
            update_bot_stats("published")
            generate_sitemap()
        else:
            update_bot_stats("skipped")

        time.sleep(3)
        generate_sitemap()

if __name__ == "__main__":
    print("🚀 Times07 Master Draft Bot Active...")
    while True:
        try:
            run_bot()
        except Exception as e:
            error_logger.error(f"Main loop crash prevented: {e}")
        
        os.system('git add -A ; git commit -m "Auto Post Update" ; git push origin main')
        print(f"\n⏰ Waiting {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)