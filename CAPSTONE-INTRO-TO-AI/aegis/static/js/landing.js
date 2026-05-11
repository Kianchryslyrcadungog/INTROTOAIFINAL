/**
 * Aegis — Landing Page JavaScript
 * Handles animations and scroll effects
 */

if (window.AegisTheme && typeof window.AegisTheme.init === 'function') {
  window.AegisTheme.init();
}

// Animate type cards on scroll
const typeCards = document.querySelectorAll('.type-card');
const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }, i * 80);
    }
  });
}, { threshold: 0.1 });

typeCards.forEach(card => {
  card.style.opacity = '0';
  card.style.transform = 'translateY(20px)';
  card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
  observer.observe(card);
});

// Animate steps
const steps = document.querySelectorAll('.step');
const stepObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      setTimeout(() => {
        entry.target.style.opacity = '1';
        entry.target.style.transform = 'translateY(0)';
      }, i * 100);
    }
  });
}, { threshold: 0.1 });

steps.forEach(step => {
  step.style.opacity = '0';
  step.style.transform = 'translateY(20px)';
  step.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
  stepObserver.observe(step);
});
