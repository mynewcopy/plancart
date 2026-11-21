/* =====================================================
   PlanCart — public.js  (public wishlist page)
   ===================================================== */

const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast' + (type ? ' ' + type : '');
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3100);
}

function formatPrice(price, currency = '₽') {
  if (!price || price <= 0) return null;
  return price >= 1000
    ? price.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ' + currency
    : Math.round(price) + ' ' + currency;
}

function categoryEmoji(cat) {
  const map = { 'Электроника': '📱', 'Одежда': '👕', 'Обувь': '👟', 'Дом и дача': '🏠', 'Книги': '📚', 'Спорт': '⚽', 'Красота': '💄', 'Игры': '🎮', 'Хобби': '🎨', 'Другое': '📦' };
  return map[cat] || '📦';
}

// Extract token from URL path /w/:token
const token = location.pathname.split('/').filter(Boolean).pop() || '';
let ownerData = null;
let allItems = [];
let activeCategory = '';

/* ---- Fetch public data ---- */
async function loadWishlist() {
  try {
    const res = await fetch(`/api/public/${token}`);
    if (res.status === 404) { showError('Вишлист не найден или ссылка устарела'); return; }
    if (res.status === 403) { showError('Этот вишлист закрыт владельцем'); return; }

    const data = await res.json();
    ownerData = data.owner;
    allItems = data.items || [];

    renderHero();
    renderGrid(allItems);
    document.getElementById('pub-filters').style.display = 'flex';
  } catch (e) {
    showError('Ошибка загрузки. Попробуй обновить страницу.');
  }
}

function showError(msg) {
  document.getElementById('hero-content').innerHTML = `<p style="font-size:16px;opacity:0.9;">⚠️ ${msg}</p>`;
  document.getElementById('pub-grid').innerHTML = '';
}

function renderHero() {
  const o = ownerData;
  const name = [o.first_name, o.last_name].filter(Boolean).join(' ') || 'Пользователь';
  const initials = ((o.first_name || '')[0] || '') + ((o.last_name || '')[0] || '');
  const totalSum = allItems.reduce((s, i) => s + (i.price || 0), 0);
  const currency = o.currency_pref || '₽';
  const reserved = allItems.filter(i => i.is_reserved).length;

  document.getElementById('hero-content').innerHTML = `
    <div class="hero-avatar">
      ${o.photo_url ? `<img src="${o.photo_url}" alt="">` : (initials || '👤')}
    </div>
    <h1>${escHtml(o.wishlist_title || `Вишлист ${name}`)}</h1>
    <p>${escHtml(o.wishlist_description || '')}</p>
    <div class="hero-stats">
      <div>
        <span class="hero-stat-num">${allItems.length}</span>
        <span class="hero-stat-lbl">желаний</span>
      </div>
      <div>
        <span class="hero-stat-num">${formatPrice(totalSum, currency) || '—'}</span>
        <span class="hero-stat-lbl">на сумму</span>
      </div>
      <div>
        <span class="hero-stat-num">${reserved}</span>
        <span class="hero-stat-lbl">забронировано</span>
      </div>
    </div>
  `;

  // Update page title
  document.title = (o.wishlist_title || `Вишлист ${name}`) + ' — PlanCart';
}

function escHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderGrid(items) {
  const grid = document.getElementById('pub-grid');
  grid.innerHTML = '';

  const filtered = activeCategory ? items.filter(i => i.category === activeCategory) : items;

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="pub-empty">
        <div class="pub-empty-icon">🛍️</div>
        <h3>Список пуст</h3>
        <p>Пока здесь нет желаний в этой категории</p>
      </div>`;
    return;
  }

  filtered.forEach(item => {
    const card = createCard(item);
    grid.appendChild(card);
  });
}

function createCard(item) {
  const div = document.createElement('div');
  div.className = 'pub-card' + (item.is_reserved ? ' reserved' : '');

  if (item.cover_photo) {
    const img = document.createElement('img');
    img.className = 'pub-card-img';
    img.src = '/' + item.cover_photo;
    img.alt = item.title;
    img.loading = 'lazy';
    img.onerror = () => {
      const em = document.createElement('div');
      em.className = 'pub-card-emoji';
      em.textContent = categoryEmoji(item.category);
      img.replaceWith(em);
    };
    div.appendChild(img);
  } else {
    const em = document.createElement('div');
    em.className = 'pub-card-emoji';
    em.textContent = categoryEmoji(item.category);
    div.appendChild(em);
  }

  if (item.is_reserved) {
    const b = document.createElement('span');
    b.className = 'pub-card-badge badge-reserved-pub';
    b.textContent = '🎁 Забронировано';
    div.appendChild(b);
  }

  if (item.priority === 3 && !item.is_reserved) {
    const b = document.createElement('span');
    b.className = 'badge-prio3';
    b.textContent = '🔥 Топ';
    div.appendChild(b);
  }

  const body = document.createElement('div');
  body.className = 'pub-card-body';

  const t = document.createElement('div');
  t.className = 'pub-card-title';
  t.textContent = item.title;
  body.appendChild(t);

  const priceStr = formatPrice(item.price, item.currency || ownerData?.currency_pref || '₽');
  const p = document.createElement('div');
  p.className = priceStr ? 'pub-card-price' : 'pub-card-price no-price';
  p.textContent = priceStr || 'Цена не указана';
  body.appendChild(p);

  div.appendChild(body);
  div.addEventListener('click', () => openDetail(item));
  return div;
}

/* ---- Item Detail ---- */
function openDetail(item) {
  const overlay = document.getElementById('modal-detail');
  const body = document.getElementById('modal-detail-body');
  body.innerHTML = '';

  // Photos
  const photoWrap = document.createElement('div');
  photoWrap.style.position = 'relative';

  if (item.photos && item.photos.length > 0) {
    const track = document.createElement('div');
    track.className = 'detail-photos-track';
    item.photos.forEach(p => {
      const img = document.createElement('img');
      img.className = 'detail-photo';
      img.src = '/' + p.file_path;
      img.alt = '';
      track.appendChild(img);
    });
    photoWrap.appendChild(track);
  } else {
    const ph = document.createElement('div');
    ph.className = 'detail-no-photo';
    ph.textContent = categoryEmoji(item.category);
    photoWrap.appendChild(ph);
  }

  // Close btn
  const closeBtn = document.createElement('button');
  closeBtn.className = 'item-detail-close-btn';
  closeBtn.style.cssText = 'position:absolute;top:10px;right:10px;z-index:10;width:32px;height:32px;border-radius:50%;background:rgba(0,0,0,0.45);border:none;color:#fff;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(4px);';
  closeBtn.textContent = '✕';
  closeBtn.onclick = () => { overlay.style.display = 'none'; };
  photoWrap.appendChild(closeBtn);
  body.appendChild(photoWrap);

  const content = document.createElement('div');
  content.className = 'detail-content';

  const titleEl = document.createElement('h2');
  titleEl.className = 'detail-title';
  titleEl.textContent = item.title;
  content.appendChild(titleEl);

  const priceStr = formatPrice(item.price, item.currency || ownerData?.currency_pref || '₽');
  if (priceStr) {
    const priceEl = document.createElement('div');
    priceEl.className = 'detail-price';
    priceEl.textContent = priceStr;
    content.appendChild(priceEl);
  }

  const badges = document.createElement('div');
  badges.className = 'detail-badges';
  if (item.category) {
    const b = document.createElement('span');
    b.className = 'detail-badge badge-cat';
    b.textContent = categoryEmoji(item.category) + ' ' + item.category;
    badges.appendChild(b);
  }
  const pMap = { 1: ['badge-p1', '💡 Идея'], 2: ['badge-p2', '⭐ Желательно'], 3: ['badge-p3', '🔥 Очень хочу'] };
  if (pMap[item.priority]) {
    const pb = document.createElement('span');
    pb.className = 'detail-badge ' + pMap[item.priority][0];
    pb.textContent = pMap[item.priority][1];
    badges.appendChild(pb);
  }
  content.appendChild(badges);

  if (item.description) {
    const desc = document.createElement('p');
    desc.className = 'detail-desc';
    desc.textContent = item.description;
    content.appendChild(desc);
  }

  if (item.is_reserved && item.reservation) {
    const r = item.reservation;
    const rbox = document.createElement('div');
    rbox.className = 'detail-reserved-box';
    const who = r.is_anonymous ? 'Анонимно' : r.by_name;
    rbox.innerHTML = `🎁 <strong>Забронировано:</strong> ${escHtml(who)}` + (r.comment ? ` — <em>"${escHtml(r.comment)}"</em>` : '');
    content.appendChild(rbox);
  }

  if (item.url) {
    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.className = 'detail-url-btn';
    link.textContent = '🛒 Перейти в магазин';
    content.appendChild(link);
  }

  // Reserve section
  if (!item.is_reserved) {
    const reserveTitle = document.createElement('h3');
    reserveTitle.style.cssText = 'font-size:16px;font-weight:700;margin-bottom:12px;color:var(--text);';
    reserveTitle.textContent = '🎁 Забронировать подарок';
    content.appendChild(reserveTitle);

    const hintEl = document.createElement('p');
    hintEl.style.cssText = 'font-size:13px;color:var(--text2);margin-bottom:12px;line-height:1.4;';
    hintEl.textContent = 'Забронируй этот подарок, чтобы другие знали, что ты уже занялся им!';
    content.appendChild(hintEl);

    const form = document.createElement('div');
    form.className = 'reserve-form';

    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.placeholder = 'Твоё имя';
    nameInput.maxLength = 80;
    form.appendChild(nameInput);

    const commentInput = document.createElement('textarea');
    commentInput.placeholder = 'Комментарий (необязательно)';
    commentInput.rows = 2;
    commentInput.maxLength = 300;
    form.appendChild(commentInput);

    const anonRow = document.createElement('div');
    anonRow.className = 'reserve-toggle';
    anonRow.innerHTML = `
      <span>🕵️ Анонимно</span>
      <label style="display:flex;align-items:center;gap:0;">
        <input type="checkbox" id="anon-check" class="toggle-input">
        <span class="toggle-slider"></span>
      </label>
    `;
    form.appendChild(anonRow);

    const reserveBtn = document.createElement('button');
    reserveBtn.className = 'btn-reserve';
    reserveBtn.textContent = '🎁 Забронировать';
    reserveBtn.onclick = async () => {
      const name = nameInput.value.trim() || 'Друг';
      const comment = commentInput.value.trim();
      const isAnon = document.getElementById('anon-check')?.checked || false;

      reserveBtn.disabled = true;
      reserveBtn.textContent = '⏳ Бронируем...';
      try {
        const res = await fetch(`/api/public/${token}/reserve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ item_id: item.id, name, comment, is_anonymous: isAnon })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Ошибка');
        toast('🎉 Подарок успешно забронирован!', 'success');
        item.is_reserved = true;
        item.reservation = data.reservation;
        overlay.style.display = 'none';
        // Update item in grid
        const idx = allItems.findIndex(i => i.id === item.id);
        if (idx !== -1) allItems[idx] = item;
        renderGrid(allItems);
      } catch (e) {
        toast('❌ ' + e.message, 'error');
        reserveBtn.disabled = false;
        reserveBtn.textContent = '🎁 Забронировать';
      }
    };
    form.appendChild(reserveBtn);
    content.appendChild(form);
  }

  body.appendChild(content);

  overlay.style.display = 'flex';
  overlay.onclick = e => { if (e.target === overlay) overlay.style.display = 'none'; };
}

/* ---- Category filter ---- */
document.getElementById('pub-filters').addEventListener('click', e => {
  const chip = e.target.closest('.pub-chip');
  if (!chip) return;
  $$('.pub-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  activeCategory = chip.dataset.cat;
  renderGrid(allItems);
});

/* ---- Boot ---- */
loadWishlist();
