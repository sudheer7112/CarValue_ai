document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.add("page-enter");
  const nav = document.querySelector(".nav"), menu = document.querySelector(".menu");
  if (menu) menu.addEventListener("click", () => nav.classList.toggle("open"));
  document.querySelectorAll("a[data-transition]").forEach(a => a.addEventListener("click", e => {
    const h = a.getAttribute("href");
    if (!h || h.startsWith("#") || h.startsWith("http")) return;
    e.preventDefault();
    document.body.classList.add("page-exit");
    setTimeout(() => location.href = h, 180);
  }));
});

window.api = async (u, o = {}) => {
  const r = await fetch(u, { headers: { "Content-Type": "application/json", ...(o.headers || {}) }, ...o });
  const d = await r.json();
  if (!r.ok) throw Error(d.error || "Request failed");
  return d;
};

/* ── Smart-Select (searchable dropdown) ── */

function syncSmartSelect(el) {
  const wrap = el._smart;
  if (!wrap) return;
  const trigger = wrap.querySelector('.smart-trigger');
  const label = el.options[el.selectedIndex]?.textContent || 'Choose an option';
  trigger.textContent = label;
  trigger.disabled = el.disabled;
  wrap.classList.toggle('is-disabled', el.disabled);
  const menu = wrap.querySelector('.smart-menu');
  menu.querySelectorAll('.smart-option').forEach(b =>
    b.classList.toggle('selected', b.dataset.value === el.value)
  );
}

function renderSmartOptions(el) {
  const wrap = el._smart;
  if (!wrap) return;
  const menu = wrap.querySelector('.smart-menu');
  const search = menu.querySelector('.smart-search');
  // Remove old options only (keep search input and no-results)
  menu.querySelectorAll('.smart-option').forEach(x => x.remove());
  const fragment = document.createDocumentFragment();
  [...el.options].forEach((opt, i) => {
    if (i === 0 && opt.value === '') return; // skip placeholder
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'smart-option';
    b.dataset.value = opt.value;
    b.textContent = opt.textContent;
    b.addEventListener('click', () => {
      el.value = opt.value;
      // Dispatch native change event so all listeners fire
      el.dispatchEvent(new Event('change', { bubbles: true }));
      closeSmartMenus();
    });
    fragment.appendChild(b);
  });
  menu.appendChild(fragment);
  // Reset search filter
  if (search) {
    search.value = '';
    // Make all options visible again
    menu.querySelectorAll('.smart-option').forEach(b => {
      b.hidden = false;
      b.style.display = 'block';
    });
    const noRes = menu.querySelector('.smart-no-results');
    if (noRes) {
      noRes.hidden = true;
      noRes.style.display = 'none';
    }
  }
  syncSmartSelect(el);
}

function enhanceSelect(el) {
  if (!el || el._smart) return el;
  const wrap = document.createElement('div');
  wrap.className = 'smart-select';
  el.parentNode.insertBefore(wrap, el);
  wrap.appendChild(el);

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'smart-trigger';
  trigger.textContent = 'Choose an option';

  const menu = document.createElement('div');
  menu.className = 'smart-menu';

  const search = document.createElement('input');
  search.type = 'search';
  search.className = 'smart-search';
  search.placeholder = 'Search options…';
  search.autocomplete = 'off';
  // Prevent click on search from bubbling and closing the menu
  search.addEventListener('click', e => e.stopPropagation());

  const noResults = document.createElement('div');
  noResults.className = 'smart-no-results';
  noResults.textContent = 'No options found';
  noResults.hidden = true;
  noResults.style.display = 'none';

  menu.appendChild(search);
  menu.appendChild(noResults);
  wrap.appendChild(trigger);
  wrap.appendChild(menu);

  el._smart = wrap;
  el.classList.add('smart-native');

  const filterOptions = () => {
    const q = search.value.toLowerCase().trim();
    const queryWords = q.split(/\s+/).filter(Boolean);
    let visible = 0;

    // Find associated brand if this is a model select
    let brandText = '';
    const form = el.closest('form, .compare-card, .form-shell, main') || document;
    const brandSelect = form.querySelector('#brand, .brand');
    if (brandSelect && brandSelect !== el && brandSelect.value) {
      brandText = brandSelect.value.toLowerCase();
    }

    menu.querySelectorAll('.smart-option').forEach(b => {
      const optionText = b.textContent.toLowerCase();
      const combinedText = brandText ? `${brandText} ${optionText}` : optionText;
      const show = !queryWords.length || queryWords.every(word => combinedText.includes(word) || optionText.includes(word));
      b.hidden = !show;
      b.style.display = show ? 'block' : 'none';
      if (show) visible++;
    });
    noResults.hidden = visible > 0;
    noResults.style.display = visible > 0 ? 'none' : 'block';
  };

  // Toggle menu open/close
  trigger.addEventListener('click', e => {
    e.stopPropagation();
    if (el.disabled) return;
    document.querySelectorAll('.smart-select.open').forEach(x => {
      x.classList.remove('open');
      const pf = x.closest('.field');
      if (pf) pf.classList.remove('is-open');
    });
    wrap.classList.toggle('open');
    const parentField = wrap.closest('.field');
    if (wrap.classList.contains('open')) {
      if (parentField) parentField.classList.add('is-open');
      search.value = '';
      menu.querySelectorAll('.smart-option').forEach(b => {
        b.hidden = false;
        b.style.display = 'block';
      });
      noResults.hidden = true;
      noResults.style.display = 'none';
      search.focus();
    } else {
      if (parentField) parentField.classList.remove('is-open');
    }
  });

  // Live search filtering
  search.addEventListener('input', filterOptions);
  search.addEventListener('keyup', filterOptions);
  search.addEventListener('search', filterOptions);

  // Handle Enter and Escape in search box
  search.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      e.stopPropagation();
      const firstVisible = Array.from(menu.querySelectorAll('.smart-option')).find(b => b.style.display !== 'none' && !b.hidden);
      if (firstVisible) {
        el.value = firstVisible.dataset.value;
        el.dispatchEvent(new Event('change', { bubbles: true }));
        closeSmartMenus();
      }
    } else if (e.key === 'Escape') {
      closeSmartMenus();
    }
  });

  // Keep trigger label in sync when the underlying <select> changes
  el.addEventListener('change', () => syncSmartSelect(el));

  renderSmartOptions(el);
  return el;
}

