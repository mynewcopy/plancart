/* =====================================================
   PlanCart — app.js  (Telegram Mini App main script)
   ===================================================== */

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.colorScheme === 'dark') document.body.classList.add('tg-dark');
}

/* ---- Helpers ---- */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function toast(msg, type = '') {
  const el = document.createElement('div');
  el.className = 'toast' + (type ? ' ' + type : '');
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3000);
}

function formatPrice(price, currency = '₽') {
  if (!price || price <= 0) return 'Цена не указана';
  return price >= 1000
    ? price.toLocaleString('ru-RU', { maximumFractionDigits: 0 }) + ' ' + currency
    : Math.round(price) + ' ' + currency;
}

function priorityLabel(p) {
  return { 1: '💡 Идея', 2: '⭐ Желательно', 3: '🔥 Очень хочу' }[p] || '';
}

function categoryEmoji(cat) {
  const map = {
    'Электроника': '📱', 'Одежда': '👕', 'Обувь': '👟',
    'Дом и дача': '🏠', 'Книги': '📚', 'Спорт': '⚽',
    'Красота': '💄', 'Игры': '🎮', 'Хобби': '🎨', 'Другое': '📦'
  };
  return map[cat] || '📦';
}

/* ---- API ---- */
const API_BASE = '';

function getInitData() {
  if (tg?.initData) return tg.initData;
  // Dev fallback: use query param or header
  const params = new URLSearchParams(location.search);
  return params.get('initData') || '';
}

async function api(method, path, body = null) {
  const opts = {
    method,
    headers: {
      'X-Telegram-Init-Data': getInitData(),
      'Content-Type': 'application/json',
    },
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Ошибка запроса');
  return data;
}

async function uploadImage(file) {
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/upload', {
    method: 'POST',
    headers: { 'X-Telegram-Init-Data': getInitData() },
    body: fd,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'Ошибка загрузки');
  return data;
}

/* ---- State ---- */
let state = {
  user: null,
  items: [],
  stats: null,
  filterStatus: '',
  filterCategory: '',
  search: '',
  pendingPhotoPaths: [],   // saved paths from /api/upload
  editingItemId: null,
};

/* ---- Render items grid ---- */
function renderItems() {
  const grid = document.getElementById('items-grid');
  const loadingEl = document.getElementById('loading-state');
  const emptyEl = document.getElementById('empty-state');

  // Remove previous cards (keep loading + empty)
  $$('.item-card', grid).forEach(el => el.remove());
  loadingEl.style.display = 'none';

  let items = state.items;

  // Filter
  if (state.filterStatus) items = items.filter(i => i.status === state.filterStatus);
  if (state.filterCategory) items = items.filter(i => i.category === state.filterCategory);
  if (state.search) {
    const q = state.search.toLowerCase();
    items = items.filter(i =>
      (i.title || '').toLowerCase().includes(q) ||
      (i.description || '').toLowerCase().includes(q)
    );
  }

  if (items.length === 0) {
    emptyEl.style.display = '';
    return;
  }
  emptyEl.style.display = 'none';

  items.forEach(item => {
    const card = createItemCard(item);
    grid.appendChild(card);
  });
}

