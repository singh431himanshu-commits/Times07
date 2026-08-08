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

CHECK_INTERVAL_MINUTES = 30
MAX_ARTICLES_PER_RUN = 20

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

def clean_slug(slug_text):
    """SEO-Friendly Pure English Slug Builder"""
    if not slug_text:
        return f"news-{int(time.time())}"
    
    # केवल शुद्ध इंग्लिश (A-Z, a-z, 0-9) और हाइफन (-) ही रहने देगा
    clean_text = re.sub(r'[^a-zA-Z0-9\s-]', '', str(slug_text)).lower().strip()
    slug = re.sub(r'[\s_]+', '-', clean_text)
    slug = re.sub(r'-+', '-', slug).strip('-')
    
    return slug if slug else f"news-{int(time.time())}"
def run_git_command(commands, commit_msg):
    """सुरक्षित Git Commands रन करने का फ़ंक्शन"""
    try:
        for cmd in commands:
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"🚀 [Git Success] {commit_msg}")
    except Exception as e:
        print(f"⚠️ [Git Warning] Sync failed: {e}")

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

def generate_sitemap_for_published_only():
    """केवल पब्लिश हुई खबरों के लिए Sitemap.xml बनाता है"""
    try:
        urls = [{"loc": "https://times07news.in/", "lastmod": datetime.utcnow().strftime("%Y-%m-%d")}]
        published_slugs = set()

        res = requests.get(FIREBASE_URL, timeout=10)
        if res.status_code == 200 and isinstance(res.json(), dict):
            for item in res.json().values():
                if isinstance(item, dict) and item.get("slug"):
                    published_slugs.add(clean_slug(item.get("slug")))

        for slug in published_slugs:
            if slug:
                link = f"https://times07news.in/article.html?slug={slug}"
                urls.append({"loc": link, "lastmod": datetime.utcnow().strftime("%Y-%m-%d")})

        xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in urls:
            xml += f"  <url>\n    <loc>{u['loc']}</loc>\n    <lastmod>{u['lastmod']}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>0.8</priority>\n  </url>\n"
        xml += "</urlset>"

        with open("sitemap.xml", "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"🗺️ [Sitemap Updated] Included {len(published_slugs)} published articles.")
        return len(published_slugs)
    except Exception as e:
        print("❌ Sitemap Generation Error:", e)
        return 0

def ping_search_engines():
    """सर्च इंजन पिंग भेजता है और स्टेटस कोड दिखाता है"""
    sitemap_url = "https://times07news.in/sitemap.xml"
    try:
        res = requests.get(f"https://www.bing.com/ping?sitemap={sitemap_url}", timeout=10)
        if res.status_code == 200:
            print("✅ [Ping Success] Bing pinged successfully (HTTP 200)!")
        else:
            print(f"⚠️ [Ping Notice] Bing ping response code: {res.status_code}")
    except Exception as e:
        print(f"❌ [Ping Failed] Could not connect: {e}")

def push_drafts_to_github():
    """केवल ड्राफ्ट्स को GitHub पर भेजता है"""
    run_git_command(
        ['git add drafts_trending.json', 'git commit -m "Updated Drafts for Dashboard"', 'git push origin main'],
        "New Draft synced to GitHub Dashboard."
    )

def check_and_process_dashboard_publications():
    """पब्लिश हुई खबरों की जांच कर Sitemap और Ping पुश करता है"""
    print("\n🔎 Syncing Published Articles with Sitemap & Search Engines...")
    published_count = generate_sitemap_for_published_only()

    if published_count > 0:
        run_git_command(
            ['git add sitemap.xml', 'git commit -m "Auto Update Sitemap for Published Articles"', 'git push origin main'],
            "Published Sitemap synced to live site!"
        )
        ping_search_engines()

def fetch_google_trends():
    trends = []
    try:
        feed = feedparser.parse("https://trends.google.com/trending/rss?geo=IN")
        for entry in feed.entries[:10]: trends.append(entry.title)
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
    आप Times07 News के सबसे वरिष्ठ और अनुभवी मुख्य पत्रकार (Chief Editor) हैं।
    विषय: {raw_title}
    संदर्भ/Context: {raw_text[:3500]}

    सख्त निर्देश:
    1. खबर पूरी तरह से तथ्यात्मक (Factual) और पेशेवर न्यूज़ चैनल की भाषा में होनी चाहिए।
    2. खबर को विस्तृत रूप से 800 से 1000 शब्दों में लिखें ताकि पाठक को विषय की पूरी जानकारी मिले।
    3. इसमें निम्नलिखित अनुभाग (H3 हेडिंग्स और <p> पैराग्राफ्स) अनिवार्य रूप से शामिल करें:
       - <h3>मुख्य समाचार और ताज़ा अपडेट</h3> (विस्तृत 2 पैराग्राफ)
       - <h3>मामले की पूरी पृष्ठभूमि और कारण</h3> (विस्तृत 2 पैराग्राफ)
       - <h3>मुख्य बिंदु, आंकड़े और तथ्य</h3> (विस्तृत विश्लेषण)
       - <h3>जनता और उद्योग पर इसका प्रभाव</h3> (गहराई से विश्लेषण)
       - <h3>निष्कर्ष और आगे की राह</h3> (अंतिम निष्कर्ष)
    4. 5 आकर्षक और SEO-फ्रेंडली टाइटल्स जनरेट करें। हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं।
    5. फोटो खोजने के लिए सही 2-5 शब्दों का 'image_keyword' प्रदान करें।

    Return strictly a VALID JSON object (NO markdown):
    {{
      "title_options": ["पहला टाइटल | Times07 News", "दूसरा टाइटल | Times07 News", "तीसरा टाइटल | Times07 News", "चौथा टाइटल | Times07 News", "पांचवा टाइटल | Times07 News"],
      "one_line_teaser": "1-लाइन का ब्रेकिंग न्यूज़ टीज़र",
      "visual_summary_points": ["मुख्य बिंदु 1", "मुख्य बिंदु 2", "मुख्य बिंदु 3", "मुख्य बिंदु 4"],
      "content_html": "<h3>मुख्य समाचार और ताज़ा अपडेट</h3><p>विस्तृत पैराग्राफ 1...</p><p>पैराग्राफ 2...</p><h3>मामले की पूरी पृष्ठभूमि</h3><p>विस्तृत विवरण...</p><h3>मुख्य बिंदु और आंकड़े</h3><p>विस्तृत विश्लेषण...</p><h3>प्रभाव और निष्कर्ष</h3><p>अंतिम विश्लेषण...</p>",
      "category": "मुख्य समाचार",
      "default_tags": ["#TrendingNews", "#LatestUpdate", "#Times07News", "#HindiNews"],
      "image_keyword": "2-5 words related to main subject",
      "english_slug": "3-4 english words separated by hyphen"
    }}
    """
    available_keys = GROQ_KEYS.copy()
    random.shuffle(available_keys)
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    
    for key in available_keys:
        for model in models:
            try:
                temp_client = OpenAI(
                    api_key=key, 
                    base_url="https://api.groq.com/openai/v1",
                    timeout=45.0
                )
                response = temp_client.chat.completions.create(
                    model=model, 
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.4, 
                    max_tokens=6000,
                    response_format={"type": "json_object"}
                )
                data = json.loads(response.choices[0].message.content.strip())
                search_keyword = data.get("image_keyword") or re.sub(r"\|.*|\b20\d{2}\b", "", raw_title)
                data["image_options"] = search_hd_images(search_keyword, count=5)
                data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # SEO Clean English Slug
                raw_slug = data.get("english_slug", "news-update")
                data["slug"] = clean_slug(raw_slug)
                
                data["bot_type"] = "trending"
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
    print(f"✅ SUCCESS: Draft saved to {drafts_file}!")

def run_bot():
    print("\n🔍 Engine Active: Scanning Google Trends & RSS Feeds...")
    pub_links, pub_titles = get_db_data()
    candidates = []

    # 1. Google Trends
    for topic in fetch_google_trends()[:5]:
        try:
            encoded_topic = urllib.parse.quote(topic)
            feed = feedparser.parse(f"https://news.google.com/rss/search?q={encoded_topic}&hl=hi&gl=IN&ceid=IN:hi")
            for entry in feed.entries[:2]:
                candidates.append({"title": entry.title, "link": entry.link, "source": "Google Trends"})
        except Exception as e:
            logging.error(f"Google Trends Parse Error: {e}")

    # 2. RSS Sources
    for src in TRUSTED_RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:5]:
                candidates.append({"title": entry.title, "link": entry.link, "source": src["source"]})
        except Exception: pass

    processed_count = 0
    print(f"📋 Found {len(candidates)} candidates. Target: Up to {MAX_ARTICLES_PER_RUN} fresh drafts.\n")

    for item in candidates:
        if processed_count >= MAX_ARTICLES_PER_RUN:
            print(f"🎯 Target of {MAX_ARTICLES_PER_RUN} drafts reached!")
            break

        title = item["title"]
        link = item["link"]
        norm_title = normalize_text(title)

        if link in pub_links or norm_title in pub_titles:
            update_bot_stats("duplicate")
            continue

        print(f"\n⚙️ Processing Draft [{processed_count + 1}/{MAX_ARTICLES_PER_RUN}]: {title[:65]}...")
        full_text = extract_full_text(link)
        
        draft = generate_trending_draft(title, full_text)
        if draft:
            save_to_drafts(draft)
            update_bot_stats("published")
            pub_titles.add(norm_title)
            pub_links.add(link)
            processed_count += 1
            time.sleep(2)
        else:
            print("❌ AI Draft Generation Failed! (Check Groq API Keys or Limits)")
            update_bot_stats("failed")

    # सभी ड्राफ्ट बन जाने के बाद एक ही बार GitHub पर पुश करें
    if processed_count > 0:
        push_drafts_to_github()

    check_and_process_dashboard_publications()
if __name__ == "__main__":
    print("🚀 Times07 Master Draft Bot Active...")
    while True:
        try:
            run_bot()
        except Exception as e:
            error_logger.error(f"Main loop crash: {e}")

        print(f"\n⏰ Waiting {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)