function closeSmartMenus() {
  document.querySelectorAll('.smart-select.open').forEach(x => {
    x.classList.remove('open');
    const pf = x.closest('.field');
    if (pf) pf.classList.remove('is-open');
  });
}
document.addEventListener('click', closeSmartMenus);

/* ── Public helpers ── */

window.fillSelect = (el, vals, ph) => {
  el.innerHTML = '';
  const fragment = document.createDocumentFragment();
  if (ph) {
    const o = document.createElement('option');
    o.value = '';
    o.textContent = ph;
    fragment.appendChild(o);
  }
  (vals || []).forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = v;
    fragment.appendChild(o);
  });
  el.appendChild(fragment);
  el.value = '';
  if (!el._smart) {
    enhanceSelect(el);
  } else {
    renderSmartOptions(el);
  }
};

window.syncSmartSelect = syncSmartSelect;
window.setSmartOptions = (el, vals, ph) => fillSelect(el, vals, ph);

window.getBatteryCapacityForModel = (brand, model) => {
  const b = (brand || '').toLowerCase();
  const m = (model || '').toLowerCase();
  if (m.includes('sierra') || m.includes('curvv')) return 55.0;
  if (m.includes('nexon')) return 40.5;
  if (m.includes('punch')) return 35.0;
  if (m.includes('tiago') || m.includes('tigor')) return 24.0;
  if (m.includes('zs') || b.includes('mg')) return 50.3;
  if (m.includes('atto') || m.includes('seal') || b.includes('byd')) return 60.4;
  if (m.includes('ioniq') || m.includes('ev6')) return 72.6;
  if (m.includes('taycan') || m.includes('eqs') || m.includes('i7')) return 90.0;
  return 40.0;
};

window.showToast = m => {
  const t = document.querySelector('.toast');
  if (!t) return;
  t.textContent = m;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2600);
};

window.validateMileage = value => {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0 || n >= 30) {
    showToast('Mileage must be below 30 km/l.');
    return false;
  }
  return true;
};

