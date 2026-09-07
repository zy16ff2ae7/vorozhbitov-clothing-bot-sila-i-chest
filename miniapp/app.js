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
      { id: "tee-sila-i-chest-001", category: "drop", name: "СИЛА И ЧЕСТЬ / TEE", price: "4 900 ₽", sizes: ["S", "M", "L", "XL", "XXL"], description: "Чёрная футболка с уставной надписью «СИЛА И ЧЕСТЬ» на груди и мечом по позвоночнику. Первый тираж — один раз и без повторов.", image: "assets/sila-i-chest/front-night.jpg", images: ["assets/sila-i-chest/front-night.jpg", "assets/sila-i-chest/back-boxing.jpg", "assets/sila-i-chest/flatlay.jpg", "assets/sila-i-chest/crew.jpg", "assets/sila-i-chest/gym.jpg"], badge: "DROP 001", material: "100% хлопок · 240 г/м²", fit: "Прямой крой", details: ["Принт спереди: «СИЛА И ЧЕСТЬ», уставной шрифт", "Принт сзади: меч по позвоночнику, монограмма ВВ у ворота", "Плотная шелкография, не трескается", "Усиленная горловина"], stock_label: "Первый тираж", active: true },
      { id: "drop-tee-001", category: "drop", name: "CORE TEE / 001", price: "4 900 ₽", sizes: ["S", "M", "L", "XL"], description: "Плотный хлопок, свободный крой, минимальный сигнал на груди. Первый тираж — один раз и без повторов.", image: "assets/base-tee.jpg", badge: "DROP 001", material: "100% хлопок · 240 г/м²", fit: "Свободный крой", details: ["Плотный хлопок", "Усиленная горловина", "Бирка-сигнал внутри"], stock_label: "Осталось мало", active: true },
      { id: "drop-hoodie-001", category: "drop", name: "CORE HOODIE / 001", price: "9 900 ₽", sizes: ["M", "L", "XL"], description: "Тяжёлое полотно, объёмный силуэт, двойная строчка. Увидел — забирай: партия ограничена.", image: "assets/hero-drop.jpg", badge: "LIMITED", material: "100% хлопок · 400 г/м²", fit: "Объемный крой", details: ["Футер 3-нитка", "Капюшон с двойной строчкой", "Металлические наконечники"], stock_label: "Последний тираж", active: true },
      { id: "hoodie-heavy-002", category: "hoodie", name: "HEAVY HOODIE / 002", price: "10 500 ₽", sizes: ["S", "M", "L", "XL"], description: "400 г/м². Держит форму и темп города. Никакой лишней графики — только посадка и вес.", image: "assets/heavy-hoodie.jpg", badge: "CORE", material: "100% хлопок · 400 г/м²", fit: "Свободный крой", details: ["Мягкий начес", "Плотные манжеты", "Карман-кенгуру"], stock_label: "В наличии", active: true },
      { id: "tee-basic-002", category: "tee", name: "EVERYDAY TEE / 002", price: "3 900 ₽", sizes: ["S", "M", "L", "XL"], description: "База на каждый день: плотная ткань, спокойная форма, вещь, которую не хочется снимать.", image: "assets/base-tee.jpg", badge: "EVERYDAY", material: "100% хлопок · 240 г/м²", fit: "Boxy fit", details: ["Гладкая фактура", "Плотная горловина", "Стирается без сюрпризов"], stock_label: "В наличии", active: true },
      { id: "cargo-city-001", category: "bottom", name: "CITY CARGO / 001", price: "8 500 ₽", sizes: ["S", "M", "L"], description: "Свободные карго с регулируемой посадкой и усиленными карманами. Город не бережёт — эти выдержат.", image: "assets/city-cargo.jpg", badge: "UTILITY", material: "Плотный хлопок · ripstop", fit: "Relaxed fit", details: ["6 функциональных карманов", "Регулировка низа", "Усиленные швы"], stock_label: "Мало размеров", active: true },
      { id: "cap-logo-001", category: "access", name: "SIGNAL CAP / 001", price: "3 200 ₽", sizes: ["ONE SIZE"], description: "Плотная шестиклинка с маленькой красной меткой. Никаких громких логотипов — свой считывает.", image: "assets/logo-cap.jpg", badge: "SIGNAL", material: "100% хлопок", fit: "Регулируемый размер", details: ["Металлическая застежка", "Вышитая метка", "Внутренняя лента"], stock_label: "В наличии", active: true }
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
    loadedFromApi: false
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
    return String(product.image || product.image_url || "assets/base-tee.jpg");
  }

  function galleryFor(product) {
    const list = Array.isArray(product.images) && product.images.length ? product.images : [imageFor(product)];
    return list.map(String).filter((src, index, all) => src && all.indexOf(src) === index);
  }

  const GALLERY_LABELS = ["ПЕРЕД", "СПИНА", "ТОВАР", "LOOK 01", "LOOK 02", "LOOK 03", "LOOK 04", "LOOK 05", "LOOK 06", "LOOK 07"];

  function showGallerySlide(index) {
    const product = state.currentProduct;
    if (!product) return;
    const slides = galleryFor(product);
    state.galleryIndex = (index + slides.length) % slides.length;
    const img = $("#sheetImage");
    img.classList.add("swapping");
    setTimeout(() => { img.src = slides[state.galleryIndex]; img.classList.remove("swapping"); }, 120);
    $("#galleryDots").innerHTML = slides.map((_, i) => `<span class="${i === state.galleryIndex ? "active" : ""}"></span>`).join("");
    const multi = slides.length > 1;
    $("#galleryPrev").classList.toggle("hidden", !multi);
    $("#galleryNext").classList.toggle("hidden", !multi);
    let label = $(".gallery-label", $(".sheet-image"));
    if (!label) { label = document.createElement("span"); label.className = "gallery-label"; $(".sheet-image").appendChild(label); }
    label.textContent = multi ? (GALLERY_LABELS[state.galleryIndex] || `${state.galleryIndex + 1} / ${slides.length}`) : "";
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
  }

  function closeModal(id) {
    const modal = document.getElementById(id);
    if (!modal) return;
    modal.classList.add("hidden");
    if (!$$('.modal-backdrop:not(.hidden)').length) document.body.classList.remove("modal-open");
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
      <div class="product-image"><img src="${escapeHTML(imageFor(product))}" alt="${escapeHTML(product.name)}" loading="lazy"><span class="product-badge">${escapeHTML(product.badge || "CORE")}</span><button class="product-save ${saved ? "saved" : ""}" data-save-id="${escapeHTML(product.id)}" type="button" aria-label="${saved ? "Удалить из сохраненных" : "Сохранить"}"><span class="icon" data-icon="bookmark"></span></button><span class="product-hover">СМОТРЕТЬ ВЕЩЬ <b>↗</b></span></div>
      <div class="product-info"><div class="product-topline"><span>${escapeHTML(categoryName(product.category))}</span><span class="product-stock">${escapeHTML(product.stock_label || "В наличии")}</span></div><h3>${escapeHTML(product.name)}</h3><div class="product-bottom"><strong class="product-price">${escapeHTML(product.price)}</strong><span class="product-fit">${escapeHTML(product.fit || "CORE FIT")}</span></div></div>
    </article>`;
  }

  function renderProducts() {
    const products = filteredProducts();
    const root = $("#productGrid");
    $("#productCount").textContent = `${products.length.toString().padStart(2, "0")} ITEMS`;
    root.innerHTML = products.map(renderProductCard).join("");
    $("#emptyState").classList.toggle("hidden", products.length > 0);
    iconize();
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
    $("#sheetDescription").textContent = product.description;
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
    const key = `${product.id}::${state.selectedSize}`;
    const existing = state.cart.find(item => item.key === key);
    if (existing) existing.qty += 1;
    else state.cart.push({ key, id: product.id, size: state.selectedSize, qty: 1 });
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
    content.innerHTML = pairs.map(({ item, product }) => `<div class="cart-line" data-cart-key="${escapeHTML(item.key)}"><img class="cart-line-image" src="${escapeHTML(imageFor(product))}" alt="${escapeHTML(product.name)}"><div class="cart-line-name"><strong>${escapeHTML(product.name)}</strong><small>Размер: ${escapeHTML(item.size)} · ${escapeHTML(product.price)}</small><div class="qty-control"><button data-qty="minus" type="button" aria-label="Уменьшить">−</button><span>${item.qty}</span><button data-qty="plus" type="button" aria-label="Увеличить">+</button></div></div><div class="cart-line-end"><strong>${rubles(priceNumber(product.price) * item.qty)}</strong><button class="remove-line" data-remove-key="${escapeHTML(item.key)}" type="button">УДАЛИТЬ</button></div></div>`).join("");
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

  function submitOrder() {
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
      items: pairs.map(({ item, product }) => ({ product_id: product.id, size: item.size, quantity: item.qty }))
    };
    const serialized = JSON.stringify(payload);
    state.cart = [];
    saveJSON("vorozhbitov_cart", state.cart);
    updateCounters();
    closeModal("cartModal");
    if (tg && typeof tg.sendData === "function") {
      try { tg.sendData(serialized); } catch (_) { /* fallback toast still confirms the local handoff */ }
    }
    $("#successToast").classList.remove("hidden");
    showToast(tg ? "Заявка передана в бот." : "Демо-заявка создана — подключи Telegram для отправки менеджеру.");
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
      if (tg.MainButton) tg.MainButton.hide();
    } catch (_) { /* browser preview */ }
  }

  async function loadCatalog() {
    try {
      const response = await fetch("/api/catalog", { headers: { Accept: "application/json" } });
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

    $("#sizeList").addEventListener("click", event => {
      const button = event.target.closest("[data-size]");
      if (!button) return;
      state.selectedSize = button.dataset.size;
      $$(".size-button", $("#sizeList")).forEach(node => node.classList.toggle("selected", node === button));
      $("#sizeHint").textContent = `Размер ${state.selectedSize} выбран.`;
      $("#sizeHint").classList.remove("error");
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
    $$('[data-close]').forEach(button => button.addEventListener("click", () => closeModal(button.dataset.close)));
    $$(".modal-backdrop").forEach(backdrop => backdrop.addEventListener("click", event => { if (event.target === backdrop) closeModal(backdrop.id); }));
    document.addEventListener("keydown", event => { if (event.key === "Escape") $$(".modal-backdrop:not(.hidden)").forEach(modal => closeModal(modal.id)); });

    const sections = ["home", "catalog", "lookbook", "join"];
    const observer = new IntersectionObserver(entries => entries.forEach(entry => { if (entry.isIntersecting) $$(".bottom-link").forEach(link => link.classList.toggle("active", link.dataset.scroll === entry.target.id)); }), { rootMargin: "-35% 0px -55% 0px", threshold: 0 });
    sections.forEach(id => { const element = document.getElementById(id); if (element) observer.observe(element); });
  }

  iconize();
  configureTelegram();
  bindEvents();
  updateCounters();
  loadCatalog();
  window.VorozhbitovShop = { state, openProduct, openCart };
})();
