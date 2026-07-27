// ==========================================================================
// ABP TIMES07 ENTERPRISE MEDIA NETWORK - UNIFIED SCRIPT ENGINE
// Firebase Realtime DB, Live Weather API, Market Tickers & Category Router
// ==========================================================================

// 1. Firebase SDK Module Imports
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, onValue } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

// Verified Firebase Project Configuration
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

// Initialize Firebase & Realtime Database Reference
const app = initializeApp(firebaseConfig);
const db = getDatabase(app);
const newsRef = ref(db, 'articles');

// Global Application State
window.sampleNews = [];
let currentSlideIndex = 0;
let featuredArticles = [];
let autoSlideInterval = null;

// 2. Theme Switcher (Dark Mode Engine)
window.toggleTheme = function() {
    document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-mode') || document.body.classList.contains('dark-theme');
    
    const themeIcons = document.querySelectorAll('#theme-icon, #theme-toggle');
    themeIcons.forEach(icon => {
        if(icon.tagName === 'I') {
            icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
        } else {
            icon.innerHTML = isDark ? '<i class="fa-solid fa-sun"></i>' : '<i class="fa-solid fa-moon"></i>';
        }
    });

    localStorage.setItem('times07_theme', isDark ? 'dark' : 'light');
};

function initTheme() {
    const savedTheme = localStorage.getItem('times07_theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        document.body.classList.add('dark-theme');
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) themeIcon.className = 'fa-solid fa-sun';
    }
}
initTheme();

// 3. Realtime Database Synchronization Listener
onValue(newsRef, (snapshot) => {
    const data = snapshot.val();
    let firebaseArticles = [];
    if (data) {
        Object.keys(data).forEach(key => {
            firebaseArticles.push({ id: key, ...data[key] });
        });
    }
    // Firebase और AutoNews दोनों को सुरक्षित मिलाकर जोड़ना
    window.sampleNews = [...firebaseArticles, ...(window.sampleNews || [])];
    renderNews();
    localStorage.setItem('times07_news', JSON.stringify(window.sampleNews));
    populateArticlePage();
});

// 4. UI Rendering Engine
function renderNews(filterCat = null) {
    const newsContainer = document.getElementById('news-container');
    if (newsContainer) newsContainer.innerHTML = "";

    featuredArticles = [];

    let filteredList = window.sampleNews || [];
    if (filterCat) {
        filteredList = filteredList.filter(item => (item.category || '').includes(filterCat) || (item.title || '').includes(filterCat));
    }

    filteredList.forEach((news, index) => {
        if (news.featured === 'yes') {
            featuredArticles.push({ data: news, originalIndex: index });
        }

        if (newsContainer) {
            const card = document.createElement('article');
            card.className = 'news-card';
            card.innerHTML = `
                <div class="card-img">
                    <a href="article.html?id=${index}">
                        <img src="${news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800'}" loading="lazy">
                    </a>
                    <span class="cat-badge">${news.category || 'मुख्य समाचार'}</span>
                </div>
                <div class="card-content">
                    <a href="article.html?id=${index}" style="text-decoration:none;">
                        <h3>${news.title}</h3>
                    </a>
                    <p class="news-excerpt" style="font-size:12px; color:var(--muted-text); margin-top:4px;">${(news.desc || news.description || '').replace(/<[^>]*>?/gm, '').substring(0, 70)}...</p>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <span style="font-size:11px; color:var(--muted-text);"><i class="fa-solid fa-eye" style="color:var(--abp-red);"></i> ${news.views || 1200} व्यूज</span>
                    </div>
                </div>
            `;
            newsContainer.appendChild(card);
        }
    });

    updateHeroSlider();
    startAutoSlider();
    renderEditorsChoice();
    renderMostReadWidget();
}

// Category Filter Router
window.filterCategory = function(categoryName) {
    showHome();
    renderNews(categoryName);
};

// 5. Hero Slider Engine
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
        const imgLink = document.getElementById('hero-img-link');
        const titleLink = document.getElementById('hero-title-link');

        if (imgLink) imgLink.href = `article.html?id=${currentSlideIndex}`;
        if (titleLink) titleLink.href = `article.html?id=${currentSlideIndex}`;
    }
}
function nextSlide() { if (featuredArticles.length > 0) { currentSlideIndex = (currentSlideIndex + 1) % featuredArticles.length; updateHeroSlider(); } }