function createItemCard(item) {
  const div = document.createElement('div');
  div.className = 'item-card' + (item.status === 'bought' ? ' bought' : '');
  div.dataset.id = item.id;

  // Cover photo or placeholder
  if (item.cover_photo) {
    const img = document.createElement('img');
    img.className = 'item-card-cover';
    img.src = '/' + item.cover_photo;
    img.alt = item.title;
    img.loading = 'lazy';
    img.onerror = () => {
      const ph = document.createElement('div');
      ph.className = 'item-card-cover-placeholder';
      ph.textContent = categoryEmoji(item.category);
      img.replaceWith(ph);
    };
    div.appendChild(img);
  } else {
    const ph = document.createElement('div');
    ph.className = 'item-card-cover-placeholder';
    ph.textContent = categoryEmoji(item.category);
    div.appendChild(ph);
  }

  // Badges
  if (item.status === 'bought') {
    const b = document.createElement('span');
    b.className = 'card-badge badge-bought';
    b.textContent = '✅ Куплено';
    div.appendChild(b);
  } else if (item.is_reserved) {
    const b = document.createElement('span');
    b.className = 'card-badge badge-reserved';
    b.textContent = '🎁 Забронировано';
    div.appendChild(b);
  }

  if (item.priority === 3 && item.status !== 'bought') {
    const b = document.createElement('span');
    b.className = 'card-badge-top-right';
    b.textContent = '🔥';
    div.appendChild(b);
  }

  // Body
  const body = document.createElement('div');
  body.className = 'item-card-body';

  const title = document.createElement('div');
  title.className = 'item-card-title';
  title.textContent = item.title;
  body.appendChild(title);

  const price = document.createElement('div');
  if (item.price > 0) {
    price.className = 'item-card-price';
    price.textContent = formatPrice(item.price, item.currency);
  } else {
    price.className = 'item-card-price no-price';
    price.textContent = 'Цена не указана';
  }
  body.appendChild(price);

  const meta = document.createElement('div');
  meta.className = 'item-card-meta';

  const prioBadge = document.createElement('span');
  prioBadge.className = `priority-badge priority-${item.priority || 2}`;
  prioBadge.textContent = priorityLabel(item.priority || 2);
  meta.appendChild(prioBadge);

  body.appendChild(meta);
  div.appendChild(body);

  div.addEventListener('click', () => openItemDetail(item));
  return div;
}

