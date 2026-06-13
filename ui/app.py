import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/chat")

st.set_page_config(
    page_title="Zrir House Assistant",
    page_icon="🥜",
    layout="centered"
)

# ── Session State FIRST ────────────────────────────────────────────────────────
if "history" not in st.session_state:
    st.session_state.history = []
if "display_messages" not in st.session_state:
    st.session_state.display_messages = []
if "language" not in st.session_state:
    st.session_state.language = "EN"

# ── Translations ───────────────────────────────────────────────────────────────
T = {
    "EN": {
        "tagline": "100% Natural · No Sugar Added · Handcrafted",
        "welcome_title": "Welcome to Zrir House 👋",
        "welcome_text": "Ask me anything about our products — ingredients, sizes, prices, or availability.<br>I can also log your order so our team contacts you directly.",
        "btn_sell": "🥜 What do you sell?",
        "btn_sell_msg": "What do you sell?",
        "btn_avail": "📦 Check availability",
        "btn_avail_msg": "What sizes are available right now?",
        "btn_pistachio": "🔍 Do you have pistachios?",
        "btn_pistachio_msg": "Do you have anything with pistachios?",
        "btn_order": "🛍️ I want to order",
        "btn_order_msg": "I'd like to place an order",
        "chat_placeholder": "Ask about our products...",
        "error": "Sorry, something went wrong. Please try again.",
        "clear": "🗑️ Clear conversation",
        "sidebar_made": "Handcrafted in Tunisia",
        "sidebar_products": "Our Products",
        "sidebar_sizes": "Sizes",
        "responding_in": "Responding in",
    },
    "FR": {
        "tagline": "100% Naturel · Sans Sucre Ajouté · Artisanal",
        "welcome_title": "Bienvenue chez Zrir House 👋",
        "welcome_text": "Posez-moi toutes vos questions sur nos produits — ingrédients, tailles, prix ou disponibilité.<br>Je peux aussi enregistrer votre commande pour que notre équipe vous contacte.",
        "btn_sell": "🥜 Que vendez-vous ?",
        "btn_sell_msg": "Que vendez-vous ?",
        "btn_avail": "📦 Vérifier la disponibilité",
        "btn_avail_msg": "Quelles tailles sont disponibles en ce moment ?",
        "btn_pistachio": "🔍 Avez-vous des pistaches ?",
        "btn_pistachio_msg": "Avez-vous des produits à la pistache ?",
        "btn_order": "🛍️ Je veux commander",
        "btn_order_msg": "Je voudrais passer une commande",
        "chat_placeholder": "Posez votre question...",
        "error": "Désolé, une erreur s'est produite. Veuillez réessayer.",
        "clear": "🗑️ Effacer la conversation",
        "sidebar_made": "Artisanat de Tunisie",
        "sidebar_products": "Nos Produits",
        "sidebar_sizes": "Tailles",
        "responding_in": "Langue de réponse",
    },
    "AR": {
        "tagline": "١٠٠٪ طبيعي · بدون سكر مضاف · صنع يدوي",
        "welcome_title": "مرحباً بكم في زرير هاوس 👋",
        "welcome_text": "اسألني عن منتجاتنا — المكونات، الأحجام، الأسعار أو التوفر.<br>يمكنني أيضاً تسجيل طلبك ليتواصل معك فريقنا.",
        "btn_sell": "🥜 ماذا تبيعون؟",
        "btn_sell_msg": "ماذا تبيعون؟",
        "btn_avail": "📦 التحقق من التوفر",
        "btn_avail_msg": "ما الأحجام المتوفرة الآن؟",
        "btn_pistachio": "🔍 هل لديكم فستق؟",
        "btn_pistachio_msg": "هل لديكم منتجات بالفستق؟",
        "btn_order": "🛍️ أريد الطلب",
        "btn_order_msg": "أريد تقديم طلب",
        "chat_placeholder": "اسأل عن منتجاتنا...",
        "error": "عذراً، حدث خطأ. يرجى المحاولة مرة أخرى.",
        "clear": "🗑️ مسح المحادثة",
        "sidebar_made": "صنع في تونس",
        "sidebar_products": "منتجاتنا",
        "sidebar_sizes": "الأحجام",
        "responding_in": "لغة الرد",
    }
}

