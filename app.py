import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIG & STYLING (EXACT POS MATCH) ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    /* Background Utama Abu-abu Muda agar Kontras */
    .stApp { background-color: #e9ecef; }
    
    /* Header Atas Biru (Seperti Gambar) */
    header[data-testid="stHeader"] {
        background-color: #0099ff !important;
    }
    
    /* Kotak Produk (Card) Putih Bersih */
    .product-card {
        background-color: white;
        padding: 10px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #ddd;
    }
    
    /* Bagian Keranjang Hijau Emerald (Seperti Gambar) */
    .cart-section {
        background-color: #27ae60;
        padding: 20px;
        border-radius: 15px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Tombol Biru Terang untuk Produk */
    div.stButton > button {
        background-color: #0099ff;
        color: white;
        border-radius: 5px;
        border: none;
        width: 100%;
        font-weight: bold;
    }
    
    /* Tombol Bayar (Khusus di Keranjang) */
    .pay-button button {
        background-color: #ffffff !important;
        color: #27ae60 !important;
        font-size: 20px !important;
        height: 3em !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        return pd.DataFrame()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}

# --- 4. LOGIN ---
if not st.session_state.auth:
    st.title("🛡️ BRANZ TECH PRO")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Masuk"):
        partners = {"admin": "branz123", "aisyah": "aisyah99", "nikmat": "cireng77"}
        if u in partners and partners[u] == p:
            st.session_state.auth = True
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- 5. DATA ---
full_df = load_data()
df = full_df[full_df['Owner_ID'] == st.session_state.user] if not full_df.empty else full_df

# --- 6. SIDEBAR ---
with st.sidebar:
    st.title("🚀 BRANZ TECH")
    st.write(f"Active: **{st.session_state.user.upper()}**")
    menu = st.radio("Menu", ["📊 Dashboard", "📦 Stok", "📷 Scan", "🛒 Kasir (POS)"])
    if st.button("Logout"):
        st.session_state.auth = False
        st.rerun()

# --- 7. MENU LOGIC ---

if menu == "📊 Dashboard":
    st.title("📊 Ringkasan Bisnis")
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Omzet Potensial", f"Rp {(df['Stok']*df['Harga Jual']).sum():,.0f}")
        c2.metric("Total Produk", len(df))
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Stok":
    st.title("📦 Daftar Inventaris")
    st.dataframe(df, use_container_width=True)

elif menu == "📷 Scan":
    st.title("📷 Scanner Barcode")
    cam = st.camera_input("Scan")
    if cam:
        data = decode(Image.open(cam))
        if data:
            code = data[0].data.decode('utf-8')
            st.success(f"Barcode: {code}")

elif menu == "🛒 Kasir (POS)":
    # Layout pembagian layar seperti gambar (Struk Kiri, Produk Kanan)
    col_struk, col_produk = st.columns([1.2, 2])

    with col_produk:
        st.markdown("### 🏷️ Daftar Menu")
        p_cols = st.columns(3)
        for i, row in df.reset_index().iterrows():
            with p_cols[i % 3]:
                st.markdown(f"""
                    <div class="product-card">
                        <p style="font-size: 14px; margin-bottom: 2px;">{row['Produk']}</p>
                        <p style="color: #0099ff; font-weight: bold;">Rp {row['Harga Jual']:,.0f}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"➕ Tambah", key=f"add_{i}"):
                    p_name = row['Produk']
                    st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1
                    st.rerun()

    with col_struk:
        st.markdown('<div class="cart-section">', unsafe_allow_html=True)
        st.markdown("### 📑 Detail Pesanan")
        
        grand_total = 0
        if st.session_state.cart:
            for item, qty in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item]['Harga Jual'].values[0]
                subtotal = price * qty
                grand_total += subtotal
                st.markdown(f"**{item}** \n{qty}x — Rp {subtotal:,.0f}")
            
            st.markdown("<hr style='border: 1px white solid;'>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: right;'>Total: Rp {grand_total:,.0f}</h2>", unsafe_allow_html=True)
            
            # Tombol Cetak dengan Style Khusus
            st.markdown('<div class="pay-button">', unsafe_allow_html=True)
            if st.button("🔥 BAYAR & CETAK"):
                # Logika PDF
                pdf = FPDF(format=(80, 150))
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12); pdf.cell(60, 8, "BRANZ TECH PRO", ln=1, align='C')
                pdf.set_font("Arial", '', 8); pdf.cell(60, 5, f"User: {st.session_state.user}", ln=1, align='C')
                pdf.cell(60, 5, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=1, align='C')
                pdf.output("struk.pdf")
                st.success("Struk Siap!")
            st.markdown('</div>', unsafe_allow_html=True)
            
            if st.button("🗑️ Kosongkan"):
                st.session_state.cart = {}
                st.rerun()
        else:
            st.write("Silahkan pilih menu...")
        st.markdown('</div>', unsafe_allow_html=True)
