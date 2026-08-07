import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"

def fetch_articles():
    try:
        req = urllib.request.urlopen(FIREBASE_URL)
        data = json.loads(req.read().decode('utf-8'))
        if not data:
            return []
        
        valid_articles = []
        if isinstance(data, dict):
            for val in data.values():
                if isinstance(val, dict):
                    valid_articles.append(val)
        elif isinstance(data, list):
            for val in data:
                if isinstance(val, dict):
                    valid_articles.append(val)
                    
        return valid_articles
    except Exception as e:
        print(f"Error fetching Firebase data: {e}")
        return []

def generate_sitemaps():
    articles = fetch_articles()
    if not articles:
        print("No articles found in Firebase.")
        return

    # 1. Standard sitemap.xml
    urlset_std = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    
    url_home = ET.SubElement(urlset_std, "url")
    ET.SubElement(url_home, "loc").text = "https://times07news.in/"
    ET.SubElement(url_home, "changefreq").text = "daily"
    ET.SubElement(url_home, "priority").text = "1.0"

    for art in articles:
        slug = art.get('slug')
        if not slug:
            continue
        link = f"https://times07news.in/article.html?slug={slug}"
        url = ET.SubElement(urlset_std, "url")
        ET.SubElement(url, "loc").text = link
        ET.SubElement(url, "changefreq").text = "daily"
        ET.SubElement(url, "priority").text = "0.8"

    ET.indent(urlset_std, space="  ") # 👈 यहाँ स्पेस इंडेंट जोड़ा गया है
    tree_std = ET.ElementTree(urlset_std)
    tree_std.write("sitemap.xml", encoding="utf-8", xml_declaration=True)
    print("✅ sitemap.xml Updated Successfully!")

    # 2. Google News news-sitemap.xml (Last 48 Hours)
    urlset_news = ET.Element("urlset", 
                             xmlns="http://www.sitemaps.org/schemas/sitemap/0.9",
                             attrib={"xmlns:news": "http://www.google.com/schemas/sitemap-news/0.9"})

    now = datetime.now()
    two_days_ago = now - timedelta(days=2)

    news_count = 0
    for art in articles:
        slug = art.get('slug')
        title = art.get('title')
        timestamp = art.get('timestamp')

        if not slug or not title:
            continue

        if timestamp:
            pub_date = datetime.fromtimestamp(timestamp / 1000.0)
        else:
            pub_date = now

        if pub_date >= two_days_ago:
            news_count += 1
            link = f"https://times07news.in/article.html?slug={slug}"
            
            url = ET.SubElement(urlset_news, "url")
            ET.SubElement(url, "loc").text = link

            news_elem = ET.SubElement(url, "news:news")
            pub_elem = ET.SubElement(news_elem, "news:publication")
            ET.SubElement(pub_elem, "news:name").text = "Times07 News"
            ET.SubElement(pub_elem, "news:language").text = "hi"

            date_iso = pub_date.strftime("%Y-%m-%dT%H:%M:%S+05:30")
            ET.SubElement(news_elem, "news:publication_date").text = date_iso
            ET.SubElement(news_elem, "news:title").text = title

    ET.indent(urlset_news, space="  ") # 👈 यहाँ स्पेस इंडेंट जोड़ा गया है
    tree_news = ET.ElementTree(urlset_news)
    tree_news.write("news-sitemap.xml", encoding="utf-8", xml_declaration=True)
    print(f"✅ news-sitemap.xml Updated Successfully ({news_count} Latest Articles)!")

if __name__ == "__main__":
    generate_sitemaps()