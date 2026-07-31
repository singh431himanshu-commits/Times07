// ==========================================================================
// ABP TIMES07 ENTERPRISE MEDIA NETWORK - UNIFIED SCRIPT ENGINE
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

window.sampleNews = [];

// Firebase Data Sync
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
    
    // 🚀 तीनों जगह का डेटा एक साथ अपडेट होगा
    renderNews();
    renderABPHeroBanner(window.sampleNews);
    renderRightSidebar(window.sampleNews); 
});

// ==========================================================
// 1. MAIN FEED ENGINE (ताज़ा ख़बरें, टेक, खेल आदि)
// ==========================================================
function renderNews() {
    const allArticles = window.sampleNews || [];
    const indexedNews = allArticles.map((data, index) => ({ data, index }));

    const createCard = (news, index) => {
        const card = document.createElement('article');
        card.className = 'news-card';
        card.innerHTML = `
            <div class="card-img">
                <a href="article.html?id=${index}"><img src="${news.img1 || news.image || 'logo.png'}" loading="lazy"></a>
            </div>
            <div class="card-content">
                <a href="article.html?id=${index}" style="text-decoration:none;"><h3>${news.title}</h3></a>
            </div>
        `;
        return card;
    };

    const populateGrid = (gridId, items) => {
        const grid = document.getElementById(gridId);
        if (grid) {
            grid.innerHTML = "";
            items.forEach((item) => grid.appendChild(createCard(item.data, item.index)));
        }
    };

    // 🔴 STRICT: Sidebar और Hero Banner वाली खबरों को मेन फ़ीड से पूरी तरह बाहर निकाल दें
    const mainFeedNews = indexedNews.filter(x => x.data.placement !== 'sidebar-sticky' && x.data.placement !== 'hero-main');

    // 🟢 ग्रिड प्लेसमेंट
    const latestItems = mainFeedNews.filter(x => x.data.placement === 'latest-news-grid' || !x.data.placement);
    const intlItems = mainFeedNews.filter(x => x.data.placement === 'intl-news-grid' || (x.data.category || '').toLowerCase().includes('world'));
    const entItems = mainFeedNews.filter(x => x.data.placement === 'entertainment-news-grid' || (x.data.category || '').includes('मनोरंजन'));
    const sportsItems = mainFeedNews.filter(x => x.data.placement === 'sports-news-grid' || (x.data.category || '').includes('खेल'));
    const techItems = mainFeedNews.filter(x => x.data.placement === 'tech-news-grid' || (x.data.category || '').includes('टेक'));

    populateGrid('latest-news-grid', latestItems.slice(0, 6));
    populateGrid('intl-news-grid', intlItems.slice(0, 6));
    populateGrid('entertainment-news-grid', entItems.slice(0, 6));
    populateGrid('sports-news-grid', sportsItems.slice(0, 6));
    populateGrid('tech-news-grid', techItems.slice(0, 6));
}

// ==========================================================
// 2. RIGHT STICKY SIDEBAR ENGINE (नया फिक्स)
// ==========================================================
let sidebarInterval = null;
let currentSidebarIndex = 0;

function renderRightSidebar(allNews) {
    const container = document.getElementById('dynamic-right-news-container');
    if (!container) return;

    // 🔴 सिर्फ 'sidebar-sticky' वाली खबरें छाँटें
    const sidebarNews = allNews
        .map((data, index) => ({ data, index }))
        .filter(x => x.data.placement === 'sidebar-sticky');

    if (sidebarNews.length === 0) {
        container.innerHTML = `<p style="padding:15px; font-size:13px; color:#888; text-align:center;">लाइव अपडेट्स लोड हो रहे हैं...</p>`;
        return;
    }

    function updateSidebar() {
        let html = '';
        let displayCount = Math.min(6, sidebarNews.length);
        
        for(let i = 0; i < displayCount; i++) {
            const item = sidebarNews[(currentSidebarIndex + i) % sidebarNews.length];
            html += `
                <div class="blinking-news-card" style="display: flex; gap: 10px; padding: 10px 0; border-bottom: 1px dashed #e2e8f0; align-items: center; animation: fadeAndPop 0.8s ease-in-out;">
                    <img src="${item.data.img1 || 'logo.png'}" onerror="this.src='logo.png'" style="width: 70px; height: 50px; object-fit: cover; border-radius: 4px; flex-shrink: 0;">
                    <a href="article.html?id=${item.index}" style="text-decoration:none; color:inherit;">
                        <h4 style="font-size: 12px; font-weight: 600; color: #1e293b; margin: 0; line-height: 1.3;">${item.data.title}</h4>
                    </a>
                </div>
            `;
        }
        container.innerHTML = html;

        if (sidebarNews.length > 6) {
            currentSidebarIndex = (currentSidebarIndex + 2) % sidebarNews.length;
        }
    }

    updateSidebar();
    if (sidebarInterval) clearInterval(sidebarInterval);
    if (sidebarNews.length > 6) {
        sidebarInterval = setInterval(updateSidebar, 5000);
    }
}

// ==========================================================
// 3. RED BOX (HERO BANNER) ENGINE
// ==========================================================
let abpSlideInterval = null;
let currentAbpIndex = 0;

