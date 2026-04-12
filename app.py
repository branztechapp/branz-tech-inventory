import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIG & ULTRA-SOFT PREMIUM STYLING ---
st.set_page_config(page_title="BRANZ TECH VIP", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    /* Global Soft Theme */
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Login Centering & Soft Card */
    .login-box {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(20px);
        padding: 40px;
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 450px;
        margin: auto;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }

    /* Product Cards POS Style */
    .product-card {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 20px;
        padding: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        transition: all 0.3s ease;
        text-align: center;
    }
    .product-card:hover { 
        background: rgba(56, 189, 248, 0.1);
        border-color: #38bdf8;
        transform: translateY(-5px);
    }

    /* Floating Cart POS */
    .cart-box {
        background: linear-gradient(145deg, #0ea5e9, #2563eb);
        border-radius: 25px;
        padding: 25px;
        color: white;
        position: sticky;
        top: 20px;
    }

    /* Softening Inputs */
    .stTextInput>div>div>input {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 12px !important;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricValue"] { color: #38bdf8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE FUNCTIONS ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url, ttl=0).dropna(subset=['Produk'])
        return data
    except Exception: return pd.DataFrame()

# Session State Init
for key in ['auth', 'cart', 'user', 'role']:
    if key not in st.session_state:
        st.session_state[key] = False if key == 'auth' else ""
if 'cart' not in st.session_state or not isinstance(st.session_state.cart, dict):
    st.session_state.cart = {}

# --- 3. SOFT LOGIN INTERFACE ---
if not st.session_state.auth:
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>💎 BRANZ TECH</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8;'>Elite Business Management System</p>", unsafe_allow_html=True)
        u = st.text_input("Access ID")
        p = st.text_input("Secret Key", type="password")
        if st.button("UNLOCK SYSTEM", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "staff": ["pos123", "KARYAWAN"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
            else: st.error("Access Denied.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. MAIN APP ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.caption(f"Active Session: {st.session_state.user.upper()}")
    st.divider()
    nav_options = ["📊 Dashboard", "📦 Inventory", "🛒 Point of Sale", "📷 Scanner"] if st.session_state.role == "ADMIN" else ["🛒 Point of Sale", "📷 Scanner"]
    menu = st.radio("MAIN MENU", nav_options)
    if st.button("🔒 EXIT SYSTEM", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# --- 5. MODULES ---
if menu == "📊 Dashboard":
    st.title("💎 Business Intelligence")
    if not df.empty:
        m1, m2, m3 = st.columns(3)
        m1.metric("POTENTIAL REVENUE", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
        m2.metric("TOTAL ASSETS", len(df))
        m3.metric("STOCK ALERT", len(df[df['Stok'] < 5]))
        st.area_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("📦 Asset Management")
    st.dataframe(df, use_container_width=True)

elif menu == "🛒 Point of Sale":
    st.title("🛒 Premium Terminal")
    left, right = st.columns([1.5, 1])
    
    with left:
        st.subheader("Product Catalogue")
        p_grid = st.columns(3)
        for idx, row in df.reset_index().iterrows():
            with p_grid[idx % 3]:
                img = row['Gambar'] if 'Gambar' in row and pd.notnull(row['Gambar']) else "https://via.placeholder.com/150"
                st.markdown(f"""
                    <div class="product-card">
                        <img src="{img}" width="100%" style="border-radius:15px; margin-bottom:10px; height:120px; object-fit:cover;">
                        <div style="font-weight: 600; font-size: 0.9em;">{row['Produk']}</div>
                        <div style="color: #38bdf8; font-weight: bold;">Rp {row['Harga Jual']:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"ADD", key=f"btn_{idx}", use_container_width=True):
                    st.session_state.cart[row['Produk']] = st.session_state.cart.get(row['Produk'], 0) + 1
                    st.rerun()

    with right:
        st.markdown('<div class="cart-box">', unsafe_allow_html=True)
        st.subheader("Current Order")
        total = 0
        for item, qty in st.session_state.cart.items():
            price = df[df['Produk'] == item]['Harga Jual'].values[0]
            total += (price * qty)
            st.markdown(f"**{item}** x{qty} <span style='float:right;'>Rp {price*qty:,.0f}</span>", unsafe_allow_html=True)
        st.divider()
        st.markdown(f"## Total: Rp {total:,.0f}")
        if st.button("💎 COMPLETE TRANSACTION", use_container_width=True):
            st.balloons()
            st.session_state.cart = {}
        if st.button("CLEAR", use_container_width=True):
            st.session_state.cart = {}
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