/* ---- Item Detail Modal ---- */
function openItemDetail(item) {
  const overlay = document.getElementById('modal-view');
  const body = document.getElementById('modal-view-body');
  body.innerHTML = '';

  // Photos
  const photoWrap = document.createElement('div');
  photoWrap.className = 'item-detail-photos';
  photoWrap.style.position = 'relative';

  if (item.photos && item.photos.length > 0) {
    const track = document.createElement('div');
    track.className = 'item-detail-photos-track';
    item.photos.forEach(p => {
      const img = document.createElement('img');
      img.className = 'item-detail-photo';
      img.src = '/' + p.file_path;
      img.alt = '';
      track.appendChild(img);
    });
    photoWrap.appendChild(track);
  } else {
    const ph = document.createElement('div');
    ph.className = 'item-detail-no-photo';
    ph.textContent = categoryEmoji(item.category);
    photoWrap.appendChild(ph);
  }

  // Close btn overlay
  const closeRow = document.createElement('div');
  closeRow.className = 'item-detail-close-row';
  const closeBtn = document.createElement('button');
  closeBtn.className = 'item-detail-close-btn';
  closeBtn.textContent = '✕';
  closeBtn.onclick = () => closeModal('modal-view');
  closeRow.appendChild(closeBtn);
  photoWrap.appendChild(closeRow);

  body.appendChild(photoWrap);

  // Content
  const content = document.createElement('div');
  content.className = 'item-detail-content';

  const titleEl = document.createElement('h2');
  titleEl.className = 'item-detail-title';
  titleEl.textContent = item.title;
  content.appendChild(titleEl);

  const priceEl = document.createElement('div');
  if (item.price > 0) {
    priceEl.className = 'item-detail-price';
    priceEl.textContent = formatPrice(item.price, item.currency);
  } else {
    priceEl.className = 'item-detail-price';
    priceEl.style.fontSize = '14px';
    priceEl.style.color = 'var(--text3)';
    priceEl.textContent = 'Цена не указана';
  }
  content.appendChild(priceEl);

  // Badges
  const badges = document.createElement('div');
  badges.className = 'item-detail-badges';

  if (item.category) {
    const b = document.createElement('span');
    b.className = 'detail-badge badge-cat';
    b.textContent = categoryEmoji(item.category) + ' ' + item.category;
    badges.appendChild(b);
  }

  const pb = document.createElement('span');
  pb.className = `detail-badge badge-prio-${item.priority || 2}`;
  pb.textContent = priorityLabel(item.priority || 2);
  badges.appendChild(pb);

  if (item.status === 'bought') {
    const sb = document.createElement('span');
    sb.className = 'detail-badge';
    sb.style.background = 'rgba(52,199,89,0.15)';
    sb.style.color = 'var(--success)';
    sb.textContent = '✅ Куплено';
    badges.appendChild(sb);
  }

  content.appendChild(badges);

  if (item.description) {
    const desc = document.createElement('p');
    desc.className = 'item-detail-desc';
    desc.textContent = item.description;
    content.appendChild(desc);
  }

  if (item.target_date) {
    const dt = document.createElement('p');
    dt.className = 'item-detail-date';
    dt.textContent = '📅 Планирую купить: ' + new Date(item.target_date).toLocaleDateString('ru-RU', { year: 'numeric', month: 'long', day: 'numeric' });
    content.appendChild(dt);
  }

  if (item.is_reserved && item.reservation) {
    const r = item.reservation;
    const rbox = document.createElement('div');
    rbox.style.cssText = 'background:rgba(255,149,0,0.1);border:1.5px solid var(--warn);border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:13px;color:var(--warn);';
    const who = r.is_anonymous ? 'Анонимно' : r.by_name;
    rbox.textContent = `🎁 Этот подарок забронирован: ${who}`;
    if (r.comment) rbox.textContent += ` — "${r.comment}"`;
    content.appendChild(rbox);
  }

  // Actions
  const actions = document.createElement('div');
  actions.className = 'item-detail-actions';

  if (item.url) {
    const link = document.createElement('a');
    link.href = item.url;
    link.target = '_blank';
    link.rel = 'noopener';
    link.className = 'btn-primary';
    link.style.textDecoration = 'none';
    link.style.display = 'block';
    link.style.textAlign = 'center';
    link.textContent = '🛒 Перейти в магазин';
    actions.appendChild(link);
  }

  const row = document.createElement('div');
  row.className = 'row';
  row.style.display = 'flex';
  row.style.gap = '10px';

  const editBtn = document.createElement('button');
  editBtn.className = 'btn-secondary';
  editBtn.style.flex = '1';
  editBtn.textContent = '✏️ Изменить';
  editBtn.onclick = () => { closeModal('modal-view'); openItemForm(item); };
  row.appendChild(editBtn);

  const toggleBtn = document.createElement('button');
  toggleBtn.className = 'btn-secondary';
  toggleBtn.style.flex = '1';
  if (item.status === 'planned') {
    toggleBtn.textContent = '✅ Куплено';
    toggleBtn.onclick = async () => {
      await api('PATCH', `/api/items/${item.id}`, { status: 'bought' });
      toast('✅ Отмечено как куплено!', 'success');
      closeModal('modal-view');
      await loadItems();
    };
  } else {
    toggleBtn.textContent = '📋 В план';
    toggleBtn.onclick = async () => {
      await api('PATCH', `/api/items/${item.id}`, { status: 'planned' });
      toast('📋 Возвращено в план', 'success');
      closeModal('modal-view');
      await loadItems();
    };
  }
  row.appendChild(toggleBtn);

  actions.appendChild(row);

  const delBtn = document.createElement('button');
  delBtn.className = 'btn-danger-outline';
  delBtn.textContent = '🗑 Удалить';
  delBtn.onclick = async () => {
    if (!confirm('Удалить этот товар?')) return;
    await api('DELETE', `/api/items/${item.id}`);
    toast('🗑 Удалено', 'success');
    closeModal('modal-view');
    await loadItems();
  };
  actions.appendChild(delBtn);

  content.appendChild(actions);
  body.appendChild(content);

  overlay.style.display = 'flex';
  overlay.onclick = e => { if (e.target === overlay) closeModal('modal-view'); };
}

/* ---- Item Form Modal ---- */
function openItemForm(item = null) {
  state.editingItemId = item ? item.id : null;
  state.pendingPhotoPaths = item ? (item.photos || []).map(p => p.file_path) : [];

  document.getElementById('modal-item-title').textContent = item ? 'Редактировать' : 'Добавить товар';
  document.getElementById('item-id').value = item ? item.id : '';
  document.getElementById('item-url').value = item?.url || '';
  document.getElementById('item-title').value = item?.title || '';
  document.getElementById('item-price').value = item?.price > 0 ? item.price : '';
  document.getElementById('item-currency').value = item?.currency || state.user?.currency_pref || '₽';
  document.getElementById('item-category').value = item?.category || 'Другое';
  document.getElementById('item-priority').value = item?.priority || 2;
  document.getElementById('item-description').value = item?.description || '';
  document.getElementById('item-target-date').value = item?.target_date || '';
  document.getElementById('item-private').checked = !!item?.is_private;

  // Status toggle
  $$('.status-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.status === (item?.status || 'planned'));
  });

  renderPhotoThumbs();

  document.getElementById('modal-item').style.display = 'flex';
}

