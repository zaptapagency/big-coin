/* ============================================================
   BigCoin — main.js
   Mobile nav toggle · smooth-scroll · scroll-reveal · year
   Vanilla JS, no dependencies.
   ============================================================ */
(function () {
  'use strict';

  /* ---- Footer year ---- */
  var yearEl = document.getElementById('year');
  if (yearEl) { yearEl.textContent = String(new Date().getFullYear()); }

  /* ---- Mobile nav toggle ---- */
  var toggle = document.getElementById('navToggle');
  var links = document.getElementById('navLinks');

  function closeNav() {
    if (!links || !toggle) return;
    links.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  }

  if (toggle && links) {
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    // Close the menu after tapping a link (mobile)
    links.addEventListener('click', function (e) {
      if (e.target.tagName === 'A') closeNav();
    });
    // Close on Escape
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeNav();
    });
    // Close if resizing up to desktop
    window.addEventListener('resize', function () {
      if (window.innerWidth > 720) closeNav();
    });
  }

  /* ---- Smooth-scroll for in-page anchors ----
     (CSS handles this too; JS provides a consistent fallback
      and respects reduced-motion preferences.) */
  var prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      var id = anchor.getAttribute('href');
      if (!id || id === '#') return;
      var target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      target.scrollIntoView({
        behavior: prefersReduced ? 'auto' : 'smooth',
        block: 'start'
      });
      // Update the URL hash without an extra jump
      if (history.pushState) history.pushState(null, '', id);
    });
  });

  /* ---- Scroll-reveal animation for elements marked .reveal ---- */
  var revealables = document.querySelectorAll('.reveal');

  if (!('IntersectionObserver' in window) || prefersReduced) {
    // No observer support or reduced motion: just show everything.
    revealables.forEach(function (el) { el.classList.add('is-visible'); });
    return;
  }

  var observer = new IntersectionObserver(function (entries, obs) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

  // Stagger reveals slightly among siblings for a polished feel.
  revealables.forEach(function (el, i) {
    el.style.transitionDelay = (Math.min(i % 6, 5) * 60) + 'ms';
    observer.observe(el);
  });
})();
