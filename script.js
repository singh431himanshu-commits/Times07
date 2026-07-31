// ==========================================================================
// ABP TIMES07 ENTERPRISE MEDIA NETWORK - UNIFIED SCRIPT ENGINE
// Firebase Realtime DB, Live Weather API, Market Tickers & Category Router
// ==========================================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

const firebaseConfig = {
    apiKey: "AIzaSyA0c_Bz7HdU6YoL62L1cGfsA89Hg7609Ww",
    authDomain: "times07news.firebaseapp.com",
    projectId: "times07news",
    storageBucket: "times07news.firebasestorage.app",
    messagingSenderId: "527951679601",
    appId: "1:527951679601:web:d33bfb58aaae9665c68bd0",
    measurementId: "G-VFC87XPD0V",
    databaseURL: "https://times07news-default-rtdb.firebaseio.com"
};

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);
const newsRef = ref(db, 'articles');

// Global Application State
window.sampleNews = [];
let currentSlideIndex = 0;
let featuredArticles = [];
let autoSlideInterval = null;

// Theme Switcher Engine
window.toggleTheme = function() {
    document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-mode');
    
    const themeIcons = document.querySelectorAll('#theme-icon');
    themeIcons.forEach(icon => {
        icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    });

    localStorage.setItem('times07_theme', isDark ? 'dark' : 'light');
};

function initTheme() {
    const savedTheme = localStorage.getItem('times07_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode', 'dark-theme');
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) themeIcon.className = 'fa-solid fa-sun';
    }
}
initTheme();

// Firebase Listener & UI Render Sync
onValue(newsRef, (snapshot) => {
    const data = snapshot.val();
    let firebaseArticles = [];
    if (data) {
        Object.keys(data).forEach(key => {
            firebaseArticles.push({ id: key, ...data[key] });
        });
        firebaseArticles.reverse(); // Latest First
    }
    window.sampleNews = firebaseArticles;
    localStorage.setItem('times07_news', JSON.stringify(window.sampleNews));
    
    renderNews();
    renderABPHeroBanner(window.sampleNews);
    populateArticlePage();
});
// Auto-populate unknown categories inside 'अन्य' Dropdown Menu
function updateDynamicCategories(articles) {
    const defaultCats = ['मुख्य समाचार', 'राजनीति', 'बिजनेस', 'खेल', 'टेक & AI', 'मनोरंजन', 'राज्य', 'लाइफस्टाइल'];
    const dropdown = document.querySelector('.dropdown-content');
    if (!dropdown) return;

    const existingCustomCats = new Set();
    articles.forEach(item => {
        if (item.category && !defaultCats.includes(item.category)) {
            existingCustomCats.add(item.category);
        }
    });

    existingCustomCats.forEach(catName => {
        const catId = `dyn-cat-${catName}`;
        if (!document.getElementById(catId)) {
            const newLink = document.createElement('a');
            newLink.id = catId;
            newLink.href = "javascript:void(0)";
            newLink.onclick = () => window.filterCategory(catName);
            newLink.innerText = catName;
            dropdown.appendChild(newLink);
        }
    });
}
// Category-wise Render Engine (6 Articles per Section)
function renderNews(filterCat = null) {
    const allArticles = window.sampleNews || [];

    // Helper Function to Create News Card
    const createCard = (news, index) => {
        const card = document.createElement('article');
        card.className = 'news-card';
        card.innerHTML = `
            <div class="card-img">
                <a href="article.html?id=${index}">
                    <img src="${news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800'}" loading="lazy">
                </a>
            </div>
            <div class="card-content">
                <a href="article.html?id=${index}" style="text-decoration:none;">
                    <h3>${news.title}</h3>
                </a>
            </div>
        `;
        return card;
    };

    // Helper to Fill Grid Containers
    const populateGrid = (gridId, items) => {
        const grid = document.getElementById(gridId);
        if (grid) {
            grid.innerHTML = "";
            items.forEach((item) => {
                grid.appendChild(createCard(item.data, item.index));
            });
        }
    };

    // Attach Original Index for URLs
    const indexedNews = allArticles.map((data, index) => ({ data, index }));

    // 1. Latest Top 6
    populateGrid('latest-news-grid', indexedNews.slice(0, 6));

    // 2. International (6)
    const intlItems = indexedNews.filter(x => 
        (x.data.category || '').toLowerCase().includes('international') || 
        (x.data.category || '').includes('विदेश') || 
        (x.data.title || '').includes('विदेश')
    ).slice(0, 6);
    populateGrid('intl-news-grid', intlItems.length ? intlItems : indexedNews.slice(0, 6));

    // 3. Entertainment (6)
    const entItems = indexedNews.filter(x => 
        (x.data.category || '').includes('मनोरंजन') || 
        (x.data.category || '').includes('बॉलीवुड')
    ).slice(0, 6);
    populateGrid('entertainment-news-grid', entItems.length ? entItems : indexedNews.slice(0, 6));

    // 4. Sports (6)
    const sportsItems = indexedNews.filter(x => 
        (x.data.category || '').includes('खेल') || 
        (x.data.category || '').toLowerCase().includes('sports')
    ).slice(0, 6);
    populateGrid('sports-news-grid', sportsItems.length ? sportsItems : indexedNews.slice(0, 6));

    // 5. Tech & Business (6)
    const techItems = indexedNews.filter(x => 
        (x.data.category || '').includes('टेक') || 
        (x.data.category || '').includes('बिजनेस')
    ).slice(0, 6);
    populateGrid('tech-news-grid', techItems.length ? techItems : indexedNews.slice(0, 6));
}
window.filterCategory = function(categoryName) {
    // Redirect directly to the dedicated Category Page
    window.location.href = `category.html?cat=${encodeURIComponent(categoryName)}`;
};

