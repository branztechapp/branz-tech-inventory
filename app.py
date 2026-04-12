import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIG & VIP PRESTIGE STYLING ---
st.set_page_config(page_title="BRANZ TECH VIP", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #f8fafc; }
    [data-testid="stHeader"] { background: rgba(0,0,0,0) !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #334155; }
    .product-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(10px);
        padding: 15px;
        border-radius: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        text-align: center;
        transition: 0.3s;
        margin-bottom: 15px;
    }
    .product-card:hover { border-color: #38bdf8; transform: translateY(-5px); }
    .cart-section {
        background: linear-gradient(180deg, #0ea5e9 0%, #0284c7 100%);
        padding: 25px;
        border-radius: 25px;
        color: white;
        box-shadow: 0 10px 25px rgba(0, 153, 255, 0.3);
    }
    div.stButton > button {
        border-radius: 12px;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=url, ttl=0).dropna(subset=['Produk'])
    except: return pd.DataFrame()

# INISIALISASI SESSION STATE
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'user' not in st.session_state: st.session_state.user = ""
if 'role' not in st.session_state: st.session_state.role = ""

# --- 3. LOGIN SYSTEM (HARUS DI ATAS SIDEBAR/DATA) ---
if not st.session_state.auth:
    st.title("💎 BRANZ TECH PRESTIGE")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("AUTHENTICATE"):
        users = {
            "admin": ["branz123", "ADMIN"],
            "aisyah": ["aisyah99", "ADMIN"],
            "staff": ["pos123", "KARYAWAN"]
        }
        if u in users and users[u][0] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.session_state.role = users[u][1]
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop() # Stop di sini jika belum login

# --- 4. DATA LOAD ---
full_df = load_data()
df = full_df

# --- 5. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1063/1063231.png", width=80)
    st.markdown(f"### {st.session_state.role}")
    st.caption(f"Operator: {st.session_state.user.upper()}")
    
    if st.session_state.role == "ADMIN":
        menu = st.radio("Navigation", ["📊 Insight", "📦 Inventory", "🛒 Terminal POS"])
    else:
        menu = st.radio("Navigation", ["🛒 Terminal POS", "📷 Scan Barcode"])
        
    if st.button("LOGOUT"):
        st.session_state.auth = False
        st.session_state.user = ""
        st.session_state.role = ""
        st.rerun()

# --- 6. MENU LOGIC ---
if menu == "📊 Insight":
    st.title("💎 Business Intelligence")
    c1, c2, c3 = st.columns(3)
    c1.metric("EST. REVENUE", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    c2.metric("ASSET COUNT", len(df))
    c3.metric("LOW STOCK", len(df[df['Stok'] < 5]))
    st.area_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("📦 Managed Assets")
    st.dataframe(df, use_container_width=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner")
    cam = st.camera_input("Scan")
    if cam:
        data = decode(Image.open(cam))
        if data:
            st.success(f"Ditemukan: {data[0].data.decode('utf-8')}")

elif menu == "🛒 Terminal POS":
    st.title("🛒 Luxury Checkout")
    col_s, col_p = st.columns([1.3, 2])
    with col_p:
        p_cols = st.columns(3)
        for i, row in df.reset_index().iterrows():
            with p_cols[i % 3]:
                img_src = row['Gambar'] if 'Gambar' in row and pd.notnull(row['Gambar']) else "https://via.placeholder.com/150"
                st.markdown(f"""
                    <div class="product-card">
                        <img src="{img_src}" width="100%" style="border-radius:10px; margin-bottom:10px;">
                        <div style="font-weight: bold;">{row['Produk']}</div>
                        <div style="color: #38bdf8;">Rp {row['Harga Jual']:,.0f}</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"SELECT", key=f"pos_{i}"):
                    st.session_state.cart[row['Produk']] = st.session_state.cart.get(row['Produk'], 0) + 1
                    st.rerun()
    with col_s:
        st.markdown('<div class="cart-section">', unsafe_allow_html=True)
        st.title("ORDER")
        total = sum(df[df['Produk'] == k]['Harga Jual'].values[0] * v for k, v in st.session_state.cart.items())
        for k, v in st.session_state.cart.items():
            st.write(f"{k} x{v}")
        st.markdown(f"<h1>Rp {total:,.0f}</h1>", unsafe_allow_html=True)
        if st.button("EXECUTE"):
            st.balloons()
            st.session_state.cart = {}
        st.markdown('</div>', unsafe_allow_html=True)
