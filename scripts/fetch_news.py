 import urllib.request
import xml.etree.ElementTree as ET
import json
import re

def clean_html(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext.strip()

# Working Hindi RSS Feeds (Zee News & NDTV Hindi)
RSS_URLS = [
    "https://zeenews.india.com/rss/india-national-news.xml",
    "https://feeds.feedburner.com/ndtvkhabar"
]

articles = []

for url in RSS_URLS:
    try:
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        xml_data = urllib.request.urlopen(req, timeout=10).read()
        root = ET.fromstring(xml_data)

        for item in root.findall('.//item')[:5]:
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            clean_desc = clean_html(desc) if desc else title

            if title:
                articles.append({
                    "title": title,
                    "desc": clean_desc[:120] + "...",
                    "img1": "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800",
                    "category": "ब्रेकिंग न्यूज़",
                    "views": 1500,
                    "date": "अभी-अभी"
                })
    except Exception as e:
        print(f"Error fetching from {url}: {e}")

# news.json को अपडेट करना
with open('news.json', 'w', encoding='utf-8') as f:
    json.dump(articles, f, ensure_ascii=False, indent=2)

print(f"Successfully saved {len(articles)} articles to news.json")