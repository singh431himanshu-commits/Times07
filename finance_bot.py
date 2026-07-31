import os
import json
import time
import random
import argparse
from datetime import datetime
from openai import OpenAI
from ddgs import DDGS
import config

# Groq Client Initialization (Bollywood bot की तरह)[cite: 7]
import random
import config

def get_next_client():
    key = random.choice(config.GROQ_KEYS)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

client = get_next_client()

def search_hd_finance_images(query, count=5):
    """गूगल/DuckDuckGo से शेयर मार्केट/क्रिप्टो से रिलेटेड 5 HD इमेजेस फेच करता है"""
    images = []
    try:
        time.sleep(2) # API Limit से बचने के लिए[cite: 7]
        with DDGS() as ddgs:
            # High resolution recent photo लगाकर सर्च करेगा[cite: 7]
            results = list(ddgs.images(f"{query} stock market finance high resolution", max_results=count))
            for res in results:
                if 'image' in res:
                    images.append(res['image'])
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Switching to Finance Premium Fallback Images...")
    
    # शेयर मार्केट, ट्रेडिंग डेस्क और क्रिप्टो की विशाल HD Fallback लाइब्रेरी 
    fallback_hd = [
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1000", # Crypto
        "https://images.unsplash.com/photo-1590283603385-18ff38593524?w=1000", # Stock Market graph
        "https://images.unsplash.com/photo-1642543492481-44e81e39148c?w=1000", # Trading
        "https://images.unsplash.com/photo-1621961458348-f013d219b50c?w=1000", # Nifty/Sensex style
        "https://images.unsplash.com/photo-1518531933037-91b2f5f229cc?w=1000", # Finance abstract
        "https://images.unsplash.com/photo-1608222351212-18fe0ec7b13b?w=1000", # Bitcoin
        "https://images.unsplash.com/photo-1526628953301-3e589a6a8b74?w=1000", # Money/Graph
        "https://images.unsplash.com/photo-1535320903710-d993d3d77d29?w=1000"  # Banking/Finance
    ]
    
    # अगर 5 इमेजेज नहीं मिलीं, तो फॉलबैक से भर देगा[cite: 7]
    if len(images) < count:
        needed = count - len(images)
        images.extend(random.sample(fallback_hd, needed))
        
    return images[:count]

