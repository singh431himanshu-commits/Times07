import urllib.request
import xml.etree.ElementTree as ET
import re
import requests
import time

# 1. Firebase URL
FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"

# 2. News Sources
RSS_URLS = [
    "https://zeenews.india.com/rss/india-national-news.xml",
    "https://feeds.feedburner.com/ndtvkhabar"
]

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    return re.sub(cleanr, '', raw_html).strip()

def fetch_and_push():
    print("Fetching news...")
    for url in RSS_URLS:
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            xml_data = urllib.request.urlopen(req, timeout=10).read()
            root = ET.fromstring(xml_data)

            for item in root.findall('.//item')[:3]:
                title = item.find('title').text if item.find('title') is not None else ""
                desc = item.find('description').text if item.find('description') is not None else ""
                
                clean_desc = clean_html(desc) if desc else title

                if title:
                    payload = {
                        "title": title,
                        "desc": clean_desc[:150] + "...",
                        "img1": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800",
                        "category": "ब्रेकिंग न्यूज़",
                        "views": 1200,
                        "timestamp": int(time.time() * 1000)
                    }
                    # Firebase में सीधे डेटा पब्लिश करना
                    requests.post(FIREBASE_URL, json=payload)
                    print(f"Published: {title[:30]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    fetch_and_push()