// 6. Widgets Engine (Most Read & Editor's Choice)
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

// 7. Live Weather Engine
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
            } catch (e) {
                console.log("Weather error", e);
            }
        });
    }
}
fetchAccurateWeather();

// 8. Live Clock Engine
function updateLiveClock() {
    const now = new Date();
    const options = { 
        weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', 
        hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true 
    };
    const clockElem = document.getElementById('live-clock');
    if(clockElem) {
        clockElem.innerText = now.toLocaleString('en-US', options) + " IST";
    }
}
setInterval(updateLiveClock, 1000);
updateLiveClock();

// 9. Google Translate Engine Fix
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
    new google.translate.TranslateElement({
        pageLanguage: 'hi',
        includedLanguages: 'hi,en,mr,bn,pa,gu,ta,te',
        autoDisplay: false
    }, 'google_translate_element');
};

function applyLanguage(langCode) {
    var select = document.querySelector('.goog-te-combo');
    if (select) {
        select.value = langCode;
        select.dispatchEvent(new Event('change'));
    }
}

window.translatePage = function(langCode, element) {
    document.querySelectorAll('.lang-switcher a').forEach(a => a.classList.remove('active'));
    if (element) {
        element.classList.add('active');
    }
    localStorage.setItem('selectedLang', langCode);
    applyLanguage(langCode);
    setTimeout(function() {
        applyLanguage(langCode);
    }, 400);
};

// 10. Navigation & Auth Controls
function showHome() {
    if(document.getElementById('main-content')) document.getElementById('main-content').classList.remove('hidden');
    if(document.getElementById('admin-panel')) document.getElementById('admin-panel').classList.add('hidden');
    window.scrollTo(0, 0);
}
window.showHome = showHome;

window.openAuthModal = function() {
    const modal = document.getElementById('auth-modal');
    if(modal) modal.style.display = 'flex';
};

window.closeAuthModal = function() {
    const modal = document.getElementById('auth-modal');
    if(modal) modal.style.display = 'none';
};

window.triggerAISearch = function() {
    const query = prompt("Times07 Pro AI - आप क्या खोजना चाहते हैं?");
    if (query) {
        renderNews(query);
    }
};

// 11. Article Page Population
function populateArticlePage() {
    const urlParams = new URLSearchParams(window.location.search);
    const newsIndex = urlParams.get('id');
    const savedNews = JSON.parse(localStorage.getItem('times07_news')) || window.sampleNews;

    if (newsIndex !== null && savedNews[newsIndex]) {
        const news = savedNews[newsIndex];
        if(document.getElementById('page-title')) document.getElementById('page-title').innerText = news.title;
        if(document.getElementById('page-cat')) document.getElementById('page-cat').innerText = news.category || "मुख्य समाचार";
        if(document.getElementById('page-img')) document.getElementById('page-img').src = news.img1 || news.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=1200';
        if(document.getElementById('page-content')) document.getElementById('page-content').innerHTML = news.desc || news.description || "खबर की विस्तृत जानकारी यहाँ उपलब्ध है।";
        if(document.getElementById('views-count')) document.getElementById('views-count').innerText = news.views || 1840;
    }
}

// 12. AUTOMATIC NEWS PUBLISHING ENGINE
async function fetchAutoNews() {
    try {
        const response = await fetch('news.json?v=' + new Date().getTime());
        if (!response.ok) return;
        
        const autoFetchedNews = await response.json();
        
        if (autoFetchedNews && autoFetchedNews.length > 0) {
            const formattedNews = autoFetchedNews.map(item => ({
                title: item.title,
                desc: item.desc || item.description,
                img1: item.img1 || item.image || 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800',
                category: item.category || 'ब्रेकिंग न्यूज़',
                views: item.views || 1500,
                date: item.date || 'अभी-अभी'
            }));

            // AutoFetchedNews को प्राथमिकता देकर आगे जोड़ना
            window.sampleNews = [...formattedNews, ...(window.sampleNews || [])];
            renderNews();
        }
    } catch (error) {
        console.log("Feed Fetch Error:", error);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    fetchAutoNews();
    setInterval(fetchAutoNews, 600000);
});