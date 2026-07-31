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

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"
STATS_URL = "https://times07news-default-rtdb.firebaseio.com/bot_stats.json"
GROQ_API_KEY = "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"

CHECK_INTERVAL_MINUTES = 30

# 📝 1. Logging System
logging.basicConfig(
    filename='bot.log', level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
)
error_logger = logging.getLogger('ErrorLogger')
error_handler = logging.FileHandler('error.log')
error_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
error_logger.addHandler(error_handler)

# 📊 2. Trusted RSS Sources
TRUSTED_RSS_SOURCES = [
    {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC News", "trust_score": 100},
    {"url": "https://pib.gov.in/RssMain.aspx?ModId=6&LangId=1", "source": "PIB India", "trust_score": 95},
    {"url": "https://www.thehindu.com/news/national/feeder/default.rss", "source": "The Hindu", "trust_score": 90},
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "NY Times", "trust_score": 88},
    {"url": "https://www.aajtak.in/rss/feed/index.xml", "source": "Aaj Tak", "trust_score": 85},
    {"url": "https://ndtv.in/rss/top-stories", "source": "NDTV India", "trust_score": 85},
    {"url": "https://www.amarujala.com/rss/breaking-news.xml", "source": "Amar Ujala", "trust_score": 80}
]

# 📈 3. Bot Stats Tracker
def update_bot_stats(stat_type):
    stats = {"published": 0, "skipped": 0, "duplicate": 0, "failed": 0, "ai_errors": 0}
    try:
        res = requests.get(STATS_URL, timeout=5)
        if res.status_code == 200 and res.json():
            stats.update(res.json())
    except:
        pass
    
    stats[stat_type] = stats.get(stat_type, 0) + 1
    
    try:
        requests.put(STATS_URL, json=stats, timeout=5)
        with open("stats.json", "w") as f:
            json.dump(stats, f, indent=4)
    except Exception as e:
        error_logger.error(f"Stats update error: {e}")

def generate_clean_slug(text):
    slug = text.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug[:80]

def normalize_text(text):
    return re.sub(r'\W+', '', text.lower())

def get_db_data():
    published_links, published_titles_normalized, published_slugs, existing_articles = set(), set(), set(), []
    try:
        response = requests.get(FIREBASE_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, dict):
                        if "link" in val: published_links.add(val["link"])
                        if "title" in val: published_titles_normalized.add(normalize_text(val["title"].replace(" | Times07News", "")))
                        if "slug" in val:
                            published_slugs.add(val["slug"])
                            existing_articles.append({"title": val.get("title", ""), "slug": val.get("slug", ""), "category": val.get("category", "मुख्य समाचार")})
    except Exception as e:
        error_logger.error(f"Database Read Error: {e}")
    return published_links, published_titles_normalized, published_slugs, existing_articles

# 📈 4. Google Trends Scraper
def fetch_google_trends():
    print("🔥 Fetching India Google Trends...")
    trends = []
    try:
        url = "https://trends.google.com/trending/rss?geo=IN"
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            trends.append(entry.title)
    except Exception as e:
        error_logger.error(f"Google Trends Fetch Error: {e}")
    return trends

def fetch_safe_image(keyword, title):
    safe_fallback = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200"
    try:
        clean_q = f"{keyword} {title}".replace(":", " ")
        q_words = " ".join(clean_q.split()[:4]) + " news photo"
        with DDGS() as ddgs:
            results = list(ddgs.images(q_words, max_results=3))
            if results:
                for res in results:
                    img_url = res.get('image', '')
                    if img_url and img_url.startswith('https://') and not any(bad in img_url.lower() for bad in ['painting', 'illustration', 'vector']):
                        return img_url
    except:
        pass
    return safe_fallback

# 🔄 5. Groq Fallback AI Generator + Social Captions
def generate_article_via_groq(raw_title, raw_text=""):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    prompt = f"""
    Aap 'Times07 News' ke Chief Editor hain. Is topic par ek Detailed, SEO-Optimized News Article Hindi mein likhein:
    Topic: {raw_title}
    Context: {raw_text[:1000]}

    Instructions:
    1. Category: 'राजनीति', 'बिजनेस', 'खेल', 'टेक & AI', 'मनोरंजन', 'राज्य', 'विदेश' mein se hi chunein.
    2. Social Captions (FB, Telegram, X) tayyar karein with emojis and hashtags.

    STRICT JSON Output:
    {{
        "seo_title": "Catchy Hindi Headline",
        "meta_description": "150-160 characters description",
        "tags": ["Tag1", "Tag2", "Tag3"],
        "summary": "4-5 lines summary",
        "content": "Full article with H3 headings and <p> tags",
        "category": "Exact Category",
        "image_keyword": "English keyword",
        "social_captions": {{
            "facebook": "Catchy Facebook caption with hashtags",
            "telegram": "Formatted Telegram caption with link placeholder",
            "x_twitter": "Short 280-char tweet caption"
        }}
    }}
    """
    
    models = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"] # Fallback Strategy
    
    for model in models:
        try:
            payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "response_format": {"type": "json_object"}}
            res = requests.post(url, headers=headers, json=payload, timeout=30)
            if res.status_code == 200:
                return json.loads(res.json()['choices'][0]['message']['content'])
            else:
                logging.warning(f"Model {model} failed. Trying fallback...")
        except Exception as e:
            error_logger.error(f"Groq API Error on model {model}: {e}")
            update_bot_stats("ai_errors")
            
    return None

