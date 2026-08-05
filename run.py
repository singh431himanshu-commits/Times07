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
from datetime import datetime
from openai import OpenAI

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"
STATS_URL = "https://times07news-default-rtdb.firebaseio.com/bot_stats.json"

import config
GROQ_KEYS = config.GROQ_KEYS

CHECK_INTERVAL_MINUTES = 30

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
    {"url": "https://www.amarujala.com/rss/breaking-news.xml", "source": "Amar Ujala", "trust_score": 80},
    {"url": "https://feeds.zeenews.india.com/hindi/rss/india.xml", "source": "Zee News Hindi", "trust_score": 85},
    {"url": "https://www.abplive.com/home/feed", "source": "ABP News", "trust_score": 85},
    {"url": "https://www.jagran.com/rss/news-national-feed.xml", "source": "Dainik Jagran", "trust_score": 85},
    {"url": "https://navbharattimes.indiatimes.com/rssfeedstopstories.cms", "source": "Navbharat Times", "trust_score": 85},
    {"url": "https://www.bhaskar.com/rss-feed/2331/", "source": "Dainik Bhaskar", "trust_score": 85},
    {"url": "https://www.news18.com/rss/india.xml", "source": "News18 India", "trust_score": 85},
    {"url": "https://www.indiatv.in/rss/india-news.xml", "source": "India TV", "trust_score": 85},
    {"url": "https://www.republicworld.com/rss/india-news.xml", "source": "Republic World", "trust_score": 80}
]

def update_bot_stats(stat_type):
    stats = {"published": 0, "skipped": 0, "duplicate": 0, "failed": 0, "ai_errors": 0}
    try:
        res = requests.get(STATS_URL, timeout=5)
        if res.status_code == 200 and res.json():
            stats.update(res.json())
    except Exception: pass
    stats[stat_type] = stats.get(stat_type, 0) + 1
    try:
        requests.put(STATS_URL, json=stats, timeout=5)
    except Exception: pass

def normalize_text(text):
    return re.sub(r'\W+', '', text.lower())

