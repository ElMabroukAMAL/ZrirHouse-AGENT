import json
import os
from pathlib import Path
from langchain_core.tools import tool
import chromadb
#from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
import datetime
import gspread
from google.oauth2.service_account import Credentials

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
        In stock: {'Yes' if p['stock'] > 0 else 'No'}
        """.strip()

        documents.append(text)
        ids.append(p["id"])
        metadatas.append({
            "name": p["name"],
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

# ── Tool 3: get_all_products ───────────────────────────────────────────────────

@tool
def get_all_products() -> str:
    """
    Return the complete Zrir House product catalog.
    Use this when the customer asks what products are available,
    asks what you sell, wants the full catalog, or asks to see all products.
    """
    products = load_products()

    output = []

    for p in products:
        status = "In stock" if p["stock"] > 0 else "Out of stock"

        # Extract size from the product name
        size = p["name"].split(" - ")[-1]

        output.append(
            f"Product: {p['product_line']}\n"
            f"Size: {size}\n"
            f"Weight: {p['weight_grams']}g\n"
            f"Price: {p['price_dt']} DT / {p['price_usd']} USD\n"
            f"Availability: {status}"        
            )

    return "\n\n".join(output)


# ── Tool 3: check_availability ─────────────────────────────────────────────────

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
        status = "In stock" if p["stock"] > 0 else "Out of stock"
        output.append(
            f"{p['name']} ({p['weight_grams']}g) — "
            f"{p['price_dt']} DT / {p['price_usd']} USD — {status}"
        )

    return "\n".join(output)


# ── Tool 4: log_order ──────────────────────────────────────────────────────────


HEADERS = ["ID", "Name", "Phone", "Address", "Products", "Total (DT)", "Total (USD)", "Date"]

def get_google_sheet():
    """Connect to Google Sheets using environment variables."""

    creds_dict = {
        "type": "service_account",
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY", "").replace("\\n", "\n").strip(),
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": (
            f"https://www.googleapis.com/robot/v1/metadata/x509/"
            f"{os.getenv('GOOGLE_CLIENT_EMAIL')}"
        )
    }

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=scopes
    )

    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        os.getenv("GOOGLE_SHEET_ID")
    )

    return sheet.sheet1


@tool
def log_order(
    customer_name: str,
    phone: str,
    address: str,
    products: str,
    total_dt: str,
    total_usd: str
) -> str:
    """
    Log a customer order directly to Google Sheets.

    Use this when the customer provides their name, phone,
    address and wants to place an order.

    Extract:
    - customer name
    - phone
    - address
    - products with sizes
    - total in DT
    - total in USD

    If some optional information is missing, use 'Not provided'.
    """

    try:
        ws = get_google_sheet()

        # Check whether the sheet already has headers
        existing = ws.get_all_values()


        if not existing or not any(existing[0]):
            ws.append_row(HEADERS)

        # Generate next order ID
        order_id = len(ws.get_all_values())

        # Current date/time
        timestamp = datetime.datetime.now().strftime(
            "%Y-%m-%d %H:%M"
        )

        # Add order to Google Sheets
        ws.append_row([
            order_id,
            customer_name,
            phone,
            address,
            products,
            total_dt,
            total_usd,
            timestamp
        ])

        print(f"Order #{order_id} saved to Google Sheets")

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

        print(f"Google Sheets error: {e}")

        return (
            "Sorry, I couldn't save your order right now. "
            "Please try again later."
        )
# EXCEL
"""from openpyxl import Workbook, load_workbook
ORDERS_PATH = Path(__file__).parent.parent / "data" / "orders.xlsx"
def get_next_id(ws) -> int:
    rows = list(ws.iter_rows(min_row=2, values_only=True))
    return len(rows) + 1

def init_excel():
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
   """
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