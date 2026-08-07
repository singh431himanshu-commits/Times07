// ==========================================================================
// ABP TIMES07 ENTERPRISE MEDIA NETWORK - UNIFIED SCRIPT ENGINE
// Firebase Realtime DB, Live Weather API, Market Tickers & Category Router
// ==========================================================================

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js";
import { getDatabase, ref, get, query, limitToLast } from "https://www.gstatic.com/firebasejs/10.7.1/firebase-database.js";

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

window.sampleNews = JSON.parse(localStorage.getItem('times07_news')) || [];
let currentSlideIndex = 0;
let featuredArticles = [];
let autoSlideInterval = null;

window.toggleTheme = function() {
    document.body.classList.toggle('dark-mode');
    document.body.classList.toggle('dark-theme');
    const isDark = document.body.classList.contains('dark-mode');
    document.querySelectorAll('#theme-icon').forEach(icon => {
        icon.className = isDark ? 'fa-solid fa-sun' : 'fa-solid fa-moon';
    });
    localStorage.setItem('times07_theme', isDark ? 'dark' : 'light');
};

function initTheme() {
    if (localStorage.getItem('times07_theme') === 'dark') {
        document.body.classList.add('dark-mode', 'dark-theme');
        const themeIcon = document.getElementById('theme-icon');
        if (themeIcon) themeIcon.className = 'fa-solid fa-sun';
    }
}
initTheme();

// 🚀 FIREBASE LISTENER (FIXED: window.sampleNews Update)
const newsQuery = query(newsRef, limitToLast(100));

get(newsQuery).then((snapshot) => {
    const data = snapshot.val();
    let firebaseArticles = [];
    if (data) {
        Object.keys(data).forEach(key => {
            const article = data[key];
            // इमेज के सभी संभावित नाम चेक करके एक स्टैंडर्ड 'image' फ़ील्ड सेट करें
            const imgUrl = article.img1 || article.image || article.img || article.imageUrl || article.insta_watermarked_img || 'logo.png';
            firebaseArticles.push({ id: key, ...article, image: imgUrl, img1: imgUrl });
        });
        firebaseArticles.reverse(); // Latest First
    }

    // 🔴 सबसे मुख्य फिक्स: global sampleNews को फ़ायरबेस डेटा से अपडेट करें
    window.sampleNews = firebaseArticles;
  
    updateDynamicCategories(window.sampleNews);
    renderNews(); // मेन ग्रिड के लिए
    renderABPHeroBanner(window.sampleNews); // रेड बॉक्स के लिए
    renderRightSidebar(window.sampleNews); // राइट साइडबार के लिए
    renderMostReadWidget();
    
    const loader = document.getElementById("loader");
    if (loader) {
        loader.style.display = "none";
    }
    
    renderEditorsChoice();
    populateArticlePage(); // आर्टिकल पेज रेंडर
});

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