def get_db_data():
    pub_links, pub_titles = set(), set()
    try:
        res = requests.get(FIREBASE_URL, timeout=10)
        if res.status_code == 200 and isinstance(res.json(), dict):
            for val in res.json().values():
                if isinstance(val, dict):
                    if "link" in val: pub_links.add(val["link"])
                    if "title" in val: pub_titles.add(normalize_text(val["title"]))
    except Exception: pass
    
    if os.path.exists("drafts_trending.json"):
        try:
            with open("drafts_trending.json", "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if "title_options" in item and item["title_options"]:
                        pub_titles.add(normalize_text(item["title_options"][0]))
        except Exception: pass
        
    return pub_links, pub_titles

def fetch_google_trends():
    trends = []
    try:
        feed = feedparser.parse("https://trends.google.com/trending/rss?geo=IN")
        for entry in feed.entries[:15]: trends.append(entry.title)
    except Exception: pass
    return trends

def search_hd_images(query, count=5):
    images = []
    try:
        time.sleep(1)
        search_queries = [f'"{query}" news photo', query]
        with DDGS(timeout=10) as ddgs:
            results = []
            for q in search_queries:
                try:
                    temp = list(ddgs.images(query=q, region="in-en", safesearch="on", max_results=15))
                    results.extend(temp)
                    if len(results) >= 20: break
                except Exception as e:
                    logging.warning(f"DDGS Query Error: {e}")
            
            for res in results:
                raw_url = res.get("image", "")
                title = str(res.get("title", "")).lower()
                source = str(res.get("source", "")).lower()
                
                if not raw_url: continue
                if any(x in source for x in ["pinterest", "shutterstock", "freepik", "istock", "alamy"]): continue
                if any(x in title for x in ["youtube", "thumbnail", "logo", "poster", "wallpaper", "vector"]): continue
                if "ytimg.com" in raw_url or raw_url.lower().endswith((".gif", ".svg")): continue
                
                images.append(raw_url)
                if len(images) >= count: break
    except Exception as e:
        print("Search Error:", e)
    return images[:count]

def generate_trending_draft(raw_title, raw_text=""):
    prompt = f"""
    आप Times07 News के सबसे बड़े जर्नलिस्ट हैं।
    विषय: {raw_title}
    संदर्भ/Context: {raw_text[:1200]}

    सख्त निर्देश:
    1. यह पूरी तरह से तथ्यात्मक (Factual) और न्यूज़ चैनल जैसी हिंदी होनी चाहिए।
    2. 500-800 शब्दों में विस्तृत खबर लिखें (H3 हेडिंग्स और <p> टैग्स के साथ)।
    3. 5 SEO फ्रेंडली टाइटल्स जनरेट करें। हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं।
    4. खबर में जिस व्यक्ति, जगह, घटना या विषय की फोटो सबसे सही होगी, उसके लिए 2-5 शब्दों का image_keyword भी दो।

    Return strictly a VALID JSON object (NO markdown):
    {{
      "title_options": ["पहला टाइटल | Times07 News", "दूसरा टाइटल | Times07 News", "तीसरा टाइटल | Times07 News", "चौथा टाइटल | Times07 News", "पांचवा टाइटल | Times07 News"],
      "one_line_teaser": "1-लाइन का ब्रेकिंग न्यूज़ टीज़र",
      "visual_summary_points": ["पॉइंट 1", "पॉइंट 2", "पॉइंट 3"],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "मुख्य समाचार",
      "default_tags": ["#TrendingNews", "#LatestUpdate", "#Times07"],
      "image_keyword": "2-5 words related to the main person, place or event",
      "english_slug": "3-4 english words only separated by hyphen for url"
    }}
    """
    available_keys = GROQ_KEYS.copy()
    random.shuffle(available_keys)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    for key in available_keys:
        for model in models:
            try:
                # API Timeouts जोड़े गए हैं ताकि कोड अटके नहीं
                temp_client = OpenAI(
                    api_key=key, 
                    base_url="https://api.groq.com/openai/v1",
                    timeout=35.0
                )
                response = temp_client.chat.completions.create(
                    model=model, 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4, 
                    max_tokens=4000, 
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content.strip())
                search_keyword = data.get("image_keyword") or re.sub(r"\|.*|\b20\d{2}\b", "", raw_title)
                data["image_options"] = search_hd_images(search_keyword, count=5)
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["slug"] = data.get("english_slug", "").lower().replace(" ", "-")
                data["bot_type"] = "trending"
                data["id"] = int(datetime.now().timestamp() * 1000)
                return data
            except Exception as e:
                error_logger.error(f"Groq API Error on model {model}: {e}")
                update_bot_stats("ai_errors")
                continue
    return None

def extract_full_text(link):
    """न्यूज़ आर्टिकल का पूरा कंटेंट निकालने का सुरक्षित तरीका"""
    try:
        article = Article(link)
        article.download()
        article.parse()
        if len(article.text) > 150:
            return article.text
    except Exception: pass
    return ""

def save_to_drafts(draft_data):
    drafts_file = "drafts_trending.json"
    drafts = []
    if os.path.exists(drafts_file):
        try:
            with open(drafts_file, "r", encoding="utf-8") as f:
                content = f.read()
                if content.strip(): drafts = json.loads(content)
        except Exception: pass
    drafts.insert(0, draft_data)
    with open(drafts_file, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=4)
    print(f"✅ SUCCESS: Trending Draft saved to {drafts_file}!")

def run_bot():
    print("\n🔍 Engine Active: Scanning Google Trends & RSS Feeds...")
    pub_links, pub_titles = get_db_data()
    candidates = []

    # 1. Google Trends
    for topic in fetch_google_trends()[:1]:
        try:
            encoded_topic = urllib.parse.quote(topic)
            feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded_topic}&hl=hi&gl=IN&ceid=IN:hi")
            for entry in feed.entries[:1]:
                candidates.append({"title": entry.title, "link": entry.link, "source": "Google Trends"})
        except Exception as e:
            logging.error(f"Google Trends Parse Error: {e}")

    # 2. RSS Sources
    for src in TRUSTED_RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:3]:
                candidates.append({"title": entry.title, "link": entry.link, "source": src["source"]})
        except Exception: pass

    # 3. खबरों को प्रोसेस और सेव करना (यह पार्ट पिछले कोड में मिसिंग था)
    for item in candidates:
        title = item["title"]
        link = item["link"]
        norm_title = normalize_text(title)

        if link in pub_links or norm_title in pub_titles:
            print(f"⏩ Skipped Duplicate: {title[:30]}...")
            update_bot_stats("duplicate")
            continue

        print(f"\n⚙️ Processing: {title}")
        full_text = extract_full_text(link)
        
        draft = generate_trending_draft(title, full_text)
        if draft:
            save_to_drafts(draft)
            update_bot_stats("published")
            pub_titles.add(norm_title)
            pub_links.add(link)
            break # 1 बार में 1 सफल खबर प्रोसेस करके ब्रेक करें
        else:
            update_bot_stats("failed")

if __name__ == "__main__":
    print("🚀 Times07 Master Draft Bot Active...")
    while True:
        try:
            run_bot()
        except Exception as e:
            error_logger.error(f"Main loop crash: {e}")
        
        # Safe Git sync
        try:
            os.system('git add -A')
            os.system('git commit -m "Auto Post Update"')
            os.system('git push origin main')
        except Exception as e:
            print(f"Git Push Error: {e}")

        print(f"\n⏰ Waiting {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)