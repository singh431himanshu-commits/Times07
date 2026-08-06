import os
import json
import requests
import feedparser
import logging
import sys
import time
import re
import random
import urllib.parse
import subprocess
from datetime import datetime
from bs4 import BeautifulSoup
from newspaper import Article
from ddgs import DDGS
from openai import OpenAI

# 🌐 Windows Terminal UTF-8 Encoding Fix
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"
STATS_URL = "https://times07news-default-rtdb.firebaseio.com/bot_stats.json"

import config
GROQ_KEYS = config.GROQ_KEYS

CHECK_INTERVAL_MINUTES = 45
MAX_ARTICLES_PER_RUN = 15

logging.basicConfig(
    filename='bot_netflix.log', level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
error_logger = logging.getLogger('ErrorLogger_Netflix')

# 🌍 Focus: All Netflix Shows (Global, Hollywood, Bollywood, K-Drama)
ENTERTAINMENT_RSS_SOURCES = [
    {"url": "https://news.google.com/rss/search?q=Netflix+New+Release+Movies+Series&hl=hi&gl=IN&ceid=IN:hi", "source": "Netflix Global Releases"},
    {"url": "https://news.google.com/rss/search?q=Netflix+India+Web+Series+Updates&hl=hi&gl=IN&ceid=IN:hi", "source": "Netflix India"},
    {"url": "https://news.google.com/rss/search?q=Upcoming+Netflix+Shows+Hollywood&hl=hi&gl=IN&ceid=IN:hi", "source": "Netflix Hollywood"},
    {"url": "https://news.google.com/rss/search?q=Korean+Drama+Netflix&hl=hi&gl=IN&ceid=IN:hi", "source": "Netflix K-Drama"},
    {"url": "https://www.jagran.com/rss/entertainment-web-series-feed.xml", "source": "Dainik Jagran OTT"},
    {"url": "https://feeds.zeenews.india.com/hindi/rss/entertainment-news.xml", "source": "Zee News Entertainment"}
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

def clean_slug(slug_text, fallback_keyword="netflix-show"):
    """PURE ENGLISH SLUG FILTER (No Hindi characters allowed)"""
    if not slug_text:
        slug_text = fallback_keyword
    clean_text = re.sub(r'[^a-zA-Z0-9\s-]', '', str(slug_text)).lower().strip()
    slug = re.sub(r'[\s_]+', '-', clean_text)
    slug = re.sub(r'-+', '-', slug).strip('-')
    if not slug or len(slug) < 3:
        fallback_clean = re.sub(r'[^a-zA-Z0-9\s-]', '', str(fallback_keyword)).lower().strip()
        fallback_slug = re.sub(r'[\s_]+', '-', fallback_clean).strip('-')
        slug = fallback_slug if fallback_slug else f"netflix-show-{int(time.time())}"
    return slug

def ping_search_engines(slug):
    """📡 AUTO PING (Google & IndexNow) - Full Featured"""
    article_url = f"https://times07news.in/article.html?slug={slug}"
    print(f"📡 [Auto Ping] Notifying Search Engines for: {slug}...")
    
    # 1. IndexNow Ping
    try:
        indexnow_payload = {
            "host": "times07news.in",
            "key": "times07news2026indexnowkey",
            "keyLocation": "https://times07news.in/times07news2026indexnowkey.txt",
            "urlList": [article_url]
        }
        res = requests.post("https://api.indexnow.org/IndexNow", json=indexnow_payload, timeout=6)
        if res.status_code in [200, 202]:
            print("   ✅ IndexNow Ping Success!")
        else:
            print(f"   ⚠️ IndexNow Ping returned status: {res.status_code}")
    except Exception as e:
        logging.warning(f"IndexNow Ping Failed: {e}")
        print(f"   ❌ IndexNow Ping Error: {e}")

    # 2. Google Sitemap Ping
    try:
        sitemap_url = "https://times07news.in/sitemap.xml"
        google_ping_url = f"https://www.google.com/ping?sitemap={urllib.parse.quote(sitemap_url)}"
        res = requests.get(google_ping_url, timeout=6)
        if res.status_code == 200:
            print("   ✅ Google Sitemap Ping Success!")
        else:
            print(f"   ⚠️ Google Ping returned status: {res.status_code}")
    except Exception as e:
        logging.warning(f"Google Ping Failed: {e}")
        print(f"   ❌ Google Ping Error: {e}")

def run_git_command(commands, commit_msg):
    """🚀 FULL GIT SYNC FUNCTION"""
    try:
        for cmd in commands:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🚀 [Git Success] {commit_msg}")
    except Exception as e:
        print(f"⚠️ [Git Warning] Sync failed: {e}")
        logging.error(f"Git Error: {e}")

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
    
    if os.path.exists("drafts_netflix.json"):
        try:
            with open("drafts_netflix.json", "r", encoding="utf-8") as f:
                for item in json.load(f):
                    if "title_options" in item and item["title_options"]:
                        pub_titles.add(normalize_text(item["title_options"][0]))
        except Exception: pass
    return pub_links, pub_titles

def push_drafts_to_github():
    run_git_command(
        ['git add drafts_netflix.json', 'git commit -m "Netflix Drafts Update - Real Characters & Auto Ping"', 'git push origin main'],
        "Netflix Drafts synced to GitHub Dashboard."
    )

def fetch_netflix_trends():
    trends = []
    queries = ["Netflix New Series Updates", "Netflix Web Series Hindi", "Top Shows on Netflix India"]
    for q in queries:
        try:
            encoded = urllib.parse.quote(q)
            feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded}&hl=hi&gl=IN&ceid=IN:hi")
            for entry in feed.entries[:3]:
                trends.append({"title": entry.title, "link": entry.link, "source": "Google Trends Netflix"})
        except Exception: pass
    return trends

def search_hd_images(query, count=5):
    images = []
    try:
        time.sleep(1)
        search_queries = [f'"{query}" netflix poster hd wallpaper', f'"{query}" netflix series hd image']
        with DDGS(timeout=10) as ddgs:
            results = []
            for q in search_queries:
                try:
                    results.extend(list(ddgs.images(query=q, region="in-en", safesearch="on", max_results=10)))
                except Exception: pass
            
            for res in results:
                raw_url = res.get("image", "")
                if not raw_url or "ytimg.com" in raw_url or raw_url.lower().endswith((".gif", ".svg")): continue
                images.append(raw_url)
                if len(images) >= count: break
    except Exception as e:
        print("Search Error:", e)
    return images[:count]

def generate_netflix_draft(raw_title, raw_text=""):
    context_body = raw_text[:3500] if len(raw_text) > 100 else f"विषय: {raw_title}।"

    prompt = f"""
    आप Times07 News के वरिष्ठ Netflix और OTT पत्रकार हैं। 
    आप दुनिया भर के (Hollywood, Bollywood, Korean, Spanish आदि) Netflix शोज़ कवर करते हैं।

    मुख्य शीर्षक: {raw_title}
    खबर का संदर्भ: {context_body}

    🚨 अति-सख्त निर्देश (AI Hallucination रोकने के लिए):
    1. 'content_html' में आपको HTML कोड खुद जनरेट करना है। कोई भी डमी या प्लेसहोल्डर टेक्स्ट (जैसे "यहाँ विवरण लिखें" या "पहला पैराग्राफ") नहीं छापना है।
    2. खबर में असली शो का नाम, असली एक्टर्स (Cast) के नाम, शो में उनके असली किरदारों (Characters) के नाम, और शो की असली कहानी (Plot) के बारे में विस्तार से लिखें।
    3. हवा-हवाई या गोल-मोल बातें न करें। शो की गहराई में जाएं और मसालेदार पत्रकारिता शैली में लिखें।
    4. "english_slug" केवल शुद्ध इंग्लिश में होगा।
    5. HTML में कोई <img> टैग या <style> न जोड़ें। केवल टेक्स्ट और टेबल दें।

    Return strictly a VALID JSON object:
    {{
      "title_options": ["Title 1 | Times07 News", "Title 2 | Times07 News", "Title 3", "Title 4", "Title 5"],
      "one_line_teaser": "1-लाइन का धमाकेदार OTT अपडेट",
      "visual_summary_points": ["असली पॉइंट 1", "असली पॉइंट 2", "असली पॉइंट 3", "असली पॉइंट 4"],
      "content_html": "यहाँ आपको पूरा HTML जनरेट करना है। सबसे पहले एक HTML Table बनाएं जिसमें (शो/फिल्म का नाम, ओटीटी प्लेटफॉर्म - Netflix, भाषाएं, और रिलीज़ स्टेटस) हो। उसके बाद 4 <h3> टैग्स (1. 🎬 क्या है पूरी खबर..., 2. 🔥 कहानी और स्टार कास्ट..., 3. 📅 Release Date..., 4. 🍿 निष्कर्ष...) का इस्तेमाल करें। हर <h3> के नीचे <p> टैग में असली एक्टर्स, किरदारों के नाम और शो की असली कहानी को कम से कम 150-200 शब्दों में विस्तार से लिखें। बिल्कुल भी डमी टेक्स्ट का प्रयोग न करें।",
      "category": "मनोरंजन",
      "default_tags": ["#Netflix", "#OTTUpdates", "#WebSeries", "#Times07News"],
      "image_keyword": "(Show Name in English for image search)",
      "english_slug": "show-name-netflix-update"
    }}
    """
    available_keys = GROQ_KEYS.copy()
    random.shuffle(available_keys)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    for key in available_keys:
        for model in models:
            try:
                temp_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1", timeout=45.0)
                response = temp_client.chat.completions.create(
                    model=model, 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.5, 
                    max_tokens=3500,
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content.strip())
                search_keyword = data.get("image_keyword") or re.sub(r"\|.*|\b20\d{2}\b", "", raw_title)
                
                # 🖼️ Only fetching URLs, NO HTML INJECTION (Fixes Double Image Bug)
                data["image_options"] = search_hd_images(search_keyword, count=5)
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                raw_english_slug = data.get("english_slug", search_keyword)
                data["slug"] = clean_slug(raw_english_slug, fallback_keyword=search_keyword)
                data["bot_type"] = "netflix"
                data["id"] = int(datetime.now().timestamp() * 1000)
                return data
            except Exception as e:
                error_logger.error(f"Groq API Error on model {model}: {e}")
                update_bot_stats("ai_errors")
                continue
    return None

def extract_full_text(link):
    try:
        article = Article(link)
        article.download()
        article.parse()
        if len(article.text) > 150: return article.text
    except Exception: pass
    return ""

def save_to_drafts(draft_data):
    drafts_file = "drafts_netflix.json"
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
    print(f"✅ SUCCESS: Quality Article saved [{draft_data['slug']}]!")

def run_bot():
    print("\n🎬 Netflix Global Bot Active: Scanning Latest Release Updates...")
    pub_links, pub_titles = get_db_data()
    candidates = fetch_netflix_trends()

    for src in ENTERTAINMENT_RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:4]:
                candidates.append({"title": entry.title, "link": entry.link, "source": src["source"]})
        except Exception: pass

    processed_count = 0
    print(f"📋 Found {len(candidates)} candidates. Target: Up to {MAX_ARTICLES_PER_RUN} fresh drafts.\n")

    for item in candidates:
        if processed_count >= MAX_ARTICLES_PER_RUN:
            break

        title = item["title"]
        link = item["link"]
        norm_title = normalize_text(title)

        if link in pub_links or norm_title in pub_titles:
            update_bot_stats("duplicate")
            continue

        print(f"\n⚙️ Processing Quality Draft [{processed_count + 1}/{MAX_ARTICLES_PER_RUN}]: {title[:65]}...")
        full_text = extract_full_text(link)
        
        draft = generate_netflix_draft(title, full_text)
        if draft:
            save_to_drafts(draft)
            update_bot_stats("published")
            pub_titles.add(norm_title)
            pub_links.add(link)
            
            # 📡 Full Auto-Ping called here
            ping_search_engines(draft["slug"])
            
            processed_count += 1
            time.sleep(2)
        else:
            print("❌ AI Draft Generation Failed!")
            update_bot_stats("failed")

    if processed_count > 0:
        push_drafts_to_github()

if __name__ == "__main__":
    print("🍿 Times07 Netflix Bot Active...")
    while True:
        try:
            run_bot()
        except Exception as e:
            error_logger.error(f"Main loop crash: {e}")

        print(f"\n⏰ Waiting {CHECK_INTERVAL_MINUTES} minutes for next cycle...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)