def calculate_trending_score(raw_title, source_name, category, occurrences_count):
    score = 0
    if any(k in raw_title.lower() for k in ["breaking", "ब्रेकिंग", "urgent", "ताज़ा"]): score += 30
    if source_name in ["BBC News", "PIB India", "Google Trends"]: score += 20
    if category == "राजनीति": score += 15
    elif category == "टेक & AI": score += 10
    if occurrences_count > 1: score += 25
    return score

def run_bot():
    print("\n🔍 Engine Active: Scanning Google Trends & RSS Feeds...")
    pub_links, pub_titles, pub_slugs, existing_articles = get_db_data()
    
    candidates = []

    # Step A: Process Google Trends First
    gt_topics = fetch_google_trends()
    for topic in gt_topics:
        encoded_q = urllib.parse.quote(topic)
        trend_rss = f"https://news.google.com/rss/search?q={encoded_q}&hl=hi&gl=IN&ceid=IN:hi"
        feed = feedparser.parse(trend_rss)
        for entry in feed.entries[:2]:
            candidates.append({"entry": entry, "source_name": "Google Trends", "trust_score": 90})

    # Step B: Process Trusted RSS Feeds
    for src in TRUSTED_RSS_SOURCES:
        try:
            feed = feedparser.parse(src["url"])
            for entry in feed.entries[:2]:
                candidates.append({"entry": entry, "source_name": src["source"], "trust_score": src["trust_score"]})
        except:
            pass

    for item in candidates:
        entry = item["entry"]
        source_name = item["source_name"]
        news_title = getattr(entry, 'title', '')
        news_url = getattr(entry, 'link', '')

        norm_t = normalize_text(news_title)
        if news_url in pub_links or norm_t in pub_titles:
            update_bot_stats("duplicate")
            continue

        print(f"\n📰 [Processing Topic]: {news_title[:55]}...")

        raw_text, pub_date, author_name = "", "", "Times07 News Bureau"
        try:
            art = Article(news_url)
            art.download()
            art.parse()
            raw_text = art.text
            if art.publish_date: pub_date = str(art.publish_date)
            if art.authors: author_name = ", ".join(art.authors)
        except:
            pass

        ai_data = generate_article_via_groq(news_title, raw_text)

        if not ai_data or "seo_title" not in ai_data:
            update_bot_stats("skipped")
            continue

        seo_title = ai_data["seo_title"]
        auto_slug = generate_clean_slug(seo_title)

        if auto_slug in pub_slugs:
            update_bot_stats("duplicate")
            continue

        category = ai_data.get("category", "मुख्य समाचार")
        trending_score = calculate_trending_score(news_title, source_name, category, 1)

        placement = "Hero Slider" if trending_score > 80 else ("Top News" if trending_score >= 60 else "Latest News")
        image_url = fetch_safe_image(ai_data.get("image_keyword", ""), seo_title)

        payload = {
            "title": f"{seo_title} | Times07News",
            "seo_title": seo_title,
            "meta_description": ai_data.get("meta_description", ""),
            "tags": ai_data.get("tags", []),
            "slug": auto_slug,
            "summary": f"{ai_data.get('summary', '')}\n\n📌 स्त्रोत: {source_name} | Trending Score: {trending_score}",
            "content": ai_data.get("content", "").replace("\n\n", "<br><br>"),
            "image": image_url,
            "link": news_url,
            "category": category,
            "trending_score": trending_score,
            "placement": placement,
            "social_captions": ai_data.get("social_captions", {}),
            "original_author": author_name,
            "original_publish_date": pub_date if pub_date else "N/A",
            "timestamp": int(time.time())
        }

        res = requests.post(FIREBASE_URL, json=payload, timeout=10)
        if res.status_code == 200:
            print(f"✅ Published: {seo_title[:45]} ({placement})")
            pub_links.add(news_url)
            pub_titles.add(norm_t)
            pub_slugs.add(auto_slug)
            update_bot_stats("published")
        else:
            update_bot_stats("failed")

        time.sleep(3)

if __name__ == "__main__":
    print("🚀 Times07 Master Bot Active (Short name: run.py)...")
    while True:
        try:
            run_bot()
        except Exception as e:
            error_logger.error(f"Main loop crash prevented: {e}")
            update_bot_stats("failed")
        
        print(f"\n⏰ Waiting {CHECK_INTERVAL_MINUTES} minutes...")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)