// ==========================================================
// 1. MAIN FEED ENGINE (STRICT PLACEMENT)
// ==========================================================
// 🔴 1. STRICT CATEGORY ROUTER (NO MIXING FALLBACKS)
function renderNews() {
    const allArticles = window.sampleNews || [];
    const indexedNews = allArticles.map((data, index) => ({ data, index }));

    // Hero aur Sidebar wali dedicated news ko main feed se alag karein
    const mainFeedNews = indexedNews.filter(x => x.data.placement !== 'sidebar-sticky' && x.data.placement !== 'hero-main');

    const latestItems = mainFeedNews.filter(x => x.data.placement === 'latest-news-grid' || x.data.placement === 'latest-news' || !x.data.placement);
    const intlItems = mainFeedNews.filter(x => x.data.placement === 'intl-news-grid' || (x.data.category || '').toLowerCase().includes('world') || (x.data.category || '').includes('विदेश'));
    const entItems = mainFeedNews.filter(x => x.data.placement === 'entertainment-news-grid' || (x.data.category || '').includes('मनोरंजन') || (x.data.category || '').includes('बॉलीवुड'));
    const sportsItems = mainFeedNews.filter(x => x.data.placement === 'sports-news-grid' || (x.data.category || '').includes('खेल') || (x.data.category || '').toLowerCase().includes('sports'));
    const techItems = mainFeedNews.filter(x => x.data.placement === 'tech-news-grid' || (x.data.category || '').includes('टेक') || (x.data.category || '').includes('बिजनेस'));

    // Fallbacks hata diye gaye hain — jis category ki news hai sirf wahin dikhegi
    populateGrid('latest-news-grid', latestItems.slice(0, 13), 'मुख्य समाचार');
    populateGrid('intl-news-grid', intlItems.slice(0, 13), 'विदेश');
    populateGrid('entertainment-news-grid', entItems.slice(0, 13), 'मनोरंजन');
    populateGrid('sports-news-grid', sportsItems.slice(0, 13), 'खेल');
    populateGrid('tech-news-grid', techItems.slice(0, 13), 'टेक & AI');
}
// 🔴 CATEGORY FILTER DIRECT ON HOMEPAGE (NO CATEGORY.HTML REDIRECT)
window.filterCategory = function(categoryName) {
    const allArticles = window.sampleNews || [];
    const filteredArticles = allArticles.filter(a => 
        (a.category || '').toLowerCase().includes(categoryName.toLowerCase()) || 
        (a.title || '').toLowerCase().includes(categoryName.toLowerCase())
    );

    const centerFeed = document.getElementById('center-main-feed');
    if (centerFeed) {
        // Filter hone par hero banner hide ho jayega
        const heroWrapper = document.querySelector('.hero-spanning-wrapper');
        if (heroWrapper) heroWrapper.style.display = 'none';

        centerFeed.innerHTML = `
            <div style="margin-bottom:20px; border-bottom:3px solid #c00000; padding-bottom:8px;">
                <h2 style="font-size:22px; font-weight:800; color:#111;">
                    <i class="fa-solid fa-layer-group" style="color:#c00000;"></i> ${categoryName} (${filteredArticles.length})
                </h2>
            </div>
            <div id="category-results-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;"></div>
        `;

        const gridBox = document.getElementById('category-results-grid');
        if (filteredArticles.length === 0) {
            gridBox.innerHTML = `<p style="padding:20px; color:#666;">इस कैटेगरी में अभी कोई खबर उपलब्ध नहीं है।</p>`;
        } else {
            filteredArticles.forEach(news => {
                gridBox.innerHTML += `
                    <div style="border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
                        <a href="article.html?slug=${news.slug || createSlug(news.title)}" style="text-decoration:none; display:flex; gap:10px; width:100%;">
                            <img src="${news.img1 || news.image || 'logo.png'}" style="width:100px; height:75px; object-fit:cover; border-radius:4px; flex-shrink:0;">
                            <div style="flex-grow:1;">
                                <div style="color: #c00000; font-size: 11px; font-weight: 800; margin-bottom: 4px;">${news.category || categoryName}</div>
                                <h4 style="font-size: 14px; font-weight: 700; line-height: 1.3; margin: 0; color: #111; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${news.title}</h4>
                            </div>
                        </a>
                    </div>
                `;
            });
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        window.location.href = `index.html`;
    }
};
const populateGrid = (gridId, items, categoryName) => {
    const grid = document.getElementById(gridId);
    if (!grid || items.length === 0) return;
    
    const validItems = items.filter(item => item && item.data && item.data.title);
    if (validItems.length === 0) return;

    grid.className = "";
    grid.style.display = "block";
    
    // 1. मुख्य बड़ी खबर (Left Image + Right Title Layout)
    let html = `
    <div style="margin-bottom: 20px; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; overflow:hidden;">
        <a href="article.html?slug=${validItems[0].data.slug || createSlug(validItems[0].data.title)}" style="text-decoration:none; display: flex; align-items: center; gap: 15px;">
            <!-- Left Image (Aadha Space) -->
            <div style="width: 45%; height: 180px; flex-shrink: 0; overflow: hidden;">
                <img src="${validItems[0].data.img1 || validItems[0].data.image || 'logo.png'}" style="width:100%; height:100%; object-fit:cover; display:block;">
            </div>
            <!-- Right Title Content -->
            <div style="padding: 15px 15px 15px 0; flex-grow: 1;">
                <span style="color: #c00000; font-size: 11px; font-weight: 800; text-transform: uppercase; margin-bottom: 6px; display: inline-block;">
                    <i class="fa-solid fa-bolt"></i> ${validItems[0].data.category || categoryName || 'मुख्य समाचार'}
                </span>
                <h3 style="margin: 0; font-size: 18px; font-weight: 800; color: #111; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden;">
                    ${validItems[0].data.title}
                </h3>
            </div>
        </a>
    </div>`;

    // 2. 2-कॉलम ग्रिड (छोटे समाचार नीचे)
    html += `<div id="${gridId}-list" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">`;
    
    validItems.slice(1, 13).forEach((item, index) => {
        const isHidden = index >= 6 ? `style="display:none;" class="hidden-news"` : `style="display:flex; gap:10px;"`;
        
        html += `
        <div ${isHidden} style="border-bottom: 1px solid #e2e8f0; padding-bottom: 10px;">
            <a href="article.html?slug=${item.data.slug || createSlug(item.data.title)}" style="text-decoration:none; display:flex; gap:10px; width:100%;">
                <img src="${item.data.img1 || item.data.image || 'logo.png'}" style="width:100px; height:75px; object-fit:cover; border-radius:4px; flex-shrink:0;">
                <div style="flex-grow:1;">
                    <div style="color: #c00000; font-size: 11px; font-weight: 800; margin-bottom: 4px;">
                        <i class="fa-solid fa-bolt"></i> ${item.data.category || 'न्यूज़'}
                    </div>
                    <h4 style="font-size: 14px; font-weight: 700; line-height: 1.3; margin: 0; color: #111; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">${item.data.title}</h4>
                </div>
            </a>
        </div>`;
    });
    html += '</div>';
    
    // See More Button
    if (validItems.length > 7) {
        html += `
        <div style="text-align: left; margin-top: 12px; margin-bottom: 25px;">
            <button onclick="window.toggleMoreNews('${gridId}', this)" style="background: transparent; color: #c00000; border: none; font-weight: 800; font-size: 14px; cursor: pointer; padding: 0;">
                See More <i class="fa-solid fa-chevron-down"></i>
            </button>
        </div>`;
    }
    
    grid.innerHTML = html;
};

// ==========================================================
// See More बटन का एक्शन (ख़बरें वहीं नीचे खोलने के लिए)
// इसे populateGrid के ठीक नीचे पेस्ट कर देना
// ==========================================================
window.toggleMoreNews = function(gridId, btn) {
    const grid = document.getElementById(gridId + '-list');
    if(!grid) return;
    
    const hiddenItems = grid.querySelectorAll('.hidden-news');
    let isExpanded = false;
    
    hiddenItems.forEach(item => {
        if (item.style.display === 'none') {
            item.style.display = 'flex';
            item.style.gap = '10px';
            isExpanded = true;
        } else {
            item.style.display = 'none';
        }
    });
    
    // बटन का टेक्स्ट बदलना
    if (isExpanded) {
        btn.innerHTML = 'See Less <i class="fa-solid fa-chevron-up"></i>';
    } else {
        btn.innerHTML = 'See More <i class="fa-solid fa-chevron-down"></i>';
    }
};
// ==========================================================
// 2. RIGHT STICKY SIDEBAR ENGINE
// ==========================================================
let sidebarInterval = null;
let currentSidebarIndex = 0;

function renderRightSidebar(allNews) {
    const container = document.getElementById('dynamic-right-news-container');
    if (!container) return;

    // सिर्फ 'sidebar-sticky' वाली खबरें छाँटें
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
                    <img loading="lazy" src="${item.data.img1 || 'logo.png'}" onerror="this.src='logo.png'" style="width: 70px; height: 50px; object-fit: cover; border-radius: 4px; flex-shrink: 0;">
                    <a href="article.html?slug=${item.slug}" style="text-decoration:none; color:inherit;">
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



// 🔴 2. STRICT RED BOX ROUTER (NO DUPLICATION)
// ==========================================================
// 3. RED BOX (HERO BANNER) AUTO SLIDE ENGINE (FIXED)
// ==========================================================
let abpSlideInterval = null;
let currentAbpIndex = 0;

function renderABPHeroBanner(newsList) {
    if (!newsList || newsList.length === 0) return;

    let indexedNews = newsList.map((data, index) => ({ data, index }));

    let heroArticles = indexedNews.filter(x => x.data.placement === 'hero-main');
    if (heroArticles.length === 0) {
        heroArticles = indexedNews.slice(0, 5);
    }

    const topFive = heroArticles.slice(0, 5);
    if (topFive.length === 0) return;

    const mainImg = document.getElementById('abp-main-img');
    const mainTitle = document.getElementById('abp-main-title');
    const sideList = document.getElementById('abp-side-headlines');

    // 1. रिप्लेस स्केलेटन लिस्ट विथ रियल डेटा
    if (sideList) {
        sideList.innerHTML = topFive.map((item, index) => {
            const newsTitle = item.data?.title || item.title || "मुख्य समाचार";
            return `<li id="bullet-${index}" onclick="window.selectHeroSlide(${index})" style="color: #fff; font-size: 11px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.15); cursor: pointer;">${newsTitle}</li>`;
        }).join('');
    }

    // 2. स्लाइड बदलने का फ़ंक्शन
    window.selectHeroSlide = function(index) {
        currentAbpIndex = index;
        const selectedNews = topFive[index];
        if (!selectedNews) return;

        const newsTitle = selectedNews.data?.title || selectedNews.title || "";
        const newsImg = selectedNews.data?.img1 || selectedNews.data?.image || "logo.png";
        const newsSlug = selectedNews.data?.slug || createSlug(newsTitle);

        if (mainImg) {
            mainImg.src = newsImg;
            mainImg.classList.remove('skeleton-img');
            mainImg.style.background = 'none';
            mainImg.onclick = () => window.location.href = `article.html?slug=${newsSlug}`;
        }

        if (mainTitle) {
            mainTitle.innerHTML = `<a href="article.html?slug=${newsSlug}" style="color:#fff; text-decoration:none;">${newsTitle}</a>`;
        }

        topFive.forEach((_, i) => {
            const el = document.getElementById(`bullet-${i}`);
            if (el) {
                el.style.color = '#ffffff';
                el.style.fontWeight = '500';
            }
        });

        const activeEl = document.getElementById(`bullet-${index}`);
        if (activeEl) {
            activeEl.style.color = '#fde047'; // पीला रंग हाइलाइट के लिए
            activeEl.style.fontWeight = '800';
        }
    };

    // पहला स्लाइड दिखाएं
    window.selectHeroSlide(0);

    // ⏱️ हर 2 सेकंड में ऑटो-स्लाइड
    if (abpSlideInterval) clearInterval(abpSlideInterval);
    abpSlideInterval = setInterval(() => {
        currentAbpIndex = (currentAbpIndex + 1) % topFive.length;
        window.selectHeroSlide(currentAbpIndex);
    }, 2000);
}
function createSlug(text) {
    if (!text) return "news-" + Date.now();
    let cleanText = text.replace(/ \| Times07 News/ig, "");

    // हिंदी को रोमन इंग्लिश में बदलेगा (Transliteration)
    if (window.transliterate) {
        try { cleanText = window.transliterate(cleanText); } catch(e){}
    }

    return cleanText
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "") // सिर्फ शुद्ध English Letters और Numbers रखेगा
        .trim()
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .replace(/^-+|-+$/g, "");
}
// ==========================================================
// DYNAMIC ARTICLE PAGE & AUTOMATIC RELATED SUGGESTIONS (RESTORED)
// ==========================================================
function populateArticlePage() {
    const urlParams = new URLSearchParams(window.location.search);
    let finalIndex = parseInt(urlParams.get('id'), 10);
    const slug = urlParams.get("slug");
    const savedNews = window.sampleNews || JSON.parse(localStorage.getItem('times07_news')) || [];

    if (slug) {
        finalIndex = savedNews.findIndex(item => (item.slug || createSlug(item.title)) === slug);
    }

    if (finalIndex !== -1 && savedNews[finalIndex]) {
        const news = savedNews[finalIndex];
        const articleSlug = news.slug || createSlug(news.title);
        const fullCanonicalUrl = `https://times07news.in/article.html?slug=${articleSlug}`;

        // 1. DYNAMIC CANONICAL FOR GOOGLE INDEXING
        let canonicalEl = document.getElementById("canonical-url") || document.querySelector('link[rel="canonical"]');
        if (canonicalEl) {
            canonicalEl.setAttribute("href", fullCanonicalUrl);
        }

        // 2. META TAGS
        document.querySelector('meta[property="og:title"]')?.setAttribute("content", news.title);
        document.querySelector('meta[property="og:description"]')?.setAttribute("content", (news.summary || news.desc || "").substring(0, 160));
        document.querySelector('meta[property="og:url"]')?.setAttribute("content", fullCanonicalUrl);
        document.querySelector('meta[property="og:image"]')?.setAttribute("content", news.image || news.img1 || "");

        // 3. SCHEMA.ORG FOR GOOGLE NEWS
        const schemaContainer = document.getElementById("news-schema");
        if (schemaContainer) {
            schemaContainer.textContent = JSON.stringify({
                "@context": "https://schema.org",
                "@type": "NewsArticle",
                "headline": news.title,
                "description": (news.summary || news.desc || "").substring(0, 160),
                "image": [news.image || news.img1 || "https://times07news.in/logo.png"],
                "url": fullCanonicalUrl,
                "mainEntityOfPage": { "@type": "WebPage", "@id": fullCanonicalUrl },
                "datePublished": news.timestamp ? new Date(news.timestamp).toISOString() : new Date().toISOString(),
                "dateModified": new Date().toISOString(),
                "author": { "@type": "Organization", "name": "Times07 News" },
                "publisher": {
                    "@type": "Organization",
                    "name": "Times07 News",
                    "logo": { "@type": "ImageObject", "url": "https://times07news.in/logo.png" }
                },
                "inLanguage": "hi-IN"
            });
        }

        document.title = `${news.title} - Times07 News`;
        if(document.getElementById("meta-title")) document.getElementById("meta-title").textContent = `${news.title} | Times07 News`;

        if(document.getElementById('page-title')) document.getElementById('page-title').innerText = news.title;
        if(document.getElementById('page-cat')) document.getElementById('page-cat').innerText = news.category || "मुख्य समाचार";
        if(document.getElementById('page-time')) {
            document.getElementById('page-time').innerText = news.timestamp ? new Date(news.timestamp).toLocaleDateString("hi-IN") : "आज";
        }
        if(document.getElementById('page-img')) {
            const articleImg = document.getElementById('page-img');
            articleImg.src = news.image || news.img1 || 'logo.png';
            articleImg.alt = news.title;
        }

        let rawContent = news.content_html || news.content || news.desc || news.summary || "खबर की विस्तृत जानकारी के लिए टाइम्स07 पर बने रहें।";
        if (rawContent) {
            rawContent = rawContent.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>');
        }
        if(document.getElementById('page-content')) document.getElementById('page-content').innerHTML = rawContent;
        if(document.getElementById('views-count')) document.getElementById('views-count').innerText = (news.views || 0).toLocaleString("en-IN");

        renderArticleSuggestions(finalIndex, news.category, savedNews);
    }
}

function renderArticleSuggestions(currentIndex, currentCategory, allNews) {
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

    let relatedNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex && (item.category || '').toLowerCase() === (currentCategory || '').toLowerCase());

    if (relatedNews.length === 0) {
        relatedNews = allNews
            .map((item, idx) => ({ ...item, originalIndex: idx }))
            .filter(item => item.originalIndex !== currentIndex)
            .slice(0, 4);
    }

    const trendingNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex)
        .sort((a, b) => (b.views || 0) - (a.views || 0))
        .slice(0, 4);

    const otherNews = allNews
        .map((item, idx) => ({ ...item, originalIndex: idx }))
        .filter(item => item.originalIndex !== currentIndex)
        .slice(4, 8);

    const buildNewsGrid = (newsList) => {
        if (!newsList || newsList.length === 0) return '<p style="color:#888; font-size:13px;">कोई अन्य खबर उपलब्ध नहीं है।</p>';
        return `
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 15px; margin-top: 15px; margin-bottom: 35px;">
                ${newsList.map(item => `
                    <div style="background: var(--bg-card, #fefefe); border: 1px solid var(--border-color, #eee); border-radius: 8px; overflow: hidden; box-shadow: 0 2px 6px rgba(0,0,0,0.06); transition: transform 0.2s ease;">
                        <a href="article.html?slug=${item.data ? (item.data.slug || createSlug(item.data.title)) : (item.slug || createSlug(item.title))}" style="text-decoration:none; color:inherit;">
                            <img src="${item.img1 || item.image || 'logo.png'}" style="width:100%; height:120px; object-fit:cover;" loading="lazy">
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

    const html = `
        <div><h3 style="font-size: 18px; font-weight: 800; color: #d32f2f; border-bottom: 3px solid #d32f2f; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">📌 संबंधित खबरें (Related News)</h3>${buildNewsGrid(relatedNews.slice(0, 4))}</div>
        <div><h3 style="font-size: 18px; font-weight: 800; color: #2980b9; border-bottom: 3px solid #2980b9; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">🔥 ट्रेंडिंग और ब्रेकिंग न्यूज़ (Trending News)</h3>${buildNewsGrid(trendingNews)}</div>
        <div><h3 style="font-size: 18px; font-weight: 800; color: #27ae60; border-bottom: 3px solid #27ae60; padding-bottom: 4px; display: inline-block; margin-bottom: 5px;">📰 अन्य प्रमुख समाचार (Other Headlines)</h3>${buildNewsGrid(otherNews.length > 0 ? otherNews : allNews.slice(0, 4))}</div>
    `;

    suggestionContainer.innerHTML = html;
}

