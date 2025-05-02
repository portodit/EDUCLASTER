document.addEventListener('DOMContentLoaded', function() {
    // Inisialisasi particles background
    initBackgroundParticles();
    
    // Form validation dan handling
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            const username = document.querySelector('input[name="username"]').value;
            const password = document.querySelector('input[name="password"]').value;
            
            // Basic validation
            if (!username.trim()) {
                event.preventDefault();
                showSnackbar('Nama pengguna tidak boleh kosong');
                return false;
            }
            
            if (!password.trim()) {
                event.preventDefault();
                showSnackbar('Kata sandi tidak boleh kosong');
                return false;
            }
            
            // AJAX login handler (optional - uncomment if you want to handle login via AJAX)
            /*
            event.preventDefault();
            
            // Show loading state
            const submitButton = loginForm.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.textContent;
            submitButton.textContent = 'Memproses...';
            submitButton.disabled = true;
            
            // Submit data via AJAX
            fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username: username,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Redirect on success
                    window.location.href = data.redirect || '/dashboard';
                } else {
                    // Show error
                    showSnackbar(data.message || 'Username atau password salah');
                    submitButton.textContent = originalButtonText;
                    submitButton.disabled = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showSnackbar('Terjadi kesalahan. Silakan coba lagi.');
                submitButton.textContent = originalButtonText;
                submitButton.disabled = false;
            });
            */
            
            // Jika semua valid dan tidak menggunakan AJAX, form akan di-submit secara normal
        });
    }
    
    // Logo hover effect enhancement
    const logo = document.querySelector('.logo-glow');
    if (logo) {
        logo.addEventListener('mouseover', function() {
            this.style.transform = 'scale(1.05)';
        });
        
        logo.addEventListener('mouseout', function() {
            this.style.transform = 'scale(1)';
        });
    }
    
    // Animasi input fields
    const inputFields = document.querySelectorAll('.form-control');
    inputFields.forEach(field => {
        field.addEventListener('focus', function() {
            this.parentElement.classList.add('input-focused');
        });
        
        field.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('input-focused');
            }
        });
    });
});

// Membuat particles background
function initBackgroundParticles() {
    const container = document.getElementById('bg-particles-container');
    if (!container) return;
    
    // Jumlah particle yang ingin ditampilkan
    const particleCount = 30;
    
    // Ukuran container
    const containerWidth = window.innerWidth;
    const containerHeight = window.innerHeight;
    
    // Membuat particles
    for (let i = 0; i < particleCount; i++) {
        createParticle(container, containerWidth, containerHeight);
    }
}

function createParticle(container, maxWidth, maxHeight) {
    // Membuat particle element
    const particle = document.createElement('div');
    particle.classList.add('bg-particle');
    
    // Random properties
    const size = Math.random() * 5 + 2; // 2-7px
    const posX = Math.random() * maxWidth;
    const delay = Math.random() * 10; // 0-10s delay
    const duration = Math.random() * 10 + 15; // 15-25s duration
    const opacity = Math.random() * 0.3 + 0.1; // 0.1-0.4 opacity
    
    // Apply styles
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${posX}px`;
    particle.style.bottom = '-10px';
    particle.style.borderRadius = '50%';
    particle.style.opacity = opacity;
    particle.style.backgroundColor = getRandomColor();
    particle.style.animationDelay = `${delay}s`;
    particle.style.animationDuration = `${duration}s`;
    
    // Add to container
    container.appendChild(particle);
    
    // Remove after animation ends and create new one
    setTimeout(() => {
        particle.remove();
        createParticle(container, maxWidth, maxHeight);
    }, (delay + duration) * 1000);
}

function getRandomColor() {
    // Random colors dalam rentang ungu
    const colors = [
        'rgba(126, 86, 216, 0.8)',
        'rgba(139, 92, 246, 0.8)',
        'rgba(167, 139, 250, 0.8)',
        'rgba(192, 132, 252, 0.8)',
        'rgba(216, 180, 254, 0.8)'
    ];
    
    return colors[Math.floor(Math.random() * colors.length)];
}

// Snackbar functions
function showSnackbar(message) {
    const snackbar = document.getElementById('snackbar');
    const messageElement = document.getElementById('snackbar-message');
    
    if (snackbar && messageElement) {
        messageElement.textContent = message;
        snackbar.className = 'snackbar show';
        
        // Auto hide after 4 seconds
        setTimeout(function() {
            closeSnackbar();
        }, 4000);
    }
}

function closeSnackbar() {
    const snackbar = document.getElementById('snackbar');
    if (snackbar) {
        snackbar.className = 'snackbar';
    }
}

// Deteksi error dari server-side (jika ada)
document.addEventListener('DOMContentLoaded', function() {
    // Ambil error dari URL query parameter (jika ada)
    const urlParams = new URLSearchParams(window.location.search);
    const errorMessage = urlParams.get('error');
    
    if (errorMessage) {
        showSnackbar(decodeURIComponent(errorMessage));
    }
    
    // Handle error messages dari Flask flash
    const flashMessages = document.querySelectorAll('.flash-message');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            const messageText = message.textContent;
            if (messageText) {
                showSnackbar(messageText);
                message.remove(); // Remove from DOM after showing in snackbar
            }
        });
    }
    
    // Check for invalid login errors
    checkLoginErrors();
});

// Fungsi untuk memeriksa error login
function checkLoginErrors() {
    // Untuk Flask: deteksi jika ada flash messages yang disisipkan ke halaman
    // terkait kredensial yang tidak valid
    
    // 1. Check for hidden input field (common pattern)
    const loginErrorField = document.querySelector('input[name="login_error"]');
    if (loginErrorField && loginErrorField.value) {
        showSnackbar(loginErrorField.value);
    }
    
    // 2. Check for data attributes
    const loginForm = document.getElementById('loginForm');
    if (loginForm && loginForm.dataset.error) {
        showSnackbar(loginForm.dataset.error);
    }
    
    // 3. Check for URL parameter 'login_failed'
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('login_failed')) {
        showSnackbar('Username atau password salah. Silakan coba lagi.');
    }
    
    // 4. Check for specific error codes
    const errorCode = urlParams.get('code');
    if (errorCode) {
        switch(errorCode) {
            case 'invalid_credentials':
                showSnackbar('Username atau password salah.');
                break;
            case 'account_locked':
                showSnackbar('Akun Anda telah dikunci. Silakan hubungi administrator.');
                break;
            case 'not_activated':
                showSnackbar('Akun Anda belum diaktifkan. Silakan periksa email Anda.');
                break;
            default:
                showSnackbar('Terjadi kesalahan saat login. Silakan coba lagi.');
        }
    }
}