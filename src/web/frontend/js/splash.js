// Euno - Splash Screen Animation

// Animation state
let splashAnimationComplete = false;
let splashAnimationPromise = null;

// Run the splash screen animation
// Returns a promise that resolves when animation is complete
// Only shows once per browser session
function runSplashAnimation() {
    if (splashAnimationPromise) return splashAnimationPromise;

    splashAnimationPromise = new Promise((resolve) => {
        // Check if splash was already shown this session
        if (sessionStorage.getItem('splashShown')) {
            // Skip animation - immediately hide splash and resolve
            const splashScreen = document.getElementById('splash-screen');
            splashScreen.classList.add('hidden');
            splashAnimationComplete = true;
            resolve();
            return;
        }

        const letters = document.querySelectorAll('.splash-letter');
        const pronunciation = document.getElementById('splash-pronunciation');
        const tagline = document.getElementById('splash-tagline');

        // Timeline:
        // 0-1200ms: Letters fade in (300ms apart)
        // 1600ms: Tagline fades in
        // 2400ms: Pronunciation fades in
        // 3200ms: Animation complete

        // Animate letters one by one
        letters.forEach((letter, index) => {
            setTimeout(() => {
                letter.classList.add('visible');
            }, index * 300);
        });

        // Animate tagline after letters
        setTimeout(() => {
            tagline.classList.add('visible');
        }, 1600);

        // Animate pronunciation after tagline
        setTimeout(() => {
            pronunciation.classList.add('visible');
        }, 2400);

        // Mark animation complete and resolve
        setTimeout(() => {
            splashAnimationComplete = true;
            sessionStorage.setItem('splashShown', 'true');
            resolve();
        }, 3200);
    });

    return splashAnimationPromise;
}

// Fade out and hide the splash screen
function hideSplashScreen() {
    const splashScreen = document.getElementById('splash-screen');
    splashScreen.classList.add('fade-out');

    // Remove from DOM after fade completes
    setTimeout(() => {
        splashScreen.classList.add('hidden');
    }, 400);
}

// Check if animation is complete
function isSplashAnimationComplete() {
    return splashAnimationComplete;
}