window.loadAnalyticsDashboard = async () => {
  try {
    const data = await window.api('/api/analytics');
    
    const statsContainer = document.getElementById('analytics-stats');
    if (statsContainer && data.stats) {
      statsContainer.innerHTML = `
        <div class="surface info-card"><div class="eyebrow">DATASET RECORDS</div><h3 style="font-size:24px;margin-top:8px;">${data.stats.records.toLocaleString()}</h3></div>
        <div class="surface info-card"><div class="eyebrow">AVERAGE PRICE</div><h3 style="font-size:24px;margin-top:8px;">₹${(data.stats.avg_price).toFixed(2)} L</h3></div>
        <div class="surface info-card"><div class="eyebrow">MEDIAN PRICE</div><h3 style="font-size:24px;margin-top:8px;">₹${(data.stats.median_price).toFixed(2)} L</h3></div>
        <div class="surface info-card"><div class="eyebrow">MARKET RANGE</div><h3 style="font-size:24px;margin-top:8px;">₹${(data.stats.min_price).toFixed(2)} L - ₹${(data.stats.max_price).toFixed(2)} L</h3></div>
      `;
    }
    
    document.getElementById('analytics-charts').style.display = 'grid';

    const blue = '#3b82f6', teal = '#14b8a6', indigo = '#6366f1', rose = '#f43f5e', amber = '#f59e0b', slate = '#64748b';

    new Chart(document.getElementById('chart-age'), {
      type: 'line',
      data: {
        labels: data.price_vs_age.map(d => d.age + ' yrs'),
        datasets: [{ label: 'Average Price (₹ L)', data: data.price_vs_age.map(d => d.price), borderColor: blue, backgroundColor: blue + '33', fill: true, tension: 0.4 }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });

    new Chart(document.getElementById('chart-km'), {
      type: 'bar',
      data: {
        labels: data.price_vs_km.map(d => d.range),
        datasets: [{ label: 'Average Price (₹ L)', data: data.price_vs_km.map(d => d.price), backgroundColor: teal }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });

    new Chart(document.getElementById('chart-brand'), {
      type: 'bar',
      data: {
        labels: data.price_by_brand.map(d => d.brand),
        datasets: [{ label: 'Average Price (₹ L)', data: data.price_by_brand.map(d => d.price), backgroundColor: indigo }]
      },
      options: { responsive: true, indexAxis: 'y', plugins: { legend: { display: false } }, scales: { x: { beginAtZero: true } } }
    });

    new Chart(document.getElementById('chart-fuel'), {
      type: 'doughnut',
      data: {
        labels: data.price_by_fuel.map(d => d.fuel),
        datasets: [{ data: data.price_by_fuel.map(d => d.price), backgroundColor: [blue, rose, amber, teal, slate] }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    });

    new Chart(document.getElementById('chart-trans'), {
      type: 'bar',
      data: {
        labels: data.price_by_transmission.map(d => d.transmission),
        datasets: [{ label: 'Average Price (₹ L)', data: data.price_by_transmission.map(d => d.price), backgroundColor: slate }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
    });

    new Chart(document.getElementById('chart-year'), {
      type: 'line',
      data: {
        labels: data.price_trend_year.map(d => d.year),
        datasets: [{ label: 'Average Price (₹ L)', data: data.price_trend_year.map(d => d.price), borderColor: teal, fill: true, backgroundColor: teal + '33', tension: 0.3 }]
      },
      options: { responsive: true, plugins: { legend: { display: false } } }
    });

    const corrLabels = Object.keys(data.correlations);
    const corrValues = Object.values(data.correlations);
    new Chart(document.getElementById('chart-corr'), {
      type: 'bar',
      data: {
        labels: corrLabels,
        datasets: [{
          label: 'Correlation with Price',
          data: corrValues,
          backgroundColor: corrValues.map(v => v > 0 ? teal : rose)
        }]
      },
      options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { min: -1, max: 1 } } }
    });

  } catch (err) {
    const statsContainer = document.getElementById('analytics-stats');
    if (statsContainer) statsContainer.innerHTML = `<div class="surface empty" style="grid-column:1/-1;color:#ef4444;padding:28px;">Failed to load analytics: ${err.message}</div>`;
  }

  const rawPred = sessionStorage.getItem('carvalue:lastPrediction');
  const btnCheck = document.getElementById('btn-check-deal');
  const statusDiv = document.getElementById('deal-prediction-status');
  const resultArea = document.getElementById('deal-result-area');
  
  if (!btnCheck) return; // Not on analytics page
  
  if (!rawPred) {
    statusDiv.innerHTML = `<div style="color:var(--muted)">No recent prediction found. Go to the Predict page and calculate a car's value first.</div>`;
    btnCheck.disabled = true;
    return;
  }
  
  try {
    const r = JSON.parse(rawPred);
    const pred = Number(r.predicted_price_lakhs || 0);
    const brand = r.input?.Brand || "Car";
    const model = r.input?.Model || "";
    
    statusDiv.innerHTML = `<strong>Active Prediction:</strong> ${brand} ${model} (₹${pred.toFixed(2)} L)`;
    btnCheck.disabled = false;
    
    btnCheck.addEventListener('click', () => {
      const sellerPrice = Number(document.getElementById('seller-price').value);
      if (!sellerPrice || sellerPrice <= 0) {
        window.showToast("Please enter a valid asking price.");
        return;
      }
      
      const ratio = sellerPrice / pred;
      let classification = "Fair Deal";
      let color = "var(--blue)";
      let icon = "⚖️";
      let message = "This asking price is right around our estimated fair market value.";
      
      if (ratio < 0.95) {
        classification = "Good Deal";
        color = "var(--green)";
        icon = "✅";
        message = `This asking price is below our estimated fair value of ₹${pred.toFixed(2)} L.`;
      } else if (ratio > 1.05) {
        classification = "Overpriced";
        color = "#ef4444";
        icon = "⚠️";
        message = `This asking price is higher than our estimated fair value of ₹${pred.toFixed(2)} L.`;
      }
      
      resultArea.innerHTML = `
        <div style="text-align: center;">
          <div style="font-size: 40px; margin-bottom: 12px;">${icon}</div>
          <h3 style="color: ${color}; margin: 0 0 8px 0; font-size: 24px;">${classification}</h3>
          <p style="color: var(--ink); margin: 0 0 16px 0;">${message}</p>
          <div style="font-size: 13px; color: var(--subtle);">Seller asking: <strong>₹${sellerPrice.toFixed(2)} L</strong><br>AI predicted: <strong>₹${pred.toFixed(2)} L</strong></div>
        </div>
      `;
    });
  } catch (e) {
    statusDiv.innerHTML = `<div style="color:var(--muted)">Prediction data invalid. Please predict again.</div>`;
    btnCheck.disabled = true;
  }
};

