from datetime import datetime
from fastapi import FastAPI, Request, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
import os
import re

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
client = bigquery.Client(project=PROJECT_ID)

# -------------------------
# INTENT DETECTION
# -------------------------
def detect_intent(message: str):
    msg = message.lower()

    if "gift" in msg:
        return "gift"

    if "compare" in msg or "difference" in msg:
        return "compare"

    if "under $" in msg or "under" in msg:
        return "price_search"

    if any(size in msg for size in ["small", "medium", "large", "xl", "xxl"]):
        return "size_search"

    return "search"

def is_show_cart_intent(message: str) -> bool:
    msg = message.lower()
    keywords = [
        "show cart",
        "see cart",
        "view cart",
        "my cart",
        "items in cart",
        "show me cart",
        "show me items",
        "let me see my cart",
    ]
    return any(k in msg for k in keywords)

def is_gift_intent(message: str) -> bool:
    msg = message.lower()
    return any(k in msg for k in ["gift", "present", "buy for", "for my"])

def is_closest_store_intent(message: str) -> bool:
    msg = message.lower()
    keywords = [
        "closest store",
        "nearest store",
        "closest distribution",
        "nearest distribution",
        "where is the closest store",
        "where is nearest store"
    ]
    return any(k in msg for k in keywords)

def is_closest_store_with_product_intent(message: str) -> bool:
    msg = message.lower()
    keywords = [
        "closest store with",
        "nearest store with",
        "closest shop with",
        "nearest shop with"
    ]
    return any(k in msg for k in keywords)

# -------------------------
# HELPERS
# -------------------------
def extract_nearest_store_limit(message: str) -> int:
    msg = message.lower()

    # explicit number
    match = re.search(r"\b(\d+)\b", msg)
    if match:
        return min(int(match.group(1)), 10)  # safety cap

    # default
    return 1

def extract_product_for_store_search(message: str):
    original = message.strip()

    # 1️⃣ Remove intent phrases (case-insensitive, from original text)
    intent_patterns = [
        r"closest store with",
        r"nearest store with",
        r"closest shop with",
        r"nearest shop with",
        r"closest store",
        r"nearest store",
        r"closest",
        r"nearest",
    ]

    cleaned = original
    for p in intent_patterns:
        cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE).strip()

    # 2️⃣ Category-based detection (cheap & reliable)
    categories = [
        "winter jacket", "winter jackets",
        "jacket", "jackets",
        "coat", "coats",
        "hoodie", "hoodies",
        "sweater", "sweaters",
        "shirt", "shirts",
        "dress", "pants"
    ]

    lowered = cleaned.lower()
    for c in categories:
        if c in lowered:
            return c

    # 3️⃣ Exact product name via capitalized words
    words = cleaned.split()

    product_words = [
        w for w in words
        if w[:1].isupper() and len(w) > 2
    ]

    if len(product_words) >= 3:
        return " ".join(product_words)

    return None

def has_search_filters(message: str) -> bool:
    msg = message.lower()

    filter_keywords = [
        "$", "under", "over", "below", "above", "less than", "more than",
        "small", "medium", "large", "xl", "xxl",
        "jacket", "coat", "hoodie", "sweater", "shirt", "dress", "pants"
    ]

    return any(k in msg for k in filter_keywords)

def looks_like_product_name(text: str) -> bool:
    """
    Heuristic:
    - long enough
    - multiple capitalized words
    - often includes hyphen / model code
    """
    if len(text) < 15:
        return False

    capital_words = sum(1 for w in text.split() if w[:1].isupper())
    return capital_words >= 3

def extract_comparison_products(message: str):
    if " and " not in message.lower():
        return None, None

    left, right = message.split(" and ", 1)
    left, right = left.strip(), right.strip()

    if looks_like_product_name(left) and looks_like_product_name(right):
        return left, right

    return None, None

def extract_price_constraint(message: str):
    msg = message.lower()

    price_match = re.search(r"\$(\d+(\.\d+)?)", msg)
    if not price_match:
        return None, None

    price = float(price_match.group(1))

    if "over" in msg or "above" in msg or "more than" in msg:
        return price, "over"

    if "under" in msg or "below" in msg or "less than" in msg:
        return price, "under"

    # "$4 jackets", "priced $4"
    return price, "exact"

