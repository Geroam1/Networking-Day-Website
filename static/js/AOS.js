// JS AOS (animate on scroll) library that simply applies scroll animations
AOS.init({
duration: 1000, // animation duration in ms
once: true // animate only once when scrolling down
});

// Smooth scroll to input fields on window resize (for mobile devices)
window.addEventListener('resize', () => {
    if (document.activeElement.tagName === 'INPUT' || document.activeElement.tagName === 'TEXTAREA') {
        document.activeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});