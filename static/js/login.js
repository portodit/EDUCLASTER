// Function to show the snackbar
function showSnackbar(message) {
    const snackbar = document.getElementById("snackbar");
    const snackbarMessage = document.getElementById("snackbar-message");
    
    snackbarMessage.textContent = message;
    snackbar.className = "snackbar show";
    
    // After 4 seconds, remove the show class
    setTimeout(function(){ 
        snackbar.className = snackbar.className.replace("show", ""); 
    }, 4000);
}

// Function to close the snackbar
function closeSnackbar() {
    const snackbar = document.getElementById("snackbar");
    snackbar.className = snackbar.className.replace("show", "");
}

// Create background particles
function createBgParticles() {
    const container = document.getElementById('bg-particles-container');
    const shapes = ['circle', 'square', 'triangle', 'diamond'];
    const colors = ['#d6bbfb', '#7e56d8', '#6840c6', '#e9d5ff'];
    
    // Create 20 particles
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('div');
        particle.classList.add('bg-particle');
        
        // Random properties
        const size = Math.random() * 30 + 10; // 10-40px
        const color = colors[Math.floor(Math.random() * colors.length)];
        const left = Math.random() * 100; // 0-100%
        const delay = Math.random() * 10; // 0-10s delay
        const duration = Math.random() * 10 + 15; // 15-25s duration
        
        // Base styles
        particle.style.width = `${size}px`;
        particle.style.height = `${size}px`;
        particle.style.left = `${left}%`;
        particle.style.bottom = '-50px';
        particle.style.animationDelay = `${delay}s`;
        particle.style.animationDuration = `${duration}s`;
        
        // Apply shape-specific styles
        const shape = shapes[Math.floor(Math.random() * shapes.length)];
        
        switch(shape) {
            case 'circle':
                particle.style.borderRadius = '50%';
                particle.style.background = color;
                break;
            case 'square':
                particle.style.borderRadius = '4px';
                particle.style.background = color;
                particle.style.transform = `rotate(${Math.random() * 45}deg)`;
                break;
            case 'triangle':
                particle.style.width = '0';
                particle.style.height = '0';
                particle.style.borderLeft = `${size/2}px solid transparent`;
                particle.style.borderRight = `${size/2}px solid transparent`;
                particle.style.borderBottom = `${size}px solid ${color}`;
                particle.style.background = 'transparent';
                break;
            case 'diamond':
                particle.style.width = `${size}px`;
                particle.style.height = `${size}px`;
                particle.style.background = color;
                particle.style.transform = 'rotate(45deg)';
                break;
        }
        
        // Add to container
        container.appendChild(particle);
    }
}

// When the document is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Create background particles
    createBgParticles();
    
    // For demo purposes - show error if URL contains error parameter
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('error')) {
        showSnackbar("Anda telah keluar dari sistem.");
    }
});