// Original Hero Slider Engine
function startAutoSlider() { stopAutoSlider(); autoSlideInterval = setInterval(() => { nextSlide(); }, 4500); }
function stopAutoSlider() { if (autoSlideInterval) clearInterval(autoSlideInterval); }
function updateHeroSlider() {
    if (featuredArticles.length === 0) return;
    const current = featuredArticles[currentSlideIndex];
    const heroBox = document.getElementById('hero-slider-box');
    if (heroBox && current) {
        heroBox.style.backgroundImage = `url('${current.data.img1 || current.data.image}')`;
        if (document.getElementById('slide-cat')) document.getElementById('slide-cat').innerText = current.data.category || "ABP एक्सक्लूसिव";
        if (document.getElementById('slide-title')) document.getElementById('slide-title').innerText = current.data.title;
        const slideLink = document.getElementById('slide-link');
        if (slideLink) slideLink.href = `article.html?id=${current.originalIndex}`;
    }
}
function nextSlide() { if (featuredArticles.length > 0) { currentSlideIndex = (currentSlideIndex + 1) % featuredArticles.length; updateHeroSlider(); } }

// Widgets Engine
function renderMostReadWidget() {
    const box = document.getElementById('most-read-box');
    if (!box) return;
    box.innerHTML = "";
    [...(window.sampleNews || [])].sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 5).forEach((news, idx) => {
        const item = document.createElement('div');
        item.style.cssText = "border-bottom:1px solid var(--border-color); padding-bottom:8px; margin-bottom:8px;";
        item.innerHTML = `<a href="article.html?id=${idx}" style="font-size:13px; font-weight:700; color:var(--heading-color); text-decoration:none;">• ${(news.title || '').substring(0, 50)}...</a>`;
        box.appendChild(item);
    });
}

function renderEditorsChoice() {
    const box = document.getElementById('editors-choice-box');
    if (!box) return;
    box.innerHTML = "";
    (window.sampleNews || []).slice(0, 3).forEach((news, idx) => {
        const item = document.createElement('div');
        item.className = 'news-card';
        item.innerHTML = `
            <div class="card-img" style="height:120px;">
                <img src="${news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800'}">
            </div>
            <div class="card-content" style="padding:10px;">
                <h4 style="font-size:13px; font-weight:700; line-height:1.3;">${(news.title || '').substring(0, 45)}...</h4>
                <a href="article.html?id=${idx}" style="font-size:11px; color:var(--abp-red); font-weight:800; text-decoration:none; margin-top:6px; display:inline-block;">विशेष कवरेज &rarr;</a>
            </div>
        `;
        box.appendChild(item);
    });
}

// Live Weather & Clock
function fetchAccurateWeather() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const lat = position.coords.latitude;
            const lon = position.coords.longitude;
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
                const data = await res.json();
                if (data && data.current_weather) {
                    const temp = Math.round(data.current_weather.temperature);
                    const geoRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                    const geoData = await geoRes.json();
                    const city = geoData.address.suburb || geoData.address.city || geoData.address.town || "Prayagraj";
                    if(document.getElementById('user-location-city')) document.getElementById('user-location-city').innerText = city;
                    if(document.getElementById('top-weather-temp')) document.getElementById('top-weather-temp').innerText = `${temp}°C Sunny`;
                }
            } catch (e) { console.log("Weather error", e); }
        });
    }
}
fetchAccurateWeather();

