import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime # Import modul utama agar tidak bentrok
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

# --- 3. RECEIPT GENERATOR (FIXED NAMEERROR) ---
def generate_receipt(cart_items, total, operator, df_data):
    pdf = FPDF(format=(80, 150))
    pdf.add_page()
    pdf.set_font("Courier", "B", 14)
    pdf.cell(0, 8, "BRANZ TECH", ln=True, align="C")
    pdf.set_font("Courier", "", 9)
    pdf.cell(0, 5, "Elite Digital Solutions", ln=True, align="C")
    pdf.cell(0, 5, "="*25, ln=True, align="C")
    
    # Perbaikan NameError datetime disini
    now_str = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
    
    pdf.set_font("Courier", "", 8)
    pdf.cell(0, 5, f"Tgl: {now_str}", ln=True)
    pdf.cell(0, 5, f"Kasir: {operator.upper()}", ln=True)
    pdf.cell(0, 5, "-"*31, ln=True)
    
    for item, qty in cart_items.items():
        price_row = df_data[df_data['Produk'] == item]['Harga Jual'].values
        price = price_row[0] if len(price_row) > 0 else 0
        subtotal = qty * price
        pdf.set_font("Courier", "B", 8)
        pdf.cell(0, 5, f"{item[:25]}", ln=True)
        pdf.set_font("Courier", "", 8)
        pdf.cell(0, 5, f"  {qty} x {price:,.0f} = Rp {subtotal:,.0f}", ln=True)
    
    pdf.cell(0, 5, "-"*31, ln=True)
    pdf.set_font("Courier", "B", 10)
    pdf.cell(0, 10, f"TOTAL: Rp {total:,.0f}", ln=True, align="R")
    pdf.ln(5)
    pdf.set_font("Courier", "I", 8)
    pdf.cell(0, 5, "Terima Kasih", ln=True, align="C")
    return pdf.output(dest='S').encode('latin-1')

# --- 4. AUTH & SESSION ---
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
        if st.button("UNLOCK SYSTEM", use_container_width=True):
            users = {"admin": ["branz123", "ADMIN"], "aisyah": ["aisyah99", "ADMIN"]}
            if u in users and users[u][0] == p:
                st.session_state.auth, st.session_state.user, st.session_state.role = True, u, users[u][1]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. MAIN APP ---
df = load_data()

with st.sidebar:
    st.markdown(f"### 🛡️ {st.session_state.role}")
    st.caption(f"Operator: {st.session_state.user.upper()}")
    st.divider()
    menu = st.radio("MENU", ["🛒 Kasir Digital", "📷 Scan Barcode", "📊 Dashboard", "📦 Inventory"])
    if st.button("🔒 LOGOUT"):
        st.session_state.auth = False
        st.rerun()

if menu == "🛒 Kasir Digital":
    st.title("🛒 POS Terminal")
    col_in, col_cart = st.columns([1.5, 1])
    
    with col_in:
        st.markdown('<div class="terminal-card">', unsafe_allow_html=True)
        if not df.empty:
            prod_list = df['Produk'].tolist()
            sel_prod = st.selectbox("Pilih Produk", [""] + prod_list)
            qty = st.number_input("Qty", min_value=1, value=1)
            if st.button("➕ TAMBAH KE KERANJANG", use_container_width=True):
                if sel_prod:
                    st.session_state.cart[sel_prod] = st.session_state.cart.get(sel_prod, 0) + qty
                    st.toast(f"{sel_prod} ditambahkan!")
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
                sub = price * q
                total += sub
                c1, c2 = st.columns([4, 1])
                c1.write(f"**{item}** \n{q} x {price:,.0f}")
                if c2.button("❌", key=f"del_{item}"):
                    del st.session_state.cart[item]
                    st.rerun()
            
            st.divider()
            st.markdown(f"### TOTAL: Rp {total:,.0f}")
            
            if st.button("💎 SELESAIKAN & CETAK", use_container_width=True):
                receipt_bytes = generate_receipt(st.session_state.cart, total, st.session_state.user, df)
                st.session_state.last_receipt = receipt_bytes
                st.session_state.cart = {} # Reset keranjang
                st.success("Transaksi Berhasil!")
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.session_state.last_receipt:
            st.download_button(
                label="📥 DOWNLOAD STRUK (PDF)", 
                data=st.session_state.last_receipt, 
                file_name=f"Struk_{datetime.datetime.now().strftime('%H%M%S')}.pdf", 
                mime="application/pdf", 
                use_container_width=True
            )

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner Barcode")
    cam = st.camera_input("Scanner")
    if cam:
        decoded_objs = decode(Image.open(cam))
        if decoded_objs:
            code = decoded_objs[0].data.decode('utf-8')
            st.success(f"Barcode: {code}")
            if 'Barcode' in df.columns:
                match = df[df['Barcode'].astype(str) == code]
                if not match.empty:
                    p_name = match['Produk'].values[0]
                    st.write(f"Produk: **{p_name}**")
                    if st.button(f"Tambah {p_name}"):
                        st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                        st.toast("Berhasil!")
        else:
            st.warning("Barcode tidak terdeteksi.")

elif menu == "📊 Dashboard":
    st.title("Ringkasan Bisnis")
    m1, m2 = st.columns(2)
    m1.metric("Omzet Potensial", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
    m2.metric("Total Produk", len(df))
    st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Inventory":
    st.title("Stok Barang")
    st.dataframe(df, use_container_width=True, hide_index=True)