lang = st.session_state.language
t = T[lang]

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=Inter:wght@300;400;500&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background-color: #F5ECD7 !important;
    font-family: 'Inter', sans-serif;
}
[data-testid="stMain"] { background-color: #F5ECD7 !important; }

.zrir-header { text-align: center; padding: 2rem 0 0.5rem 0; }
.zrir-logo { font-family: 'Playfair Display', serif; font-size: 3.2rem !important; font-weight: 600; color: #3B5323; letter-spacing: 0.02em; margin: 0; }
.zrir-tagline { font-size: 0.9rem; color: #7A6A52; font-weight: 300; letter-spacing: 0.08em; text-transform: uppercase; margin-top: 0.3rem; }
.zrir-divider { width: 60px; height: 2px; background: #C8860A; margin: 1rem auto; border: none; }

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    background-color: #EDE0C4 !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 0.8rem 1rem !important;
    margin-left: 2rem !important;
    border: 1px solid #D4C4A0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    background-color: #FFFFFF !important;
    border-radius: 16px 16px 16px 4px !important;
    padding: 0.8rem 1rem !important;
    margin-right: 2rem !important;
    border: 1px solid #E8DCC8 !important;
    box-shadow: 0 1px 4px rgba(59, 83, 35, 0.07) !important;
}
[data-testid="stChatInput"] {
    background-color: #FFFFFF !important;
    border: 1.5px solid #C8860A !important;
    border-radius: 24px !important;
}
[data-testid="stSidebar"] { background-color: #3B5323 !important; }
[data-testid="stSidebar"] * { color: #F5ECD7 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(245, 236, 215, 0.2) !important; }
.product-card {
    background: rgba(245, 236, 215, 0.08);
    border-radius: 10px;
    padding: 0.7rem 0.9rem;
    margin-bottom: 0.6rem;
    border-left: 3px solid #C8860A;
}
.product-name { font-weight: 500; font-size: 0.9rem; color: #F5ECD7 !important; }
.product-ingredients { font-size: 0.78rem; color: rgba(245, 236, 215, 0.65) !important; margin-top: 0.15rem; }
[data-testid="stSidebar"] .stButton > button {
    background-color: transparent !important;
    border: 1px solid rgba(245, 236, 215, 0.35) !important;
    color: #F5ECD7 !important;
    border-radius: 20px !important;
    font-size: 0.82rem !important;
    width: 100% !important;
}
.welcome-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 1.4rem 1.6rem;
    margin: 1rem 0 1.5rem 0;
    border: 1px solid #E8DCC8;
    text-align: center;
    box-shadow: 0 2px 8px rgba(59, 83, 35, 0.06);
}
.welcome-title { font-family: 'Playfair Display', serif; font-size: 1.1rem; color: #3B5323; margin-bottom: 0.4rem; }
.welcome-text { font-size: 0.85rem; color: #7A6A52; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="zrir-header">
    <p class="zrir-logo"> Zrir House</p>
    <p class="zrir-tagline">{t['tagline']}</p>
    <hr class="zrir-divider">
</div>
""", unsafe_allow_html=True)

# ── Language Switcher ──────────────────────────────────────────────────────────
lang_options = ["🌐 EN", "🌐 FR", "🌐 AR"]
lang_codes = {"🌐 EN": "EN", "🌐 FR": "FR", "🌐 AR": "AR"}
current_option = {"EN": "🌐 EN", "FR": "🌐 FR", "AR": "🌐 AR"}[lang]

_, _, lang_col = st.columns([4, 1, 1])
with lang_col:
    chosen = st.selectbox(
        "Language",
        options=lang_options,
        index=lang_options.index(current_option),
        label_visibility="collapsed"
    )
    new_lang = lang_codes[chosen]
    if new_lang != st.session_state.language:
        st.session_state.language = new_lang
        st.rerun()



# ── Welcome card ───────────────────────────────────────────────────────────────
if not st.session_state.display_messages:
    st.markdown(f"""
    <div class="welcome-card">
        <p class="welcome-title">{t['welcome_title']}</p>
        <p class="welcome-text">{t['welcome_text']}</p>
    </div>
    """, unsafe_allow_html=True)

    _, col1, col2, _ = st.columns([0.5, 1, 1, 0.5])
    with col1:
        if st.button(t["btn_sell"], use_container_width=True):
            st.session_state._suggestion = t["btn_sell_msg"]
            st.rerun()
        if st.button(t["btn_avail"], use_container_width=True):
            st.session_state._suggestion = t["btn_avail_msg"]
            st.rerun()
    with col2:
        if st.button(t["btn_pistachio"], use_container_width=True):
            st.session_state._suggestion = t["btn_pistachio_msg"]
            st.rerun()
        if st.button(t["btn_order"], use_container_width=True):
            st.session_state._suggestion = t["btn_order_msg"]
            st.rerun()

# ── Handle suggestion click ────────────────────────────────────────────────────
if "_suggestion" in st.session_state:
    prompt = st.session_state.pop("_suggestion")
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    try:
        response = requests.post(API_URL, json={
            "message": prompt,
            "history": st.session_state.history,
            "language": st.session_state.language
        })
        data = response.json()
        agent_reply = data["response"] if "response" in data else t["error"]
        st.session_state.history = data.get("history", st.session_state.history)
    except:
        agent_reply = t["error"]
    st.session_state.display_messages.append({"role": "assistant", "content": agent_reply})
    st.rerun()

# ── Display Chat History ───────────────────────────────────────────────────────
for msg in st.session_state.display_messages:
    with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🥜"):
        st.markdown(msg["content"])

# ── Chat Input ─────────────────────────────────────────────────────────────────
if prompt := st.chat_input(t["chat_placeholder"]):
    st.session_state.display_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑"):
        st.markdown(prompt)
    with st.chat_message("assistant", avatar="🥜"):
        with st.spinner(""):
            try:
                response = requests.post(API_URL, json={
                    "message": prompt,
                    "history": st.session_state.history,
                    "language": st.session_state.language
                })
                data = response.json()
                agent_reply = data["response"] if "response" in data else t["error"]
                st.session_state.history = data.get("history", st.session_state.history)
            except:
                agent_reply = t["error"]
        st.markdown(agent_reply)
        st.session_state.display_messages.append({"role": "assistant", "content": agent_reply})

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<p style="font-family:Playfair Display,serif; font-size:1.4rem; color:#F5ECD7;"> Zrir House</p>', unsafe_allow_html=True)
    st.markdown(f'<p style="font-size:0.8rem; opacity:0.65; margin-top:-0.5rem;">{t["sidebar_made"]}</p>', unsafe_allow_html=True)
    st.divider()
    st.markdown(f'<p style="font-size:0.75rem; letter-spacing:0.08em; text-transform:uppercase; opacity:0.6; margin-bottom:0.7rem;">{t["sidebar_products"]}</p>', unsafe_allow_html=True)
    prod_translations = {
        "EN": [("Zrir Healthy", "Hazelnuts · Almonds · Sesame"), ("Pistachio Zrir", "Pistachios · Almonds")],
        "FR": [("Zrir Healthy", "Noisettes · Amandes · Sésame"), ("Zrir Pistache", "Pistaches · Amandes")],
        "AR": [("زرير صحي", "بندق · لوز · سمسم"), ("زرير الفستق", "فستق · لوز")]
    }
    for name, ingredients in prod_translations[lang]:
        st.markdown(f"""
        <div class="product-card">
            <p class="product-name">{name}</p>
            <p class="product-ingredients">{ingredients}</p>
        </div>
        """, unsafe_allow_html=True)
    st.divider()
    st.markdown(f'<p style="font-size:0.75rem; letter-spacing:0.08em; text-transform:uppercase; opacity:0.6; margin-bottom:0.7rem;">{t["sidebar_sizes"]}</p>', unsafe_allow_html=True)
    sizes = {
        "EN": ["Small", "Medium", "Large"],
        "FR": ["Petit", "Moyen", "Grand"],
        "AR": ["صغير", "وسط", "كبير"]
    }
    weights = ["200غ", "370غ", "750غ"] if lang == "AR" else ["200g", "370g", "750g"]
    sizes_html = "".join([f"{s} — {w} 📦<br>" if lang == "AR" else f"📦 {s} — {w}<br>" for s, w in zip(sizes[lang], weights)])
    st.markdown(f'<p style="font-size:0.83rem; line-height:2.2;">{sizes_html}</p>', unsafe_allow_html=True)
    st.divider()
    if st.button(t["clear"]):
        st.session_state.history = []
        st.session_state.display_messages = []
        st.rerun()
        
        
       