def detect_recipient_gender(message: str):
    msg = message.lower()

    female = [
        "girlfriend", "wife", "mother", "mom",
        "sister", "daughter", "grandmother"
    ]
    male = [
        "boyfriend", "husband", "father", "dad",
        "brother", "son", "grandfather"
    ]

    if any(k in msg for k in female):
        return "Women"

    if any(k in msg for k in male):
        return "Men"

    return None

def detect_gender_department(message: str):
    msg = message.lower()

    women_keywords = ["girlfriend", "wife", "mother", "mom", "sister", "grandmother", "parent"]
    men_keywords = ["boyfriend", "man", "father", "dad", "son", "grandfather", "parent"]

    if any(k in msg for k in women_keywords):
        return "Women"
    if any(k in msg for k in men_keywords):
        return "Men"

    return None


def detect_size(message: str):
    msg = message.lower()
    size_map = {
        "small": "s",
        "medium": "m",
        "large": "l",
        "xl": "xl",
        "xxl": "xxl",
    }
    for k, v in size_map.items():
        if k in msg:
            return v
    return None


def detect_category_keyword(message: str):
    keywords = ["jacket", "coat", "hoodie", "sweater", "shirt", "dress", "pants"]
    for k in keywords:
        if k in message.lower():
            return k
    return None

def get_user(user_id: int) -> dict | None:
    query = """
    SELECT
      id,
      first_name,
      last_name,
      email,
      age,
      gender,
      state,
      street_address,
      postal_code,
      city,
      country,
      latitude,
      longitude,
      traffic_source,
      created_at,
      user_geom
    FROM `bigquery-public-data.thelook_ecommerce.users`
    WHERE id = @user_id
    LIMIT 1
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_id", "INT64", user_id)
        ]
    )

    results = client.query(query, job_config=job_config).result()
    rows = list(results)

    if not rows:
        return None

    return dict(rows[0])

USER_ID_ENV = os.getenv("USER_ID")

if not USER_ID_ENV:
    raise RuntimeError(
        "USER_ID environment variable is not set. "
        "Please define USER_ID in your environment or .env file."
    )

USER_ID = int(USER_ID_ENV)
USER = get_user(USER_ID)

if not USER:
    raise RuntimeError(f"User {USER_ID} not found in database")

def user_has_location(user: dict) -> bool:
    return user.get("latitude") is not None and user.get("longitude") is not None

def find_nearest_stores(user_lat: float, user_lng: float, limit: int = 1):
    query = f"""
    SELECT
      name,
      latitude,
      longitude,
      ST_DISTANCE(
        ST_GEOGPOINT(longitude, latitude),
        ST_GEOGPOINT(@user_lng, @user_lat)
      ) / 1000 AS distance_km
    FROM `bigquery-public-data.thelook_ecommerce.distribution_centers`
    WHERE latitude IS NOT NULL
      AND longitude IS NOT NULL
    ORDER BY distance_km ASC
    LIMIT {limit}
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_lat", "FLOAT64", user_lat),
            bigquery.ScalarQueryParameter("user_lng", "FLOAT64", user_lng),
        ]
    )

    results = client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]