function updateLiveClock() {
    const now = new Date();
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    const clockElem = document.getElementById('live-clock');
    if(clockElem) clockElem.innerText = now.toLocaleString('en-US', options) + " IST";
}
setInterval(updateLiveClock, 1000);
updateLiveClock();

// Google Translate Engine
(function() {
    if (!document.getElementById('google-translate-script')) {
        var gtScript = document.createElement('script');
        gtScript.id = 'google-translate-script';
        gtScript.type = 'text/javascript';
        gtScript.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
        document.body.appendChild(gtScript);
    }
})();

window.googleTranslateElementInit = function() {
    new google.translate.TranslateElement({ pageLanguage: 'hi', includedLanguages: 'hi,en,mr,bn,pa,gu,ta,te', autoDisplay: false }, 'google_translate_element');
};

window.translatePage = function(langCode, element) {
    document.querySelectorAll('.lang-switcher a').forEach(a => a.classList.remove('active'));
    if (element) element.classList.add('active');
    var select = document.querySelector('.goog-te-combo');
    if (select) { select.value = langCode; select.dispatchEvent(new Event('change')); }
    setTimeout(() => { if (select) { select.value = langCode; select.dispatchEvent(new Event('change')); } }, 400);
};

// Modals & Navigation
window.showHome = function() {
    if(document.getElementById('main-content')) document.getElementById('main-content').classList.remove('hidden');
    if(document.getElementById('admin-panel')) document.getElementById('admin-panel').classList.add('hidden');
    window.scrollTo(0, 0);
};

window.openAuthModal = function() { const modal = document.getElementById('auth-modal'); if(modal) modal.style.display = 'flex'; };
window.closeAuthModal = function() { const modal = document.getElementById('auth-modal'); if(modal) modal.style.display = 'none'; };

// ==========================================================================
// DYNAMIC ARTICLE PAGE & AUTOMATIC RELATED / TRENDING SUGGESTIONS ENGINE
// ==========================================================================

function populateArticlePage() {
    const urlParams = new URLSearchParams(window.location.search);
    const newsIndex = parseInt(urlParams.get('id'), 10);
    const savedNews = JSON.parse(localStorage.getItem('times07_news')) || window.sampleNews || [];

    if (!isNaN(newsIndex) && savedNews[newsIndex]) {
        const news = savedNews[newsIndex];
        
        // Article Header & Image Updates
        if(document.getElementById('page-title')) document.getElementById('page-title').innerText = news.title;
        if(document.getElementById('page-cat')) document.getElementById('page-cat').innerText = news.category || "मुख्य समाचार";
        if(document.getElementById('page-img')) document.getElementById('page-img').src = news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200';
        
        // Full Article Content Rendering with HTML Line Breaks
        let rawContent = news.content || news.summary || news.desc || news.description || "खबर की विस्तृत जानकारी के लिए टाइम्स07 पर बने रहें।";
        if (rawContent) {
            rawContent = rawContent.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        }
        if(document.getElementById('page-content')) document.getElementById('page-content').innerHTML = rawContent;
        if(document.getElementById('views-count')) document.getElementById('views-count').innerText = news.views || 1840;

        // 🚀 Article ke niche Related, Trending aur Top News automatically render karna
        renderArticleSuggestions(newsIndex, news.category, savedNews);
    }
}

