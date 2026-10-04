import json
import os
from pathlib import Path
from langchain_core.tools import tool
import chromadb
#from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

# ── Setup ──────────────────────────────────────────────────────────────────────

PRODUCTS_PATH = Path(__file__).parent.parent / "data" / "products.json"

# Embedding function using a free local model
"""embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)"""

embedding_fn = DefaultEmbeddingFunction()

# ChromaDB in-memory client
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection(
    name="zrir_products",
    embedding_function=embedding_fn
)

def load_products() -> list[dict]:
    with open(PRODUCTS_PATH, "r") as f:
        return json.load(f)

def build_catalog():
    """Load products into ChromaDB at startup."""
    products = load_products()

    # Build a rich text document for each product
    # The richer the text, the better the search
    documents = []
    ids = []
    metadatas = []

    for p in products:
        text = f"""
        Product: {p['name']}
        Line: {p['product_line']}
        Ingredients: {', '.join(p['ingredients'])}
        Weight: {p['weight_grams']}g
        Price: {p['price_dt']} DT / {p['price_usd']} USD
        In stock: {p['in_stock']}
        """.strip()

        documents.append(text)
        ids.append(p["id"])
        metadatas.append({
            "name": p["name"],
            "in_stock": str(p["in_stock"]),
            "price_dt": p["price_dt"],
            "price_usd": p["price_usd"],
            "weight_grams": p["weight_grams"],
            "product_line": p["product_line"]
        })

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"Catalog loaded: {len(products)} products indexed")

# Lazy loading — build catalog on first call
_catalog_built = False

def ensure_catalog():
    global _catalog_built
    if not _catalog_built:
        build_catalog()
        _catalog_built = True

# ── Tool 1: search_catalog ─────────────────────────────────────────────────────

@tool
def search_catalog(query: str) -> str:
    """
    Search the Zrir House product catalog using a natural language query.
    Use this when the customer asks about products, ingredients, prices, or sizes.
    """
    ensure_catalog()
    results = collection.query(
        query_texts=[query],
        n_results=2  # return top 3 most relevant products
    )

    if not results["documents"][0]:
        return "No matching products found in the catalog."

    # Format results into a clean readable string for the LLM
    output = []
    for i, doc in enumerate(results["documents"][0]):
        output.append(f"--- Result {i+1} ---\n{doc}")

    return "\n\n".join(output)


# ── Tool 2: check_availability ─────────────────────────────────────────────────

@tool
def check_availability(product_name: str) -> str:
    """
    Check if a specific product is in stock.
    Use this when the customer asks about availability of a specific product.
    The product_name should match the product name or product line from the catalog.
    """
    products = load_products()

    def normalize(s: str) -> str:
        return s.lower().replace("-", " ").replace("  ", " ").strip()

    query_words = normalize(product_name).split()

    # A product matches if ALL words from the query appear in its name/product_line
    matches = [
        p for p in products
        if all(word in normalize(f"{p['name']} {p['product_line']}") for word in query_words)
    ]

    if not matches:
        return f"No product found matching '{product_name}'."

    # Format availability for each match
    output = []
    for p in matches:
        status = "In stock" if p["in_stock"] else "Out of stock"
        output.append(
            f"{p['name']} ({p['weight_grams']}g) — "
            f"{p['price_dt']} DT / {p['price_usd']} USD — {status}"
        )

    return "\n".join(output)


# ── Tool 3: log_order ──────────────────────────────────────────────────────────

import datetime
from openpyxl import Workbook, load_workbook

ORDERS_PATH = Path(__file__).parent.parent / "data" / "orders.xlsx"

HEADERS = ["ID", "Name", "Phone", "Address", "Products", "Total (DT)", "Total (USD)", "Message", "Date"]

def get_next_id(ws) -> int:
    """Get next order ID based on existing rows."""
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    return len(rows) + 1

def init_excel():
    """Create Excel file with headers if it doesn't exist."""
    if not ORDERS_PATH.exists():
        wb = Workbook()
        ws = wb.active
        ws.title = "Orders"
        ws.append(HEADERS)
        # Style header row
        for col in range(1, len(HEADERS) + 1):
            ws.cell(row=1, column=col).font = ws.cell(row=1, column=col).font.copy(bold=True)
        wb.save(ORDERS_PATH)

# Initialize on import
init_excel()

@tool
def log_order(
    customer_name: str,
    phone: str,
    address: str,
    products: str,
    total_dt: str,
    total_usd: str,
    message: str
) -> str:
    """
    Log a customer order to Excel.
    Use this when the customer provides their name and wants to place an order.
    Extract: name, phone, address, products with prices, total in DT and USD.
    If some info is missing, use 'Not provided'.

    Args:
        customer_name: Full name of the customer
        phone: Phone number
        address: Delivery address
        products: Products ordered with prices e.g. "2x Zrir Healthy Medium (31 DT / 10 USD)"
        total_dt: Total price in DT e.g. "62 DT"
        total_usd: Total price in USD e.g. "20 USD"
        message: Original message from the customer
    """
    try:
        wb = load_workbook(ORDERS_PATH)
        ws = wb.active

        order_id = get_next_id(ws)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        ws.append([
            order_id,
            customer_name,
            phone,
            address,
            products,
            total_dt,
            total_usd,
            message,
            timestamp
        ])

        wb.save(ORDERS_PATH)

        return (
            f"Order #{order_id} saved successfully!\n"
            f"Order Summary:\n"
            f"- Name: {customer_name}\n"
            f"- Phone: {phone}\n"
            f"- Address: {address}\n"
            f"- Products: {products}\n"
            f"- Total: {total_dt} / {total_usd}\n\n"
            f"The Zrir House team will contact you soon to confirm your order."
        )

    except Exception as e:
        return f"Sorry, there was an error saving your order. ({str(e)})"
    
#### TEST ###
"""if __name__ == "__main__":
   result = search_catalog.invoke("something with pistachios")
    print(result)
    
    print(check_availability.invoke("Zrir Healthy"))
    print("---")
    print(check_availability.invoke("Pistachio Zrir")) 

    result = log_inquiry.invoke({
        "customer_name": "Sara",
        "message": "I want to order 2 medium Zrir Healthy boxes."
    })
    print(result)"""