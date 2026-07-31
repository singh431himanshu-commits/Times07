// ==========================================================================
// TIMES07 ENTERPRISE DASHBOARD LOGIC
// ==========================================================================

const FIREBASE_URL = "https://times07news-default-rtdb.firebaseio.com/articles.json";

// 1. Firebase से लाइव खबरें एडमिन टेबल में लोड करें
window.loadAdminNewsTable = async function() {
    // admin.html की टेबल को टारगेट करने के लिए सही ID का इस्तेमाल
    const tableBody = document.getElementById('articles-list-table') || document.querySelector('table tbody');
    if (!tableBody) return;

    try {
        const response = await fetch(FIREBASE_URL);
        const data = await response.json();
        
        tableBody.innerHTML = ''; // पुरानी टेबल साफ़ करें

        if (!data) {
            tableBody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:15px; color:#888;">कोई खबर नहीं मिली। Bot चलाकर खबरें पब्लिश करें!</td></tr>`;
            return;
        }

        // Firebase के डेटा को लूप करके टेबल में दिखाएं
        Object.keys(data).reverse().forEach(key => {
            const item = data[key];
            const row = document.createElement('tr');
            row.style.borderBottom = "1px solid #2f3542";
            
            row.innerHTML = `
                <td style="padding: 12px; color: #fff; font-size: 14px;">${item.title || 'No Title'}</td>
                <td style="padding: 12px; color: #00d2d3; font-size: 13px;">${item.category || 'मुख्य समाचार'}</td>
                <td style="padding: 12px; text-align: left;">
                    <button onclick="window.deleteArticleAdmin('${key}')" style="background:#ff4757; color:#fff; border:none; padding:6px 12px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold;">हटाएं (Delete)</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    } catch (err) {
        console.error("Dashboard Load Error:", err);
    }
};

// 2. खबर हटाने (Delete Article) का असली Firebase फ़ंक्शन
window.deleteArticleAdmin = async function(articleId) {
    if(confirm("क्या आप वाकई इस खबर को हमेशा के लिए डिलीट करना चाहते हैं?")) {
        try {
            const deleteUrl = `https://times07news-default-rtdb.firebaseio.com/articles/${articleId}.json`;
            await fetch(deleteUrl, { method: 'DELETE' });
            alert("खबर सफलता से डिलीट कर दी गई है!");
            window.loadAdminNewsTable(); // टेबल को तुरंत रिफ़्रेश करें
        } catch(err) {
            alert("डिलीट करने में एरर आया!");
        }
    }
};

// 3. लाइव विज़िटर्स सिम्युलेटर (डैशबोर्ड स्टैट्स के लिए)
setInterval(() => {
    const visitorElem = document.querySelector('#sec-dashboard .stat-card:nth-child(3) h2');
    if(visitorElem) {
        const randomCount = Math.floor(Math.random() * (1400 - 1200 + 1)) + 1200;
        visitorElem.innerText = randomCount;
    }
}, 3000);

// ==========================================================================
// AURA-07 (MAXI) UI & CHAT LOGIC
// ==========================================================================

window.loadChatHistory = async function() {
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
        window.appendUserMessage(item.user);
        window.appendAiMessage(item.ai);
      });
    }
    chatLogs.scrollTop = chatLogs.scrollHeight;
  } catch (err) {
    chatLogs.innerHTML = `<div style="color: #ff4757; font-size: 12px;">⚠️ Server offline. Please run aura.py</div>`;
  }
};

window.appendUserMessage = function(msg) {
  const chatLogs = document.getElementById('chat-logs');
  const div = document.createElement('div');
  div.style.cssText = "align-self: flex-end; background: #2f3542; color: #fff; padding: 9px 13px; border-radius: 12px 12px 0px 12px; max-width: 80%; font-size: 13px; word-break: break-word;";
  div.innerHTML = `<b>You:</b> ${msg}`;
  chatLogs.appendChild(div);
  chatLogs.scrollTop = chatLogs.scrollHeight;
};

window.appendAiMessage = function(msg) {
  const chatLogs = document.getElementById('chat-logs');
  const div = document.createElement('div');
  div.style.cssText = "align-self: flex-start; background: #1e272e; color: #00d2d3; padding: 9px 13px; border-radius: 12px 12px 12px 0px; max-width: 80%; font-size: 13px; border-left: 3px solid #00d2d3; word-break: break-word;";
  div.innerHTML = `<b>Maxi:</b> ${msg}`;
  chatLogs.appendChild(div);
  chatLogs.scrollTop = chatLogs.scrollHeight;
};

window.sendAuraCmd = async function() {
  const adminInput = document.getElementById('admin-input');
  if (!adminInput) return;
  const msg = adminInput.value.trim();
  if (!msg) return;

  window.appendUserMessage(msg);
  adminInput.value = '';

  try {
    const res = await fetch('http://127.0.0.1:5000/api/admin_chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    window.appendAiMessage(data.reply);
  } catch (err) {
    window.appendAiMessage("सर्वर कनेक्ट नहीं हो पाया बॉस! कृपया चेक करें कि python aura.py चल रहा है या नहीं।");
  }
};

// Init Function on Load
document.addEventListener("DOMContentLoaded", () => {
  window.loadAdminNewsTable(); // Load News Table for Admin
  window.loadChatHistory();    // Load Chat History
  
  const input = document.getElementById('admin-input');
  if (input) {
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        window.sendAuraCmd();
      }
    });
  }
});