def fetch_live_finance_news():
    """गूगल पर चल रही ताज़ा शेयर बाजार और क्रिप्टो की 5 ख़बरें फेच करता है"""
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            # 5 news fetch करने का लॉजिक[cite: 7]
            news_results = list(ddgs.news("share market cryptocurrency finance breaking news", max_results=5))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_finance_draft(topic_context):
    """बोट का मेन AI जनरेटर लॉजिक जो Deep Research करेगा[cite: 7]"""
    
    prompt = f"""
    आप भारत के नंबर 1 फाइनेंशियल एनालिस्ट और Times07 News के एक्सपर्ट रिपोर्टर हैं।
    विषय: '{topic_context}'.
    
    सख्त निर्देश (CRITICAL COMMANDS):
    1. भाषा: सब कुछ शुद्ध और प्रोफेशनल लेकिन आसान हिंदी में लिखें (PURE HINDI).
    2. गहराई (Deep Research): खबर को पूरे विस्तार से समझाएं (कम से कम 500 से 700 शब्दों में).
    3. संरचना: कम से कम 4-5 अलग-अलग हेडिंग्स (<h3>) शामिल करें, जैसे: 
       - आज की बड़ी खबर क्या है?
       - शेयर बाजार / क्रिप्टो पर इसका क्या असर होगा?
       - निवेशकों (Investors) के लिए सलाह।
       - भविष्य का अनुमान।
    4. 5 कैंची (Catchy/Clickbait) टाइटल्स जनरेट करें जो लोगों को क्लिक करने पर मजबूर कर दें। हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं[cite: 7]।
    5. शानदार SEO फ्रेंडली Google Meta Tags और Hashtags (जिसमें #Times07News, #ShareMarket, #CryptoNews शामिल हों) जनरेट करें।

    Return strictly a VALID JSON object (NO markdown formatting, just raw JSON)[cite: 7]:
    {{
      "title_options": [
        "पहला कैंची टाइटल | Times07 News",
        "दूसरा वायरल टाइटल | Times07 News",
        "तीसरा सस्पेंस टाइटल | Times07 News",
        "चौथा ब्रेकिंग टाइटल | Times07 News",
        "पांचवा ट्रेंडिंग टाइटल | Times07 News"
      ],
      "meta_description": "गूगल सर्च के लिए 2 लाइन का शानदार SEO मेटा डिस्क्रिप्शन",
      "hashtags": ["#Times07News", "#ShareMarket", "#Crypto", "#FinanceIndia", "न्यूज़ से जुड़े 5 और टैग्स"],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत 500 शब्दों का रिसर्च पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 3</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "बिजनेस",
      "default_tags": ["शेयर बाजार", "क्रिप्टोकरेंसी", "फाइनेंस"]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=6000, 
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content.strip())
        
        # 5 HD इमेजेज फेच करना
        data["image_options"] = search_hd_finance_images(topic_context, count=5)
        
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "finance_crypto"
        data["id"] = int(datetime.now().timestamp() * 1000)
        
        return data
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        return None

def save_to_drafts(draft_data):
    """डैशबोर्ड के लिए drafts_finance.json में सेव करता है[cite: 7]"""
    drafts_file = "drafts_finance.json"
    drafts = []
    if os.path.exists(drafts_file):
        try:
            with open(drafts_file, "r", encoding="utf-8") as f:
                drafts = json.load(f)
        except Exception:
            drafts = []
            
    drafts.insert(0, draft_data)
    with open(drafts_file, "w", encoding="utf-8") as f:
        json.dump(drafts, f, ensure_ascii=False, indent=4)
        
    print(f"✅ SUCCESS: Finance Draft saved to drafts_finance.json!")

def run_finance_bot_batch():
    """एक बार में 5 न्यूज़ जनरेट करने का ऑटोमेशन लॉजिक"""
    print("\n📈 Finance & Crypto Bot Running Batch Execution...")
    
    # इंटरनेट से 5 ताज़ा ख़बरें उठाएगा
    live_news_list = fetch_live_finance_news()
    
    # अगर इंटरनेट से 5 न्यूज़ नहीं मिलीं, तो इन एवरग्रीन टॉपिक्स का इस्तेमाल करेगा
    evergreen_finance_topics = [
        "Nifty 50 and Sensex Today Market Prediction", 
        "Bitcoin and Ethereum Price Analysis Today", 
        "Best Penny Stocks to Buy in Indian Market", 
        "Upcoming IPOs in India and GMP Updates", 
        "Mutual Funds vs Direct Stocks: Where to invest?",
        "Gold Prices Today and Future Prediction"
    ]
    random.shuffle(evergreen_finance_topics)
    
    generated_count = 0
    
    # पहले ताज़ा खबरों पर रिसर्च करेगा
    for news in live_news_list:
        if generated_count >= 5:
            break
        print(f"📰 Generating Deep Research for News: {news[:50]}...")
        draft = generate_finance_draft(topic_context=news)
        if draft:
            save_to_drafts(draft)
            generated_count += 1

    # अगर ताज़ा खबरें 5 से कम रह गईं, तो एवरग्रीन टॉपिक्स पर लिखेगा
    topic_index = 0
    while generated_count < 5 and topic_index < len(evergreen_finance_topics):
        topic = evergreen_finance_topics[topic_index]
        print(f"📊 Generating Deep Research for Evergreen Topic: {topic}...")
        draft = generate_finance_draft(topic_context=topic)
        if draft:
            save_to_drafts(draft)
            generated_count += 1
        topic_index += 1

    print(f"✨ BATCH COMPLETE: 5 Deep Finance Topics successfully sent to Dashboard!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help='Manual command to generate a specific finance topic')
    args = parser.parse_args()

    # मैन्युअल कमांड[cite: 7]
    if args.topic:
        print(f"⚡ Manual Command Received for: {args.topic}")
        draft = generate_finance_draft(topic_context=args.topic)
        if draft: 
            save_to_drafts(draft)
            print("✅ Manual Topic Generated Successfully!")
    else:
        # ऑटोमैटिक लूप[cite: 7]
        print("🚀 PRO Finance Bot Service Started (Auto-runs every 1 hour)...")
        while True:
            run_finance_bot_batch()
            print("⏰ Sleeping for 1 Hour (3600 Seconds)...")
            time.sleep(3600)