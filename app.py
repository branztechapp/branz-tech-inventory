import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime
import io

# --- 1. CONFIG & ELITE STYLING ---
st.set_page_config(page_title="BRANZ TECH VIP", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .login-box {
        background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(15px);
        padding: 50px; border-radius: 35px; border: 1px solid rgba(255, 255, 255, 0.1);
        max-width: 450px; margin: auto;
    }
    .terminal-card {
        background: rgba(30, 41, 59, 0.4); border-radius: 25px;
        padding: 25px; border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .cart-box {
        background: linear-gradient(145deg, #0ea5e9, #2563eb);
        border-radius: 30px; padding: 30px; color: white;
    }
    .stButton>button { border-radius: 12px !important; font-weight: bold !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

@st.cache_data(ttl=10)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        return conn.read(spreadsheet=url, ttl=0).dropna(subset=['Produk'])
    except: return pd.DataFrame()

# --- 3. RECEIPT GENERATOR (PDF) ---
def generate_receipt(cart_items, total, operator):
    pdf = FPDF(format=(80, 150)) # Format struk thermal 80mm
    pdf.add_page()
    pdf.set_font("Courier", "B", 12)
    pdf.cell(0, 5, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 5, "Elite Digital Solutions", ln=True, align="C")
    pdf.cell(0, 5, "-"*30, ln=True, align="C")
    pdf.cell(0, 5, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.cell(0, 5, f"Op: {operator.upper()}", ln=True)
    pdf.cell(0, 5, "-"*30, ln=True)
    
    for item, qty in cart_items.items():
        price = df[df['Produk'] == item]['Harga Jual'].values[0]
        pdf.cell(0, 5, f"{item[:15]}", ln=True)
        pdf.cell(0, 5, f"   {qty}x Rp{price:,.0f} = Rp{qty*price:,.0f}", ln=True)
    
    pdf.cell(0, 5, "-"*30, ln=True)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(0, 10, f"TOTAL: Rp{total:,.0f}", ln=True, align="R")
    pdf.set_font("Courier", "I", 8)
    pdf.cell(0, 10, "Terima kasih atas kepercayaan Anda", ln=True, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH SYSTEM ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'last_receipt' not in st.session_state: st.session_state.last_receipt = None

if not st.session_state.auth:
    _, center, _ = st.columns([1, 1.8, 1])
    with center:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align: center;'>💎 BRANZ TECH</h2>", unsafe_allow_html=True)
        u = st.text_input("Access ID").lower().strip()
        p = st.text_input("Secret Key", type="password")
        if st.button("UNLOCK", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "ADMIN"], "staff": ["pos123", "KARYAWAN"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. MAIN APP ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.caption(f"User: {st.session_state.user.upper()}")
    st.divider()
    nav = ["🛒 Kasir Digital", "📷 Scan Barcode", "📊 Dashboard", "📦 Inventory"]
    if st.session_state.role != "ADMIN": nav = ["🛒 Kasir Digital", "📷 Scan Barcode"]
    menu = st.radio("MENU", nav)
    if st.button("🔒 LOGOUT"):
        st.session_state.auth = False
        st.rerun()

if menu == "🛒 Kasir Digital":
    st.title("🛒 POS Terminal")
    col_in, col_cart = st.columns([1.5, 1])
    
    with col_in:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        prod_list = df['Produk'].tolist()
        sel_prod = st.selectbox("Pilih Produk", [""] + prod_list)
        qty = st.number_input("Qty", min_value=1, value=1)
        if st.button("➕ TAMBAH KE KERANJANG", use_container_width=True):
            if sel_prod:
                st.session_state.cart[sel_prod] = st.session_state.cart.get(sel_prod, 0) + qty
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_cart:
        st.markdown('<div class="cart-box">', unsafe_allow_html=True)
        st.subheader("Detail Pesanan")
        total = 0
        if not st.session_state.cart:
            st.write("Keranjang kosong.")
        else:
            for item, q in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                total += (price * q)
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{item}** x{q}")
                if c2.button("❌", key=f"del_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.markdown(f"### TOTAL: Rp {total:,.0f}")
            
            if st.button("💎 SELESAIKAN TRANSAKSI", use_container_width=True):
                # Simpan data struk sebelum dihapus
                receipt_data = generate_receipt(st.session_state.cart, total, st.session_state.user)
                st.session_state.last_receipt = receipt_data
                st.session_state.cart = {}
                st.balloons()
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Fitur Cetak Struk Muncul setelah transaksi sukses
        if st.session_state.last_receipt:
            st.write("---")
            st.download_button(
                label="📥 DOWNLOAD STRUK (PDF)",
                data=st.session_state.last_receipt,
                file_name=f"struk_{datetime.now().strftime('%H%M%S')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            if st.button("Transaksi Baru"):
                st.session_state.last_receipt = None
                st.rerun()

elif menu == "📊 Dashboard":
    st.title("💎 Dashboard")
    m1, m2 = st.columns(2)
    m1.metric("OMZET ESTIMASI", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    m2.metric("VARIAN PRODUK", len(df))
    st.area_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("📦 Stok Barang")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner")
    cam = st.camera_input("Scan Barcode")
    if cam:
        data = decode(Image.open(cam))
        if data: st.success(f"Terdeteksi: {data[0].data.decode('utf-8')}")
