import os
import json
import time
import random
import argparse
from datetime import datetime
from openai import OpenAI
from ddgs import DDGS
import config

# Groq Client Initialization
import random
import config

def get_next_client():
    key = random.choice(config.GROQ_KEYS)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")

client = get_next_client()

def search_hd_images(query, count=5):
    """गूगल/DuckDuckGo से एक्टर या न्यूज़ से रिलेटेड 5 HD इमेजेस फेच करता है, एरर आने पर प्रीमियम बैकअप यूज करेगा"""
    images = []
    try:
        time.sleep(2) # API Limit से बचने के लिए
        with DDGS() as ddgs:
            results = list(ddgs.images(f"{query} high resolution recent photo", max_results=count))
            for res in results:
                if 'image' in res:
                    images.append(res['image'])
    except Exception as e:
        print(f"⚠️ Image Search API Limit Hit. Switching to Premium Fallback Images...")
    
    # विशाल HD Fallback लाइब्रेरी 
    fallback_hd = [
        "https://images.unsplash.com/photo-1598899134739-24c46f58b8c0?w=1000",
        "https://images.unsplash.com/photo-1485846234645-a62644f84728?w=1000",
        "https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=1000",
        "https://images.unsplash.com/photo-1536440136628-849c177e76a1?w=1000",
        "https://images.unsplash.com/photo-1524985069026-dd778a71c7b4?w=1000",
        "https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1000",
        "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=1000",
        "https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1000",
        "https://images.unsplash.com/photo-1515694346937-94d85e41e6f0?w=1000"
    ]
    
    if len(images) < count:
        needed = count - len(images)
        images.extend(random.sample(fallback_hd, needed))
        
    return images[:count]

def fetch_live_trending_news():
    """गूगल पर चल रही ताज़ा बॉलीवुड गॉसिप फेच करता है"""
    try:
        time.sleep(1)
        with DDGS() as ddgs:
            news_results = list(ddgs.news("Bollywood viral gossip breaking news india", max_results=3))
            if news_results:
                return [n['title'] + " " + n.get('body', '') for n in news_results]
    except Exception as e:
        print(f"⚠️ News Fetch Warning: {e}")
    return []