function renderArticleSuggestions(currentIndex, currentCategory, allNews) {
    // Check if container exists, if not create one dynamically below #page-content
    let suggestionContainer = document.getElementById('article-suggestions-container');
    
    if (!suggestionContainer) {
        const pageContent = document.getElementById('page-content');
        if (pageContent && pageContent.parentElement) {
            suggestionContainer = document.createElement('div');
            suggestionContainer.id = 'article-suggestions-container';
            suggestionContainer.style.cssText = "margin-top: 40px; border-top: 2px solid var(--border-color, #ddd); padding-top: 25px;";
            pageContent.parentElement.appendChild(suggestionContainer);
        } else {
            return;
        }
    }

    suggestionContainer.innerHTML = '';

    // 1. Related News (Same Category, current article ko chhod kar)
    let relatedNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex && (item.category || '').toLowerCase() === (currentCategory || '').toLowerCase());

    // Agar same category ki zyada news na mile, toh fallback list
    if (relatedNews.length === 0) {
        relatedNews = allNews
            .map((item, idx) => ({ ...item, originalIndex: idx }))
            .filter(item => item.originalIndex !== currentIndex)
            .slice(0, 4);
    }

    // 2. Trending / Breaking News (Highest Views / Featured)
    const trendingNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex)
        .sort((a, b) => (b.views || 0) - (a.views || 0))
        .slice(0, 4);

    // 3. Other Headlines (Recent Articles)
    const otherNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex)
        .slice(4, 8);

    // Cards Grid Design Generator
    const buildNewsGrid = (newsList) => {
        if (!newsList || newsList.length === 0) {
            return '<p style="color:#888; font-size:13px;">कोई अन्य खबर उपलब्ध नहीं है।</p>';
        }
        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-top: 15px; margin-bottom: 35px;">
                ${newsList.map(item => `
                    <div style="background: var(--bg-card, #fefefe); border: 1px solid var(--border-color, #eee); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.06); transition: transform 0.2s ease;">
                        <a href="article.html?id=${item.originalIndex}" style="text-decoration:none; color:inherit;">
                            <img src="${item.img1 || item.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=400'}" style="width:100%; height:120px; object-fit:cover;" loading="lazy">
                            <div style="padding: 10px;">
                                <span style="font-size:10px; background:#e74c3c; color:#fff; padding:2px 6px; border-radius:3px; font-weight:bold; text-transform:uppercase;">${item.category || 'समाचार'}</span>
                                <h4 style="font-size: 13px; font-weight: 700; margin-top: 6px; line-height: 1.4; color: var(--heading-color, #111); display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${item.title || ''}</h4>
                            </div>
                        </a>
                    </div>
                `).join('')}
            </div>
        `;
    };

    // Construct Suggestion HTML Sections
    const html = `
        <!-- Block 1: Related News -->
        <div>
            <h3 style="font-size: 18px; font-weight: 800; color: #d32f2f; border-bottom: 3px solid #d32f2f; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">
                📌 संबंधित खबरें (Related News)
            </h3>
            ${buildNewsGrid(relatedNews.slice(0, 4))}
        </div>

        <!-- Block 2: Trending & Breaking News -->
        <div>
            <h3 style="font-size: 18px; font-weight: 800; color: #2980b9; border-bottom: 3px solid #2980b9; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">
                🔥 ट्रेंडिंग और ब्रेकिंग न्यूज़ (Trending News)
            </h3>
            ${buildNewsGrid(trendingNews)}
        </div>

        <!-- Block 3: Other Top Headlines -->
        <div>
            <h3 style="font-size: 18px; font-weight: 800; color: #27ae60; border-bottom: 3px solid #27ae60; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">
                📰 अन्य प्रमुख समाचार (Other Headlines)
            </h3>
            ${buildNewsGrid(otherNews.length > 0 ? otherNews : allNews.slice(0, 4))}
        </div>
    `;

    suggestionContainer.innerHTML = html;
}

// ABP Dynamic Hero Banner (Side Bullets)
let abpSlideInterval = null;
let currentAbpIndex = 0;

function renderABPHeroBanner(newsList) {
    if (!newsList || newsList.length === 0) return;

    const mainImg = document.getElementById('abp-main-img');
    const mainTitle = document.getElementById('abp-main-title');
    const sideList = document.getElementById('abp-side-headlines');
    const topFive = newsList.slice(0, 5);

    if (sideList) {
        sideList.innerHTML = topFive.map((item, index) => `
            <li id="bullet-${index}" onclick="window.selectHeroSlide(${index})">${item.title}</li>
        `).join('');
    }

    window.selectHeroSlide = function(index) {
        currentAbpIndex = index;
        const selectedNews = topFive[index];

        if (mainImg) {
            mainImg.src = selectedNews.img1 || selectedNews.image || "https://images.unsplash.com/photo-1585829365295-ab7cd400c167?w=800";
            mainImg.onclick = () => window.location.href = `article.html?id=${index}`;
        }
        if (mainTitle) {
            mainTitle.innerText = selectedNews.title;
            mainTitle.onclick = () => window.location.href = `article.html?id=${index}`;
        }

        topFive.forEach((_, i) => {
            const el = document.getElementById(`bullet-${i}`);
            if (el) el.classList.remove('active-bullet');
        });
        const activeEl = document.getElementById(`bullet-${index}`);
        if (activeEl) activeEl.classList.add('active-bullet');
    };

    window.selectHeroSlide(0);

    if (abpSlideInterval) clearInterval(abpSlideInterval);
    abpSlideInterval = setInterval(() => {
        currentAbpIndex = (currentAbpIndex + 1) % topFive.length;
        window.selectHeroSlide(currentAbpIndex);
    }, 3500);
}

// ==========================================================================
// TIMES07 SEARCH ENGINE & AUTO-CATEGORIZATION BOT
// ==========================================================================

// 1. Auto-Categorization Bot (न्यूज़ को सही कैटेगरी में फ़िट करने के लिए)
window.categorizeNewsBot = function(article) {
    const title = (article.title || '').toLowerCase();
    const content = (article.content || article.summary || article.desc || '').toLowerCase();
    const text = title + " " + content;

    if (text.match(/stock|market|nifty|sensex|share|invest|dow|nasdaq|ipo/i)) {
        return 'Global Markets';
    } else if (text.match(/ev|car|bike|tesla|vehicle|auto|truck|engine/i)) {
        return 'Auto & EV Tech';
    } else if (text.match(/ai|tech|robot|software|google|ibm|nvidia|cyber|quantum/i)) {
        return 'Tech & AI';
    } else if (text.match(/crypto|bitcoin|btc|eth|blockchain/i)) {
        return 'Cryptocurrency';
    } else if (text.match(/world|us|uk|global|president|china|international/i)) {
        return 'World News';
    } else if (text.match(/economy|inflation|bank|fed|loan|finance/i)) {
        return 'Economy';
    }
    return article.category || 'World News'; // Default Niche
};

// 2. Master Search Engine Trigger (जब यूज़र सर्च आइकन दबाए)
// Aesthetic Search Bar Toggle
window.toggleSearchOverlay = function() {
    const overlay = document.getElementById('search-overlay');
    if (!overlay) return;
    
    if (overlay.style.display === 'none' || overlay.style.display === '') {
        overlay.style.display = 'block';
        const input = document.getElementById('aesthetic-search-input');
        if (input) input.focus();
    } else {
        overlay.style.display = 'none';
    }
};

window.triggerAISearch = function() {
    window.toggleSearchOverlay();
};

// Execute Search and Render Results
window.executeAestheticSearch = function() {
    const input = document.getElementById('aesthetic-search-input');
    if (!input) return;
    const query = input.value.trim().toLowerCase();
    if (!query) return;

    const allNews = window.sampleNews || JSON.parse(localStorage.getItem('times07_news')) || [];

    const searchResults = allNews.filter(article => {
        const title = (article.title || '').toLowerCase();
        const desc = (article.summary || article.desc || '').toLowerCase();
        const cat = (article.category || '').toLowerCase();
        return title.includes(query) || desc.includes(query) || cat.includes(query);
    });

    const centerFeed = document.getElementById('center-main-feed');
    const heroWrapper = document.querySelector('.hero-spanning-wrapper');
    if (heroWrapper) heroWrapper.style.display = 'none';

    if (centerFeed) {
        centerFeed.innerHTML = `
            <div style="margin-bottom: 25px; border-bottom: 3px solid #c00000; padding-bottom: 10px;">
                <p style="color: #94a3b8; font-size: 12px; margin: 0; font-weight: 700;">SEARCH RESULTS FOR</p>
                <h1 style="font-size: 24px; font-weight: 800; color: #111; margin: 4px 0 0; text-transform: uppercase;">
                    <i class="fa-solid fa-magnifying-glass" style="color: #c00000;"></i> "${query}" (${searchResults.length} Found)
                </h1>
            </div>
            
            <div class="hybrid-news-grid" id="search-results-grid"></div>
        `;

        const gridBox = document.getElementById('search-results-grid');
        if (searchResults.length === 0) {
            gridBox.innerHTML = `<p style="color:#666; font-size:14px; padding:20px;">No matching news found. Try searching for "Markets", "Tesla", "AI" or "Crypto".</p>`;
        } else {
            searchResults.forEach((news) => {
                const index = allNews.indexOf(news);
                const card = document.createElement('article');
                card.className = 'news-card';
                card.innerHTML = `
                    <div class="card-img">
                        <a href="article.html?id=${index}">
                            <img src="${news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800'}" loading="lazy">
                        </a>
                    </div>
                    <div class="card-content">
                        <a href="article.html?id=${index}" style="text-decoration:none;">
                            <span style="font-size:10px; background:#c00000; color:#fff; padding:2px 6px; border-radius:3px; font-weight:bold;">${news.category || 'GLOBAL'}</span>
                            <h3 style="margin-top:5px;">${news.title}</h3>
                        </a>
                    </div>
                `;
                gridBox.appendChild(card);
            });
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};