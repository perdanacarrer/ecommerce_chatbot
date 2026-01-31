from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
import os
import re

app = FastAPI()

# ✅ CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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

# -------------------------
# HELPERS
# -------------------------
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

# -------------------------
# CHAT ENDPOINT
# -------------------------
@app.get("/chat")
def chat(message: str):
    msg = message.lower()

    # 🔍 Extract filters FIRST
    price, price_op = extract_price_constraint(message)
    department = detect_gender_department(message)
    size = detect_size(message)
    category = detect_category_keyword(message)
    
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
        SELECT p.name, p.category, p.brand, p.retail_price, dc.name AS distribution_name FROM `bigquery-public-data.thelook_ecommerce.products` p
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
    SELECT p.name, p.category, p.brand, p.retail_price, dc.name AS distribution_name FROM `bigquery-public-data.thelook_ecommerce.products` p
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

@app.get("/health")
def health():
    return {"status": "ok"}