// ==========================================================
// OTHER APP FUNCTIONS (Widgets, Weather, Clock, Search)
// ==========================================================
function renderMostReadWidget() {
    const box = document.getElementById('most-read-box');
    if (!box) return;
    box.innerHTML = "";
    [...(window.sampleNews || [])].sort((a, b) => (b.views || 0) - (a.views || 0)).slice(0, 5).forEach((news, idx) => {
        const item = document.createElement('div');
        item.style.cssText = "border-bottom:1px solid var(--border-color); padding-bottom:8px; margin-bottom:8px;";
        item.innerHTML = `<a href="article.html?slug=${item.slug}" style="font-size:13px; font-weight:700; color:var(--heading-color); text-decoration:none;">• ${(news.title || '').substring(0, 50)}...</a>`;
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
                <img src="${news.img1 || news.image || 'logo.png'}">
            </div>
            <div class="card-content" style="padding:10px;">
                <h4 style="font-size:13px; font-weight:700; line-height:1.3;">${(news.title || '').substring(0, 45)}...</h4>
                <a href="article.html?slug=${item.slug}" style="font-size:11px; color:var(--abp-red); font-weight:800; text-decoration:none; margin-top:6px; display:inline-block;">विशेष कवरेज &rarr;</a>
            </div>
        `;
        box.appendChild(item);
    });
}

function fetchAccurateWeather() {
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(async (position) => {
            const lat = position.coords.latitude, lon = position.coords.longitude;
            try {
                const res = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current_weather=true`);
                const data = await res.json();
                if (data && data.current_weather) {
                    const temp = Math.round(data.current_weather.temperature);
                    const geoRes = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`);
                    const geoData = await geoRes.json();
                    const city = geoData.address.suburb || geoData.address.city || geoData.address.town || "India";
                    if(document.getElementById('user-location-city')) document.getElementById('user-location-city').innerText = city;
                    if(document.getElementById('top-weather-temp')) document.getElementById('top-weather-temp').innerText = `${temp}°C Sunny`;
                }
            } catch (e) {}
        });
    }
}
fetchAccurateWeather();

function updateLiveClock() {
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    if(document.getElementById('live-clock')) document.getElementById('live-clock').innerText = new Date().toLocaleString('en-US', options) + " IST";
}
setInterval(updateLiveClock, 1000); updateLiveClock();

window.categorizeNewsBot = function(article) {
    const title = (article.title || '').toLowerCase();
    const content = (article.content || article.summary || article.desc || '').toLowerCase();
    const text = title + " " + content;

    if (text.match(/stock|market|nifty|sensex|share|invest|dow|nasdaq|ipo/i)) return 'Global Markets';
    else if (text.match(/ev|car|bike|tesla|vehicle|auto|truck|engine/i)) return 'Auto & EV Tech';
    else if (text.match(/ai|tech|robot|software|google|ibm|nvidia|cyber|quantum/i)) return 'Tech & AI';
    else if (text.match(/crypto|bitcoin|btc|eth|blockchain/i)) return 'Cryptocurrency';
    else if (text.match(/world|us|uk|global|president|china|international/i)) return 'World News';
    else if (text.match(/economy|inflation|bank|fed|loan|finance/i)) return 'Economy';
    return article.category || 'World News'; 
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
            gridBox.innerHTML += `<article class="news-card"><div class="card-img"><a href="article.html?slug=${news.slug || createSlug(news.title)}"><img src="${news.img1||'logo.png'}"></a></div><div class="card-content"><a href="article.html?slug=${news.slug || createSlug(news.title)}" style="text-decoration:none;"><span style="font-size:10px; background:#c00000; color:#fff; padding:2px 6px; border-radius:3px; font-weight:bold;">${news.category||'GLOBAL'}</span><h3 style="margin-top:5px;">${news.title}</h3></a></div></article>`;
        });
        window.scrollTo(0,0);
    }
};

window.showHome = function() { window.scrollTo(0, 0); };

// Google Translate
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
window.addEventListener("DOMContentLoaded", () => {
    populateArticlePage();
});