def generate_bollywood_draft(topic_context=None, is_biography=False):
    """बोट का मेन AI जनरेटर लॉजिक"""
    
    if is_biography:
        prompt_instruction = f"""
        विषय: बॉलीवुड सुपरस्टार बायोग्राफी (Biography Special) - '{topic_context}'.
        
        सख्त निर्देश (CRITICAL COMMAND - DO NOT IGNORE):
        1. यह एक बेहद विस्तृत और प्रो-लेवल बायोग्राफी होनी चाहिए (Wikipedia स्टाइल में)। 
        2. शब्द सीमा: कम से कम 1200 से 1500 शब्दों का प्रयोग करें। (VERY LONG FORM ARTICLE).
        3. कम से कम 6-7 अलग-अलग हेडिंग्स (<h3>) शामिल करें: 
           - प्रारंभिक जीवन और संघर्ष
           - फिल्मी करियर की शुरुआत
           - टर्निंग पॉइंट और सबसे बड़ी हिट फिल्में
           - लव लाइफ, अफेयर्स और विवाद (गॉसिप स्टाइल)
           - कुल संपत्ति (Net Worth) और लाइफस्टाइल
           - आने वाले प्रोजेक्ट्स
        4. टोन: मसालेदार, रोचक और पढ़ने में मजेदार।
        """
    else:
        prompt_instruction = f"""
        विषय: बॉलीवुड ताज़ा ब्रेकिंग / गॉसिप खबर - '{topic_context}'.
        
        सख्त निर्देश:
        1. टोन एकदम चटपटा, बॉलीवुड मसाला स्टाइल और सस्पेंस से भरा होना चाहिए।
        2. आर्टिकल में कम से कम 4 सब-हेडिंग्स (<h3>) जरूर होनी चाहिए।
        3. खबर को विस्तार से 500-800 शब्दों में <p> टैग्स के साथ लिखें।
        """

    prompt = f"""
    आप Times07 News के सबसे बड़े एंटरटेनमेंट जर्नलिस्ट हैं।
    {prompt_instruction}

    CRITICAL REQUIREMENTS:
    1. WRITE EVERYTHING STRICTLY IN PURE HINDI (हिंदी भाषा में).
    2. 5 चटपटे और SEO फ्रेंडली टाइटल्स जनरेट करें (title_options में 5 ऑप्शंस दें)।
    3. हर टाइटल के अंत में ' | Times07 News' ज़रूर लगाएं।

    Return strictly a VALID JSON object (NO markdown formatting, just raw JSON):
    {{
      "title_options": [
        "पहला चटपटा टाइटल | Times07 News",
        "दूसरा वायरल टाइटल | Times07 News",
        "तीसरा सस्पेंस टाइटल | Times07 News",
        "चौथा बड़ा खुलासा टाइटल | Times07 News",
        "पांचवा ट्रेंडिंग टाइटल | Times07 News"
      ],
      "one_line_teaser": "हिंदी में 1-लाइन का मसालेदार टीज़र",
      "visual_summary_points": [
        "मुख्य बिंदु 1", "मुख्य बिंदु 2", "मुख्य बिंदु 3", "मुख्य बिंदु 4"
      ],
      "content_html": "<h3>हेडिंग 1</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 2</h3><p>विस्तृत पैराग्राफ...</p><h3>हेडिंग 3</h3><p>विस्तृत पैराग्राफ...</p>",
      "category": "मनोरंजन",
      "default_tags": ["#BollywoodGossip", "#Times07Exclusive", "#CelebUpdate"]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=6000, 
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content.strip())
        
        search_keyword = topic_context if topic_context else "Bollywood Stars"
        data["image_options"] = search_hd_images(search_keyword, count=5)
        
        data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["bot_type"] = "bollywood"
        data["id"] = int(datetime.now().timestamp() * 1000)
        
        return data
    except Exception as e:
        print(f"❌ Generation Error: {e}")
        return None

def save_to_drafts(draft_data):
    """डैशबोर्ड के लिए drafts.json में सेव करता है"""
    drafts_file = "drafts.json"
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
        
    print(f"✅ SUCCESS: Draft saved to drafts.json!")

def run_bollywood_bot_batch():
    """एक बार में 3 टॉपिक्स जनरेट करने का प्रो-लेवल ऑटोमेशन लॉजिक"""
    print("\n🎬 Bollywood Bot Running PRO Batch Execution...")
    
    live_news_list = fetch_live_trending_news()
    
    famous_actors = [
        "Shah Rukh Khan", "Salman Khan", "Deepika Padukone", "Ranbir Kapoor", 
        "Amitabh Bachchan", "Alia Bhatt", "Hrithik Roshan", "Kareena Kapoor", 
        "Akshay Kumar", "Katrina Kaif", "Ranveer Singh", "Priyanka Chopra", 
        "Aamir Khan", "Anushka Sharma", "Tiger Shroff", "Shraddha Kapoor",
        "Ajay Devgn", "Kajol", "Vicky Kaushal", "Kiara Advani",
        "Kartik Aaryan", "Kriti Sanon", "Varun Dhawan", "Janhvi Kapoor"
    ]
    random.shuffle(famous_actors)
    
    generated_count = 0
    
    for news in live_news_list[:3]:
        print(f"📰 Generating Deep News Draft for: {news[:40]}...")
        draft = generate_bollywood_draft(topic_context=news, is_biography=False)
        if draft:
            save_to_drafts(draft)
            generated_count += 1

    actor_index = 0
    while generated_count < 3 and actor_index < len(famous_actors):
        actor = famous_actors[actor_index]
        print(f"⭐ Generating PRO Biography Draft (1500 words) for Actor: {actor}...")
        draft = generate_bollywood_draft(topic_context=actor, is_biography=True)
        if draft:
            save_to_drafts(draft)
            generated_count += 1
        actor_index += 1

    print(f"✨ BATCH COMPLETE: 3 In-depth Topics successfully sent to Admin Dashboard!\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--topic', type=str, help='Manual command to generate a specific topic')
    args = parser.parse_args()

    # अगर डैशबोर्ड से मैन्युअल कमांड आती है तो यह रन होगा
    if args.topic:
        print(f"⚡ Manual Command Received for: {args.topic}")
        draft = generate_bollywood_draft(topic_context=args.topic, is_biography=True)
        if draft: 
            save_to_drafts(draft)
            print("✅ Manual Topic Generated Successfully!")
    else:
        print("🚀 PRO Bollywood Bot Service Started (Auto-runs every 1 hour)...")
        while True:
            run_bollywood_bot_batch()
            print("⏰ Sleeping for 1 Hour (3600 Seconds)...")
            time.sleep(3600)