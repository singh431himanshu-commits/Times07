import os
import re
import json
import math
import time
import logging
import subprocess
import requests
from datetime import datetime
from openai import OpenAI
import config

# ==========================================
# 1. LOGGING & GROQ CLIENT SETUP
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

# Groq Cloud Client Setup (For gsk_ API Keys)
client = OpenAI(
    api_key=config.GROK_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

# ==========================================
# 2. HELPER FUNCTIONS (SEO & SLUG)
# ==========================================
def generate_slug(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[\s_-]+', '-', text)

def calculate_reading_time(text):
    words = len(re.findall(r'\w+', text))
    minutes = math.ceil(words / 200)
    return f"{minutes} min read"

def is_duplicate(title, db_file="news.json"):
    if not os.path.exists(db_file):
        return False
    try:
        with open(db_file, "r", encoding="utf-8") as f:
            existing_news = json.load(f)
            for item in existing_news:
                if item.get("title").lower() == title.lower():
                    return True
    except Exception as e:
        logging.error(f"Error checking duplicates: {e}")
    return False

# ==========================================
# 3. FREE HD IMAGE DOWNLOADER
# ==========================================
def fetch_and_save_hd_image(category, slug):
    logging.info(f"Downloading HD image for category: {category}...")
    image_url = f"https://source.unsplash.com/1200x800/?{category},finance,stock"
    
    os.makedirs("images", exist_ok=True)
    local_path = f"images/{slug}.jpg"
    
    try:
        res = requests.get(image_url, timeout=15)
        if res.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(res.content)
            logging.info(f"Image saved locally at {local_path}")
            return local_path
    except Exception as e:
        logging.warning(f"Image download failed ({e}), using fallback image.")
        
    return "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80"

# ==========================================
# 4. GENERATE ARTICLE WITH GROQ AI (LLAMA-3.3)
# ==========================================
# ==========================================
# 4. GENERATE ARTICLE WITH GROQ AI (STRICT JSON)
# ==========================================
def generate_news_with_groq():
    logging.info("Fetching latest market news and writing article using Groq AI...")
    
    prompt = """
    You are a Wall Street Financial Analyst & Master SEO Editor.
    Generate the absolute latest breaking financial/crypto news from verified sources (Reuters, Bloomberg, CNBC, CoinDesk) for today.
    
    Write an in-depth, 100% accurate, professional article in English.
    
    Return a strictly valid JSON object with the following fields:
    {
      "title": "SEO Catchy Headline",
      "one_line_headline": "1-line quick summary",
      "summary_50_words": "Brief summary around 50 words",
      "summary_150_words": "Detailed summary around 150 words",
      "content_html": "Full long article in clean HTML (<p>, <h3>, <ul>, <li>)",
      "category": "Stocks",
      "source_name": "Reuters",
      "source_url": "https://reuters.com",
      "meta_title": "Meta Title under 60 chars",
      "meta_description": "Meta Description under 160 chars",
      "keywords": ["Stocks", "Crypto", "Finance"]
    }
    """

    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}  # 👈 इससे Groq सिर्फ शुद्ध JSON ही देगा
            )
            raw_text = response.choices[0].message.content.strip()
            return json.loads(raw_text)
        except json.JSONDecodeError as e:
            logging.warning(f"JSON Parsing Error: {e} (Attempt {attempt+1}/3). Retrying...")
            time.sleep(2)
        except Exception as e:
            logging.error(f"Groq API Error: {e}")
            time.sleep(2)
            
    return None
def auto_git_push(article_title):
    logging.info("Pushing new article to GitHub...")
    try:
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", f"Auto-news: {article_title}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        logging.info("SUCCESS: Successfully pushed to GitHub!")
    except Exception as e:
        logging.error(f"Git Push failed: {e}")

# ==========================================
# 6. MAIN BOT EXECUTION
# ==========================================
def run_bot():
    ai_data = generate_news_with_groq()
    if not ai_data:
        logging.error("Failed to generate article from Groq.")
        return

    if is_duplicate(ai_data["title"]):
        logging.info(f"Skipping duplicate news: {ai_data['title']}")
        return

    slug = generate_slug(ai_data["title"])
    local_image_path = fetch_and_save_hd_image(ai_data["category"], slug)
    source_name = ai_data.get("source_name", "Reuters")
    credibility_score = config.SOURCE_CREDIBILITY.get(source_name, 9)

    schema_org = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": ai_data["title"],
        "image": [f"https://times07news.in/{local_image_path}"],
        "datePublished": datetime.now().isoformat(),
        "author": {"@type": "Organization", "name": "Times07 News"},
        "publisher": {"@type": "Organization", "name": "Times07 News"}
    }

    entry = {
        "id": int(datetime.now().timestamp()),
        "slug": slug,
        "title": ai_data["title"],
        "one_line_headline": ai_data["one_line_headline"],
        "summary_50": ai_data["summary_50_words"],
        "summary_150": ai_data["summary_150_words"],
        "content_html": ai_data["content_html"],
        "category": ai_data["category"],
        "image": local_image_path,
        "reading_time": calculate_reading_time(ai_data["content_html"]),
        "source": source_name,
        "source_url": ai_data.get("source_url", "https://times07news.in"),
        "credibility_score": f"{credibility_score}/10",
        "seo": {
            "meta_title": ai_data["meta_title"],
            "meta_description": ai_data["meta_description"],
            "keywords": ai_data["keywords"],
            "canonical_url": f"https://times07news.in/article.html?slug={slug}",
            "json_ld": schema_org
        },
        "published_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # Save to news.json
    db_file = "news.json"
    news_list = []
    if os.path.exists(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                news_list = json.load(f)
        except json.JSONDecodeError:
            news_list = []

    news_list.insert(0, entry)

    with open(db_file, "w", encoding="utf-8") as f:
        json.dump(news_list, f, ensure_ascii=False, indent=4)

    logging.info(f"SUCCESS: Article '{ai_data['title']}' generated and saved to news.json!")

    # Auto Push to GitHub
    auto_git_push(ai_data["title"])

if __name__ == "__main__":
    run_bot()