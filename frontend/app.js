let lastProducts = [];
let compareList = [];
let cart = [];

const messages = document.getElementById("messages");
const quickReplies = document.getElementById("quickReplies");

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

function showTyping() {
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
}

/* --------------------
   PRODUCT RENDERING
-------------------- */
function renderProducts(products) {
  lastProducts = products;

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

/* --------------------
   QUICK REPLIES
-------------------- */
function renderQuickReplies(replies) {
  quickReplies.innerHTML = "";

  replies.forEach(label => {
    const btn = document.createElement("button");
    btn.innerText = label;
    btn.onclick = () => {
        clearQuickReplies();
        send(label);
    };
    quickReplies.appendChild(btn);
  });
}

function clearQuickReplies() {
  quickReplies.innerHTML = "";
}

/* --------------------
   SEND MESSAGE
-------------------- */
async function send(textOverride) {
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

    if (data.reply) addMessage(data.reply, "bot");
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
  cart.push(product);
  addMessage(
    `${product.name} added to cart. Would you like to checkout or keep shopping?`,
    "bot"
  );
  renderQuickReplies(["Checkout", "Show more"]);
}