// main.js - File utama yang memuat semua file JavaScript

// Impor semua file JS terpisah
document.addEventListener('DOMContentLoaded', function() {
    // Load hero section scripts
    const heroScript = document.createElement('script');
    heroScript.src = '/static/js/hero-section.js';
    document.body.appendChild(heroScript);
    
    // Load platform section scripts
    const platformScript = document.createElement('script');
    platformScript.src = '/static/js/platform-section.js';
    document.body.appendChild(platformScript);
    
    // Load profile section scripts
    const profileScript = document.createElement('script');
    profileScript.src = '/static/js/profile-section.js';
    document.body.appendChild(profileScript);
    
    // Load FAQ section scripts
    const faqScript = document.createElement('script');
    faqScript.src = '/static/js/faq-section.js';
    document.body.appendChild(faqScript);
    
    // Load footer section scripts
    const footerScript = document.createElement('script');
    footerScript.src = '/static/js/footer-section.js';
    document.body.appendChild(footerScript);
});
