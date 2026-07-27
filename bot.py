import urllib.request
import xml.etree.ElementTree as ET
import re
import requests
import time
from bs4 import BeautifulSoup

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"

# टॉप न्यूज़ और कैटेगरी वाइज़ सोर्सेस (RSS Feeds)
RSS_CONFIG = [
    # 1. ब्रेकिंग और इंडिया न्यूज़
    {"url": "https://zeenews.india.com/rss/india-national-news.xml", "category": "भारत"},
    {"url": "https://feeds.feedburner.com/ndtvkhabar", "category": "ब्रेकिंग न्यूज़"},
    
    # 2. इंटरनेशनल न्यूज़ और पॉलिटिक्स
    {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "category": "विदेश"},
    {"url": "http://feeds.bbci.co.uk/news/world/rss.xml", "category": "विदेश"},
    
    # 3. गेमिंग (Gaming News)
    {"url": "https://www.ign.com/rss/articles/feed?filter=games", "category": "गेमिंग"},
    {"url": "https://www.gamespot.com/feeds/news/", "category": "गेमिंग"},
    
    # 4. लाइफस्टाइल (Lifestyle)
    {"url": "https://timesofindia.indiatimes.com/rssfeeds/2886704.cms", "category": "लाइफस्टाइल"}
]

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, 'html.parser')
    return soup.get_text().strip()

def get_image(item_xml_str):
    soup = BeautifulSoup(item_xml_str, 'html.parser')
    
    # 1. Check img tags inside description/content
    img = soup.find('img')
    if img and img.get('src'):
        return img['src']
        
    # 2. Check media:content, media:thumbnail, or enclosure
    media = soup.find(['media:content', 'media:thumbnail', 'enclosure'])
    if media and media.get('url'):
        return media['url']
        
    # Default High Quality Fallback Image
    return "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800"

def fetch_and_push():
    print("Fetching news from all categories...")
    for item_config in RSS_CONFIG:
        url = item_config["url"]
        category = item_config["category"]
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req, timeout=10).read()
            root = ET.fromstring(xml_data)

            # हर सोर्स से टॉप 3 ताज़ा खबरें
            for item in root.findall('.//item')[:3]:
                item_str = ET.tostring(item, encoding='utf8').decode('utf8')
                
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                
                clean_desc = clean_html(desc) if desc else title
                img_url = get_image(item_str)

                if title:
                    payload = {
                        "title": title,
                        "desc": clean_desc[:250] + "...",
                        "img1": img_url,
                        "category": category,
                        "views": 1500,
                        "timestamp": int(time.time() * 1000)
                    }
                    requests.post(FIREBASE_URL, json=payload)
                    print(f"[{category}] Published: {title[:30]}...")
        except Exception as e:
            print(f"Error fetching from {url}: {e}")

if __name__ == "__main__":
    fetch_and_push()