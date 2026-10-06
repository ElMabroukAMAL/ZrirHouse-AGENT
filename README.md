# Zrir House AI Sales Agent

An end-to-end multilingual AI sales agent for **Zrir House**, a Tunisian business. The agent handles customer inquiries, checks product availability, and logs orders automatically to Google Sheets — in **English, French, and Arabic**.

🌐 **Live Demo**: [zrirhouse-ui.onrender.com](https://zrirhouse-ui.onrender.com)  

---

## Features

- 🤖 **Conversational AI Agent** — powered by GPT-OSS 20B via Groq
- 🔍 **Semantic Product Search** — RAG with ChromaDB
- 📦 **Real-time Stock Checking** — automatic availability verification
- 🛒 **Smart Order Management** — collects name, phone, address, products before logging
- 📊 **Google Sheets Integration** — orders saved automatically in real-time
- 🌍 **Trilingual** — full UI and responses in English, French, and Arabic (RTL)
- 🚀 **Production Deployed** — FastAPI backend + Streamlit frontend on Render

---

## Architecture

```
Streamlit UI (Frontend)
      ↓ HTTP POST /chat
FastAPI Backend
      ↓
LangGraph Agent
      ↓
LLaMA 3.3 70B (Groq API)
      ↓ tool_calls
┌─────────────────────────────────────┐
│ search_catalog    → ChromaDB (RAG)  │
│ get_all_products  → products.json   │
│ check_availability→ products.json   │
│ log_order         → Google Sheets   │
└─────────────────────────────────────┘
```

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Logic | LangGraph |
| LLM | LLaMA 3.3 70B (Groq API) |
| Vector Store | ChromaDB |
| Embeddings | ONNX Runtime (DefaultEmbeddingFunction) |
| Backend API | FastAPI + Uvicorn |
| Frontend | Streamlit |
| Order Storage | Google Sheets API (gspread) |
| Deployment | Render (2 separate services) |
| CI/CD | GitHub → Render (auto-deploy) |

---


## Run Locally

### 1. Clone the repo
```bash
git clone https://github.com/ElMabroukAMAL/ZrirHouse-AGENT.git
cd ZrirHouse-AGENT
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file:
```env
GROQ_API_KEY=your_groq_api_key
GOOGLE_PROJECT_ID=your_project_id
GOOGLE_PRIVATE_KEY_ID=your_private_key_id
GOOGLE_PRIVATE_KEY=your_private_key
GOOGLE_CLIENT_EMAIL=your_service_account_email
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_SHEET_ID=your_google_sheet_id
```

### 5. Start the backend
```bash
uvicorn api.main:app --reload
```

### 6. Start the frontend (new terminal)
```bash
streamlit run ui/app.py
```

