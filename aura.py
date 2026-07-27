from ddgs import DDGS
import json
import os

def fetch_trending_news():
    print("🌐 AURA-07: लाइव ट्रेंडिंग खबरें स्क्रैप की जा रही हैं...")
    try:
        results = list(DDGS().text("breaking news india hindi aajtak tv9", max_results=5))
        articles = []
        for i, item in enumerate(results, 1):
            # ऑटोमैटिक अनस्पलैश इमेज यूआरएल (न्यूज़ टॉपिक के हिसाब से)
            image_url = f"https://picsum.photos/800/400?random={i}"
            articles.append({
                "id": i,
                "title": item['title'],
                "summary": item['body'],
                "link": item['href'],
                "image": image_url
            })
        return articles
    except Exception as e:
        print(f"❌ स्क्रैपिंग एरर: {e}")
        return []

def update_website_data(news_list):
    print("📝 AURA-07: 'news.json' डेटाबेस अपडेट किया जा रहा है...")
    try:
        with open("news.json", "w", encoding="utf-8") as f:
            json.dump(news_list, f, ensure_ascii=False, indent=4)
        print("✅ 'news.json' सफलतापूर्वक अपडेट हो गया!")
    except Exception as e:
        print(f"❌ JSON सेव एरर: {e}")

def aura_main():
    print("====================================")
    print("🤖 AURA-07 AUTOMATIC PUBLISHER ONLINE")
    print("====================================\n")
    
    news = fetch_trending_news()
    if news:
        update_website_data(news)
        print("\n🚀 बधाई हो बॉस! AURA-07 ने सभी ट्रेंडिंग आर्टिकल्स पब्लिश करने के लिए तैयार कर दिए हैं।")
    else:
        print("⚠️ कोई नई खबर नहीं मिली।")

if __name__ == "__main__":
    aura_main()