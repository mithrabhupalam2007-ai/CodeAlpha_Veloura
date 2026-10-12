/* VELOURA — vanilla JS interactions */
(function () {
  'use strict';

  /* ---------------- Toast auto-dismiss ---------------- */
  document.querySelectorAll('[data-toast]').forEach(function (toast) {
    setTimeout(function () {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-8px)';
      setTimeout(function () { toast.remove(); }, 300);
    }, 4500);
  });

  /* ---------------- Mobile nav toggle ---------------- */
  var navToggle = document.getElementById('nav-toggle');
  var mainNav = document.getElementById('main-nav');
  if (navToggle && mainNav) {
    navToggle.addEventListener('click', function () {
      var open = mainNav.classList.toggle('is-open');
      navToggle.setAttribute('aria-expanded', String(open));
    });
  }

  /* ---------------- Profile dropdown ---------------- */
  var profileMenu = document.getElementById('profile-menu');
  if (profileMenu) {
    var trigger = profileMenu.querySelector('.profile-menu__trigger');
    trigger.addEventListener('click', function (e) {
      e.stopPropagation();
      profileMenu.classList.toggle('is-open');
      trigger.setAttribute('aria-expanded', profileMenu.classList.contains('is-open'));
    });
    document.addEventListener('click', function (e) {
      if (!profileMenu.contains(e.target)) profileMenu.classList.remove('is-open');
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') profileMenu.classList.remove('is-open');
    });
  }

  /* ---------------- Product gallery ---------------- */
  var mainImg = document.getElementById('gallery-main-img');
  document.querySelectorAll('.gallery__thumb').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      if (!mainImg) return;
      mainImg.src = thumb.dataset.full;
      document.querySelectorAll('.gallery__thumb').forEach(function (t) {
        t.classList.remove('is-active');
      });
      thumb.classList.add('is-active');
    });
  });

  /* ---------------- Size / colour chips (visual state) ---------------- */
  document.querySelectorAll('.chip-row').forEach(function (row) {
    row.addEventListener('change', function () {
      row.querySelectorAll('.chip').forEach(function (chip) {
        chip.classList.toggle('is-active', !!chip.querySelector('input:checked'));
      });
    });
  });

  /* ---------------- Quantity stepper (product page) ---------------- */
  var qtyInput = document.getElementById('qty-input');
  if (qtyInput) {
    document.querySelectorAll('[data-qty]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var delta = parseInt(btn.getAttribute('data-qty'), 10);
        var max = parseInt(qtyInput.max || '999', 10);
        var next = (parseInt(qtyInput.value, 10) || 1) + delta;
        if (next < 1) next = 1;
        if (next > max) next = max;
        qtyInput.value = next;
      });
    });
    qtyInput.addEventListener('change', function () {
      var max = parseInt(qtyInput.max || '999', 10);
      var v = parseInt(qtyInput.value, 10) || 1;
      if (v < 1) qtyInput.value = 1;
      if (v > max) qtyInput.value = max;
    });
  }

  /* ---------------- Filters drawer (mobile) ---------------- */
  var filters = document.getElementById('filters');
  if (filters) {
    filters.querySelectorAll('input[type="number"], select').forEach(function (el) {
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          e.preventDefault();
          var form = document.getElementById('filter-form');
          if (form) form.submit();
        }
      });
    });
  }

  /* ---------------- Newsletter inline validation ---------------- */
  document.querySelectorAll('.newsletter__form').forEach(function (form) {
    form.addEventListener('submit', function (e) {
      var input = form.querySelector('input[type="email"]');
      if (input && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.value)) {
        e.preventDefault();
        input.setCustomValidity('Please enter a valid email address.');
        input.reportValidity();
        input.setCustomValidity('');
      }
    });
  });
})();
