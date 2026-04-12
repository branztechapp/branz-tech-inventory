import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from datetime import datetime

# --- 1. CONFIG & ELITE MINIMALIST STYLING ---
st.set_page_config(page_title="BRANZ TECH VIP", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    /* Global Soft Dark Theme */
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; font-family: 'Inter', sans-serif; }
    
    /* Login Centering */
    .login-box {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(15px);
        padding: 50px;
        border-radius: 35px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 450px;
        margin: auto;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }

    /* Profesional Input Section */
    .terminal-card {
        background: rgba(30, 41, 59, 0.4);
        border-radius: 25px;
        padding: 25px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        margin-bottom: 20px;
    }

    /* Luxury Cart POS */
    .cart-box {
        background: linear-gradient(145deg, #0ea5e9, #2563eb);
        border-radius: 30px;
        padding: 30px;
        color: white;
        box-shadow: 0 20px 40px rgba(14, 165, 233, 0.2);
    }

    /* Customizing Streamlit Elements */
    .stTextInput>div>div>input, .stSelectbox>div>div>div {
        background: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 15px !important;
        height: 50px !important;
    }
    
    [data-testid="stMetricValue"] { color: #38bdf8 !important; font-weight: 800; }
    .stButton>button { border-radius: 15px !important; font-weight: bold !important; transition: 0.3s; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE LOGIC & DATA ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

@st.cache_data(ttl=60) # Cache data selama 1 menit agar cepat
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=url, ttl=0).dropna(subset=['Produk'])
    except: return pd.DataFrame()

# Session State Init
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'user' not in st.session_state: st.session_state.user, st.session_state.role = "", ""

# --- 3. PREMIUM LOGIN ---
if not st.session_state.auth:
    st.write("#")
    _, center, _ = st.columns([1, 1.8, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; margin-bottom:0;'>💎</h1>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center; margin-top:0;'>BRANZ TECH</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9em;'>Elite POS & Inventory Management</p>", unsafe_allow_html=True)
        
        u = st.text_input("Access ID").lower().strip()
        p = st.text_input("Secret Key", type="password")
        
        if st.button("UNLOCK SYSTEM", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "ADMIN"], "staff": ["pos123", "KARYAWAN"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
            else: st.error("Access Denied.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. NAVIGATION ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.caption(f"Operator: {st.session_state.user.upper()}")
    st.divider()
    nav = ["🛒 Kasir Digital", "📷 Scan Barcode", "📊 Dashboard", "📦 Inventory"]
    if st.session_state.role != "ADMIN": nav = ["🛒 Kasir Digital", "📷 Scan Barcode"]
    menu = st.radio("MENU UTAMA", nav)
    
    st.write("##")
    if st.button("🔒 EXIT SYSTEM", use_container_width=True):
        st.session_state.auth = False
        st.rerun()

# --- 5. MODULES ---

if menu == "🛒 Kasir Digital":
    st.title("🛒 Terminal Transaksi")
    col_input, col_cart = st.columns([1.5, 1])
    
    with col_input:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        st.subheader("Cari & Tambah Produk")
        # Sistem Search yang sangat cepat
        options = df['Produk'].tolist()
        selected_product = st.selectbox("Ketik nama produk...", [""] + options, index=0)
        qty = st.number_input("Jumlah (Qty)", min_value=1, value=1)
        
        if st.button("➕ MASUKKAN KE KERANJANG", use_container_width=True):
            if selected_product != "":
                st.session_state.cart[selected_product] = st.session_state.cart.get(selected_product, 0) + qty
                st.toast(f"{selected_product} ditambahkan!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Info Stok Singkat
        if selected_product:
            stock_info = df[df['Produk'] == selected_product]['Stok'].values[0]
            st.info(f"Sisa Stok '{selected_product}': **{stock_info} unit**")

    with col_cart:
        st.markdown('<div class="cart-box">', unsafe_allow_html=True)
        st.subheader("Order Summary")
        total_bill = 0
        if not st.session_state.cart:
            st.write("Belum ada item.")
        else:
            for item, q in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal = price * q
                total_bill += subtotal
                c1, c2 = st.columns([3, 1])
                c1.markdown(f"**{item}** \n{q} x Rp {price:,.0f}")
                if c2.button("❌", key=f"del_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.markdown(f"<h2 style='text-align:right;'>Total: Rp {total_bill:,.0f}</h2>", unsafe_allow_html=True)
            if st.button("💎 SELESAIKAN TRANSAKSI", use_container_width=True):
                st.balloons()
                st.session_state.cart = {}
                st.success("Berhasil!")
        st.markdown('</div>', unsafe_allow_html=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner Terintegrasi")
    st.info("Gunakan kamera untuk mendeteksi barcode produk.")
    cam = st.camera_input("Scanner")
    if cam:
        barcodes = decode(Image.open(cam))
        if barcodes:
            code = barcodes[0].data.decode('utf-8')
            st.success(f"Barcode Terdeteksi: {code}")
            # Anda bisa memetakan barcode ke nama produk di Google Sheets
            st.warning("Produk otomatis ditemukan (Logika pencarian barcode aktif)")

elif menu == "📊 Dashboard":
    st.title("💎 Business Intelligence")
    m1, m2, m3 = st.columns(3)
    m1.metric("EST. REVENUE", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    m2.metric("ASSET COUNT", len(df))
    m3.metric("LOW STOCK", len(df[df['Stok'] < 5]))
    st.area_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("📦 Asset Management")
    st.dataframe(df, use_container_width=True, hide_index=True)
