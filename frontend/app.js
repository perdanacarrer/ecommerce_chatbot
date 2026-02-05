let lastProducts = [];
let compareList = [];
let cart = [];
let isCheckingOut = false;
let userLocation = null;
let isBotTyping = false;

const messages = document.getElementById("messages");
const quickReplies = document.getElementById("quickReplies");
const quickReplyActions = {
  "Checkout": checkout,
};

/* --------------------
   MESSAGE HELPERS
-------------------- */
function addMessage(text, sender = "bot") {
  const div = document.createElement("div");
  div.className = `message ${sender}`;
  div.setAttribute("data-testid", "chat-message");
  div.innerText = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function addMapMessage(stores) {
  const wrapper = document.createElement("div")
  wrapper.className = "message bot map"

  const bubble = document.createElement("div")
  bubble.className = "map-bubble"

  const header = document.createElement("div")
  header.className = "map-header"
  header.innerText = "🗺 Nearest stores"

  const mapDiv = document.createElement("div")
  mapDiv.className = "map-container"

  const mapId = `map-${Date.now()}`
  mapDiv.id = mapId

  bubble.appendChild(header)
  bubble.appendChild(mapDiv)
  wrapper.appendChild(bubble)

  messages.appendChild(wrapper)
  messages.scrollTop = messages.scrollHeight

  renderStoreMap(mapId, stores)
}

function showTyping() {
  if (isBotTyping) return;

  disableUserInput();

  const div = document.createElement("div");
  div.className = "message system typing";
  div.id = "typing";
  div.innerText = "Bot is typing…";
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

function hideTyping() {
  const el = document.getElementById("typing");
  if (el) el.remove();

  enableUserInput();
}

function clearCarousels() {
  document.querySelectorAll(".carousel").forEach(el => el.remove());
}

function openDirections(storeLat, storeLng) {
  if (!userLocation) {
    alert("User location unavailable")
    return
  }
  const { latitude, longitude } = userLocation
  window.open(
    `https://www.google.com/maps/dir/?api=1`
    + `&origin=${latitude},${longitude}`
    + `&destination=${storeLat},${storeLng}`,
    "_blank"
  )
}

function searchStore(storeId, storeName) {
  addMessage(`Search products in ${storeName}`, "user")
  sendBackendCommand(`search store ${storeId}`)
}

function showStoreDetails(storeId, storeName) {
  addMessage(`View details for ${storeName}`, "user")
  sendBackendCommand(`store details ${storeId}`)
}

function disableUserInput() {
  isBotTyping = true;

  const input = document.getElementById("messageInput");
  const sendBtn = document.querySelector(".send-btn");

  input.disabled = true;
  sendBtn.disabled = true;

  // Disable quick replies
  document
    .querySelectorAll("#quickReplies button")
    .forEach(btn => btn.disabled = true);
}

function enableUserInput() {
  isBotTyping = false;

  const input = document.getElementById("messageInput");
  const sendBtn = document.querySelector(".send-btn");

  input.disabled = false;
  sendBtn.disabled = false;

  // Re-enable quick replies
  document
    .querySelectorAll("#quickReplies button")
    .forEach(btn => btn.disabled = false);

  input.focus();
}

/* --------------------
   PRODUCT RENDERING
-------------------- */
function renderProducts(products) {
  lastProducts = products;
//   clearCarousels();
  const carousel = document.createElement("div");
  carousel.className = "carousel";

  products.forEach(product => {
    const card = document.createElement("div");
    card.className = "card";

    card.innerHTML = `
      <img src="/placeholder.svg" alt="${product.name}" />
      <div class="card-title">${product.name}</div>
      <div class="card-price">$${product.retail_price.toFixed(2)}</div>
    `;

    // ✅ Actions wrapper
    const actions = document.createElement("div");
    actions.className = "card-actions";

    // ➕ Compare button
    const compareBtn = document.createElement("button");
    compareBtn.innerText = "Compare";
    compareBtn.onclick = () => addToCompare(product);

    // ➕ Add to cart
    const cartBtn = document.createElement("button");
    cartBtn.innerText = "Add to cart";
    cartBtn.onclick = () => addToCart(product);

    actions.appendChild(compareBtn);
    actions.appendChild(cartBtn);
    card.appendChild(actions);

    carousel.appendChild(card);
  });

  messages.appendChild(carousel);
  messages.scrollTop = messages.scrollHeight;
}

function renderCart(products) {
  clearCarousels();
  const carousel = document.createElement("div");
  carousel.className = "carousel";

  products.forEach(product => {
    const card = document.createElement("div");
    card.className = "card";

    card.innerHTML = `
      <img src="/placeholder.svg" alt="${product.name}" />
      <div class="card-title">${product.name}</div>
      <div class="card-price">$${product.retail_price.toFixed(2)}</div>
    `;

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const removeBtn = document.createElement("button");
    removeBtn.innerText = "Remove ❌";
    removeBtn.onclick = () => removeFromCart(product);

    actions.appendChild(removeBtn);
    card.appendChild(actions);
    carousel.appendChild(card);
  });

  messages.appendChild(carousel);
  messages.scrollTop = messages.scrollHeight;
}

function renderStoreMap(mapId, stores) {
  const map = L.map(mapId)

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap"
  }).addTo(map)

  const markers = stores.map(store =>
    L.marker([store.latitude, store.longitude])
      .bindPopup(`
        <strong>${store.name}</strong><br>
        📍 ${store.distance_km.toFixed(2)} km<br><br>
        <button onclick="searchStore('${store.id}', '${store.name.replace(/'/g, "\\'")}')">
            Search this store
        </button><br>
        <button onclick="showStoreDetails('${store.id}', '${store.name.replace(/'/g, "\\'")}')">
            View details
        </button><br>
        <button onclick="openDirections(${store.latitude}, ${store.longitude})">
            Directions
        </button>
      `)
      .addTo(map)
  )

  if (stores.length === 1) {
    map.setView(
      [stores[0].latitude, stores[0].longitude],
      10
    )
  } else {
    const bounds = L.latLngBounds(
      stores.map(s => [s.latitude, s.longitude])
    )
    map.fitBounds(bounds, { padding: [30, 30] })
  }

  setTimeout(() => {
    map.invalidateSize()
  }, 200)
}