def find_nearest_stores_with_product(
    user_lat: float,
    user_lng: float,
    product_keyword: str,
    limit: int = 5
):
    query = f"""
    SELECT DISTINCT
      dc.name,
      dc.latitude,
      dc.longitude,
      ST_DISTANCE(
        ST_GEOGPOINT(dc.longitude, dc.latitude),
        ST_GEOGPOINT(@user_lng, @user_lat)
      ) / 1000 AS distance_km
    FROM `bigquery-public-data.thelook_ecommerce.distribution_centers` dc
    JOIN `bigquery-public-data.thelook_ecommerce.products` p
      ON dc.id = p.distribution_center_id
    WHERE dc.latitude IS NOT NULL
      AND dc.longitude IS NOT NULL
      AND LOWER(p.name) LIKE @product
    ORDER BY distance_km ASC
    LIMIT {limit}
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("user_lat", "FLOAT64", user_lat),
            bigquery.ScalarQueryParameter("user_lng", "FLOAT64", user_lng),
            bigquery.ScalarQueryParameter(
                "product",
                "STRING",
                f"%{product_keyword.lower()}%"
            ),
        ]
    )

    results = client.query(query, job_config=job_config).result()
    return [dict(row) for row in results]

# -------------------------
# CHAT ENDPOINT
# -------------------------
@app.get("/chat")
def chat(message: str):
    msg = message.lower()

    # 🏪 CLOSEST STORE WITH PRODUCT
    if is_closest_store_with_product_intent(message):
        if not user_has_location(USER):
            return {
                "reply": "I don’t have your location to find nearby stores."
            }

        product = extract_product_for_store_search(message)

        if not product:
            return {
                "reply": (
                    "Which product are you looking for?\n"
                    "You can say something like:\n"
                    "• Closest store with winter jackets\n"
                    "• Closest store with Levi’s Denim Jacket"
                )
            }

        limit = extract_nearest_store_limit(message)

        stores = find_nearest_stores_with_product(
            USER["latitude"],
            USER["longitude"],
            product,
            limit=limit
        )

        if not stores:
            return {
                "reply": (
                    f"I couldn’t find nearby stores carrying {product}."
                )
            }

        lines = []
        for i, s in enumerate(stores, start=1):
            lines.append(
                f"{i}. {s['name']} — {round(s['distance_km'], 2)} km"
            )

        return {
            "reply": (
                f"🏪 Here are the nearest stores with {product}:\n\n"
                + "\n".join(lines)
            )
        }

    # 📍 NEAREST STORES
    if is_closest_store_intent(message):
        if not user_has_location(USER):
            return {
                "reply": "Sorry, I don’t have your location to find nearby stores."
            }

        limit = extract_nearest_store_limit(message)

        stores = find_nearest_stores(
            USER["latitude"],
            USER["longitude"],
            limit=limit
        )

        if not stores:
            return {
                "reply": "I couldn’t find any nearby stores."
            }

        if limit == 1:
            store = stores[0]
            distance = round(store["distance_km"], 2)
            return {
                "reply": (
                    f"📍 The closest store to you is {store['name']}, "
                    f"about {distance} km away."
                )
            }

        # multiple stores
        lines = []
        for i, s in enumerate(stores, start=1):
            lines.append(
                f"{i}. {s['name']} — {round(s['distance_km'], 2)} km"
            )

        return {
            "reply": (
                f"📍 Here are the {len(stores)} nearest stores to you:\n\n"
                + "\n".join(lines)
            )
        }

    # 🛒 SHOW CART
    if is_show_cart_intent(message):
        return {
            "reply": "Here’s what’s currently in your cart 👇",
            "action": "show_cart"
        }

    # 🔍 Extract filters FIRST
    price, price_op = extract_price_constraint(message)
    recipient_gender = detect_recipient_gender(message)
    gift_intent = is_gift_intent(message)
    size = detect_size(message)
    category = detect_category_keyword(message)

    department = None
    # 🎁 If buying for someone else → recipient wins
    if gift_intent and recipient_gender:
        department = recipient_gender

    # 🙋 Otherwise → use user's gender
    elif not gift_intent:
        if USER["gender"] == "M":
            department = "Men"
        elif USER["gender"] == "F":
            department = "Women"
    
    # 🔎 Extract possible product names
    p1, p2 = extract_comparison_products(message)

    # 🆚 COMPARISON MODE (SAFE)
    is_explicit_compare = "compare" in msg or "difference" in msg
    is_implicit_compare = p1 and p2 and not has_search_filters(message)

    if is_explicit_compare or is_implicit_compare:
        if not p1 or not p2:
            return {
                "reply": "Which two products would you like me to compare? Please provide their full names."
            }

        query = """
        SELECT p.id, p.name, p.category, p.brand, p.department, p.retail_price, p.sku, p.distribution_center_id, dc.name AS distribution_name
        FROM `bigquery-public-data.thelook_ecommerce.products` p
        LEFT JOIN `bigquery-public-data.thelook_ecommerce.distribution_centers` dc
        ON p.distribution_center_id = dc.id
        WHERE LOWER(p.name) LIKE @p1
        OR LOWER(p.name) LIKE @p2
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("p1", "STRING", f"%{p1.lower()}%"),
                bigquery.ScalarQueryParameter("p2", "STRING", f"%{p2.lower()}%"),
            ]
        )

        results = client.query(query, job_config=job_config).result()
        products = [dict(row) for row in results]

        if len(products) < 2:
            return {
                "reply": "I couldn’t confidently match both products. Please try clearer product names."
            }

        return {
            "reply": "Here’s a comparison of the two products you mentioned:",
            "products": products
        }

    # 🧱 Build dynamic SQL
    query = """
    SELECT p.id, p.name, p.category, p.brand, p.department, p.retail_price, p.sku, p.distribution_center_id, dc.name AS distribution_name
    FROM `bigquery-public-data.thelook_ecommerce.products` p
    LEFT JOIN `bigquery-public-data.thelook_ecommerce.distribution_centers` dc
    ON p.distribution_center_id = dc.id
    WHERE 1=1
    """
    params = []

    # 💰 Price logic
    if price is not None:
        if price_op == "under":
            query += " AND p.retail_price <= @price"
            params.append(
                bigquery.ScalarQueryParameter("price", "FLOAT64", price)
            )

        elif price_op == "over":
            query += " AND p.retail_price >= @price"
            params.append(
                bigquery.ScalarQueryParameter("price", "FLOAT64", price)
            )

        elif price_op == "exact":
            query += " AND p.retail_price BETWEEN @low AND @high"
            params.extend([
                bigquery.ScalarQueryParameter("low", "FLOAT64", price - 0.01),
                bigquery.ScalarQueryParameter("high", "FLOAT64", price + 0.01),
            ])

    # 👕 Department
    if department:
        query += " AND p.department = @dept"
        params.append(
            bigquery.ScalarQueryParameter("dept", "STRING", department)
        )

    # 📏 Size (from name)
    if size:
        query += " AND LOWER(p.name) LIKE @size"
        params.append(
            bigquery.ScalarQueryParameter("size", "STRING", f"%{size}%")
        )

    # 🧥 Category
    if category:
        query += " AND LOWER(p.name) LIKE @category"
        params.append(
            bigquery.ScalarQueryParameter("category", "STRING", f"%{category}%")
        )

    query += " LIMIT 5"

    job_config = bigquery.QueryJobConfig(query_parameters=params)
    results = client.query(query, job_config=job_config).result()
    products = [dict(row) for row in results]

    # ❌ NO RESULTS
    if not products:
        reasons = []

        if category:
            reasons.append(category + "s")

        if department:
            reasons.append(f"for {department.lower()}")

        if size:
            reasons.append(f"size {size.upper()}")

        if price is not None:
            if price_op == "under":
                reasons.append(f"under ${price}")
            elif price_op == "over":
                reasons.append(f"over ${price}")
            elif price_op == "exact":
                reasons.append(f"priced at ${price}")

        reason_text = " ".join(reasons)

        return {
            "reply": (
                f"Sorry, I couldn’t find any items {reason_text}. "
                f"Would you like to adjust your filters?"
            ),
            "quick_replies": [
                "Increase budget",
                "Remove size filter",
                "Show similar items"
            ]
        }

    # ✅ RESULTS FOUND
    reply_parts = ["Here are"]

    if category:
        reply_parts.append(category + "s")

    if department:
        reply_parts.append(f"for {department.lower()}")

    if size:
        reply_parts.append(f"in size {size.upper()}")

    if price is not None:
        if price_op == "under":
            reply_parts.append(f"under ${price}")
        elif price_op == "over":
            reply_parts.append(f"over ${price}")
        elif price_op == "exact":
            reply_parts.append(f"priced at ${price}")

    reply = " ".join(reply_parts) + "."

    return {
        "reply": reply,
        "products": products
    }

