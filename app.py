import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
from datetime import datetime

# --- 1. CONFIG & STYLING (THEME POS MODERN) ---
st.set_page_config(page_title="BRANZ TECH PRO", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    /* Background Utama */
    .stApp { background-color: #f4f7f9; }
    
    /* Kotak Produk (Card) */
    .product-card {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        margin-bottom: 10px;
        border: 1px solid #e1e8ed;
        min-height: 150px;
    }
    
    /* Metrik Dashboard */
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #e1e8ed;
    }

    /* Bagian Keranjang/Total */
    .cart-section {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border-left: 5px solid #0099ff;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    
    /* Tombol Global */
    div.stButton > button {
        border-radius: 8px;
        font-weight: bold;
        transition: 0.3s;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
url = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit?usp=sharing"

def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        data = conn.read(spreadsheet=url, ttl=0)
        return data.dropna(subset=['Produk'])
    except Exception as e:
        st.error(f"Koneksi Database Gagal: {e}")
        return pd.DataFrame()

# --- 3. SESSION STATE (AUTH & CART) ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}

# --- 4. LOGIN SYSTEM ---
if not st.session_state.auth:
    st.title("🛡️ BRANZ TECH SaaS")
    col_l, col_r = st.columns([1, 1])
    with col_l:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Masuk"):
            partners = {"admin": "branz123", "aisyah": "aisyah99", "nikmat": "cireng77"}
            if u in partners and partners[u] == p:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Login Gagal! Cek kembali kredensial Anda.")
    st.stop()

# --- 5. DATA FILTERING ---
full_df = load_data()
df = full_df[full_df['Owner_ID'] == st.session_state.user] if not full_df.empty else full_df

# --- 6. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header("🚀 BRANZ TECH")
    st.write(f"User: **{st.session_state.user.upper()}**")
    st.markdown("---")
    menu = st.radio("Menu Utama", ["📊 Dashboard", "📦 Stok Saya", "📷 Scan Barcode", "🛒 Kasir (POS)"])
    if st.button("Keluar"):
        st.session_state.auth = False
        st.rerun()

# --- 7. MENU LOGIC ---

if menu == "📊 Dashboard":
    st.title(f"📈 Dashboard Analitik: {st.session_state.user.upper()}")
    if not df.empty:
        total_omzet = (df['Stok'] * df['Harga Jual']).sum()
        low_stock = df[df['Stok'] <= 10].shape[0]
        
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Omzet Potensial", f"Rp {total_omzet:,.0f}")
        c2.metric("⚠️ Stok Tipis", f"{low_stock} Produk", delta=f"{low_stock}", delta_color="inverse")
        c3.metric("📦 Total Produk", len(df))
        
        st.markdown("---")
        st.subheader("Visualisasi Stok Terkini")
        st.bar_chart(df.set_index('Produk')['Stok'])

elif menu == "📦 Stok Saya":
    st.title("📦 Inventaris Produk")
    st.dataframe(df, use_container_width=True)

elif menu == "📷 Scan Barcode":
    st.title("📷 Scanner Barcode")
    cam = st.camera_input("Arahkan Barcode ke Kamera")
    if cam:
        data = decode(Image.open(cam))
        if data:
            code = data[0].data.decode('utf-8')
            st.success(f"Ditemukan: {code}")
            item = df[df['Barcode'].astype(str) == code]
            st.write(item if not item.empty else "Produk tidak ada di database.")

elif menu == "🛒 Kasir (POS)":
    st.title("🛒 Terminal Kasir Modern")
    
    col_struk, col_produk = st.columns([1.2, 2])

    with col_produk:
        st.subheader("Pilih Produk")
        p_cols = st.columns(3)
        for i, row in df.iterrows():
            with p_cols[i % 3]:
                st.markdown(f"""
                    <div class="product-card">
                        <p style="font-weight: bold; color: #333;">{row['Produk']}</p>
                        <p style="color: #0099ff; font-size: 18px; font-weight: bold;">Rp {row['Harga Jual']:,.0f}</p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Tambah", key=f"add_{i}"):
                    p_name = row['Produk']
                    st.session_state.cart[p_name] = st.session_state.cart.get(p_name, 0) + 1

    with col_struk:
        st.markdown('<div class="cart-section">', unsafe_allow_html=True)
        st.subheader("Struk Belanja")
        
        grand_total = 0
        if st.session_state.cart:
            for item_name, count in list(st.session_state.cart.items()):
                price = df[df['Produk'] == item_name]['Harga Jual'].values[0]
                subtotal = price * count
                grand_total += subtotal
                st.write(f"**{item_name}** x{count} : Rp {subtotal:,.0f}")
            
            st.write("---")
            st.markdown(f"<h2 style='text-align: right; color: #2ecc71;'>Total: Rp {grand_total:,.0f}</h2>", unsafe_allow_html=True)
            
            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("❌ Reset"):
                st.session_state.cart = {}
                st.rerun()
            
            if c_btn2.button("🔥 CETAK STRUK"):
                # --- PDF GENERATION ---
                pdf = FPDF(format=(80, 150))
                pdf.add_page()
                pdf.set_font("Arial", 'B', 12); pdf.cell(60, 8, "BRANZ TECH PRO", ln=1, align='C')
                pdf.set_font("Arial", '', 8); pdf.cell(60, 5, f"Partner: {st.session_state.user.upper()}", ln=1, align='C')
                pdf.cell(60, 5, datetime.now().strftime("%d/%m/%Y %H:%M"), ln=1, align='C')
                pdf.cell(60, 5, "-"*40, ln=1, align='C')
                
                for item_name, count in st.session_state.cart.items():
                    price = df[df['Produk'] == item_name]['Harga Jual'].values[0]
                    pdf.cell(30, 8, item_name[:15]); pdf.cell(10, 8, str(count)); pdf.cell(20, 8, f"{price*count:,.0f}", ln=1, align='R')
                
                pdf.cell(60, 5, "-"*40, ln=1, align='C')
                pdf.set_font("Arial", 'B', 10); pdf.cell(30, 10, "TOTAL"); pdf.cell(30, 10, f"Rp {grand_total:,.0f}", ln=1, align='R')
                
                fname = f"struk_{datetime.now().strftime('%H%M%S')}.pdf"
                pdf.output(fname)
                with open(fname, "rb") as f:
                    st.download_button("📥 Download Struk", f, file_name=fname)
        else:
            st.info("Keranjang kosong. Pilih produk di sebelah kanan.")
        st.markdown('</div>', unsafe_allow_html=True)