function renderPhotoThumbs() {
  const row = document.getElementById('photos-row');
  row.innerHTML = '';

  state.pendingPhotoPaths.forEach((path, idx) => {
    const thumb = document.createElement('div');
    thumb.className = 'photo-thumb';
    const img = document.createElement('img');
    img.src = '/' + path;
    img.alt = '';
    thumb.appendChild(img);

    if (idx === 0) {
      const coverLbl = document.createElement('span');
      coverLbl.className = 'photo-thumb-cover';
      coverLbl.textContent = 'Обложка';
      thumb.appendChild(coverLbl);
    }

    const rm = document.createElement('button');
    rm.type = 'button';
    rm.className = 'photo-thumb-remove';
    rm.textContent = '✕';
    rm.onclick = () => {
      state.pendingPhotoPaths.splice(idx, 1);
      renderPhotoThumbs();
    };
    thumb.appendChild(rm);
    row.appendChild(thumb);
  });

  const addBtn = document.createElement('button');
  addBtn.type = 'button';
  addBtn.className = 'photo-add-btn';
  addBtn.id = 'btn-add-photo';
  addBtn.innerHTML = '<span>+</span><small>Добавить</small>';
  addBtn.onclick = () => document.getElementById('file-input').click();
  row.appendChild(addBtn);
}

/* ---- Profile Modal ---- */
function openProfileModal() {
  const user = state.user;
  if (!user) return;

  // Profile card
  const card = document.getElementById('profile-card');
  const initials = ((user.first_name || '')[0] || '') + ((user.last_name || '')[0] || '');
  card.innerHTML = `
    <div class="profile-avatar">
      ${user.photo_url ? `<img src="${user.photo_url}" alt="">` : initials || '👤'}
    </div>
    <div class="profile-info">
      <h3>${[user.first_name, user.last_name].filter(Boolean).join(' ') || 'Пользователь'}</h3>
      <p>${user.username ? '@' + user.username : 'ID: ' + user.id}</p>
    </div>
  `;

  document.getElementById('profile-title').value = user.wishlist_title || '';
  document.getElementById('profile-desc').value = user.wishlist_description || '';
  document.getElementById('profile-currency').value = user.currency_pref || '₽';
  document.getElementById('profile-public').checked = !!user.is_public;

  const pubUrl = user.public_url || '';
  document.getElementById('public-url-input').value = pubUrl;
  document.getElementById('share-block').style.display = user.is_public ? '' : 'none';

  document.getElementById('modal-profile').style.display = 'flex';
}

/* ---- Data loading ---- */
async function loadUser() {
  const data = await api('GET', '/api/me');
  state.user = data.user;
}

async function loadItems() {
  document.getElementById('loading-state').style.display = '';
  $$('.item-card').forEach(e => e.remove());
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('stats-bar').style.display = 'none';

  const params = new URLSearchParams();
  if (state.filterStatus) params.set('status', state.filterStatus);
  if (state.filterCategory) params.set('category', state.filterCategory);
  if (state.search) params.set('search', state.search);

  const data = await api('GET', '/api/items?' + params.toString());
  state.items = data.items || [];

  updateStatsBar();
  renderItems();
}

function updateStatsBar() {
  const planned = state.items.filter(i => i.status === 'planned');
  const bought = state.items.filter(i => i.status === 'bought');
  const sum = planned.reduce((s, i) => s + (i.price || 0), 0);
  const currency = state.user?.currency_pref || '₽';

  document.getElementById('stat-count').textContent = planned.length;
  document.getElementById('stat-sum').textContent = formatPrice(sum, currency);
  document.getElementById('stat-bought').textContent = bought.length;
  document.getElementById('stats-bar').style.display = state.items.length > 0 ? '' : 'none';
}

