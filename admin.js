// ==========================================================================
// TIMES07 ENTERPRISE DASHBOARD LOGIC
// ==========================================================================

// 1. ऑटो न्यूज़ पब्लिशर ट्रिगर (Auto News Sync)
window.fetchInstantAutoNews = async function() {
    alert("GNews API से ताज़ा ऑटो-न्यूज़ लोड हो रही है...");
    // यहाँ से ऑटो-फ़ेच ट्रिगर होगा
};

// 2. खबर हटाने (Delete Article) का फ़ंक्शन
window.deleteArticleAdmin = function(articleId) {
    if(confirm("क्या आप वाकई इस खबर को डिलीट करना चाहते हैं?")) {
        alert("खबर #" + articleId + " सफलता से डिलीट कर दी गई है!");
    }
};

// 3. लाइव विज़िटर्स सिम्युलेटर
setInterval(() => {
    const visitorElem = document.querySelector('#sec-dashboard .stat-card:nth-child(3) h2');
    if(visitorElem) {
        const randomCount = Math.floor(Math.random() * (1400 - 1200 + 1)) + 1200;
        visitorElem.innerText = randomCount;
    }
}, 3000);
// AURA-07 UI & Chat Logic
async function loadChatHistory() {
  const chatLogs = document.getElementById('chat-logs');
  if (!chatLogs) return;

  try {
    const res = await fetch('http://127.0.0.1:5000/api/chat_history');
    const history = await res.json();
    chatLogs.innerHTML = '';

    if (history.length === 0) {
      chatLogs.innerHTML = `<div style="background: #202225; padding: 10px 14px; border-radius: 8px; color: #00ffcc; max-width: 85%; font-size: 13px;"><b>Maxi:</b> जी बॉस! मैं तैयार हूँ। हुक्म कीजिए।</div>`;
    } else {
      history.forEach(item => {
        appendUserMessage(item.user);
        appendAiMessage(item.ai);
      });
    }
    chatLogs.scrollTop = chatLogs.scrollHeight;
  } catch (err) {
    chatLogs.innerHTML = `<div style="color: #ff4757; font-size: 12px;">⚠️ Server offline. Please run aura.py</div>`;
  }
}

function appendUserMessage(msg) {
  const chatLogs = document.getElementById('chat-logs');
  const div = document.createElement('div');
  div.style.cssText = "align-self: flex-end; background: #2f3542; color: #fff; padding: 9px 13px; border-radius: 12px 12px 0px 12px; max-width: 80%; font-size: 13px; word-break: break-word;";
  div.innerHTML = `<b>You:</b> ${msg}`;
  chatLogs.appendChild(div);
  chatLogs.scrollTop = chatLogs.scrollHeight;
}

function appendAiMessage(msg) {
  const chatLogs = document.getElementById('chat-logs');
  const div = document.createElement('div');
  div.style.cssText = "align-self: flex-start; background: #1e272e; color: #00d2d3; padding: 9px 13px; border-radius: 12px 12px 12px 0px; max-width: 80%; font-size: 13px; border-left: 3px solid #00d2d3; word-break: break-word;";
  div.innerHTML = `<b>Maxi:</b> ${msg}`;
  chatLogs.appendChild(div);
  chatLogs.scrollTop = chatLogs.scrollHeight;
}

async function sendAuraCmd() {
  const adminInput = document.getElementById('admin-input');
  const msg = adminInput.value.trim();
  if (!msg) return;

  appendUserMessage(msg);
  adminInput.value = '';

  try {
    const res = await fetch('http://127.0.0.1:5000/api/admin_chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    appendAiMessage(data.reply);
  } catch (err) {
    appendAiMessage("सर्वर कनेक्ट नहीं हो पाया बॉस! कृपया चेक करें कि python aura.py चल रहा है या नहीं।");
  }
}

// Enter key binding & Auto Load History
document.addEventListener("DOMContentLoaded", () => {
  loadChatHistory();
  const input = document.getElementById('admin-input');
  if (input) {
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") sendAuraCmd();
    });
  }
});