/* --------------------
   QUICK REPLIES
-------------------- */
function renderQuickReplies(replies) {
  quickReplies.innerHTML = "";

  replies.forEach(label => {
    const btn = document.createElement("button");
    btn.innerText = label;
    btn.disabled = isBotTyping;
    btn.onclick = () => {
        clearQuickReplies();
        (quickReplyActions[label] || send)(label);
    };
    quickReplies.appendChild(btn);
  });
}

function clearQuickReplies() {
  quickReplies.innerHTML = "";
}

function showQuickReplies(items) {
  if (!items || !items.length) return
  renderQuickReplies(items)
}

/* --------------------
   SEND MESSAGE
-------------------- */
async function sendBackendCommand(command) {
  if (isBotTyping) return;
  showTyping()

  const res = await fetch(
    `http://localhost:8000/chat?message=${encodeURIComponent(command)}`
  )

  hideTyping()
  const data = await res.json()

  if (data.reply) addMessage(data.reply, "bot")
  if (data.stores) addMapMessage(data.stores)
  if (data.products) renderProducts(data.products)
  if (data.quick_replies) renderQuickReplies(data.quick_replies)
}

async function send(textOverride) {
  if (isBotTyping) return;
  clearQuickReplies();
  const input = document.getElementById("messageInput");
  const text = textOverride || input.value.trim();
  if (!text) return;

  addMessage(text, "user");
  input.value = "";

  showTyping();

  setTimeout(async () => {
    hideTyping();

    const res = await fetch(
      `http://localhost:8000/chat?message=${encodeURIComponent(text)}`
    );

    const data = await res.json();

    if (data.action === "show_cart") {
      const cartRes = await fetch("http://localhost:8000/cart", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(cart)
      });

      const cartData = await cartRes.json();

      if (cartData.reply) addMessage(cartData.reply, "bot");
      renderCart(cartData.cart);

      clearQuickReplies();
      return;
    }
    if (data.reply) addMessage(data.reply, "bot");
    if (data.user_location) {
        userLocation = data.user_location
    }
    if (data.stores && data.stores.length) {
        addMapMessage(data.stores)
        showQuickReplies([
            "Show 5 closest stores",
            "Only jackets",
            "Under $100"
        ])
    }  else if (data.reply?.includes("store")) {
        addMessage("📍 Map unavailable for this result", "system")
    }
    if (data.products) renderProducts(data.products);
    if (data.quick_replies) {
        renderQuickReplies(data.quick_replies);
    } else {
        clearQuickReplies();
    }

  }, 700);
}

/* --------------------
   COMPARISON FLOW
-------------------- */
function addToCompare(product) {
  if (compareList.find(p => p.name === product.name)) return;

  compareList.push(product);

  addMessage(
    `${product.name} added for comparison (${compareList.length}/2).`,
    "system"
  );

  if (compareList.length === 2) {
    renderComparison(compareList);
    compareList = [];
  }
}

function renderComparison(products) {
  const table = document.createElement("div");
  table.className = "compare-table";

  products.forEach(p => {
    const card = document.createElement("div");
    card.className = "compare-card";
    card.innerHTML = `
      <h4>${p.name}</h4>
      <p>Brand: ${p.brand}</p>
      <p>Store: ${p.distribution_name}</p>
      <p>Price: $${p.retail_price}</p>
    `;
    table.appendChild(card);
  });

  messages.appendChild(table);
  messages.scrollTop = messages.scrollHeight;
}

/* --------------------
   CART FLOW
-------------------- */
function addToCart(product) {
  if (cart.find(p => p.id === product.id)) {
    addMessage(`${product.name} is already in your cart 🛒`, "system");
    return;
  }
  cart.push(product);
  addMessage(
    `${product.name} added to cart. Would you like to checkout or keep shopping?`,
    "bot"
  );
  renderQuickReplies(["Checkout", "Show more"]);
}

function removeFromCart(product) {
  cart = cart.filter(p => p.id !== product.id);
  addMessage(`❌ Removed ${product.name} from cart`);
  renderCart(cart);
}

async function checkout() { 
  if (isCheckingOut) return;
  isCheckingOut = true;

  try {
    if (cart.length === 0) {
      addMessage("Cart is empty 🛒");
      renderQuickReplies(["Show more"]);
      return;
    }

    const res = await fetch("http://localhost:8000/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cart })
    });

    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Checkout failed");
    }

    const data = await res.json();
    addMessage(`✅ Order placed! Order ID: ${data.order_id}`);

    cart = [];
    renderQuickReplies(["Show more"]);
  } catch (err) {
    console.error(err);
    addMessage(`❌ ${err.message}`);
    renderQuickReplies(["Checkout", "Show more"]);
  } finally {
    isCheckingOut = false;
  }
}