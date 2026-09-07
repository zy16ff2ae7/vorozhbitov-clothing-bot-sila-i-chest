(() => {
  "use strict";

  const FALLBACK_CATALOG = {
    brand: { name: "ВОРОЖБИТОВ", descriptor: "городская форма / лимитированные дропы", drop: "DROP 001" },
    channel_url: "https://t.me/+XufFz8GGR0o3Njky",
    categories: [
      { id: "drop", name: "Дроп 001" },
      { id: "hoodie", name: "Худи" },
      { id: "tee", name: "Футболки" },
      { id: "bottom", name: "Низ" },
      { id: "access", name: "Аксессуары" }
    ],
    products: [
      { id: "tee-sila-i-chest-001", category: "drop", name: "СИЛА И ЧЕСТЬ / TEE", price: "4 900 ₽", sizes: ["S", "M", "L", "XL", "XXL"], description: "Чёрная футболка с уставной надписью «СИЛА И ЧЕСТЬ» на груди и мечом по позвоночнику. Первый тираж — один раз и без повторов.", image: "assets/img/front-night.jpg", images: ["assets/img/front-night.jpg", "assets/img/back-boxing.jpg", "assets/img/flatlay.jpg", "assets/img/crew.jpg", "assets/img/gym.jpg"], badge: "DROP 001", material: "100% хлопок · 240 г/м²", fit: "Прямой крой", details: ["Принт спереди: «СИЛА И ЧЕСТЬ», уставной шрифт", "Принт сзади: меч по позвоночнику, монограмма ВВ у ворота", "Плотная шелкография, не трескается", "Усиленная горловина"], stock_label: "Первый тираж", active: true },
      {"id": "tag-sila-i-chest-001", "category": "drop", "name": "СИЛА И ЧЕСТЬ / ЖЕТОН", "price": "1 900 ₽", "sizes": ["ONE SIZE"], "description": "Армейский жетон из нержавеющей стали с лазерной гравировкой. Лицевая сторона — монограмма ВВ с мечом, оборот — «СИЛА И ЧЕСТЬ» и личный номер тиража. Каждый жетон уникален: номер не повторяется.", "badge": "DROP 001 · NEW", "fit": "Нумерованный", "stock_label": "Тираж 100 шт.", "material": "Нержавеющая сталь · лазерная гравировка", "details": ["Сталь AISI 304, 50×29 мм, 2 мм", "Лазерная гравировка с двух сторон", "Личный номер № 00001–00100", "Шариковая цепочка 60 см в комплекте", "Фирменный зип-пакет"], "image": "assets/img/tag-front.jpg", "images": ["assets/img/tag-front.jpg", "assets/img/tag-back.jpg", "assets/img/tag-front-studio.jpg", "assets/img/bag-desk.jpg"], "real_photos": true, "personalization": {"label": "НОМЕР ЖЕТОНА", "hint": "Свободные номера подтвердит менеджер. Хочешь конкретный — напиши его здесь.", "placeholder": "например, 00063", "pattern": "^[0-9]{1,5}$", "optional": true}},
      {"id": "set-sila-i-chest-001", "category": "drop", "name": "СИЛА И ЧЕСТЬ / НАБОР", "price": "6 300 ₽", "compare_price": "6 800 ₽", "sizes": ["S", "M", "L", "XL", "XXL"], "description": "Футболка «СИЛА И ЧЕСТЬ» и нумерованный стальной жетон в одном пакете. Размер — для футболки, номер жетона подберёт менеджер или укажи желаемый.", "badge": "DROP 001 · SET", "fit": "Футболка + жетон", "stock_label": "Пока есть номера", "material": "Хлопок 240 г/м² + сталь", "details": ["Футболка + жетон с номером", "Выгода 500 ₽ против покупки по отдельности", "Фирменный зип-пакет «ПУТЬ, ДОСТОЙНЫЙ ВОИНА»"], "image": "assets/img/bag-desk.jpg", "images": ["assets/img/bag-desk.jpg", "assets/img/front-night.jpg", "assets/img/tag-front.jpg", "assets/img/tag-back.jpg"], "real_photos": true, "personalization": {"label": "НОМЕР ЖЕТОНА", "hint": "Необязательно. Свободные номера подтвердит менеджер.", "placeholder": "например, 00063", "pattern": "^[0-9]{1,5}$", "optional": true}},
      { id: "drop-tee-001", category: "drop", name: "CORE TEE / 001", price: "4 900 ₽", sizes: ["S", "M", "L", "XL"], description: "Плотный хлопок, свободный крой, минимальный сигнал на груди. Первый тираж — один раз и без повторов.", image: "assets/img/base-tee.jpg", badge: "DROP 001", material: "100% хлопок · 240 г/м²", fit: "Свободный крой", details: ["Плотный хлопок", "Усиленная горловина", "Бирка-сигнал внутри"], stock_label: "Осталось мало", active: true },
      { id: "drop-hoodie-001", category: "drop", name: "CORE HOODIE / 001", price: "9 900 ₽", sizes: ["M", "L", "XL"], description: "Тяжёлое полотно, объёмный силуэт, двойная строчка. Увидел — забирай: партия ограничена.", image: "assets/img/front-night.jpg", badge: "LIMITED", material: "100% хлопок · 400 г/м²", fit: "Объемный крой", details: ["Футер 3-нитка", "Капюшон с двойной строчкой", "Металлические наконечники"], stock_label: "Последний тираж", active: true },
      { id: "hoodie-heavy-002", category: "hoodie", name: "HEAVY HOODIE / 002", price: "10 500 ₽", sizes: ["S", "M", "L", "XL"], description: "400 г/м². Держит форму и темп города. Никакой лишней графики — только посадка и вес.", image: "assets/img/heavy-hoodie.jpg", badge: "CORE", material: "100% хлопок · 400 г/м²", fit: "Свободный крой", details: ["Мягкий начес", "Плотные манжеты", "Карман-кенгуру"], stock_label: "В наличии", active: true },
      { id: "tee-basic-002", category: "tee", name: "EVERYDAY TEE / 002", price: "3 900 ₽", sizes: ["S", "M", "L", "XL"], description: "База на каждый день: плотная ткань, спокойная форма, вещь, которую не хочется снимать.", image: "assets/img/base-tee.jpg", badge: "EVERYDAY", material: "100% хлопок · 240 г/м²", fit: "Boxy fit", details: ["Гладкая фактура", "Плотная горловина", "Стирается без сюрпризов"], stock_label: "В наличии", active: true },
      { id: "cargo-city-001", category: "bottom", name: "CITY CARGO / 001", price: "8 500 ₽", sizes: ["S", "M", "L"], description: "Свободные карго с регулируемой посадкой и усиленными карманами. Город не бережёт — эти выдержат.", image: "assets/img/city-cargo.jpg", badge: "UTILITY", material: "Плотный хлопок · ripstop", fit: "Relaxed fit", details: ["6 функциональных карманов", "Регулировка низа", "Усиленные швы"], stock_label: "Мало размеров", active: true },
      { id: "cap-logo-001", category: "access", name: "SIGNAL CAP / 001", price: "3 200 ₽", sizes: ["ONE SIZE"], description: "Плотная шестиклинка с маленькой красной меткой. Никаких громких логотипов — свой считывает.", image: "assets/img/logo-cap.jpg", badge: "SIGNAL", material: "100% хлопок", fit: "Регулируемый размер", details: ["Металлическая застежка", "Вышитая метка", "Внутренняя лента"], stock_label: "В наличии", active: true }
    ]
  };

  const ICONS = {
    bookmark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4.5A2.5 2.5 0 0 1 8.5 2h7A2.5 2.5 0 0 1 18 4.5V22l-6-3.8L6 22V4.5Z"/></svg>',
    bag: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 8h14l1 13H4L5 8Z"/><path d="M8.5 9V6a3.5 3.5 0 0 1 7 0v3"/></svg>',
    sliders: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/><path d="M8 4v4M15 10v4M10 16v4"/></svg>',
    search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 5 5"/></svg>',
    share: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="2.5"/><circle cx="6" cy="12" r="2.5"/><circle cx="18" cy="19" r="2.5"/><path d="m8.2 10.8 7.5-4.3M8.2 13.2l7.5 4.3"/></svg>',
    home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 10.8 9-7.3 9 7.3V21H3V10.8Z"/><path d="M9 21v-6h6v6"/></svg>',
    grid: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>',
    eye: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.4-6 9.5-6 9.5 6 9.5 6-3.4 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.6"/></svg>'
  };

  const state = {
    data: FALLBACK_CATALOG,
    category: "all",
    search: "",
    stock: "all",
    cart: loadJSON("vorozhbitov_cart", []),
    saved: loadJSON("vorozhbitov_saved", []),
    currentProduct: null,
    selectedSize: null,
    galleryIndex: 0,
    toastTimer: null,
    loadedFromApi: false,
    manifest: {},
    note: "",
    submitting: false
  };

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

  function loadJSON(key, fallback) {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || "null");
      return parsed === null ? fallback : parsed;
    } catch (_) { return fallback; }
  }

  function saveJSON(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (_) { /* private mode */ }
  }

  function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>'"]/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  }

  function iconize() {
    $$('[data-icon]').forEach(node => { node.innerHTML = ICONS[node.dataset.icon] || ""; });
  }

  function imageFor(product) {
    return String(product.image || product.image_url || "assets/img/base-tee.jpg");
  }

  // manifest.json (tools/optimize_images.py) → srcset WebP/JPEG + LQIP-плейсхолдер.
  function manifestEntry(src) {
    const key = String(src || "").replace(/^.*\//, "").replace(/\.(jpe?g|png|webp)$/i, "");
    return state.manifest[key] || null;
  }

  function pictureFor(src, alt, sizes, opts = {}) {
    const entry = manifestEntry(src);
    const cls = `${opts.className || ""} lqip`.trim();
    const eager = opts.eager ? 'fetchpriority="high"' : 'loading="lazy" decoding="async"';
    if (!entry) return `<img class="${cls}" src="${escapeHTML(src)}" alt="${escapeHTML(alt)}" ${eager} onload="this.classList.add('loaded')">`;
    const set = list => list.map(([w, url]) => `${url} ${w}w`).join(", ");
    const style = entry.lqip ? ` style="background-image:url(${entry.lqip})"` : "";
    return `<picture><source type="image/webp" srcset="${set(entry.webp)}" sizes="${sizes}"><img class="${cls}" src="${escapeHTML(entry.src)}" srcset="${set(entry.jpg)}" sizes="${sizes}" width="${entry.width}" height="${entry.height}" alt="${escapeHTML(alt)}" ${eager}${style} onload="this.classList.add('loaded')"></picture>`;
  }

  function markLoadedImages(root = document) {
    $$("img.lqip", root).forEach(img => { if (img.complete && img.naturalWidth > 0) img.classList.add("loaded"); });
  }

  function galleryFor(product) {
    const list = Array.isArray(product.images) && product.images.length ? product.images : [imageFor(product)];
    return list.map(String).filter((src, index, all) => src && all.indexOf(src) === index);
  }

  const GALLERY_LABELS = ["ПЕРЕД", "СПИНА", "ТОВАР", "LOOK 01", "LOOK 02", "LOOK 03", "LOOK 04", "LOOK 05", "LOOK 06", "LOOK 07"];
  const GALLERY_LABELS_REAL = ["ЛИЦЕВАЯ · РЕАЛЬНОЕ ФОТО", "ОБОРОТ · № ТИРАЖА", "СТУДИЯ", "ПАКЕТ"];

  function showGallerySlide(index) {
    const product = state.currentProduct;
    if (!product) return;
    const slides = galleryFor(product);
    state.galleryIndex = (index + slides.length) % slides.length;
    const img = $("#sheetImage");
    img.classList.add("swapping");
    setTimeout(() => {
      const entry = manifestEntry(slides[state.galleryIndex]);
      if (entry) { img.srcset = entry.jpg.map(([w, url]) => `${url} ${w}w`).join(", "); img.sizes = "(max-width: 680px) 100vw, 50vw"; img.src = entry.src; }
      else { img.removeAttribute("srcset"); img.src = slides[state.galleryIndex]; }
      img.classList.remove("swapping");
    }, 120);
    $("#galleryDots").innerHTML = slides.map((_, i) => `<span class="${i === state.galleryIndex ? "active" : ""}"></span>`).join("");
    const multi = slides.length > 1;
    $("#galleryPrev").classList.toggle("hidden", !multi);
    $("#galleryNext").classList.toggle("hidden", !multi);
    let label = $(".gallery-label", $(".sheet-image"));
    if (!label) { label = document.createElement("span"); label.className = "gallery-label"; $(".sheet-image").appendChild(label); }
    const labels = product.real_photos ? GALLERY_LABELS_REAL : GALLERY_LABELS;
    label.textContent = multi ? (labels[state.galleryIndex] || `${state.galleryIndex + 1} / ${slides.length}`) : "";
  }

  function productById(id) {
    return state.data.products.find(product => product.id === id);
  }

  function priceNumber(price) {
    const parsed = Number(String(price || "0").replace(/[^0-9]/g, ""));
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function rubles(value) {
    return `${Math.round(value).toLocaleString("ru-RU")} ₽`;
  }

  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.classList.add("visible");
    clearTimeout(state.toastTimer);
    state.toastTimer = setTimeout(() => toast.classList.remove("visible"), 2800);
  }

  function scrollToId(id) {
    const element = document.getElementById(id);
    if (element) element.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function openModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.remove("hidden");
    document.body.classList.add("modal-open");
    syncTelegramChrome();
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("hidden");
    if (!$$('.modal-backdrop:not(.hidden)').length) document.body.classList.remove("modal-open");
    syncTelegramChrome();
  }

  function categoryName(id) {
    const found = state.data.categories.find(category => category.id === id);
    return found ? found.name : "DROP 001";
  }

  function renderCategoryChips() {
    const root = $("#categoryChips");
    const all = [{ id: "all", name: "Все вещи" }, ...state.data.categories];
    root.innerHTML = all.map(category => `<button class="category-chip ${state.category === category.id ? "active" : ""}" data-category="${escapeHTML(category.id)}" type="button" role="tab" aria-selected="${state.category === category.id}">${escapeHTML(category.name)}</button>`).join("");
  }

  function filteredProducts() {
    const search = state.search.trim().toLowerCase();
    return state.data.products.filter(product => {
      if (product.active === false) return false;
      if (state.category !== "all" && product.category !== state.category) return false;
      if (state.stock === "limited" && !/limited|последн|мало|drop/i.test(`${product.badge} ${product.stock_label}`)) return false;
      if (state.stock === "available" && /limited|последн|мало|drop/i.test(`${product.badge} ${product.stock_label}`)) return false;
      if (search && !`${product.name} ${product.description} ${product.badge} ${product.material}`.toLowerCase().includes(search)) return false;
      return true;
    });
  }

  function renderProductCard(product, index) {
    const saved = state.saved.includes(product.id);
    return `<article class="product-card" data-product-id="${escapeHTML(product.id)}" style="--card-index:${index}">
      <div class="product-image">${pictureFor(imageFor(product), product.name, "(max-width: 680px) 50vw, (max-width: 900px) 50vw, 33vw", { eager: index < 2 })}<span class="product-badge ${/new/i.test(product.badge || "") ? "new" : ""}">${escapeHTML(product.badge || "CORE")}</span>${product.real_photos ? '<span class="product-real">РЕАЛЬНОЕ ФОТО</span>' : ""}<button class="product-save ${saved ? "saved" : ""}" data-save-id="${escapeHTML(product.id)}" type="button" aria-label="${saved ? "Удалить из сохраненных" : "Сохранить"}"><span class="icon" data-icon="bookmark"></span></button><span class="product-hover">СМОТРЕТЬ ВЕЩЬ <b>↗</b></span></div>
      <div class="product-info"><div class="product-topline"><span>${escapeHTML(categoryName(product.category))}</span><span class="product-stock">${escapeHTML(product.stock_label || "В наличии")}</span></div><h3>${escapeHTML(product.name)}</h3><div class="product-bottom"><strong class="product-price">${escapeHTML(product.price)}${product.compare_price ? `<s class="compare-price">${escapeHTML(product.compare_price)}</s>` : ""}</strong><span class="product-fit">${escapeHTML(product.fit || "CORE FIT")}</span></div></div>
    </article>`;
  }

  function renderProducts() {
    const products = filteredProducts();
    const root = $("#productGrid");
    $("#productCount").textContent = `${products.length.toString().padStart(2, "0")} ITEMS`;
    root.innerHTML = products.map(renderProductCard).join("");
    $("#emptyState").classList.toggle("hidden", products.length > 0);
    iconize();
    markLoadedImages(root);
    updateCounters();
  }

  function renderSheet(product) {
    state.currentProduct = product;
    state.selectedSize = null;
    $("#sheetImage").alt = product.name;
    state.galleryIndex = 0;
    $("#sheetImage").src = galleryFor(product)[0];
    showGallerySlide(0);
    $("#sheetBadge").textContent = product.badge || "CORE";
    $("#sheetKicker").textContent = `${categoryName(product.category).toUpperCase()} / ${product.fit || "CORE"}`;
    $("#sheetTitle").textContent = product.name;
    $("#sheetPrice").textContent = product.price;
    const compare = $("#sheetComparePrice");
    compare.textContent = product.compare_price || "";
    compare.classList.toggle("hidden", !product.compare_price);
    $("#sheetDescription").textContent = product.description;
    renderPersonalization(product);
    renderBundleHint(product);
    $("#sheetFacts").innerHTML = `<div class="fact-row"><span>Материал</span><span>${escapeHTML(product.material || "Плотный хлопок")}</span></div><div class="fact-row"><span>Посадка</span><span>${escapeHTML(product.fit || "Свободная")}</span></div><div class="fact-row"><span>Статус</span><span>${escapeHTML(product.stock_label || "В наличии")}</span></div>`;
    $("#sizeList").innerHTML = (product.sizes || []).map(size => `<button class="size-button" data-size="${escapeHTML(size)}" type="button">${escapeHTML(size)}</button>`).join("");
    $("#sizeHint").textContent = "Выбери размер, чтобы добавить вещь в заявку.";
    $("#sizeHint").classList.remove("error");
    $("#sheetDetails").innerHTML = `<strong>ДЕТАЛИ</strong><br>${(product.details || []).map(escapeHTML).join(" · ")}`;
    const saved = state.saved.includes(product.id);
    $("#sheetSave").classList.toggle("saved", saved);
    $("#sheetSave").setAttribute("aria-label", saved ? "Удалить из сохраненных" : "Сохранить");
    iconize();
  }

  function renderPersonalization(product) {
    const block = $("#personalizeBlock");
    const rule = product.personalization;
    state.note = "";
    if (!rule) { block.classList.add("hidden"); return; }
    block.classList.remove("hidden");
    $("#personalizeLabel").textContent = rule.label || "ПОЖЕЛАНИЕ";
    $("#personalizeHint").textContent = rule.hint || "";
    const input = $("#personalizeInput");
    input.value = "";
    input.placeholder = rule.placeholder || "";
    input.classList.remove("invalid");
    $("#tagPreview").classList.add("hidden");
  }

  function noteIsValid(product, value) {
    const rule = product && product.personalization;
    if (!rule || !value) return true;
    try { return new RegExp(rule.pattern || ".*").test(value); } catch (_) { return true; }
  }

  function onPersonalizeInput() {
    const product = state.currentProduct;
    if (!product || !product.personalization) return;
    const input = $("#personalizeInput");
    const value = input.value.replace(/\s+/g, "").trim();
    const ok = noteIsValid(product, value);
    input.classList.toggle("invalid", !ok);
    state.note = ok ? value : "";
    const preview = $("#tagPreview");
    if (ok && value) { $("#tagPreviewNumber").textContent = value.padStart(5, "0"); preview.classList.remove("hidden"); }
    else preview.classList.add("hidden");
  }

  function renderBundleHint(product) {
    const hint = $("#bundleHint");
    const bundle = state.data.products.find(item => /^set-/.test(item.id) && item.active !== false);
    const isPart = bundle && product.id !== bundle.id && /sila-i-chest/.test(product.id);
    if (!isPart) { hint.classList.add("hidden"); hint.onclick = null; return; }
    hint.innerHTML = `<b>НАБОР</b> ${escapeHTML(bundle.name)} — ${escapeHTML(bundle.price)}${bundle.compare_price ? ` вместо <s>${escapeHTML(bundle.compare_price)}</s>` : ""} ↗`;
    hint.classList.remove("hidden");
    hint.onclick = () => openProduct(bundle.id);
  }

  function openProduct(id) {
    const product = productById(id);
    if (!product) return;
    renderSheet(product);
    openModal("productModal");
  }

  function toggleSaved(id) {
    if (state.saved.includes(id)) {
      state.saved = state.saved.filter(item => item !== id);
      showToast("Убрано из сохранённых.");
    } else {
      state.saved.push(id);
      showToast("Сохранено. Вернёшься — вещь будет ждать.");
    }
    saveJSON("vorozhbitov_saved", state.saved);
    renderProducts();
    if (state.currentProduct && state.currentProduct.id === id) {
      $("#sheetSave").classList.toggle("saved", state.saved.includes(id));
    }
  }

  function addToCart() {
    const product = state.currentProduct;
    if (!product) return;
    if (!state.selectedSize) {
      $("#sizeHint").textContent = "Сначала выбери размер.";
      $("#sizeHint").classList.add("error");
      return;
    }
    if (product.personalization && !noteIsValid(product, state.note)) {
      $("#personalizeInput").classList.add("invalid");
      return showToast("Проверь номер: только цифры, до 5 знаков.");
    }
    const note = state.note || "";
    const key = `${product.id}::${state.selectedSize}::${note}`;
    const existing = state.cart.find(item => item.key === key);
    if (existing) existing.qty += 1;
    else state.cart.push({ key, id: product.id, size: state.selectedSize, qty: 1, note });
    saveJSON("vorozhbitov_cart", state.cart);
    updateCounters();
    closeModal("productModal");
    showToast("Добавлено в заявку.");
    setTimeout(() => openCart(), 170);
  }

  function cartItems() {
    return state.cart.map(item => ({ item, product: productById(item.id) })).filter(pair => pair.product);
  }

  function cartTotal() {
    return cartItems().reduce((sum, pair) => sum + priceNumber(pair.product.price) * pair.item.qty, 0);
  }

  function renderCart() {
    const pairs = cartItems();
    const content = $("#cartContent");
    if (!pairs.length) {
      content.innerHTML = `<div class="cart-empty"><span class="empty-mark">∅</span><h3>Заявка пока пустая.</h3><p>Добавь вещь из дропа — здесь соберём всё перед отправкой менеджеру.</p></div>`;
      $("#checkoutForm").classList.add("hidden");
      return;
    }
    content.innerHTML = pairs.map(({ item, product }) => `<div class="cart-line" data-cart-key="${escapeHTML(item.key)}"><img class="cart-line-image" src="${escapeHTML((manifestEntry(imageFor(product)) || { src: imageFor(product) }).src.replace(/(\.jpg)$/, "$1").replace(/-800\.jpg$/, "-480.jpg"))}" alt="${escapeHTML(product.name)}" loading="lazy"><div class="cart-line-name"><strong>${escapeHTML(product.name)}</strong><small>${item.size === "ONE SIZE" ? "" : `Размер: ${escapeHTML(item.size)} · `}${escapeHTML(product.price)}${item.note ? ` · <span class="order-code">№ ${escapeHTML(String(item.note).padStart(5, "0"))}</span>` : ""}</small><div class="qty-control"><button data-qty="minus" type="button" aria-label="Уменьшить">−</button><span>${item.qty}</span><button data-qty="plus" type="button" aria-label="Увеличить">+</button></div></div><div class="cart-line-end"><strong>${rubles(priceNumber(product.price) * item.qty)}</strong><button class="remove-line" data-remove-key="${escapeHTML(item.key)}" type="button">УДАЛИТЬ</button></div></div>`).join("");
    $("#cartTotal").textContent = rubles(cartTotal());
    $("#checkoutForm").classList.remove("hidden");
  }

  function openCart() {
    renderCart();
    openModal("cartModal");
  }

  function updateCartItem(key, delta) {
    const line = state.cart.find(item => item.key === key);
    if (!line) return;
    line.qty += delta;
    if (line.qty <= 0) state.cart = state.cart.filter(item => item.key !== key);
    saveJSON("vorozhbitov_cart", state.cart);
    renderCart();
    updateCounters();
  }

  function removeCartItem(key) {
    state.cart = state.cart.filter(item => item.key !== key);
    saveJSON("vorozhbitov_cart", state.cart);
    renderCart();
    updateCounters();
    showToast("Вещь убрана из заявки.");
  }

  function updateCounters() {
    const cartCount = state.cart.reduce((sum, item) => sum + Number(item.qty || 0), 0);
    const savedCount = state.saved.length;
    [$("#cartCount"), $("#bottomCartCount")].forEach(node => { if (node) { node.textContent = cartCount; node.classList.toggle("hidden", cartCount === 0); } });
    const saved = $("#savedCount");
    if (saved) { saved.textContent = savedCount; saved.classList.toggle("hidden", savedCount === 0); }
  }

  function selectStock(button) {
    $$(".filter-chip").forEach(node => node.classList.toggle("active", node === button));
    state.stock = button.dataset.stock || "all";
    const count = state.stock === "all" ? 0 : 1;
    $("#filterCount").textContent = count;
    $("#filterCount").classList.toggle("hidden", count === 0);
    renderProducts();
  }

  function setSubmitState(text, isError = false) {
    const node = $("#submitState");
    if (!node) return;
    node.textContent = text || "";
    node.classList.toggle("error", Boolean(isError));
  }

  async function submitOrder() {
    if (state.submitting) return;
    const pairs = cartItems();
    const name = $("#checkoutName").value.trim();
    const phone = $("#checkoutPhone").value.trim();
    const city = $("#checkoutCity").value.trim();
    const consent = $("#checkoutConsent").checked;
    if (!pairs.length) return showToast("Добавь хотя бы одну вещь.");
    if (name.length < 2) return showToast("Напиши имя — менеджеру нужно знать, как обратиться.");
    if (phone.replace(/\D/g, "").length < 10) return showToast("Проверь номер телефона.");
    if (city.length < 2) return showToast("Укажи город или способ доставки.");
    if (!consent) return showToast("Подтверди согласие на обработку данных.");

    const payload = {
      type: "order",
      request_id: `web-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      customer: { name, phone, city },
      consent: true,
      items: pairs.map(({ item, product }) => ({ product_id: product.id, size: item.size, quantity: item.qty, note: item.note || "" }))
    };
    const button = $("#submitOrder");
    state.submitting = true;
    button.disabled = true;
    setSubmitState("Отправляем в бот…");

    const finishOk = detail => {
      state.cart = [];
      saveJSON("vorozhbitov_cart", state.cart);
      updateCounters();
      closeModal("cartModal");
      $("#successDetail").textContent = detail;
      $("#successToast").classList.remove("hidden");
      if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.notificationOccurred === "function") tg.HapticFeedback.notificationOccurred("success");
      setSubmitState("");
    };
    const finishFail = message => {
      setSubmitState(message, true);
      showToast(message);
      if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.notificationOccurred === "function") tg.HapticFeedback.notificationOccurred("error");
    };

    try {
      const initData = tg && tg.initData ? tg.initData : "";
      // 1) Основной канал — HTTP в бот (работает из inline-кнопки, меню и по ссылке, где sendData молчит).
      if (initData && state.data.orders_endpoint !== false) {
        const response = await fetch("/api/order", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-Telegram-Init-Data": initData },
          body: JSON.stringify({ order: payload })
        });
        let result = null;
        try { result = await response.json(); } catch (_) { result = null; }
        if (response.ok && result && result.ok) {
          const codes = (result.orders || []).map(order => `№ ${order.code}`).join(", ");
          finishOk(codes ? `Заявка ${codes}. Бот уже прислал подтверждение, менеджер свяжется с тобой.` : "Бот прислал подтверждение. Менеджер свяжется с тобой.");
          return;
        }
        if (response.status === 401 || response.status === 503) throw new Error("fallback");
        finishFail((result && result.error) || "Не получилось отправить заявку. Попробуй ещё раз.");
        return;
      }
      throw new Error("fallback");
    } catch (_) {
      // 2) Запасной канал — sendData: доставляется только если витрина открыта с reply-кнопки.
      if (tg && typeof tg.sendData === "function" && tg.initData) {
        try {
          tg.sendData(JSON.stringify(payload));
          finishOk("Заявка передана в бот. Если бот не ответил в течение минуты — напиши ему «/start» и отправь заявку ещё раз.");
          return;
        } catch (err) { /* ниже */ }
      }
      if (!tg || !tg.initData) {
        finishOk("Демо-режим: вне Telegram заявка никуда не отправляется. Открой витрину из бота.");
        return;
      }
      finishFail("Нет связи с ботом. Проверь интернет и попробуй ещё раз.");
    } finally {
      state.submitting = false;
      button.disabled = false;
    }
  }

  function openChannel() {
    const url = state.data.channel_url || FALLBACK_CATALOG.channel_url;
    if (tg && typeof tg.openTelegramLink === "function" && /^https:\/\/t\.me\//.test(url)) tg.openTelegramLink(url);
    else window.open(url, "_blank", "noopener,noreferrer");
  }

  async function shareSignal() {
    const text = "Я в закрытом дропе ВОРОЖБИТОВ. Смотри вещи для своих:";
    const url = state.data.channel_url || FALLBACK_CATALOG.channel_url;
    const shareUrl = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;
    if (tg && typeof tg.openTelegramLink === "function") return tg.openTelegramLink(shareUrl);
    try {
      await navigator.clipboard.writeText(`${text} ${url}`);
      showToast("Ссылка скопирована. Отправь своим.");
    } catch (_) { window.open(shareUrl, "_blank", "noopener,noreferrer"); }
  }

  function configureTelegram() {
    if (!tg) return;
    try {
      tg.ready();
      tg.expand();
      if (typeof tg.setHeaderColor === "function") tg.setHeaderColor("#0b0b0d");
      if (typeof tg.setBackgroundColor === "function") tg.setBackgroundColor("#0b0b0d");
      if (typeof tg.setBottomBarColor === "function") tg.setBottomBarColor("#0b0b0d");
      if (typeof tg.disableVerticalSwipes === "function") tg.disableVerticalSwipes();
      if (typeof tg.isVersionAtLeast === "function" && tg.isVersionAtLeast("6.1") && typeof tg.enableClosingConfirmation === "function") {
        // спросить перед закрытием, если в заявке есть вещи
        if (state.cart.length) tg.enableClosingConfirmation();
      }
      document.body.classList.toggle("tg-light", tg.colorScheme === "light");
      if (typeof tg.onEvent === "function") {
        tg.onEvent("themeChanged", () => document.body.classList.toggle("tg-light", tg.colorScheme === "light"));
        tg.onEvent("backButtonClicked", () => {
          const open = $$(".modal-backdrop:not(.hidden)");
          if (open.length) { open.forEach(modal => { closeModal(modal.id); if (modal.id === "teaserModal") closeTeaser(); }); }
          syncTelegramChrome();
        });
        tg.onEvent("mainButtonClicked", () => {
          if (!$("#productModal").classList.contains("hidden")) return addToCart();
          if (!$("#cartModal").classList.contains("hidden")) return submitOrder();
        });
      }
      if (tg.MainButton) tg.MainButton.hide();
    } catch (_) { /* browser preview */ }
  }

  // Нативные кнопки Telegram: BackButton закрывает шторки, MainButton дублирует главное действие.
  function syncTelegramChrome() {
    if (!tg) return;
    try {
      const productOpen = !$("#productModal").classList.contains("hidden");
      const cartOpen = !$("#cartModal").classList.contains("hidden");
      const anyOpen = $$(".modal-backdrop:not(.hidden)").length > 0;
      if (tg.BackButton) { if (anyOpen) tg.BackButton.show(); else tg.BackButton.hide(); }
      if (tg.MainButton) {
        if (productOpen) {
          tg.MainButton.setParams({ text: state.selectedSize ? "ДОБАВИТЬ В ЗАЯВКУ" : "ВЫБЕРИ РАЗМЕР", color: "#ff3e26", text_color: "#0b0b0d", is_active: Boolean(state.selectedSize), is_visible: true });
        } else if (cartOpen && cartItems().length) {
          tg.MainButton.setParams({ text: state.submitting ? "ОТПРАВЛЯЕМ…" : `ОТПРАВИТЬ ЗАЯВКУ · ${rubles(cartTotal())}`, color: "#ff3e26", text_color: "#0b0b0d", is_active: !state.submitting, is_visible: true });
        } else tg.MainButton.hide();
        document.body.classList.toggle("tg-mainbutton", Boolean(tg.MainButton.isVisible));
      }
      if (typeof tg.enableClosingConfirmation === "function" && typeof tg.disableClosingConfirmation === "function") {
        if (state.cart.length) tg.enableClosingConfirmation(); else tg.disableClosingConfirmation();
      }
    } catch (_) { /* старые клиенты */ }
  }

  function renderSkeleton(count = 4) {
    $("#productGrid").innerHTML = Array.from({ length: count }, (_, index) => `<article class="product-card skeleton" style="--card-index:${index}"><div class="product-image"></div><div class="product-info"><div class="product-topline"><span>·</span></div><h3>·</h3><div class="product-bottom"><strong class="product-price">·</strong></div></div></article>`).join("");
  }

  async function loadManifest(url) {
    try {
      const response = await fetch(url || "assets/img/manifest.json", { headers: { Accept: "application/json" } });
      if (response.ok) state.manifest = await response.json();
    } catch (_) { state.manifest = {}; }
  }

  async function loadCatalog() {
    renderSkeleton();
    try {
      const [response] = await Promise.all([
        fetch("/api/catalog", { headers: { Accept: "application/json" } }),
        loadManifest()
      ]);
      if (!response.ok) throw new Error("catalog unavailable");
      const remote = await response.json();
      if (Array.isArray(remote.products) && Array.isArray(remote.categories)) {
        state.data = { ...FALLBACK_CATALOG, ...remote, products: remote.products.filter(product => product.active !== false) };
        state.loadedFromApi = true;
      }
    } catch (_) {
      state.data = FALLBACK_CATALOG;
    }
    renderCategoryChips();
    renderProducts();
    applyMedia();
  }

  function applyMedia() {
    // URL видео приходят из catalog.json (/api/catalog) — ролик можно заменить без пересборки образа.
    const media = state.data.media || {};
    const swap = (video, src, poster) => {
      if (!video || !src) return;
      const source = video.querySelector("source");
      if (source && source.getAttribute("src") !== src) { source.setAttribute("src", src); video.load(); }
      if (poster) video.setAttribute("poster", poster);
    };
    swap(heroVideo, media.hero_video, media.hero_poster);
    if (media.hero_poster) { const fb = $(".hero-fallback"); if (fb) fb.src = media.hero_poster; }
    swap(teaserVideo, media.teaser, media.teaser_poster);
    if (media.teaser_poster) { const img = $("#teaserCard img"); if (img) img.src = media.teaser_poster; }
    if (heroVideo && heroVideo.paused) tryPlayHero();
  }

  // ------------------------------------------------------------------ video
  // Hero-loop — тихий зацикленный ролик вместо hero-картинки. Правила:
  //  • autoplay только muted+playsinline; iOS WKWebView всё равно может отказать —
  //    тогда показываем постер и кнопку ▶ (никаких «мёртвых» автоплеев);
  //  • saveData / reduced-motion → не грузим видео вообще;
  //  • пауза, когда hero ушёл с экрана или приложение свернули (батарея).
  const heroVideo = $("#heroVideo");
  const heroVisual = $("#heroVisual");
  const heroPlay = $("#heroPlay");
  const teaserVideo = $("#teaserVideo");
  const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
  const lowData = Boolean(conn && (conn.saveData || /(^|-)2g$/.test(conn.effectiveType || "")));
  const reducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let heroAllowed = !lowData && !reducedMotion;
  let heroInView = true;

  function tryPlayHero() {
    if (!heroVideo || !heroAllowed || !heroInView || document.hidden) return;
    const attempt = heroVideo.play();
    if (attempt && typeof attempt.catch === "function") {
      attempt.then(() => { heroPlay.classList.add("hidden"); }).catch(() => { heroPlay.classList.remove("hidden"); });
    }
  }

  function setupHeroVideo() {
    if (!heroVideo) return;
    if (!heroAllowed) { heroVideo.removeAttribute("preload"); heroVideo.preload = "none"; heroPlay.classList.remove("hidden"); }
    heroVideo.addEventListener("playing", () => { heroVisual.classList.add("video-ready"); heroPlay.classList.add("hidden"); });
    heroVideo.addEventListener("error", () => { heroVisual.classList.remove("video-ready"); heroPlay.classList.add("hidden"); heroAllowed = false; });
    heroPlay.addEventListener("click", () => { heroAllowed = true; heroVideo.preload = "auto"; tryPlayHero(); });
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(entries => entries.forEach(entry => {
        heroInView = entry.isIntersecting;
        if (heroInView) tryPlayHero(); else if (!heroVideo.paused) heroVideo.pause();
      }), { threshold: 0.2 }).observe(heroVisual);
    }
    document.addEventListener("visibilitychange", () => { if (document.hidden) { if (!heroVideo.paused) heroVideo.pause(); } else tryPlayHero(); });
    tryPlayHero();
  }

  function openTeaser() {
    if (!heroVideo.paused) heroVideo.pause();
    openModal("teaserModal");
    if (teaserVideo) {
      teaserVideo.muted = false;
      const attempt = teaserVideo.play();
      if (attempt && typeof attempt.catch === "function") attempt.catch(() => { /* пользователь нажмёт ▶ в controls */ });
    }
    if (tg && tg.HapticFeedback && typeof tg.HapticFeedback.impactOccurred === "function") tg.HapticFeedback.impactOccurred("light");
  }

  function closeTeaser() {
    if (teaserVideo) { teaserVideo.pause(); try { teaserVideo.currentTime = 0; } catch (_) { /* not loaded */ } }
    tryPlayHero();
  }

  function shareTeaserToStory() {
    // Bot API 7.8+: Telegram сам скачивает media_url, поэтому нужен абсолютный публичный HTTPS-URL.
    const media = state.data.media || {};
    const url = media.teaser_story_url || new URL("assets/video/teaser-720.mp4", window.location.href).href;
    if (!tg || typeof tg.shareToStory !== "function") return showToast("Сторис доступны только внутри Telegram.");
    const params = { text: "СИЛА И ЧЕСТЬ — DROP 001. Забрать размер — в боте." };
    if (media.story_link) params.widget_link = { url: media.story_link, name: "ВОРОЖБИТОВ" };
    try { tg.shareToStory(url, params); } catch (_) { showToast("Не удалось открыть редактор сторис."); }
  }

  function setupStoryButton() {
    const button = $("#storyButton");
    if (!button) return;
    const supported = tg && typeof tg.shareToStory === "function" && typeof tg.isVersionAtLeast === "function" && tg.isVersionAtLeast("7.8");
    button.classList.toggle("hidden", !supported);
    button.addEventListener("click", shareTeaserToStory);
  }

  function bindEvents() {
    $("#categoryChips").addEventListener("click", event => {
      const button = event.target.closest("[data-category]");
      if (!button) return;
      state.category = button.dataset.category;
      renderCategoryChips();
      renderProducts();
    });

    $("#productGrid").addEventListener("click", event => {
      const saveButton = event.target.closest("[data-save-id]");
      if (saveButton) { event.stopPropagation(); return toggleSaved(saveButton.dataset.saveId); }
      const card = event.target.closest("[data-product-id]");
      if (card) openProduct(card.dataset.productId);
    });

    $("#personalizeInput").addEventListener("input", onPersonalizeInput);
    $("#bundleHint").addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); $("#bundleHint").click(); } });
    const lookbookReal = $("#lookbookReal");
    if (lookbookReal) {
      lookbookReal.addEventListener("click", () => openProduct("tag-sila-i-chest-001"));
      lookbookReal.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openProduct("tag-sila-i-chest-001"); } });
    }
    $("#sizeList").addEventListener("click", event => {
      const button = event.target.closest("[data-size]");
      if (!button) return;
      state.selectedSize = button.dataset.size;
      $$(".size-button", $("#sizeList")).forEach(node => node.classList.toggle("selected", node === button));
      $("#sizeHint").textContent = `Размер ${state.selectedSize} выбран.`;
      $("#sizeHint").classList.remove("error");
      syncTelegramChrome();
    });

    $("#sheetSave").addEventListener("click", () => { if (state.currentProduct) toggleSaved(state.currentProduct.id); });
    $("#galleryPrev").addEventListener("click", event => { event.stopPropagation(); showGallerySlide(state.galleryIndex - 1); });
    $("#galleryNext").addEventListener("click", event => { event.stopPropagation(); showGallerySlide(state.galleryIndex + 1); });
    $("#sheetImage").addEventListener("click", () => { if (galleryFor(state.currentProduct || {}).length > 1) showGallerySlide(state.galleryIndex + 1); });
    let touchX = null;
    $(".sheet-image").addEventListener("touchstart", event => { touchX = event.touches[0].clientX; }, { passive: true });
    $(".sheet-image").addEventListener("touchend", event => {
      if (touchX === null) return;
      const dx = event.changedTouches[0].clientX - touchX; touchX = null;
      if (Math.abs(dx) > 40) showGallerySlide(state.galleryIndex + (dx < 0 ? 1 : -1));
    }, { passive: true });
    document.addEventListener("keydown", event => {
      if ($("#productModal").classList.contains("hidden")) return;
      if (event.key === "ArrowRight") showGallerySlide(state.galleryIndex + 1);
      if (event.key === "ArrowLeft") showGallerySlide(state.galleryIndex - 1);
    });
    $("#addToCartButton").addEventListener("click", addToCart);
    $("#cartButton").addEventListener("click", openCart);
    $("#bottomCartButton").addEventListener("click", openCart);
    $("#savedButton").addEventListener("click", () => {
      if (!state.saved.length) return showToast("Пока ничего не сохранено.");
      state.category = "all"; state.search = "";
      $("#searchInput").value = "";
      renderCategoryChips();
      const savedProducts = state.data.products.filter(product => state.saved.includes(product.id));
      $("#productGrid").innerHTML = savedProducts.map(renderProductCard).join("");
      $("#productCount").textContent = `${savedProducts.length.toString().padStart(2, "0")} SAVED`;
      $("#emptyState").classList.toggle("hidden", savedProducts.length > 0);
      iconize();
      scrollToId("catalog");
    });

    $("#cartContent").addEventListener("click", event => {
      const row = event.target.closest("[data-cart-key]");
      if (!row) return;
      const key = row.dataset.cartKey;
      if (event.target.closest("[data-qty='plus']")) updateCartItem(key, 1);
      if (event.target.closest("[data-qty='minus']")) updateCartItem(key, -1);
      const remove = event.target.closest("[data-remove-key]");
      if (remove) removeCartItem(remove.dataset.removeKey);
    });

    $("#searchInput").addEventListener("input", event => { state.search = event.target.value; $("#clearSearch").classList.toggle("hidden", !state.search); renderProducts(); });
    $("#clearSearch").addEventListener("click", () => { state.search = ""; $("#searchInput").value = ""; $("#clearSearch").classList.add("hidden"); renderProducts(); });
    $("#filterToggle").addEventListener("click", () => $("#filterPanel").classList.toggle("hidden"));
    $("#filterOptions").addEventListener("click", event => { const button = event.target.closest("[data-stock]"); if (button) selectStock(button); });
    $("#resetFilters").addEventListener("click", () => { state.stock = "all"; state.search = ""; state.category = "all"; $("#searchInput").value = ""; $("#clearSearch").classList.add("hidden"); selectStock($("[data-stock='all']")); renderCategoryChips(); });
    $("#emptyReset").addEventListener("click", () => { $("#resetFilters").click(); });
    $("#submitOrder").addEventListener("click", submitOrder);
    $("#channelButton").addEventListener("click", openChannel);
    $("#shareButton").addEventListener("click", shareSignal);
    $("#sizeGuideButton").addEventListener("click", () => openModal("sizeGuideModal"));
    $("#closeToast").addEventListener("click", () => $("#successToast").classList.add("hidden"));

    $$('[data-scroll]').forEach(button => button.addEventListener("click", () => scrollToId(button.dataset.scroll)));
    $$('[data-open="manifesto"]').forEach(button => button.addEventListener("click", () => scrollToId("manifesto")));
    $$('[data-close]').forEach(button => button.addEventListener("click", () => { closeModal(button.dataset.close); if (button.dataset.close === "teaserModal") closeTeaser(); }));
    const teaserCard = $("#teaserCard");
    if (teaserCard) {
      teaserCard.addEventListener("click", openTeaser);
      teaserCard.addEventListener("keydown", event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openTeaser(); } });
    }
    $$(".modal-backdrop").forEach(backdrop => backdrop.addEventListener("click", event => { if (event.target === backdrop) { closeModal(backdrop.id); if (backdrop.id === "teaserModal") closeTeaser(); } }));
    document.addEventListener("keydown", event => { if (event.key === "Escape") $$(".modal-backdrop:not(.hidden)").forEach(modal => { closeModal(modal.id); if (modal.id === "teaserModal") closeTeaser(); }); });

    const sections = ["home", "catalog", "lookbook", "join"];
    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) $$(".bottom-link").forEach(link => link.classList.toggle("active", link.dataset.scroll === entry.target.id)); }), { rootMargin: "-35% 0px -55% 0px", threshold: 0 });
      sections.forEach(id => { const element = document.getElementById(id); if (element) observer.observe(element); });
    }
  }

  iconize();
  configureTelegram();
  bindEvents();
  setupHeroVideo();
  setupStoryButton();
  updateCounters();
  loadCatalog();
  markLoadedImages();
  window.VorozhbitovShop = { state, openProduct, openCart };
})();
