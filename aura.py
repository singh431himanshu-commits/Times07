import os
import json
import sqlite3
import ollama
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json"

# 🧠 SQLite Memory Setup
def init_db():
    conn = sqlite3.connect("aura_memory.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_cmd TEXT,
            ai_reply TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def save_memory(cmd, reply):
    conn = sqlite3.connect("aura_memory.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO memory (user_cmd, ai_reply) VALUES (?, ?)", (cmd, reply))
    conn.commit()
    conn.close()

@app.route("/api/admin_chat", methods=["POST"])
def admin_chat():
    data = request.json
    user_msg = data.get("message", "")

    # 1. AUTO NEWS COMMAND CHECK
    if "news" in user_msg.lower() or "खबर" in user_msg or "publish" in user_msg.lower():
        try:
            # RSS/Bot script execution
            os.system("python bot.py")
            ai_reply = "बॉस! मैंने ताज़ा खबरें ऑटो-फेच करके वेबसाइट पर पब्लिश कर दी हैं। 🚀"
        except Exception as e:
            ai_reply = f"खबरें पब्लिश करने में एरर आया बॉस: {str(e)}"

    # 2. CODE/LAYOUT CHANGE REQUEST
    elif "layout" in user_msg.lower() or "grid" in user_msg.lower() or "डिजाइन" in user_msg:
        ai_reply = "बॉस! लेआउट और HTML/CSS कोड में बदलाव का निर्देश मिल गया है। मैं इसे प्रोसेस कर रहा हूँ..."

    # 3. NORMAL CHAT & ASSISTANCE (Phi-3 AI)
    else:
        full_prompt = f"""
        आप याशी (Boss) के पर्सनल AI असिस्टेंट Maxi (AURA-07) हैं। 
        वेबसाइट 'Times07' के एडमिन कंट्रोलर हैं।
        Boss का संदेश: {user_msg}
        छोटा, सटीक और मददगार जवाब दें।
        """
        try:
            response = ollama.chat(
                model='phi3',
                messages=[{'role': 'user', 'content': full_prompt}]
            )
            ai_reply = response['message']['content'].strip()
        except Exception as e:
            ai_reply = f"एरर आया बॉस: {str(e)}"

    save_memory(user_msg, ai_reply)

    # 4. GIT AUTO PUSH
    if "push" in user_msg.lower() or "live" in user_msg.lower() or "पब्लिश" in user_msg:
        os.system("git add .")
        os.system('git commit -m "Auto Update by AURA Maxi"')
        os.system("git push origin master")
        ai_reply += "\n\n🚀 (सभी बदलाव GitHub पर लाइव पुश कर दिए गए हैं!)"

    return jsonify({"reply": ai_reply})

@app.route("/api/chat_history", methods=["GET"])
def chat_history():
    conn = sqlite3.connect("aura_memory.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_cmd, ai_reply FROM memory ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    
    history = [{"user": r[0], "ai": r[1]} for r in rows]
    return jsonify(history)

if __name__ == "__main__":
    print("🤖 AURA-07 (Phi-3 Engine) Started on Port 5000...")
    app.run(port=5000)