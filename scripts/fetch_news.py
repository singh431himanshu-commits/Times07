import urllib.request
import xml.etree.ElementTree as ET
import json

# ताज़ा हिंदी न्यूज़ फ़ीड्स (आजतक और ज़ी न्यूज़)
RSS_URLS = [
    "https://zeenews.india.com/rss/india-national-news.xml",
    "https://www.amarujala.com/rss/breaking-news.xml"
]

news_list = []

for url in RSS_URLS:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        xml_data = response.read()
        
        root = ET.fromstring(xml_data)
        for item in root.findall('.//item')[:8]:
            title = item.find('title').text if item.find('title') is not None else ""
            desc = item.find('description').text if item.find('description') is not None else ""
            
            # HTML टैग्स साफ़ करना
            clean_desc = desc.split('<')[0] if '<' in desc else desc
            
            img = "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800"
            
            if title:
                news_list.append({
                    "title": title,
                    "desc": clean_desc[:120] + "...",
                    "img1": img,
                    "category": "ब्रेकिंग न्यूज़",
                    "views": 1500
                })
    except Exception as e:
        print(f"Error fetching {url}: {e}")

# news.json फ़ाइल बनाना
with open("news.json", "w", encoding="utf-8") as f:
    json.dump(news_list, f, ensure_ascii=False, indent=4)

print("ताज़ा खबरें सफलतापूर्वक अपडेट हो गईं!")