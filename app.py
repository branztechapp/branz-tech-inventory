import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from pyzbar.pyzbar import decode
from fpdf import FPDF
import datetime

# --- 1. CONFIG & STYLING ---
st.set_page_config(page_title="BRANZ TECH PRESTIGE", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top right, #1e293b, #0f172a); color: #f8fafc; }
    .stButton>button { border-radius: 10px !important; transition: 0.3s; font-weight: 600 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. DATA ENGINE ---
URL_DB = "https://docs.google.com/spreadsheets/d/18W7as8Lqc6wyci4Q4AWLvszSV-miwkFMiNAi4EH3QMo/edit#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read(spreadsheet=URL_DB, ttl=0)
        data.columns = data.columns.str.strip() 
        df_clean = data.dropna(subset=['Produk']).copy()
        df_clean['Stok'] = pd.to_numeric(df_clean['Stok'], errors='coerce').fillna(0)
        df_clean['Harga Jual'] = pd.to_numeric(df_clean['Harga Jual'], errors='coerce').fillna(0)
        return df_clean
    except Exception as e:
        st.error(f"Koneksi Gagal: {e}")
        return pd.DataFrame()

# --- 3. SESSION STATE ---
if 'auth' not in st.session_state: st.session_state.auth = False
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'df_local' not in st.session_state:
    st.session_state.df_local = load_data()

# --- 4. LOGIN SYSTEM ---
if not st.session_state.auth:
    _, col_center, _ = st.columns([1, 1, 1])
    with col_center:
        st.title("💎 LOGIN")
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password")
        if st.button("AUTHENTICATE", use_container_width=True):
            users = {"admin": "branz123", "aisyah": "aisyah99"}
            if u in users and users[u] == p:
                st.session_state.auth = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Access Denied")
    st.stop()

# --- 5. FUNGSI CETAK PDF ---
def generate_receipt(cart_data, total_price, user):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "BRANZ TECH PRESTIGE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, f"Tanggal: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True, align='C')
    pdf.cell(190, 5, f"Kasir: {user.upper()}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 10, "Produk", 1)
    pdf.cell(30, 10, "Qty", 1)
    pdf.cell(60, 10, "Subtotal", 1, ln=True)
    
    pdf.set_font("Arial", size=12)
    for item, q in cart_data.items():
        price = st.session_state.df_local[st.session_state.df_local['Produk'] == item]['Harga Jual'].values[0]
        pdf.cell(100, 10, str(item), 1)
        pdf.cell(30, 10, str(q), 1)
        pdf.cell(60, 10, f"Rp {price*q:,.0f}", 1, ln=True)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 10, f"TOTAL: Rp {total_price:,.0f}", ln=True, align='R')
    return pdf.output(dest='S').encode('latin-1')

# --- 6. NAVIGATION & MENU ---
df = st.session_state.df_local

with st.sidebar:
    st.header(f"👤 {st.session_state.user.upper()}")
    menu = st.radio("Menu", ["📊 Dashboard", "🛒 Kasir (POS)"])
    if st.button("🔄 Sync Cloud"):
        st.session_state.df_local = load_data()
        st.rerun()

if menu == "🛒 Kasir (POS)":
    st.title("🛒 Kasir & Barcode Scanner")
    
    # Fitur Barcode
    with st.expander("📸 Buka Scanner Barcode"):
        img_file = st.camera_input("Scan Barcode Produk")
        if img_file:
            img = Image.open(img_file)
            decoded_objs = decode(img)
            for obj in decoded_objs:
                barcode_val = obj.data.decode("utf-8")
                st.success(f"Terdeteksi: {barcode_val}")
                # Logika pencarian produk berdasarkan barcode bisa ditambahkan di sini

    col_left, col_right = st.columns([1.5, 1])
    
    with col_left:
        prod_options = [f"{r['Produk']} | Sisa: {int(r['Stok'])}" for _, r in df.iterrows()]
        pick = st.selectbox("Pilih Barang", [""] + prod_options)
        
        if pick:
            name_only = pick.split(" | ")[0]
            current_stock = df[df['Produk'] == name_only]['Stok'].values[0]
            qty = st.number_input("Jumlah", min_value=1, max_value=int(current_stock) if current_stock > 0 else 1, value=1)
            
            if st.button("➕ Tambah Ke Keranjang"):
                st.session_state.cart[name_only] = st.session_state.cart.get(name_only, 0) + qty
                st.session_state.df_local.loc[df['Produk'] == name_only, 'Stok'] -= qty
                st.rerun()

    with col_right:
        st.subheader("📝 Keranjang")
        total_belanja = 0
        for item, q in list(st.session_state.cart.items()):
            price = df[df['Produk'] == item]['Harga Jual'].values[0]
            total_belanja += (price * q)
            st.write(f"**{item}** ({q})")
        
        st.divider()
        st.write(f"### TOTAL: Rp {total_belanja:,.0f}")
        
        if st.button("✅ SELESAIKAN & SIMPAN CLOUD"):
            if st.session_state.cart:
                try:
                    conn.update(spreadsheet=URL_DB, data=st.session_state.df_local)
                    st.success("Data Berhasil Disimpan ke Cloud!")
                    
                    # Siapkan PDF untuk diunduh
                    pdf_data = generate_receipt(st.session_state.cart, total_belanja, st.session_state.user)
                    st.download_button("📥 Download Struk (PDF)", data=pdf_data, file_name=f"Struk_{datetime.datetime.now().strftime('%Y%m%d')}.pdf", mime="application/pdf")
                    
                    st.session_state.cart = {}
                except Exception as e:
                    st.error(f"Gagal Simpan: {e}")

elif menu == "📊 Dashboard":
    st.title("📈 Dashboard")
    st.metric("Total Varian", len(df))
    st.bar_chart(df.set_index('Produk')['Stok'])