/* ---- Parse URL ---- */
async function parseUrl() {
  const url = document.getElementById('item-url').value.trim();
  if (!url) return;

  document.getElementById('url-loading').style.display = '';
  try {
    const data = await api('POST', '/api/parse-link', { url });
    const meta = data.metadata || {};

    if (meta.title && !document.getElementById('item-title').value) {
      document.getElementById('item-title').value = meta.title;
    }
    if (meta.price && !document.getElementById('item-price').value) {
      document.getElementById('item-price').value = meta.price;
    }
    if (meta.description && !document.getElementById('item-description').value) {
      document.getElementById('item-description').value = meta.description?.slice(0, 500) || '';
    }
    if (meta.image_url && state.pendingPhotoPaths.length === 0) {
      // Try to download and upload the OG image
      try {
        const imgResp = await fetch('/api/parse-link', {
          method: 'POST',
          headers: { 'X-Telegram-Init-Data': getInitData(), 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: meta.image_url })
        });
        // We can't directly upload from URL in this flow — just notify
        toast('💡 Найдено изображение, загрузи его вручную', '');
      } catch {}
    }
    if (meta.title) toast('✅ Данные загружены!', 'success');
    else toast('⚠️ Не удалось распознать товар по ссылке');
  } catch (e) {
    toast('❌ Ошибка: ' + e.message, 'error');
  } finally {
    document.getElementById('url-loading').style.display = 'none';
  }
}

