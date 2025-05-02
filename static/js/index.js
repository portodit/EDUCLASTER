document.addEventListener('DOMContentLoaded', function() {
    // Hero Section
    // Set data-text untuk efek glow
    document.querySelectorAll('.gradient-text').forEach(el => {
        el.setAttribute('data-text', el.textContent);
    });
    
    // Membuat partikel sparkle untuk efek sprinkle
    const sprinkleContainer = document.querySelector('.sprinkle-container');
    
    function createSparkle() {
        const sparkle = document.createElement('span');
        sparkle.className = 'sparkle';
        
        // Random position
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        const size = Math.random() * 3 + 1;
        
        sparkle.style.cssText = `
            position: absolute;
            left: ${x}%;
            top: ${y}%;
            width: ${size}px;
            height: ${size}px;
            background: #a88bfa;
            border-radius: 50%;
            box-shadow: 0 0 8px rgba(138, 112, 214, 0.6);
            pointer-events: none;
            opacity: 0;
            animation: sparkle 1.5s ease-in-out;
        `;
        
        sprinkleContainer.appendChild(sparkle);
        
        // Remove sparkle after animation
        setTimeout(() => {
            sparkle.remove();
        }, 1500);
    }
    
    // Create sparkles periodically
    setInterval(createSparkle, 200);
    
    // Buat animasi tambahan untuk elemen yang muncul secara acak
    function createRandomBubble() {
        const bubble = document.createElement('div');
        const size = Math.random() * 15 + 5;
        const duration = Math.random() * 4 + 3;
        
        // Posisi acak di sekitar layar
        const x = Math.random() * 100;
        const y = Math.random() * 100;
        
        // Warna acak yang sesuai dengan tema
        const colors = ['rgba(168, 139, 250, 0.2)', 'rgba(107, 70, 193, 0.2)', 'rgba(139, 92, 246, 0.2)', 'rgba(196, 181, 253, 0.2)'];
        const color = colors[Math.floor(Math.random() * colors.length)];
        
        bubble.style.cssText = `
            position: absolute;
            left: ${x}%;
            top: ${y}%;
            width: ${size}px;
            height: ${size}px;
            background: ${color};
            border-radius: 50%;
            pointer-events: none;
            opacity: 0;
            z-index: 5;
            animation: bubbleRise ${duration}s ease-in-out forwards;
        `;
        
        document.querySelector('section').appendChild(bubble);
        
        // Hapus bubble setelah animasi selesai
        setTimeout(() => {
            bubble.remove();
        }, duration * 1000);
    }
    
    // Buat animasi bubbles secara periodik
    setInterval(createRandomBubble, 1000);
    
    // Tambahkan keyframe untuk bubble rise
    const style = document.createElement('style');
    style.textContent = `
        @keyframes bubbleRise {
            0% {
                opacity: 0;
                transform: translateY(0) scale(0);
            }
            20% {
                opacity: 0.7;
                transform: translateY(-10px) scale(1);
            }
            80% {
                opacity: 0.7;
                transform: translateY(-${Math.random() * 50 + 20}px) scale(0.8);
            }
            100% {
                opacity: 0;
                transform: translateY(-${Math.random() * 80 + 40}px) scale(0);
            }
        }
    `;
    document.head.appendChild(style);

    // Platform Introduction Section
    // Intersection Observer for scroll animations
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in-visible');
            }
        });
    }, {
        threshold: 0.1
    });
    
    document.querySelectorAll('.fade-in-section').forEach(el => {
        observer.observe(el);
    });
    
    // Create particles for background
    function createParticles() {
        const container = document.querySelector('.particles-container');
        if (!container) return;
        
        const particleCount = 20;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('span');
            particle.classList.add('particle');
            
            // Random properties
            const size = Math.random() * 4 + 2;
            const posX = Math.random() * 100;
            const posY = Math.random() * 100;
            const delay = Math.random() * 10;
            const duration = 15 + Math.random() * 10;
            
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            particle.style.left = `${posX}%`;
            particle.style.top = `${posY}%`;
            particle.style.animationDelay = `${delay}s`;
            particle.style.animationDuration = `${duration}s`;
            
            container.appendChild(particle);
        }
    }
    
    createParticles();
    
    // Add interactive hover effects for feature cards
    const featureCards = document.querySelectorAll('.feature-card');
    
    featureCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            // Add subtle shadow effect on hover
            card.style.boxShadow = '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)';
            
            // Find the icon container and add extra animation
            const iconContainer = card.querySelector('.icon-container');
            if (iconContainer) {
                iconContainer.style.transform = 'scale(1.1)';
                iconContainer.style.transition = 'all 0.3s ease';
            }
        });
        
        card.addEventListener('mouseleave', () => {
            // Reset styles on mouse leave
            card.style.boxShadow = '';
            
            const iconContainer = card.querySelector('.icon-container');
            if (iconContainer) {
                iconContainer.style.transform = '';
            }
        });
    });
    
    // Add particle float animation
    document.querySelectorAll('.particle').forEach(particle => {
        const randomX = (Math.random() - 0.5) * 100;
        
        particle.animate([
            { transform: 'translateY(0) translateX(0)', opacity: 0 },
            { opacity: 0.8, offset: 0.2 },
            { opacity: 0.8, offset: 0.8 },
            { transform: `translateY(-100vh) translateX(${randomX}px)`, opacity: 0 }
        ], {
            duration: parseFloat(particle.style.animationDuration) * 1000,
            delay: parseFloat(particle.style.animationDelay) * 1000,
            iterations: Infinity
        });
    });

    // Profile Section - Carousel
    // Carousel functionality
    const track = document.querySelector('.carousel-track');
    const slides = document.querySelectorAll('.carousel-slide');
    const indicators = document.querySelectorAll('.carousel-indicator');
    const slideCount = slides.length;
    let currentSlide = 0;
    let autoSlideInterval;
    
    // Function to go to a specific slide dengan transisi lebih halus
    function goToSlide(index) {
        if (index < 0) index = slideCount - 1;
        if (index >= slideCount) index = 0;
        
        track.style.transform = `translateX(-${index * 100}%)`;
        currentSlide = index;
        
        // Update indicators
        indicators.forEach((indicator, i) => {
            if (i === index) {
                indicator.classList.add('active');
                indicator.classList.remove('bg-purple-300');
                indicator.classList.add('bg-purple-600');
            } else {
                indicator.classList.remove('active');
                indicator.classList.remove('bg-purple-600');
                indicator.classList.add('bg-purple-300');
            }
        });
    }
    
    // Start auto slide functionality - slide every 3 seconds
    function startAutoSlide() {
        autoSlideInterval = setInterval(() => {
            goToSlide((currentSlide + 1) % slideCount);
        }, 3000); // Change slide every 3 seconds
    }
    
    // Initialize first slide
    if (track && slides.length > 0) {
        goToSlide(0);
        
        // Start auto sliding
        startAutoSlide();
        
        // Setup indicators click events
        indicators.forEach((indicator, index) => {
            indicator.addEventListener('click', () => {
                // Clear the auto slide interval when user interacts
                clearInterval(autoSlideInterval);
                
                // Go to the clicked slide
                goToSlide(index);
                
                // Restart auto slide after user interaction
                setTimeout(startAutoSlide, 5000);
            });
        });
        
        // Pause auto slide when mouse is over the carousel
        const carousel = document.querySelector('.profile-carousel');
        if (carousel) {
            carousel.addEventListener('mouseenter', () => {
                clearInterval(autoSlideInterval);
            });
            
            // Resume auto slide when mouse leaves the carousel
            carousel.addEventListener('mouseleave', () => {
                startAutoSlide();
            });
        }
    }

    // FAQ Section
    // Script untuk FAQ accordion dengan animasi yang lebih menarik dan scrollable content
    const faqItems = document.querySelectorAll('.faq-item');
    
    faqItems.forEach((item, index) => {
        // Add staggered entrance animation
        setTimeout(() => {
            item.style.opacity = "1";
            item.style.transform = "translateY(0)";
        }, 100 * index);
        
        const question = item.querySelector('.faq-question');
        
        // Add initial styles
        item.style.opacity = "0";
        item.style.transform = "translateY(20px)";
        item.style.transition = "all 0.4s ease";
        
        question.addEventListener('click', () => {
            // Toggle active class
            const isActive = item.classList.contains('active');
            
            // Close all items first with animation
            faqItems.forEach(faqItem => {
                if (faqItem.classList.contains('active')) {
                    const answer = faqItem.querySelector('.faq-answer');
                    const p = answer.querySelector('p');
                    
                    // Animate paragraph out first
                    p.style.opacity = "0";
                    p.style.transform = "translateY(10px)";
                    
                    // Then close the accordion after a short delay
                    setTimeout(() => {
                        faqItem.classList.remove('active');
                    }, 150);
                }
            });
            
            // If the clicked item wasn't active before, make it active with animation
            if (!isActive) {
                setTimeout(() => {
                    item.classList.add('active');
                    
                    // Add a ripple effect to the question
                    const ripple = document.createElement('span');
                    ripple.classList.add('ripple-effect');
                    ripple.style.cssText = `
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        width: 0;
                        height: 0;
                        background: rgba(139, 92, 246, 0.1);
                        border-radius: 50%;
                        z-index: -1;
                        animation: ripple 0.6s ease-out;
                    `;
                    
                    question.appendChild(ripple);
                    
                    // Remove ripple after animation completes
                    setTimeout(() => {
                        ripple.remove();
                    }, 600);
                    
                    // Add keyframe for ripple dynamically
                    if (!document.querySelector('#ripple-keyframe')) {
                        const rippleStyle = document.createElement('style');
                        rippleStyle.id = 'ripple-keyframe';
                        rippleStyle.textContent = `
                            @keyframes ripple {
                                to {
                                    width: 300%;
                                    height: 300%;
                                    opacity: 0;
                                }
                            }
                        `;
                        document.head.appendChild(rippleStyle);
                    }
                    
                    // Enhanced scrollable functionality
                    const answer = item.querySelector('.faq-answer');
                    const content = answer.querySelector('p');
                    
                    // Check if the content is overflowing
                    setTimeout(() => {
                        if (content.offsetHeight > 250) { // If content is taller than container
                            // Add a subtle indicator that content is scrollable
                            const scrollIndicator = document.createElement('div');
                            scrollIndicator.classList.add('scroll-indicator');
                            scrollIndicator.style.cssText = `
                                position: absolute;
                                bottom: 10px;
                                right: 10px;
                                width: 30px;
                                height: 30px;
                                background-color: rgba(139, 92, 246, 0.1);
                                border-radius: 50%;
                                display: flex;
                                align-items: center;
                                justify-content: center;
                                pointer-events: none;
                                opacity: 0.7;
                                animation: pulseIndicator 2s infinite;
                            `;
                            
                            // Add arrow icon
                            scrollIndicator.innerHTML = `
                                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="#6B46C1" viewBox="0 0 16 16">
                                    <path d="M8 15a.5.5 0 0 1-.5-.5V2.707l-3.146 3.147a.5.5 0 0 1-.708-.708l4-4a.5.5 0 0 1 .708 0l4 4a.5.5 0 1 1-.708.708L8.5 2.707V14.5a.5.5 0 0 1-.5.5z"/>
                                </svg>
                            `;
                            
                            answer.style.position = 'relative';
                            answer.appendChild(scrollIndicator);
                            
                            // Create animation for the indicator
                            if (!document.querySelector('#pulse-indicator-keyframe')) {
                                const indicatorStyle = document.createElement('style');
                                indicatorStyle.id = 'pulse-indicator-keyframe';
                                indicatorStyle.textContent = `
                                    @keyframes pulseIndicator {
                                        0%, 100% { transform: translateY(0); opacity: 0.7; }
                                        50% { transform: translateY(-5px); opacity: 1; }
                                    }
                                `;
                                document.head.appendChild(indicatorStyle);
                            }
                            
                            // Hide indicator when scrolling
                            answer.addEventListener('scroll', () => {
                                scrollIndicator.style.opacity = '0';
                                scrollIndicator.style.animation = 'none';
                                
                                // Remove after scrolling
                                setTimeout(() => {
                                    scrollIndicator.remove();
                                }, 500);
                            });
                        }
                    }, 300);
                }, 200);
            }
        });
        
        // Add hover effect
        question.addEventListener('mouseenter', () => {
            if (!item.classList.contains('active')) {
                item.style.transform = "translateX(5px)";
            }
        });
        
        question.addEventListener('mouseleave', () => {
            if (!item.classList.contains('active')) {
                item.style.transform = "translateY(0)";
            }
        });
    });

    // Footer
    // Animated elements for footer
    function createFooterAnimations() {
        const footer = document.querySelector('footer');
        if (!footer) return;
        
        // Add multiple animated bubbles to footer
        for (let i = 0; i < 12; i++) {
            const bubble = document.createElement('div');
            bubble.classList.add('footer-bubble');
            
            const size = Math.random() * 40 + 10;
            const posX = Math.random() * 100;
            const posY = Math.random() * 100;
            const delay = Math.random() * 5;
            
            bubble.style.cssText = `
                width: ${size}px;
                height: ${size}px;
                left: ${posX}%;
                top: ${posY}%;
                animation-delay: ${delay}s;
                animation-duration: ${15 + Math.random() * 10}s;
            `;
            
            footer.appendChild(bubble);
        }
        
        // Add animated light rays
        for (let i = 0; i < 5; i++) {
            const ray = document.createElement('div');
            ray.classList.add('footer-light-ray');
            
            const posY = Math.random() * 80 + 10;
            const width = Math.random() * 150 + 50;
            const delay = Math.random() * 8;
            
            ray.style.cssText = `
                top: ${posY}%;
                left: 0;
                width: ${width}px;
                animation-delay: ${delay}s;
                animation-duration: ${10 + Math.random() * 8}s;
            `;
            
            footer.appendChild(ray);
        }
        
        // Add animated waves
        for (let i = 0; i < 3; i++) {
            const wave = document.createElement('div');
            wave.classList.add('footer-wave');
            
            // Create SVG wave pattern
            wave.style.cssText = `
                bottom: ${i * 10}px;
                opacity: ${0.1 - i * 0.02};
                background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 120' preserveAspectRatio='none'%3E%3Cpath d='M0,0V46.29c47.79,22.2,103.59,32.17,158,28,70.36-5.37,136.33-33.31,206.8-37.5C438.64,32.43,512.34,53.67,583,72.05c69.27,18,138.3,24.88,209.4,13.08,36.15-6,69.85-17.84,104.45-29.34C989.49,25,1113-14.29,1200,52.47V0Z' opacity='.25' fill='%23FFFFFF'/%3E%3C/svg%3E");
                background-size: 100% 100%;
                height: ${15 + i * 5}px;
                animation-delay: ${i * 2}s;
            `;
            
            footer.appendChild(wave);
        }
        
        // Add floating particles
        for (let i = 0; i < 30; i++) {
            const particle = document.createElement('span');
            particle.classList.add('footer-particle');
            
            const size = Math.random() * 3 + 1;
            const posX = Math.random() * 100;
            const delay = Math.random() * 5;
            const duration = 10 + Math.random() * 15;
            const xEnd = (Math.random() - 0.5) * 200; // Random end position on X
            
            particle.style.cssText = `
                left: ${posX}%;
                width: ${size}px;
                height: ${size}px;
                bottom: -5%;
                opacity: 0;
                --x-end: ${xEnd}px;
                animation-delay: ${delay}s;
                animation-duration: ${duration}s;
            `;
            
            footer.appendChild(particle);
        }
    }
    
    createFooterAnimations();
});