function renderABPHeroBanner(newsList) {
    if (!newsList || newsList.length === 0) return;
    let indexedNews = newsList.map((data, index) => ({ data, index }));

    // सिर्फ "hero-main" वाली खबरें
    let heroArticles = indexedNews.filter(x => x.data.placement === 'hero-main');
    
    // अगर 5 से कम हैं, तो बाकियों से भरें (लेकिन Sidebar वाली कभी नहीं!)
    if (heroArticles.length < 5) {
        const otherNews = indexedNews.filter(x => x.data.placement !== 'sidebar-sticky' && x.data.placement !== 'hero-main');
        heroArticles = [...heroArticles, ...otherNews];
    }
    const topFive = heroArticles.slice(0, 5);
    if (topFive.length === 0) return;

    const mainImg = document.getElementById('abp-main-img'), mainTitle = document.getElementById('abp-main-title'), sideList = document.getElementById('abp-side-headlines');
    if (sideList) sideList.innerHTML = topFive.map((item, idx) => `<li id="bullet-${idx}" onclick="window.selectHeroSlide(${idx})">${item.data.title}</li>`).join('');

    window.selectHeroSlide = function(idx) {
        currentAbpIndex = idx; const selected = topFive[idx];
        if (mainImg) { mainImg.src = selected.data.img1 || 'logo.png'; mainImg.onclick = () => window.location.href = `article.html?id=${selected.index}`; }
        if (mainTitle) { mainTitle.innerText = selected.data.title; mainTitle.onclick = () => window.location.href = `article.html?id=${selected.index}`; }
        topFive.forEach((_, i) => { const el = document.getElementById(`bullet-${i}`); if(el) el.classList.remove('active-bullet'); });
        const activeEl = document.getElementById(`bullet-${idx}`); if(activeEl) activeEl.classList.add('active-bullet');
    };
    window.selectHeroSlide(0);
    if (abpSlideInterval) clearInterval(abpSlideInterval);
    abpSlideInterval = setInterval(() => { currentAbpIndex = (currentAbpIndex + 1) % topFive.length; window.selectHeroSlide(currentAbpIndex); }, 3500);
}

// ==========================================================
// OTHER APP FUNCTIONS (Theme, Clock, Article Page, Search)
// ==========================================================
window.filterCategory = function(categoryName) { window.location.href = `category.html?cat=${encodeURIComponent(categoryName)}`; };
window.showHome = function() { window.scrollTo(0, 0); };

// Live Weather
function fetchAccurateWeather() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const lat = position.coords.latitude, lon = position.coords.longitude;
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
                const data = await res.json();
                if (data && data.current_weather) {
                    const temp = Math.round(data.current_weather.temperature);
                    if(document.getElementById('top-weather-temp')) document.getElementById('top-weather-temp').innerText = `${temp}°C Sunny`;
                }
            } catch (e) {}
        });
    }
}
fetchAccurateWeather();

// Live Clock
function updateLiveClock() {
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    if(document.getElementById('live-clock')) document.getElementById('live-clock').innerText = new Date().toLocaleString('en-US', options) + " IST";
}
setInterval(updateLiveClock, 1000); updateLiveClock();

// Article Page Population
window.populateArticlePage = function() {
    const urlParams = new URLSearchParams(window.location.search);
    const newsIndex = parseInt(urlParams.get('id'), 10);
    const savedNews = JSON.parse(localStorage.getItem('times07_news')) || window.sampleNews || [];

    if (!isNaN(newsIndex) && savedNews[newsIndex]) {
        const news = savedNews[newsIndex];
        if(document.getElementById('page-title')) document.getElementById('page-title').innerText = news.title;
        if(document.getElementById('page-cat')) document.getElementById('page-cat').innerText = news.category || "न्यूज़";
        if(document.getElementById('page-img')) document.getElementById('page-img').src = news.img1 || 'logo.png';
        let rawContent = news.content || news.desc || "";
        if(document.getElementById('page-content')) document.getElementById('page-content').innerHTML = rawContent.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
    }
};

// Search Engine
window.toggleSearchOverlay = function() {
    const overlay = document.getElementById('search-overlay');
    if (!overlay) return;
    overlay.style.display = overlay.style.display === 'none' || overlay.style.display === '' ? 'block' : 'none';
    if(overlay.style.display === 'block') document.getElementById('aesthetic-search-input').focus();
};
window.triggerAISearch = function() { window.toggleSearchOverlay(); };
window.executeAestheticSearch = function() {
    const query = (document.getElementById('aesthetic-search-input').value || '').trim().toLowerCase();
    if (!query) return;
    const searchResults = (window.sampleNews || []).filter(a => (a.title||'').toLowerCase().includes(query) || (a.desc||'').toLowerCase().includes(query));
    const centerFeed = document.getElementById('center-main-feed');
    if(document.querySelector('.hero-spanning-wrapper')) document.querySelector('.hero-spanning-wrapper').style.display = 'none';
    if (centerFeed) {
        centerFeed.innerHTML = `
            <div style="margin-bottom:25px; border-bottom:3px solid #c00000; padding-bottom:10px;">
                <h1 style="font-size:24px; font-weight:800; color:#111;"><i class="fa-solid fa-magnifying-glass" style="color:#c00000;"></i> "${query}" (${searchResults.length} Found)</h1>
            </div>
            <div class="hybrid-news-grid" id="search-results-grid"></div>
        `;
        const gridBox = document.getElementById('search-results-grid');
        if (searchResults.length === 0) gridBox.innerHTML = `<p style="padding:20px;">No results found.</p>`;
        else searchResults.forEach(news => {
            const index = window.sampleNews.indexOf(news);
            gridBox.innerHTML += `<article class="news-card"><div class="card-img"><a href="article.html?id=${index}"><img src="${news.img1||'logo.png'}"></a></div><div class="card-content"><a href="article.html?id=${index}" style="text-decoration:none;"><h3 style="margin-top:5px;">${news.title}</h3></a></div></article>`;
        });
        window.scrollTo(0,0);
    }
};