/* ---- Save item ---- */
async function saveItem(e) {
  e.preventDefault();

  const title = document.getElementById('item-title').value.trim();
  if (!title) { toast('❌ Введи название товара', 'error'); return; }

  const statusBtn = $('.status-btn.active');
  const status = statusBtn ? statusBtn.dataset.status : 'planned';

  const payload = {
    title,
    price: parseFloat(document.getElementById('item-price').value) || 0,
    currency: document.getElementById('item-currency').value || '₽',
    url: document.getElementById('item-url').value.trim() || null,
    description: document.getElementById('item-description').value.trim() || null,
    category: document.getElementById('item-category').value || 'Другое',
    priority: parseInt(document.getElementById('item-priority').value) || 2,
    status,
    is_private: document.getElementById('item-private').checked,
    target_date: document.getElementById('item-target-date').value || null,
    photos: state.pendingPhotoPaths,
  };

  const btn = document.getElementById('btn-save-item');
  btn.disabled = true;
  btn.textContent = '⏳ Сохранение...';

  try {
    if (state.editingItemId) {
      await api('PUT', `/api/items/${state.editingItemId}`, payload);
      toast('✅ Изменения сохранены', 'success');
    } else {
      await api('POST', '/api/items', payload);
      toast('✅ Товар добавлен в список!', 'success');
      if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    }
    closeModal('modal-item');
    await loadItems();
  } catch (err) {
    toast('❌ ' + err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '💾 Сохранить';
  }
}

/* ---- Save profile ---- */
async function saveProfile() {
  const payload = {
    wishlist_title: document.getElementById('profile-title').value.trim(),
    wishlist_description: document.getElementById('profile-desc').value.trim(),
    currency_pref: document.getElementById('profile-currency').value,
    is_public: document.getElementById('profile-public').checked,
  };

  try {
    const data = await api('POST', '/api/me', payload);
    state.user = data.user;
    toast('✅ Настройки сохранены', 'success');
    closeModal('modal-profile');
  } catch (e) {
    toast('❌ ' + e.message, 'error');
  }
}

/* ---- Share ---- */
async function shareWishlist() {
  if (!state.user) return;
  const url = state.user.public_url || '';
  const text = `🎁 Смотри мой вишлист покупок: ${url}`;

  if (tg?.switchInlineQuery) {
    tg.switchInlineQuery(text);
  } else if (navigator.share) {
    try { await navigator.share({ title: 'Мой вишлист PlanCart', url }); } catch {}
  } else {
    await navigator.clipboard.writeText(url);
    toast('📋 Ссылка скопирована!', 'success');
  }
}

/* ---- Modal helpers ---- */
function closeModal(id) {
  document.getElementById(id).style.display = 'none';
}

/* ---- Init ---- */
async function init() {
  try {
    await loadUser();
    await loadItems();
  } catch (e) {
    console.error('Init error:', e);
    toast('❌ Ошибка загрузки. Попробуй открыть через Telegram.', 'error');
  }
}

/* ---- Event listeners ---- */
document.addEventListener('DOMContentLoaded', () => {
  init();

  // FAB
  document.getElementById('fab-add').addEventListener('click', () => openItemForm());

  // Header buttons
  document.getElementById('btn-search').addEventListener('click', () => {
    const bar = document.getElementById('search-bar');
    bar.style.display = bar.style.display === 'none' ? '' : 'none';
    if (bar.style.display !== 'none') document.getElementById('search-input').focus();
  });

  document.getElementById('btn-search-close').addEventListener('click', () => {
    document.getElementById('search-bar').style.display = 'none';
    document.getElementById('search-input').value = '';
    state.search = '';
    renderItems();
  });

  let searchTimer;
  document.getElementById('search-input').addEventListener('input', e => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => { state.search = e.target.value; renderItems(); }, 300);
  });

  document.getElementById('btn-share').addEventListener('click', shareWishlist);
  document.getElementById('btn-profile').addEventListener('click', openProfileModal);

  // Filter tabs
  document.getElementById('filter-tabs').addEventListener('click', e => {
    const btn = e.target.closest('.tab');
    if (!btn) return;
    $$('.tab').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    state.filterStatus = btn.dataset.status;
    renderItems();
  });

  // Category chips
  document.getElementById('category-chips').addEventListener('click', e => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    $$('.chip').forEach(c => c.classList.remove('active'));
    chip.classList.add('active');
    state.filterCategory = chip.dataset.cat;
    renderItems();
  });

  // Item form
  document.getElementById('btn-item-close').addEventListener('click', () => closeModal('modal-item'));
  document.getElementById('modal-item').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-item')) closeModal('modal-item');
  });

  document.getElementById('btn-parse-url').addEventListener('click', parseUrl);

  document.getElementById('item-form').addEventListener('submit', saveItem);

  // Status buttons
  document.getElementById('status-toggle').addEventListener('click', e => {
    const btn = e.target.closest('.status-btn');
    if (!btn) return;
    $$('.status-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });

  // File upload
  document.getElementById('file-input').addEventListener('change', async e => {
    const files = [...e.target.files];
    if (!files.length) return;

    for (const file of files.slice(0, 10)) {
      if (file.size > 10 * 1024 * 1024) { toast('❌ Файл слишком большой (> 10 МБ)', 'error'); continue; }
      try {
        const result = await uploadImage(file);
        state.pendingPhotoPaths.push(result.path);
        toast('📸 Фото добавлено', 'success');
      } catch (err) {
        toast('❌ ' + err.message, 'error');
      }
    }
    renderPhotoThumbs();
    e.target.value = '';
  });

  // Profile modal
  document.getElementById('btn-profile-close').addEventListener('click', () => closeModal('modal-profile'));
  document.getElementById('modal-profile').addEventListener('click', e => {
    if (e.target === document.getElementById('modal-profile')) closeModal('modal-profile');
  });
  document.getElementById('btn-save-profile').addEventListener('click', saveProfile);

  document.getElementById('profile-public').addEventListener('change', e => {
    document.getElementById('share-block').style.display = e.target.checked ? '' : 'none';
  });

  document.getElementById('btn-copy-url').addEventListener('click', async () => {
    const url = document.getElementById('public-url-input').value;
    await navigator.clipboard.writeText(url);
    toast('📋 Ссылка скопирована!', 'success');
  });

  document.getElementById('btn-share-url').addEventListener('click', async () => {
    const url = document.getElementById('public-url-input').value;
    if (tg?.switchInlineQuery) tg.switchInlineQuery('Мой вишлист: ' + url);
    else if (navigator.share) await navigator.share({ url });
    else { await navigator.clipboard.writeText(url); toast('📋 Скопировано!', 'success'); }
  });

  document.getElementById('btn-regen-token').addEventListener('click', async () => {
    if (!confirm('Создать новую ссылку? Старая перестанет работать!')) return;
    try {
      const data = await api('POST', '/api/me', { regenerate_token: true });
      state.user = data.user;
      document.getElementById('public-url-input').value = data.user.public_url;
      toast('🔄 Новая ссылка создана', 'success');
    } catch (e) {
      toast('❌ ' + e.message, 'error');
    }
  });

  // Telegram back button
  if (tg?.BackButton) {
    tg.BackButton.onClick(() => {
      const modals = $$('.modal-overlay').filter(m => m.style.display !== 'none');
      if (modals.length > 0) {
        modals[modals.length - 1].style.display = 'none';
      } else {
        tg.close();
      }
    });
  }
});