@app.post("/cart")
def show_cart(cart: list = Body(...)):
    if not cart:
        return {
            "reply": "🛒 Your cart is empty.",
            "cart": []
        }

    return {
        "reply": f"🛒 You have {len(cart)} item(s) in your cart:",
        "cart": cart
    }

@app.post("/checkout")
async def checkout(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    cart = data.get("cart")

    if not isinstance(cart, list) or len(cart) == 0:
        raise HTTPException(status_code=400, detail="Cart is empty")

    fake_order_id = int(datetime.utcnow().timestamp())

    return {
        "order_id": fake_order_id,
        "message": "✅ Order placed successfully (demo mode)"
    }

##Enable Billing in gcloud to make real checkout work
# @app.post("/checkout")
# async def checkout(request: Request):
#     data = await request.json()
#     cart = data["cart"]

#     num_of_item = len(cart)

#     # 1️⃣ Insert order
#     order_query = """
#     INSERT INTO `bigquery-public-data.thelook_ecommerce.orders`
#       (user_id, status, gender, created_at, num_of_item)
#     VALUES
#       (@user_id, 'Processing', @gender, CURRENT_TIMESTAMP(), @num)
#     """

#     job_config = bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("user_id", "INT64", USER["id"]),
#             bigquery.ScalarQueryParameter("gender", "STRING", USER["gender"]),
#             bigquery.ScalarQueryParameter("num", "INT64", num_of_item),
#         ]
#     )

#     client.query(order_query, job_config=job_config).result()

#     # 2️⃣ Get order_id
#     order_id = client.query("""
#     SELECT order_id
#     FROM `bigquery-public-data.thelook_ecommerce.orders`
#     WHERE user_id = @user_id
#     ORDER BY created_at DESC
#     LIMIT 1
#     """, job_config=bigquery.QueryJobConfig(
#         query_parameters=[
#             bigquery.ScalarQueryParameter("user_id", "INT64", USER["id"])
#         ]
#     )).result().to_dataframe().iloc[0]["order_id"]

#     # 3️⃣ Loop products
#     for p in cart:
#         # inventory_items
#         inventory_query = """
#         INSERT INTO `bigquery-public-data.thelook_ecommerce.inventory_items`
#           (product_id, created_at, cost, product_retail_price,
#            product_name, product_brand, product_category,
#            product_department, product_sku, product_distribution_center_id)
#         VALUES
#           (@pid, CURRENT_TIMESTAMP(), @cost, @price,
#            @name, @brand, @category, @dept, @sku, @dc)
#         """

#         inventory_config = bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("pid", "INT64", p["id"]),
#                 bigquery.ScalarQueryParameter("cost", "FLOAT64", p.get("cost", 0)),
#                 bigquery.ScalarQueryParameter("price", "FLOAT64", p["retail_price"]),
#                 bigquery.ScalarQueryParameter("name", "STRING", p["name"]),
#                 bigquery.ScalarQueryParameter("brand", "STRING", p["brand"]),
#                 bigquery.ScalarQueryParameter("category", "STRING", p["category"]),
#                 bigquery.ScalarQueryParameter("dept", "STRING", p["department"]),
#                 bigquery.ScalarQueryParameter("sku", "STRING", p["sku"]),
#                 bigquery.ScalarQueryParameter("dc", "INT64", p["distribution_center_id"]),
#             ]
#         )

#         client.query(inventory_query, job_config=inventory_config).result()

#         inventory_id = client.query("""
#           SELECT id
#             FROM `bigquery-public-data.thelook_ecommerce.inventory_items`
#             WHERE product_id = @pid
#             ORDER BY created_at DESC
#             LIMIT 1
#         """, job_config=bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("pid", "INT64", p["id"])
#             ]
#         )).result().to_dataframe().iloc[0]["id"]

#         # order_items
#         order_item_query = """
#         INSERT INTO `bigquery-public-data.thelook_ecommerce.order_items`
#           (order_id, user_id, product_id, inventory_item_id,
#            status, sale_price, created_at)
#         VALUES
#           (@oid, @uid, @pid, @iid,
#            'Processing', @price, CURRENT_TIMESTAMP())
#         """

#         client.query(order_item_query, job_config=bigquery.QueryJobConfig(
#             query_parameters=[
#                 bigquery.ScalarQueryParameter("oid", "INT64", order_id),
#                 bigquery.ScalarQueryParameter("uid", "INT64", USER["id"]),
#                 bigquery.ScalarQueryParameter("pid", "INT64", p["id"]),
#                 bigquery.ScalarQueryParameter("iid", "INT64", inventory_id),
#                 bigquery.ScalarQueryParameter("price", "FLOAT64", p["retail_price"]),
#             ]
#         )).result()

#     return {"order_id": order_id}

@app.get("/health")
def health():
    return {"status": "ok"}