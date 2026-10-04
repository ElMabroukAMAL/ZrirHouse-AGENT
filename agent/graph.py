from dotenv import load_dotenv
import os
import json
from pathlib import Path

from langchain_groq import ChatGroq
#from langchain_openai import ChatOpenAI

from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from agent.state import AgentState
from agent.tools import search_catalog, get_all_products, check_availability, log_order

load_dotenv()

# ── Load prices from products.json ─────────────────────────────────────────────
PRODUCTS_PATH = Path(__file__).parent.parent / "data" / "products.json"

def build_price_list() -> str:
    with open(PRODUCTS_PATH, "r") as f:
        products = json.load(f)
    lines = []
    for p in products:
        lines.append(
            f"{p['name']} {p['weight_grams']}g = {p['price_dt']}DT / {p['price_usd']}USD"
        )
    return "\n".join(lines)

PRICE_LIST = build_price_list()

# ── LLM Setup ──────────────────────────────────────────────────────────────────
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0
)
"""llm = ChatGroq(
    #model="llama-3.3-70b-versatile",
    model="llama-3.1-8b-instant",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.1,
    max_tokens=512
)llm = ChatOpenAI(
    model="meta-llama/llama-3.3-70b-instruct:free",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
    temperature=0.3,
    max_tokens=512
)"""
tools = [search_catalog, get_all_products, check_availability, log_order]
llm_with_tools = llm.bind_tools(tools)

# ── System Prompt ──────────────────────────────────────────────────────────────
SYSTEM_PROMPT = f"""
You are a sales assistant for Zrir House, a Tunisian handmade nut blends business.
Be warm, friendly, and concise. 
## PRODUCT INFORMATION
- When the customer asks what you sell, asks for the full catalog, or asks to see all products, ALWAYS call get_all_products.
- When the customer asks about a specific product, ingredient, price, or size, use search_catalog.
- When the customer asks whether a specific product/size is in stock, use check_availability.
- Never assume or invent availability. Use the tool results.

You help customers by:
- Answering questions about products, ingredients, sizes, and prices
- Checking product availability
- Taking and logging complete orders

## PRICES (never invent, use only these):
{PRICE_LIST}
Delivery: +9DT always (no exceptions). Total = sum of products + 9DT delivery.
Show calculation: e.g. "2x Medium Healthy (2x31=62DT) + Delivery (9DT) = 71DT"

## ORDER PROCESS (follow strictly):
1. AVAILABILITY: 
When the customer mentions a product and size, ALWAYS call check_availability first.
- If the product is IN STOCK → confirm and proceed to collect remaining info
- If the product is OUT OF STOCK → you MUST present EXACTLY these 2 options to the customer:
  Option 1: Switch to the closest available size (suggest it explicitly with price)
  Option 2: Keep the original size — the order will be prepared in 1-2 extra days
  Use this exact format:
  "The [size] [product] is currently out of stock. Here are your options:
   1️⃣ Switch to [closest available size] — [price] DT / [price] USD (available now)
   2️⃣ Keep the Large size — your order will be ready in 1-2 extra days
   Which option do you prefer?"
  NEVER proceed to log the order until the customer explicitly chooses option 1 or 2.

2. COLLECT before log_order: full name + phone + address + product(s) with size(s).
   Missing any? Ask for it. Never call log_order with incomplete info.

3. LOG: call log_order EXACTLY ONCE when all info is confirmed.
   - Prices are in both DT (Tunisian Dinar) and USD
   - Delivery fee: always add 9 DT to the total (delivery is fixed at 9 DT, free delivery is not offered)
   - ALWAYS show the calculation before giving the total: e.g. "1x Large Pistachio (89 DT / 28.5 USD) + 2x Healthy Medium (2x 31 DT / 10 USD) + Delivery (9 DT) = 160 DT / 51.5 USD total"
   - After logging: show full summary with prices + total. Stop asking for info.
"""

# ── Nodes ──────────────────────────────────────────────────────────────────────

def agent_node(state: AgentState) -> dict:
    """Main node — LLM thinks and decides whether to call a tool or respond."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


def should_continue(state: AgentState) -> str:
    """
    Edge function — decides where to go after the agent node.
    If the LLM called a tool → go to tools node.
    If the LLM gave a final answer → go to END.
    """
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return END


# ── Build the Graph ────────────────────────────────────────────────────────────

tool_node = ToolNode(tools)

graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)

# Set entry point
graph_builder.set_entry_point("agent")

# Add edges
graph_builder.add_conditional_edges(
    "agent",
    should_continue,
    {"tools": "tools", END: END}
)
graph_builder.add_edge("tools", "agent")

# Compile
agent_graph = graph_builder.compile()

print("Agent graph compiled successfully")